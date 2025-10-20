import logging
from collections import defaultdict

from recipes import get_all_recipes_by_machine, get_base_parts, get_default_enablement_set, get_all_recipes
from economy import get_default_economy
from lp_solver import solve_lp, SolverResult, SolverStatus

# Variable type constant for LP generation
INTEGER = "INTEGER"

_LOGGER = logging.getLogger("satisgraphery")
_LOGGER.setLevel(logging.DEBUG)


class Variable:
    """Variable metadata for LP model.
    
    Attributes:
        name: variable name
        var_type: INTEGER or CONTINUOUS
        lb: lower bound (default 0)
    """
    def __init__(self, name: str, var_type, lb: float = 0):
        self.name = name
        self.var_type = var_type
        self.lb = lb


class LinExpr:
    """Linear expression holding variable-coefficient pairs and a constant.
    
    Attributes:
        terms: list of (Variable, coefficient) tuples
        constant: constant offset in the expression
    """
    def __init__(self, terms: list[tuple[Variable, float]] = None, constant: float = 0):
        self.terms = terms if terms is not None else []
        self.constant = constant
    
    def mul(self, scalar: float) -> "LinExpr":
        """Multiply all terms and constant by scalar."""
        new_terms = [(var, coef * scalar) for var, coef in self.terms]
        return LinExpr(new_terms, self.constant * scalar)
    
    def add(self, other: "LinExpr") -> "LinExpr":
        """Add another linear expression to this one."""
        new_terms = self.terms + other.terms
        new_constant = self.constant + other.constant
        return LinExpr(new_terms, new_constant)
    
    def sub(self, other: "LinExpr") -> "LinExpr":
        """Subtract another linear expression from this one."""
        return self.add(other.mul(-1))
    
    def greater_or_equal(self, rhs: float):
        """Create constraint: this expression >= rhs."""
        return Constraint(self, rhs)


class Constraint:
    """Constraint: expr >= rhs.
    
    Attributes:
        expr: LinExpr on left side
        rhs: right-hand side value
    """
    def __init__(self, expr: LinExpr, rhs: float):
        self.expr = expr
        self.rhs = rhs


class LPBuilder:
    """Builder for generating CPLEX LP format text.
    
    Tracks variables, constraints, and objective function.
    Generates LP format text via to_lp_text().
    """
    def __init__(self):
        self.variables = []
        self.constraints = []
        self.constraint_names = []
        self.objective = None
    
    def add_var(self, name: str, var_type, lb: float = 0) -> LinExpr:
        """Create new variable and return LinExpr representing it."""
        var = Variable(name, var_type, lb)
        self.variables.append(var)
        return LinExpr([(var, 1.0)], 0)
    
    def add_constraint(self, constraint: Constraint, name: str):
        """Add constraint with given name."""
        self.constraints.append(constraint)
        self.constraint_names.append(name)
    
    def set_objective(self, expr: LinExpr):
        """Set objective function to minimize."""
        self.objective = expr
    
    def _consolidate_terms(self, terms: list[tuple[Variable, float]]) -> dict[str, tuple[Variable, float]]:
        """Consolidate duplicate variables by summing their coefficients."""
        consolidated = {}
        for var, coef in terms:
            if var.name in consolidated:
                _, existing_coef = consolidated[var.name]
                consolidated[var.name] = (var, existing_coef + coef)
            else:
                consolidated[var.name] = (var, coef)
        return consolidated
    
    def _format_expression_line(self, label: str, terms_dict: dict, constant: float = 0, max_line_len: int = 500) -> list[str]:
        """Format expression terms into lines respecting line length limit."""
        lines = []
        current_line = label
        
        for var, coef in terms_dict.values():
            if abs(coef) > 1e-10:  # Skip near-zero coefficients
                if coef >= 0:
                    term = f"  +{coef} {var.name}"
                else:
                    term = f"  {coef} {var.name}"
                
                # Check if adding this term would exceed line length
                if len(current_line) + len(term) > max_line_len and current_line != label:
                    lines.append(current_line)
                    current_line = " " + term  # Continuation lines start with space
                else:
                    current_line += term
        
        # Add constant if non-zero
        if abs(constant) > 1e-10:
            if constant >= 0:
                term = f"  +{constant}"
            else:
                term = f"  {constant}"
            if len(current_line) + len(term) > max_line_len and current_line != label:
                lines.append(current_line)
                current_line = " " + term
            else:
                current_line += term
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def to_lp_text(self) -> str:
        """Generate CPLEX LP format text."""
        lines = []
        lines.append("\\Problem name: ")
        lines.append("")
        lines.append("Minimize")
        
        # Objective function - consolidate and handle line breaks
        if self.objective:
            consolidated = self._consolidate_terms(self.objective.terms)
            obj_lines = self._format_expression_line("OBJROW:", consolidated, self.objective.constant)
            lines.extend(obj_lines)
        else:
            lines.append("OBJROW:")
        
        # Constraints - consolidate and handle line breaks
        lines.append("Subject To")
        for constraint, name in zip(self.constraints, self.constraint_names):
            consolidated = self._consolidate_terms(constraint.expr.terms)
            # Move constant to RHS
            rhs = constraint.rhs - constraint.expr.constant
            constr_lines = self._format_expression_line(f"{name}:", consolidated)
            # Add >= rhs to the last line
            if constr_lines:
                constr_lines[-1] += f" >= {rhs}"
            else:
                constr_lines.append(f"{name}: >= {rhs}")
            lines.extend(constr_lines)
        
        # Bounds (only if non-default)
        lines.append("Bounds")
        for var in self.variables:
            if var.lb != 0:
                lines.append(f"{var.lb} <= {var.name}")
        
        # Integer variables - handle line breaks for long lists
        lines.append("Integers")
        int_vars = [var.name for var in self.variables if var.var_type == INTEGER]
        if int_vars:
            # Break into multiple lines if too long
            current_line = ""
            for var_name in int_vars:
                if len(current_line) + len(var_name) + 1 > 500:
                    lines.append(current_line + " ")
                    current_line = var_name
                else:
                    current_line += (" " if current_line else "") + var_name
            if current_line:
                lines.append(current_line + " ")
        
        lines.append("End")
        return "\n".join(lines)


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


