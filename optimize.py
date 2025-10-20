import logging
from collections import defaultdict

from mip import INTEGER, Model, OptimizationStatus, xsum

from recipes import get_all_recipes_by_machine, get_base_parts, get_default_enablement_set, get_all_recipes
from economy import get_default_economy

_LOGGER = logging.getLogger("satisgraphery")
_LOGGER.setLevel(logging.DEBUG)


def _safe_var_name(name: str) -> str:
    return (
        name.replace(":", "")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
        .replace(" ", "_")
    )


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
    """Optimize the recipes for a given set of inputs and outputs.
    
    Args:
        inputs: The known inputs to the factory.
        outputs: The known outputs from the factory.
        enablement_set: The set of recipes to enable.
        economy: The economy of the factory.
        input_costs_weight: The weight of the input costs in the objective function.
        machine_counts_weight: The weight of the machine counts in the objective function.
        power_consumption_weight: The weight of the power consumption in the objective function.
        design_power: Whether to design the power. Forced to True if "MWm" is in the outputs.
    """
    enablement_set = enablement_set or get_default_enablement_set()
    if (invalid_recipes := enablement_set - set(get_all_recipes())):
        raise ValueError(f"Enablement set contains invalid recipes: {invalid_recipes}")

    if "MWm" in outputs:
        design_power = True

    economy = economy if economy is not None else get_default_economy()

    part_recipe_matrix = defaultdict(dict)
        
    for _machine_name, machine_recipes in get_all_recipes_by_machine().items():
        for recipe_name, recipe in machine_recipes.items():
            if enablement_set is not None and recipe_name not in enablement_set:
                continue
            for part, amount in recipe.inputs.items():
                part_recipe_matrix[part][recipe_name] = -amount
            for part, amount in recipe.outputs.items():
                part_recipe_matrix[part][recipe_name] = amount

    if (invalid_outputs := set(outputs.keys()) - set(part_recipe_matrix.keys())):
        raise ValueError(f"Outputs contain unrecognized parts: {invalid_outputs}")

    model = Model()
    model.verbose = 0

    # Add variables for each recipe
    recipe_vars = {
        recipe_name: model.add_var(
            name=_safe_var_name(f"{machine_name}_{recipe_name}"), var_type=INTEGER, lb=0
        )
        for machine_name, machine_recipes in get_all_recipes_by_machine().items()
        for recipe_name in machine_recipes.keys()
        if enablement_set is None or recipe_name in enablement_set
    }

    power_sum = None

    base_parts = get_base_parts()

    part_costs = []
    for part, contibutors_dict in part_recipe_matrix.items():
        part_recipe_contributions = [
            amount * recipe_vars[recipe_name]
            for recipe_name, amount in contibutors_dict.items()
            if part != "MWm" or design_power or amount <= 0  # No power production when power design is disabled
        ]
        assert len(part_recipe_contributions) > 0, "It should not be in the matrix if it has no contributors."
        part_count = xsum(part_recipe_contributions) + inputs.get(part, 0)

        if part in outputs:
            model += part_count >= outputs[part], _safe_var_name(f"{part}_output")
            if part == "MWm":
                power_sum = part_count if power_sum is not None else part_count
        else:
            # The part is a cost only if the balance is negative. (default lb is zero)
            part_cost = model.add_var(
                name=_safe_var_name(f"{part}_cost"), var_type=INTEGER
            )

            weighted_part_cost = -part_count

            if economy:
                if part in economy:
                    weighted_part_cost *= economy[part]
                else:
                    _LOGGER.warning(
                        "Part %s not found in the provided economy. Using default value of 1.",
                        part
                    )

            if part == "MWm":
                if design_power:
                    power_sum = power_sum + part_count if power_sum is not None else part_count
                if power_consumption_weight > 0:
                    weighted_part_cost *= power_consumption_weight
                else:
                    weighted_part_cost = None
            elif part in base_parts:
                # Allow base parts to have negative balances.
                if input_costs_weight > 0:
                    weighted_part_cost *= input_costs_weight
                else:
                    weighted_part_cost = None
            else:
                # Force non-base parts to have non-negative balances.
                model += part_count >= 0

            if weighted_part_cost is not None:
                constraint = part_cost >= weighted_part_cost, _safe_var_name(f"{part}_cost")
                model += constraint
                part_costs.append(part_cost)
                

    if design_power:
        # Basically, treat power the same as we treat a non-base part, a non-negative balance.
        assert power_sum is not None
        model += power_sum >= 0

    model.objective = xsum(part_costs) * input_costs_weight + xsum(recipe_vars.values()) * machine_counts_weight
    model.optimize()

    if model.status != OptimizationStatus.OPTIMAL:
        model.write("model.lp")
        message = f"Optimization failed with status {model.status}"
        if model.status == OptimizationStatus.INFEASIBLE:
            message = "ERROR: Couldn't design the factory. Make sure that recipes are enabled to produce output parts and all intermediate parts from base parts."
            if design_power:
                message = "ERROR: Couldn't design the factory. Make sure that recipes are enabled to produce power, output parts, and all intermediate parts from base parts.."            
        raise ValueError(message)

    return {
        recipe_name: recipe_vars[recipe_name].x
        for recipe_name in recipe_vars.keys()
        if recipe_vars[recipe_name].x > 0
    }
