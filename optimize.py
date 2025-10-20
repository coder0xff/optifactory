import logging
from collections import defaultdict

from mip import INTEGER, Model, OptimizationStatus, xsum

from recipes import get_all_recipes_by_machine, get_base_parts, get_default_enablement_set, get_all_recipes
from economy import get_default_economy

_LOGGER = logging.getLogger("satisgraphery")
_LOGGER.setLevel(logging.DEBUG)


def _safe_var_name(name: str) -> str:
    """Convert a string to a safe MIP solver variable name.

    Precondition:
        name is a non-empty string

    Postcondition:
        returns a string with special characters removed or replaced
        colons, parentheses are removed
        hyphens and spaces are replaced with underscores

    Args:
        name: string to convert to safe variable name

    Returns:
        string safe for use as MIP solver variable name
    """
    return (
        name.replace(":", "")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
        .replace(" ", "_")
    )


def _validate_and_set_defaults(
    enablement_set: set[str] | None,
    economy: dict[str, float] | None,
    outputs: dict[str, float],
    design_power: bool,
) -> tuple[set[str], dict[str, float], bool]:
    """Validate inputs and set defaults for optimization parameters.

    Precondition:
        enablement_set is either None or a set of recipe names
        economy is either None or a dict mapping item names to values
        outputs is a dict mapping material names to required amounts
        design_power is a boolean

    Postcondition:
        returns (validated_enablement_set, validated_economy, final_design_power)
        enablement_set is set to defaults if None
        economy is set to default if None
        design_power is True if "MWm" in outputs

    Args:
        enablement_set: optional set of enabled recipe names
        economy: optional economy dict
        outputs: required outputs
        design_power: whether to design power

    Returns:
        tuple of (enablement_set, economy, design_power) with defaults applied

    Raises:
        ValueError: if enablement_set contains invalid recipe names
    """
    final_enablement = enablement_set or get_default_enablement_set()
    if invalid_recipes := final_enablement - set(get_all_recipes()):
        raise ValueError(f"Enablement set contains invalid recipes: {invalid_recipes}")

    final_design_power = design_power or ("MWm" in outputs)
    final_economy = economy if economy is not None else get_default_economy()

    return final_enablement, final_economy, final_design_power


def _build_part_recipe_matrix(enablement_set: set[str]) -> dict[str, dict[str, float]]:
    """Build a matrix of how recipes produce/consume materials.

    Precondition:
        enablement_set is a set of valid recipe names

    Postcondition:
        returns nested dict where part_recipe_matrix[part][recipe] = amount
        negative amounts represent consumption (inputs)
        positive amounts represent production (outputs)

    Args:
        enablement_set: set of enabled recipe names

    Returns:
        nested dict mapping material -> recipe -> amount (neg=input, pos=output)
    """
    part_recipe_matrix = defaultdict(dict)

    for _machine_name, machine_recipes in get_all_recipes_by_machine().items():
        for recipe_name, recipe in machine_recipes.items():
            if enablement_set is not None and recipe_name not in enablement_set:
                continue
            for part, amount in recipe.inputs.items():
                part_recipe_matrix[part][recipe_name] = -amount
            for part, amount in recipe.outputs.items():
                part_recipe_matrix[part][recipe_name] = amount

    return part_recipe_matrix


def _validate_outputs_are_producible(
    outputs: dict[str, float],
    part_recipe_matrix: dict[str, dict[str, float]]
) -> None:
    """Validate that all requested outputs can be produced by enabled recipes.

    Precondition:
        outputs is a dict mapping material names to required amounts
        part_recipe_matrix is populated with recipe data

    Postcondition:
        returns None if all outputs are producible
        raises ValueError if any outputs are not producible

    Args:
        outputs: required output materials
        part_recipe_matrix: matrix of recipe inputs/outputs

    Raises:
        ValueError: if any output material is not produced by enabled recipes
    """
    if invalid_outputs := set(outputs.keys()) - set(part_recipe_matrix.keys()):
        raise ValueError(f"Outputs contain unrecognized parts: {invalid_outputs}")