def _create_lp_builder() -> LPBuilder:
    """Create LP builder for generating LP format text.

    Precondition:
        none

    Postcondition:
        returns an LPBuilder instance

    Returns:
        LPBuilder instance
    """
    return LPBuilder()


def _create_recipe_variables(builder: LPBuilder, enablement_set: set[str]) -> dict:
    """Create LP variables for each enabled recipe.

    Precondition:
        builder is an LPBuilder instance
        enablement_set is a set of enabled recipe names

    Postcondition:
        returns dict mapping recipe_name -> LinExpr
        variables are INTEGER type with lower bound 0
        variables are added to the builder

    Args:
        builder: LP builder to add variables to
        enablement_set: set of enabled recipe names

    Returns:
        dict mapping recipe name -> LinExpr
    """
    recipe_vars = {
        recipe_name: builder.add_var(
            name=_safe_var_name(f"{machine_name}_{recipe_name}"), var_type=INTEGER, lb=0
        )
        for machine_name, machine_recipes in get_all_recipes_by_machine().items()
        for recipe_name in machine_recipes.keys()
        if enablement_set is None or recipe_name in enablement_set
    }
    return recipe_vars


def _validate_optimization_succeeded(result: SolverResult, design_power: bool, lp_text: str = None) -> None:
    """Check that optimization succeeded and raise error if not.

    Precondition:
        result contains optimization status
        design_power indicates whether power design was requested
        lp_text is optional LP format text to write on failure

    Postcondition:
        returns None if optimization succeeded
        raises ValueError with helpful message if optimization failed
        writes model.lp file if optimization failed

    Args:
        result: SolverResult from optimization
        design_power: whether power design was enabled
        lp_text: optional LP format text to write to model.lp on failure

    Raises:
        ValueError: if optimization status is not OPTIMAL
    """
    if not result.is_optimal():
        # Write LP text to file for debugging
        if lp_text:
            with open("model.lp", "w", encoding="utf-8") as f:
                f.write(lp_text)
        
        message = f"Optimization failed with status {result.status}"
        if result.status == SolverStatus.INFEASIBLE:
            message = "ERROR: Couldn't design the factory. Make sure that recipes are enabled to produce output parts and all intermediate parts from base parts."
            if design_power:
                message = "ERROR: Couldn't design the factory. Make sure that recipes are enabled to produce power, output parts, and all intermediate parts from base parts.."
        raise ValueError(message)


