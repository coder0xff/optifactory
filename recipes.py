import json
from collections import defaultdict
from dataclasses import dataclass
from enum import IntEnum

from frozendict import frozendict

# All qunaities are "per minute"

# The speeds of the conveyors in the game
_CONVEYORS = [60, 120, 270, 480]


class Purity(IntEnum):
    """resource node purity levels"""

    IMPURE = 0
    NORMAL = 1
    PURE = 2


# The speeds of the miners in the gamers, major axis is miner version, second axis is purity
_MINERS = [
    [30, 60, 120],  # Mk. 1
    [60, 120, 240],  # Mk. 2
    [120, 240, 480],  # Mk. 3
]

_WATER_EXTRACTOR = 120  # cubic meters per minute

_OIL_EXTRACTORS = [60, 120, 240]  # impure, normal, pure


@dataclass(frozen=True)
class Recipe:
    """a Satisfactory recipe"""

    machine: str
    inputs: dict[str, float]
    outputs: dict[str, float]


with open("recipes.json", "r", encoding="utf-8") as f:
    _RECIPES: dict[str, dict[str, dict[str, float]]] = json.load(f)


with open("loads.json", "r", encoding="utf-8") as f:
    _LOADS: dict[str, float] = json.load(f)


_BY_OUTPUT: dict[str, dict[float, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
_BY_MACHINE: dict[str, dict[str, Recipe]] = defaultdict(dict)
_ALL_PARTS: set[str] = set()
_ALL_RECIPES: dict[str, Recipe] = dict()
_RECIPE_NAMES: dict[Recipe, str] = dict()
_BASE_PARTS: set[str] = set()
_TERMINAL_PARTS: set[str] = set()
_DEFAULT_ENABLEMENT_SET: set[str] = set()

# This is just to keep the global scope cleaner
def _populate_lookups():
    for machine, recipes in _RECIPES.items():
        for recipe_name, recipe in recipes.items():
            _ALL_PARTS.update(recipe["in"].keys())
            _ALL_PARTS.update(recipe["out"].keys())

            for output, amount in recipe["out"].items():
                _BY_OUTPUT[output][amount].append((machine, recipe_name))

            inputs = recipe["in"].copy()
            if machine in _LOADS:
                inputs["MWm"] = inputs.get("MWm", 0) + _LOADS[machine]

            recipe = Recipe(machine, frozendict(inputs), frozendict(recipe["out"]))
            _BY_MACHINE[machine][recipe_name] = recipe
            _ALL_RECIPES[recipe_name] = recipe
            _RECIPE_NAMES[recipe] = recipe_name

    for part in _ALL_PARTS:
        if part not in _BY_OUTPUT or all(not recipe.inputs for recipe in _ALL_RECIPES.values() if part in recipe.outputs):
            _BASE_PARTS.add(part)
        if not any(part in recipe.inputs for recipe in _ALL_RECIPES.values()):
            _TERMINAL_PARTS.add(part)
    _BASE_PARTS.add("Iron Ore")
    _BASE_PARTS.add("Copper Ore")
    _BASE_PARTS.add("Limestone")
    _BASE_PARTS.add("Caterium Ore")
    _BASE_PARTS.add("Coal")
    _BASE_PARTS.add("Water")
    _BASE_PARTS.add("Crude Oil")
    
    for machine, recipes in _BY_MACHINE.items():
        for name, recipe in recipes.items():
            if "MWm" not in recipe.outputs and machine != "Packager":
                _DEFAULT_ENABLEMENT_SET.add(name)

_populate_lookups()


def get_conveyor_rate(speed: int) -> float:
    """Get the conveyor rate for a given speed."""
    return _CONVEYORS[speed]


def get_mining_rate(mark: int, purity: Purity) -> float:
    """Get the mining rate for a given mark and purity."""
    return _MINERS[mark][purity]


def get_water_extraction_rate() -> float:
    """Get the water extraction rate."""
    return _WATER_EXTRACTOR


def get_oil_extraction_rate(purity: Purity) -> float:
    """Get the oil extraction rate for a given purity."""
    return _OIL_EXTRACTORS[purity]


def get_load(machine: str) -> float:
    """Get the load for a given machine."""
    return _LOADS[machine]


def get_all_recipes_by_machine() -> dict[str, dict[str, Recipe]]:
    """Get all recipes by machine."""
    return {machine: recipes.copy() for machine, recipes in _BY_MACHINE.items()}


def get_all_recipes() -> dict[str, Recipe]:
    """Get all recipes."""
    return _ALL_RECIPES.copy()


def get_recipes_for(
    output: str, enablement_set: set[str] | None = None
) -> dict[float, list[tuple[str, Recipe]]]:
    """Get all recipes for a given output."""
    results = defaultdict(list)
    for amount, machine_recipe_name_pairs in _BY_OUTPUT[output].items():
        for machine, recipe_name in machine_recipe_name_pairs:
            if not enablement_set or recipe_name in enablement_set:
                results[amount].append(
                    (recipe_name,
                        Recipe(
                            machine, (r := _RECIPES[machine][recipe_name])["in"], r["out"]
                        )
                    )
                )
    return results


def get_recipe_for(
    output: str, enablement_set: set[str] | None = None
) -> tuple[float, str, Recipe]:
    """Get the highest rate recipe for a given output."""
    amount, recipes = max(
        get_recipes_for(output, enablement_set).items(), key=lambda x: x[0]
    )
    return amount, *recipes[0]


def find_recipe_name(recipe: Recipe) -> str:
    """Find the recipe name in _RECIPES that matches the given recipe."""
    return _RECIPE_NAMES[recipe]


def get_base_parts() -> set[str]:
    """Get the parts that have no recipe to create them."""
    return _BASE_PARTS.copy()


def get_terminal_parts() -> set[str]:
    """Get the parts that have no recipe that consumes them."""
    return _TERMINAL_PARTS.copy()


def get_default_enablement_set() -> set[str]:
    """Get the default enablement set."""
    return _DEFAULT_ENABLEMENT_SET.copy()