def _create_mip_model() -> Model:
    """Create and configure a MIP optimization model.

    Precondition:
        none

    Postcondition:
        returns a MIP Model with verbose=0 (no output)

    Returns:
        configured MIP Model instance
    """
    model = Model()
    model.verbose = 0
    return model


def _create_recipe_variables(model: Model, enablement_set: set[str]) -> dict:
    """Create MIP variables for each enabled recipe.

    Precondition:
        model is a MIP Model instance
        enablement_set is a set of enabled recipe names

    Postcondition:
        returns dict mapping recipe_name -> MIP variable
        variables are INTEGER type with lower bound 0
        variables are added to the model

    Args:
        model: MIP model to add variables to
        enablement_set: set of enabled recipe names

    Returns:
        dict mapping recipe name -> MIP variable
    """
    recipe_vars = {
        recipe_name: model.add_var(
            name=_safe_var_name(f"{machine_name}_{recipe_name}"), var_type=INTEGER, lb=0
        )
        for machine_name, machine_recipes in get_all_recipes_by_machine().items()
        for recipe_name in machine_recipes.keys()
        if enablement_set is None or recipe_name in enablement_set
    }
    return recipe_vars


def _validate_optimization_succeeded(model: Model, design_power: bool) -> None:
    """Check that optimization succeeded and raise error if not.

    Precondition:
        model has been optimized
        design_power indicates whether power design was requested

    Postcondition:
        returns None if optimization succeeded
        raises ValueError with helpful message if optimization failed
        writes model.lp file if optimization failed

    Args:
        model: optimized MIP model
        design_power: whether power design was enabled

    Raises:
        ValueError: if optimization status is not OPTIMAL
    """
    if model.status != OptimizationStatus.OPTIMAL:
        model.write("model.lp")
        message = f"Optimization failed with status {model.status}"
        if model.status == OptimizationStatus.INFEASIBLE:
            message = "ERROR: Couldn't design the factory. Make sure that recipes are enabled to produce output parts and all intermediate parts from base parts."
            if design_power:
                message = "ERROR: Couldn't design the factory. Make sure that recipes are enabled to produce power, output parts, and all intermediate parts from base parts.."
        raise ValueError(message)


def _extract_recipe_counts(recipe_vars: dict) -> dict[str, float]:
    """Extract recipe counts from optimized MIP variables.

    Precondition:
        recipe_vars contains optimized MIP variables
        variables have been solved (have .x attribute)

    Postcondition:
        returns dict containing only recipes with positive counts
        counts are extracted from variable.x

    Args:
        recipe_vars: dict mapping recipe name -> MIP variable

    Returns:
        dict mapping recipe name -> machine count (positive values only)
    """
    return {
        recipe_name: recipe_vars[recipe_name].x
        for recipe_name in recipe_vars.keys()
        if recipe_vars[recipe_name].x > 0
    }


def _compute_part_count(
    part: str,
    contributors_dict: dict[str, float],
    recipe_vars: dict,
    inputs: dict[str, float],
    design_power: bool,
):
    """Compute total available amount of a part (production + inputs).

    Precondition:
        part is a material name
        contributors_dict maps recipe names to amounts (neg=input, pos=output)
        recipe_vars maps recipe names to MIP variables
        inputs maps material names to available input amounts
        design_power indicates whether power production is enabled

    Postcondition:
        returns MIP expression for total part availability
        includes recipe contributions and available inputs

    Args:
        part: material name
        contributors_dict: recipe contributions for this part
        recipe_vars: MIP variables for recipes
        inputs: available input materials
        design_power: whether power design is enabled

    Returns:
        MIP expression for total part count
    """
    part_recipe_contributions = [
        amount * recipe_vars[recipe_name]
        for recipe_name, amount in contributors_dict.items()
        if part != "MWm" or design_power or amount <= 0  # No power production when power design is disabled
    ]
    assert len(part_recipe_contributions) > 0, "It should not be in the matrix if it has no contributors."
    return xsum(part_recipe_contributions) + inputs.get(part, 0)