def _extract_recipe_counts(recipe_vars: dict, result: SolverResult) -> dict[str, float]:
    """Extract recipe counts from solver result.

    Precondition:
        recipe_vars contains LinExpr for each recipe
        result contains solved variable values

    Postcondition:
        returns dict containing only recipes with positive counts
        counts are extracted from result variable values by name

    Args:
        recipe_vars: dict mapping recipe name -> LinExpr
        result: SolverResult with variable values

    Returns:
        dict mapping recipe name -> machine count (positive values only)
    """
    output = {}
    for recipe_name, linexpr in recipe_vars.items():
        # LinExpr should have exactly one term for recipe variables
        assert len(linexpr.terms) == 1, f"Recipe variable should have exactly one term: {recipe_name}"
        var, coef = linexpr.terms[0]
        assert coef == 1.0, f"Recipe variable should have coefficient 1: {recipe_name}"
        
        # Look up variable value in result
        value = result.variable_values.get(var.name, 0)
        if value > 0:
            output[recipe_name] = value
    
    return output


def _compute_part_count(
    part: str,
    contributors_dict: dict[str, float],
    recipe_vars: dict,
    inputs: dict[str, float],
    design_power: bool,
) -> LinExpr:
    """Compute total available amount of a part (production + inputs).

    Precondition:
        part is a material name
        contributors_dict maps recipe names to amounts (neg=input, pos=output)
        recipe_vars maps recipe names to LinExpr
        inputs maps material names to available input amounts
        design_power indicates whether power production is enabled

    Postcondition:
        returns LinExpr for total part availability
        includes recipe contributions and available inputs

    Args:
        part: material name
        contributors_dict: recipe contributions for this part
        recipe_vars: LinExpr for recipes
        inputs: available input materials
        design_power: whether power design is enabled

    Returns:
        LinExpr for total part count
    """
    part_recipe_contributions = [
        recipe_vars[recipe_name].mul(amount)
        for recipe_name, amount in contributors_dict.items()
        if part != "MWm" or design_power or amount <= 0  # No power production when power design is disabled
    ]
    assert len(part_recipe_contributions) > 0, "It should not be in the matrix if it has no contributors."
    
    # Chain .add() to sum all contributions
    result = part_recipe_contributions[0]
    for expr in part_recipe_contributions[1:]:
        result = result.add(expr)
    
    # Add input constant if present
    input_amount = inputs.get(part, 0)
    if input_amount != 0:
        result = result.add(LinExpr([], input_amount))
    
    return result


def _apply_economy_weight(
    weighted_cost: LinExpr,
    part: str,
    economy: dict[str, float] | None,
) -> LinExpr:
    """Apply economy weight to a part cost.

    Precondition:
        weighted_cost is a LinExpr
        part is a material name
        economy is either None or a dict of material values

    Postcondition:
        returns weighted_cost multiplied by economy value if available
        logs warning if part not in economy
        returns original weighted_cost if economy is None

    Args:
        weighted_cost: LinExpr to weight
        part: material name
        economy: optional economy dict

    Returns:
        weighted LinExpr
    """
    if economy:
        if part in economy:
            return weighted_cost.mul(economy[part])
        else:
            _LOGGER.warning(
                "Part %s not found in the provided economy. Using default value of 1.",
                part
            )
    return weighted_cost


def _compute_weighted_part_cost(
    part: str,
    part_count: LinExpr,
    base_parts: set[str],
    design_power: bool,
    input_costs_weight: float,
    power_consumption_weight: float,
    economy: dict[str, float] | None,
    builder: LPBuilder,
    power_sum: LinExpr | None,
) -> tuple[LinExpr | None, LinExpr | None]:
    """Compute weighted cost for a non-output part and update power tracking.

    Precondition:
        part is a material name not in outputs
        part_count is a LinExpr for part availability
        base_parts is the set of base materials
        design_power indicates whether power design is enabled
        weights are non-negative floats
        economy is either None or a dict of material values
        builder is the LPBuilder
        power_sum is current power tracking expression or None

    Postcondition:
        returns (weighted_part_cost, updated_power_sum)
        weighted_part_cost may be None if weight is zero
        adds balance constraint to builder for non-base, non-power parts
        updates power_sum if part is "MWm" and design_power is True

    Args:
        part: material name
        part_count: LinExpr for part availability
        base_parts: set of base material names
        design_power: whether power design is enabled
        input_costs_weight: weight for input costs
        power_consumption_weight: weight for power consumption
        economy: optional economy dict
        builder: LP builder
        power_sum: current power sum tracking or None

    Returns:
        tuple of (weighted_part_cost or None, updated_power_sum or None)
    """
    weighted_part_cost = part_count.mul(-1)
    weighted_part_cost = _apply_economy_weight(weighted_part_cost, part, economy)

    if part == "MWm":
        if design_power:
            power_sum = power_sum.add(part_count) if power_sum is not None else part_count
        if power_consumption_weight > 0:
            weighted_part_cost = weighted_part_cost.mul(power_consumption_weight)
        else:
            weighted_part_cost = None
    elif part in base_parts:
        # Allow base parts to have negative balances
        if input_costs_weight > 0:
            weighted_part_cost = weighted_part_cost.mul(input_costs_weight)
        else:
            weighted_part_cost = None
    else:
        # Force non-base parts to have non-negative balances
        constraint = part_count.greater_or_equal(0)
        builder.add_constraint(constraint, _safe_var_name(f"{part}_balance"))

    return weighted_part_cost, power_sum


