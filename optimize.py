import logging
from collections import defaultdict

from mip import INTEGER, Model, OptimizationStatus, xsum

from recipes import get_all_recipes_by_machine
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
) -> dict[str, float]:
    """Optimize the recipes for a given set of inputs and outputs."""
    part_recipe_matrix = defaultdict(dict)
    economy = economy or get_default_economy()
    for _machine_name, machine_recipes in get_all_recipes_by_machine().items():
        for recipe_name, recipe in machine_recipes.items():
            if enablement_set is not None and recipe_name not in enablement_set:
                continue
            for part, amount in recipe.inputs.items():
                part_recipe_matrix[part][recipe_name] = -amount
            for part, amount in recipe.outputs.items():
                part_recipe_matrix[part][recipe_name] = amount

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

    part_costs = []
    for part, contibutors_dict in part_recipe_matrix.items():
        part_recipe_contributions = [
            amount * recipe_vars[recipe_name]
            for recipe_name, amount in contibutors_dict.items()
        ]
        if len(part_recipe_contributions) == 0:
            continue
        part_count = xsum(part_recipe_contributions)

        if part in inputs:
            part_count += inputs[part]

        if part in outputs:
            model += part_count >= outputs[part]
        else:
            # The part is a cost only if the balance is negative.
            part_cost = model.add_var(
                name=_safe_var_name(f"{part}_cost"), var_type=INTEGER
            )

            constraint = part_cost >= -part_count
            if economy:
                if part in economy:
                    constraint = part_cost >= -part_count * economy[part]
                else:
                    _LOGGER.warning(
                        f"Part {part} not found in the provided economy. Using default value of 1."
                    )
            model += constraint

            part_costs.append(part_cost)

    model.objective = xsum(part_costs)
    model.optimize()

    if model.status != OptimizationStatus.OPTIMAL:
        raise ValueError(f"Optimization failed with status {model.status}")

    return {
        recipe_name: recipe_vars[recipe_name].x
        for recipe_name in recipe_vars.keys()
        if recipe_vars[recipe_name].x > 0
    }