def _apply_economy_weight(
    weighted_cost,
    part: str,
    economy: dict[str, float] | None,
):
    """Apply economy weight to a part cost.

    Precondition:
        weighted_cost is a MIP expression
        part is a material name
        economy is either None or a dict of material values

    Postcondition:
        returns weighted_cost multiplied by economy value if available
        logs warning if part not in economy
        returns original weighted_cost if economy is None

    Args:
        weighted_cost: MIP expression to weight
        part: material name
        economy: optional economy dict

    Returns:
        weighted MIP expression
    """
    if economy:
        if part in economy:
            return weighted_cost * economy[part]
        else:
            _LOGGER.warning(
                "Part %s not found in the provided economy. Using default value of 1.",
                part
            )
    return weighted_cost


def _compute_weighted_part_cost(
    part: str,
    part_count,
    base_parts: set[str],
    design_power: bool,
    input_costs_weight: float,
    power_consumption_weight: float,
    economy: dict[str, float] | None,
    model: Model,
    power_sum,
) -> tuple:
    """Compute weighted cost for a non-output part and update power tracking.

    Precondition:
        part is a material name not in outputs
        part_count is a MIP expression for part availability
        base_parts is the set of base materials
        design_power indicates whether power design is enabled
        weights are non-negative floats
        economy is either None or a dict of material values
        model is the MIP model
        power_sum is current power tracking expression or None

    Postcondition:
        returns (weighted_part_cost, updated_power_sum)
        weighted_part_cost may be None if weight is zero
        adds balance constraint to model for non-base, non-power parts
        updates power_sum if part is "MWm" and design_power is True

    Args:
        part: material name
        part_count: MIP expression for part availability
        base_parts: set of base material names
        design_power: whether power design is enabled
        input_costs_weight: weight for input costs
        power_consumption_weight: weight for power consumption
        economy: optional economy dict
        model: MIP model
        power_sum: current power sum tracking or None

    Returns:
        tuple of (weighted_part_cost or None, updated_power_sum or None)
    """
    weighted_part_cost = -part_count
    weighted_part_cost = _apply_economy_weight(weighted_part_cost, part, economy)

    if part == "MWm":
        if design_power:
            power_sum = power_sum + part_count if power_sum is not None else part_count
        if power_consumption_weight > 0:
            weighted_part_cost *= power_consumption_weight
        else:
            weighted_part_cost = None
    elif part in base_parts:
        # Allow base parts to have negative balances
        if input_costs_weight > 0:
            weighted_part_cost *= input_costs_weight
        else:
            weighted_part_cost = None
    else:
        # Force non-base parts to have non-negative balances
        model += part_count >= 0

    return weighted_part_cost, power_sum


def _add_material_balance_constraints(
    model: Model,
    part_recipe_matrix: dict[str, dict[str, float]],
    recipe_vars: dict,
    inputs: dict[str, float],
    outputs: dict[str, float],
    economy: dict[str, float] | None,
    design_power: bool,
    input_costs_weight: float,
    power_consumption_weight: float,
    base_parts: set[str],
) -> tuple:
    """Add material balance constraints to MIP model for all parts.

    Precondition:
        model is a MIP Model with recipe variables added
        part_recipe_matrix maps materials to recipe contributions
        recipe_vars maps recipe names to MIP variables
        inputs maps material names to available amounts
        outputs maps material names to required amounts
        economy is either None or a dict of material values
        design_power indicates whether power design is enabled
        weights are non-negative floats
        base_parts is the set of base material names

    Postcondition:
        material balance constraints are added to model
        output constraints ensure outputs meet requirements
        cost constraints track input costs
        returns (list of cost variables, power_sum expression or None)

    Args:
        model: MIP model
        part_recipe_matrix: material -> recipe -> amount
        recipe_vars: recipe -> MIP variable
        inputs: material -> available amount
        outputs: material -> required amount
        economy: optional economy dict
        design_power: whether power design is enabled
        input_costs_weight: weight for input costs
        power_consumption_weight: weight for power consumption
        base_parts: set of base material names

    Returns:
        tuple of (part_costs list, power_sum expression or None)
    """
    power_sum = None
    part_costs = []

    for part, contributors_dict in part_recipe_matrix.items():
        part_count = _compute_part_count(part, contributors_dict, recipe_vars, inputs, design_power)

        if part in outputs:
            # Add output constraint
            model += part_count >= outputs[part], _safe_var_name(f"{part}_output")
            if part == "MWm":
                power_sum = part_count if power_sum is not None else part_count
        else:
            # Handle cost for non-output parts
            part_cost = model.add_var(
                name=_safe_var_name(f"{part}_cost"), var_type=INTEGER
            )

            weighted_part_cost, power_sum = _compute_weighted_part_cost(
                part,
                part_count,
                base_parts,
                design_power,
                input_costs_weight,
                power_consumption_weight,
                economy,
                model,
                power_sum,
            )

            if weighted_part_cost is not None:
                constraint = part_cost >= weighted_part_cost, _safe_var_name(f"{part}_cost")
                model += constraint
                part_costs.append(part_cost)

    return part_costs, power_sum