def _add_material_balance_constraints(
    builder: LPBuilder,
    part_recipe_matrix: dict[str, dict[str, float]],
    recipe_vars: dict,
    inputs: dict[str, float],
    outputs: dict[str, float],
    economy: dict[str, float] | None,
    design_power: bool,
    input_costs_weight: float,
    power_consumption_weight: float,
    base_parts: set[str],
) -> tuple[list[LinExpr], LinExpr | None]:
    """Add material balance constraints to LP builder for all parts.

    Precondition:
        builder is an LPBuilder with recipe variables added
        part_recipe_matrix maps materials to recipe contributions
        recipe_vars maps recipe names to LinExpr
        inputs maps material names to available amounts
        outputs maps material names to required amounts
        economy is either None or a dict of material values
        design_power indicates whether power design is enabled
        weights are non-negative floats
        base_parts is the set of base material names

    Postcondition:
        material balance constraints are added to builder
        output constraints ensure outputs meet requirements
        cost constraints track input costs
        returns (list of cost LinExpr, power_sum expression or None)

    Args:
        builder: LP builder
        part_recipe_matrix: material -> recipe -> amount
        recipe_vars: recipe -> LinExpr
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
            # Add output constraint: part_count >= outputs[part]
            constraint = part_count.sub(LinExpr([], outputs[part])).greater_or_equal(0)
            builder.add_constraint(constraint, _safe_var_name(f"{part}_output"))
            if part == "MWm":
                power_sum = part_count if power_sum is None else part_count
        else:
            # Handle cost for non-output parts
            part_cost = builder.add_var(
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
                builder,
                power_sum,
            )

            if weighted_part_cost is not None:
                # part_cost >= weighted_part_cost  =>  part_cost - weighted_part_cost >= 0
                constraint = part_cost.sub(weighted_part_cost).greater_or_equal(0)
                builder.add_constraint(constraint, _safe_var_name(f"{part}_cost"))
                part_costs.append(part_cost)

    return part_costs, power_sum


def _set_objective(
    builder: LPBuilder,
    part_costs: list[LinExpr],
    recipe_vars: dict,
    input_costs_weight: float,
    machine_counts_weight: float,
) -> None:
    """Set optimization objective in LP builder.

    Precondition:
        builder has all constraints added
        part_costs is a list of LinExpr cost variables
        recipe_vars maps recipe names to LinExpr
        weights are non-negative floats

    Postcondition:
        builder.objective is set to weighted sum of costs and machine counts

    Args:
        builder: LP builder with constraints
        part_costs: list of cost LinExpr
        recipe_vars: recipe -> LinExpr
        input_costs_weight: weight for input costs
        machine_counts_weight: weight for machine counts
    """
    # Sum all part costs
    objective = LinExpr([], 0)
    for cost in part_costs:
        objective = objective.add(cost)
    objective = objective.mul(input_costs_weight)
    
    # Add machine counts
    machine_sum = LinExpr([], 0)
    for recipe_expr in recipe_vars.values():
        machine_sum = machine_sum.add(recipe_expr)
    objective = objective.add(machine_sum.mul(machine_counts_weight))
    
    builder.set_objective(objective)


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

    builder = _create_lp_builder()
    recipe_vars = _create_recipe_variables(builder, enablement_set)

    part_costs, power_sum = _add_material_balance_constraints(
        builder,
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
        constraint = power_sum.greater_or_equal(0)
        builder.add_constraint(constraint, "power_balance")

    _set_objective(builder, part_costs, recipe_vars, input_costs_weight, machine_counts_weight)

    # Generate LP text and solve
    lp_text = builder.to_lp_text()
    result = solve_lp(lp_text)

    _validate_optimization_succeeded(result, design_power, lp_text)
    return _extract_recipe_counts(recipe_vars, result)