def _set_objective_and_optimize(
    model: Model,
    part_costs: list,
    recipe_vars: dict,
    input_costs_weight: float,
    machine_counts_weight: float,
) -> None:
    """Set optimization objective and run optimizer.

    Precondition:
        model has all constraints added
        part_costs is a list of MIP cost variables
        recipe_vars maps recipe names to MIP variables
        weights are non-negative floats

    Postcondition:
        model.objective is set to weighted sum of costs and machine counts
        model.optimize() has been called

    Args:
        model: MIP model with constraints
        part_costs: list of cost variables
        recipe_vars: recipe -> MIP variable
        input_costs_weight: weight for input costs
        machine_counts_weight: weight for machine counts
    """
    model.objective = xsum(part_costs) * input_costs_weight + xsum(recipe_vars.values()) * machine_counts_weight
    model.optimize()


def optimize_recipes(
    inputs: dict[str, float],
    outputs: dict[str, float],
    *,
    enablement_set: set[str] | None = None,
    economy: dict[str, float] | None= None,
    input_costs_weight: float = 1.0,
    machine_counts_weight: float = 0.0,
    power_consumption_weight: float = 0.0,
    design_power: bool = False,
) -> dict[str, float]:
    """Optimize recipes to minimize costs while meeting output requirements.

    Precondition:
        inputs is a dict mapping material names to available amounts
        outputs is a dict mapping material names to required amounts
        enablement_set is either None or a valid set of recipe names
        economy is either None or a dict mapping items to values
        weights are non-negative floats
        design_power is a boolean

    Postcondition:
        returns dict mapping recipe names to machine counts
        only recipes with positive counts are included
        satisfies all output requirements
        minimizes objective function based on weights

    Args:
        inputs: available input materials and amounts
        outputs: required output materials and amounts
        enablement_set: optional set of enabled recipe names (None = default)
        economy: optional economy for valuing items (None = default)
        input_costs_weight: weight for input costs in objective
        machine_counts_weight: weight for machine counts in objective
        power_consumption_weight: weight for power consumption in objective
        design_power: whether to design power generation (forced True if MWm in outputs)

    Returns:
        dict mapping recipe name -> number of machines needed

    Raises:
        ValueError: if enablement set is invalid, outputs are unrecognized,
                   or optimization fails (infeasible/unbounded)
    """
    enablement_set, economy, design_power = _validate_and_set_defaults(
        enablement_set, economy, outputs, design_power
    )

    part_recipe_matrix = _build_part_recipe_matrix(enablement_set)
    _validate_outputs_are_producible(outputs, part_recipe_matrix)

    model = _create_mip_model()
    recipe_vars = _create_recipe_variables(model, enablement_set)

    part_costs, power_sum = _add_material_balance_constraints(
        model,
        part_recipe_matrix,
        recipe_vars,
        inputs,
        outputs,
        economy,
        design_power,
        input_costs_weight,
        power_consumption_weight,
        get_base_parts(),
    )

    if design_power:
        # Treat power the same as non-base parts: require non-negative balance
        assert power_sum is not None
        model += power_sum >= 0

    _set_objective_and_optimize(model, part_costs, recipe_vars, input_costs_weight, machine_counts_weight)

    _validate_optimization_succeeded(model, design_power)
    return _extract_recipe_counts(recipe_vars)
