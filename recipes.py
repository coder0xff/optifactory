import json
from collections import defaultdict
from dataclasses import dataclass
from enum import IntEnum

from frozendict import frozendict

# All qunaities are "per minute"

# The capacities of the conveyors in the game
_CONVEYORS = [60, 120, 270, 480]
# The capacities of the pipelines in the game
_PIPELINES = [300, 600]

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


with open("fluids.json", "r", encoding="utf-8") as f:
    _FLUIDS: dict[str, str] = json.load(f)


_BY_OUTPUT: dict[str, dict[float, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
_BY_MACHINE: dict[str, dict[str, Recipe]] = defaultdict(dict)
_ALL_PARTS: set[str] = set()
_ALL_RECIPES: dict[str, Recipe] = dict()
_RECIPE_NAMES: dict[Recipe, str] = dict()
_BASE_PARTS: set[str] = set()
_TERMINAL_PARTS: set[str] = set()
_DEFAULT_ENABLEMENT_SET: set[str] = set()

def _collect_recipe_parts(recipe_data: dict[str, float]) -> None:
    """Collect all input and output parts from a recipe into _ALL_PARTS.

    Precondition:
        recipe_data contains "in" and "out" keys with dict values
        _ALL_PARTS is a module-level set

    Postcondition:
        _ALL_PARTS is updated with all keys from recipe_data["in"] and recipe_data["out"]

    Args:
        recipe_data: raw recipe dict with "in" and "out" keys
    """
    _ALL_PARTS.update(recipe_data["in"].keys())
    _ALL_PARTS.update(recipe_data["out"].keys())


def _index_recipe_outputs(recipe_data: dict[str, float], machine: str, recipe_name: str) -> None:
    """Add recipe to the _BY_OUTPUT index for each output material.

    Precondition:
        recipe_data contains "out" key with dict mapping material -> amount
        _BY_OUTPUT is a module-level nested defaultdict

    Postcondition:
        _BY_OUTPUT[output][amount] includes (machine, recipe_name) for each output

    Args:
        recipe_data: raw recipe dict with "out" key
        machine: machine type name
        recipe_name: recipe name
    """
    for output, amount in recipe_data["out"].items():
        _BY_OUTPUT[output][amount].append((machine, recipe_name))


def _add_power_consumption(inputs: dict[str, float], machine: str) -> dict[str, float]:
    """Add machine power consumption to recipe inputs.

    Precondition:
        inputs is a dict mapping material -> amount
        machine is a string machine name
        _LOADS is a module-level dict mapping machine -> power consumption

    Postcondition:
        returns new dict with power consumption added if machine has a load
        original inputs dict is not modified

    Args:
        inputs: recipe input materials and amounts
        machine: machine type name

    Returns:
        new dict with power consumption (MWm) added if applicable
    """
    result = inputs.copy()
    if machine in _LOADS:
        result["MWm"] = result.get("MWm", 0) + _LOADS[machine]
    return result


def _create_recipe_object(machine: str, recipe_data: dict[str, float]) -> Recipe:
    """Create a Recipe object with power consumption added to inputs.

    Precondition:
        machine is a string machine name
        recipe_data contains "in" and "out" keys with dict values

    Postcondition:
        returns a Recipe with frozen dicts for inputs/outputs
        inputs include power consumption if machine has a load

    Args:
        machine: machine type name
        recipe_data: raw recipe dict with "in" and "out" keys

    Returns:
        Recipe object with power consumption included
    """
    inputs_with_power = _add_power_consumption(recipe_data["in"], machine)
    return Recipe(machine, frozendict(inputs_with_power), frozendict(recipe_data["out"]))


def _register_recipe(recipe: Recipe, recipe_name: str, machine: str) -> None:
    """Register a recipe in multiple lookup tables.

    Precondition:
        recipe is a Recipe object
        recipe_name is a non-empty string
        machine is a non-empty string
        _BY_MACHINE, _ALL_RECIPES, _RECIPE_NAMES are module-level dicts

    Postcondition:
        recipe is registered in _BY_MACHINE, _ALL_RECIPES, and _RECIPE_NAMES

    Args:
        recipe: Recipe object to register
        recipe_name: name of the recipe
        machine: machine type name
    """
    _BY_MACHINE[machine][recipe_name] = recipe
    _ALL_RECIPES[recipe_name] = recipe
    _RECIPE_NAMES[recipe] = recipe_name


def _is_base_part(part: str) -> bool:
    """Check if a part is a base part (has no recipe to create it).

    Precondition:
        part is a non-empty string
        _BY_OUTPUT and _ALL_RECIPES are populated

    Postcondition:
        returns True if part has no recipes, or only recipes with no inputs

    Args:
        part: material name to check

    Returns:
        True if part is a base material (no recipe creates it from other materials)
    """
    if part not in _BY_OUTPUT:
        return True
    # Check if all recipes that output this part have no inputs
    return all(
        not recipe.inputs
        for recipe in _ALL_RECIPES.values()
        if part in recipe.outputs
    )


def _is_terminal_part(part: str) -> bool:
    """Check if a part is a terminal part (no recipe consumes it).

    Precondition:
        part is a non-empty string
        _ALL_RECIPES is populated

    Postcondition:
        returns True if part is not an input to any recipe

    Args:
        part: material name to check

    Returns:
        True if part is not consumed by any recipe
    """
    return not any(part in recipe.inputs for recipe in _ALL_RECIPES.values())


def _add_hardcoded_base_parts() -> None:
    """Add hardcoded base materials to _BASE_PARTS.

    Precondition:
        _BASE_PARTS is a module-level set

    Postcondition:
        _BASE_PARTS includes all hardcoded base materials (ores, water, oil)
    """
    _BASE_PARTS.add("Iron Ore")
    _BASE_PARTS.add("Copper Ore")
    _BASE_PARTS.add("Limestone")
    _BASE_PARTS.add("Caterium Ore")
    _BASE_PARTS.add("Coal")
    _BASE_PARTS.add("Water")
    _BASE_PARTS.add("Crude Oil")


def _classify_parts() -> None:
    """Classify all parts as base parts and/or terminal parts.

    Precondition:
        _ALL_PARTS, _ALL_RECIPES are populated
        _BASE_PARTS, _TERMINAL_PARTS are module-level sets

    Postcondition:
        _BASE_PARTS contains all base materials (no recipe creates them)
        _TERMINAL_PARTS contains all terminal materials (no recipe consumes them)
        hardcoded base materials are added
    """
    for part in _ALL_PARTS:
        if _is_base_part(part):
            _BASE_PARTS.add(part)
        if _is_terminal_part(part):
            _TERMINAL_PARTS.add(part)
    _add_hardcoded_base_parts()


def _should_enable_recipe_by_default(recipe: Recipe, machine: str) -> bool:
    """Check if a recipe should be enabled by default.

    Precondition:
        recipe is a Recipe object
        machine is a non-empty string

    Postcondition:
        returns True if recipe should be enabled by default

    Args:
        recipe: Recipe to check
        machine: machine type for this recipe

    Returns:
        True if recipe doesn't output MWm and isn't from Packager
    """
    return "MWm" not in recipe.outputs and machine != "Packager"


def _build_default_enablement_set() -> None:
    """Build the set of recipes enabled by default.

    Precondition:
        _BY_MACHINE is populated with all recipes
        _DEFAULT_ENABLEMENT_SET is a module-level set

    Postcondition:
        _DEFAULT_ENABLEMENT_SET contains names of recipes enabled by default
        (excludes MWm producers and Packager recipes)
    """
    for machine, recipes in _BY_MACHINE.items():
        for name, recipe in recipes.items():
            if _should_enable_recipe_by_default(recipe, machine):
                _DEFAULT_ENABLEMENT_SET.add(name)


def _process_single_recipe(machine: str, recipe_name: str, recipe_data: dict) -> None:
    """Process a single recipe: collect parts, index outputs, create and register Recipe.

    Precondition:
        machine is a non-empty string
        recipe_name is a non-empty string
        recipe_data is a dict with "in" and "out" keys

    Postcondition:
        recipe parts are added to _ALL_PARTS
        recipe is indexed in _BY_OUTPUT
        Recipe object is created and registered in multiple lookups

    Args:
        machine: machine type name
        recipe_name: recipe name
        recipe_data: raw recipe dict with "in" and "out" keys
    """
    _collect_recipe_parts(recipe_data)
    _index_recipe_outputs(recipe_data, machine, recipe_name)
    recipe_obj = _create_recipe_object(machine, recipe_data)
    _register_recipe(recipe_obj, recipe_name, machine)


# This is just to keep the global scope cleaner
def _populate_lookups():
    """Initialize all module-level lookup tables from recipe data.

    Precondition:
        _RECIPES is loaded with recipe data from JSON
        _LOADS is loaded with machine power consumption data
        Module-level lookup tables are defined but may be empty

    Postcondition:
        All module-level lookups are populated:
        - _ALL_PARTS: all materials
        - _BY_OUTPUT: recipes indexed by output
        - _BY_MACHINE: recipes indexed by machine
        - _ALL_RECIPES: all recipes by name
        - _RECIPE_NAMES: reverse lookup
        - _BASE_PARTS: materials with no recipe
        - _TERMINAL_PARTS: materials not consumed
        - _DEFAULT_ENABLEMENT_SET: default enabled recipes
    """
    # Process all recipes
    for machine, recipes in _RECIPES.items():
        for recipe_name, recipe_data in recipes.items():
            _process_single_recipe(machine, recipe_name, recipe_data)

    # Classify parts
    _classify_parts()

    # Build default enablement
    _build_default_enablement_set()

_populate_lookups()


def get_conveyor_rate(speed: int) -> float:
    """Get the conveyor belt capacity for a given speed tier.

    Precondition:
        speed is an integer in range [0, 3] (valid conveyor tier)

    Postcondition:
        returns the items/minute capacity for that conveyor tier

    Args:
        speed: conveyor tier (0=Mk.1, 1=Mk.2, 2=Mk.3, 3=Mk.4)

    Returns:
        items per minute capacity of the conveyor belt

    Raises:
        IndexError: if speed is out of valid range
    """
    return _CONVEYORS[speed]


def get_mining_rate(mark: int, purity: Purity) -> float:
    """Get the mining rate for a given miner tier and resource node purity.

    Precondition:
        mark is an integer in range [0, 2] (valid miner tier)
        purity is a Purity enum value (IMPURE=0, NORMAL=1, PURE=2)

    Postcondition:
        returns the items/minute extraction rate

    Args:
        mark: miner tier (0=Mk.1, 1=Mk.2, 2=Mk.3)
        purity: resource node purity level

    Returns:
        items per minute extraction rate

    Raises:
        IndexError: if mark or purity is out of valid range
    """
    return _MINERS[mark][purity]


def get_water_extraction_rate() -> float:
    """Get the water extraction rate for water extractors.

    Precondition:
        none

    Postcondition:
        returns the fixed water extraction rate (120 m³/min)

    Returns:
        cubic meters per minute of water extraction
    """
    return _WATER_EXTRACTOR


def get_oil_extraction_rate(purity: Purity) -> float:
    """Get the oil extraction rate for a given resource node purity.

    Precondition:
        purity is a Purity enum value (IMPURE=0, NORMAL=1, PURE=2)

    Postcondition:
        returns the m³/minute extraction rate for oil

    Args:
        purity: resource node purity level

    Returns:
        cubic meters per minute of oil extraction

    Raises:
        IndexError: if purity is out of valid range
    """
    return _OIL_EXTRACTORS[purity]


def get_load(machine: str) -> float:
    """Get the power consumption for a given machine type.

    Precondition:
        machine is a non-empty string
        _LOADS is populated

    Postcondition:
        returns the power consumption in MW for the machine

    Args:
        machine: machine type name

    Returns:
        power consumption in megawatts per minute (MWm)

    Raises:
        KeyError: if machine is not in _LOADS
    """
    return _LOADS[machine]


def get_all_recipes_by_machine() -> dict[str, dict[str, Recipe]]:
    """Get all recipes grouped by machine type.

    Precondition:
        _BY_MACHINE is populated with recipe data

    Postcondition:
        returns a deep copy of recipes indexed by machine
        modifications to returned dict do not affect _BY_MACHINE

    Returns:
        dict mapping machine name -> dict of (recipe_name -> Recipe)
    """
    return {machine: recipes.copy() for machine, recipes in _BY_MACHINE.items()}


def get_all_recipes() -> dict[str, Recipe]:
    """Get all recipes by name.

    Precondition:
        _ALL_RECIPES is populated with recipe data

    Postcondition:
        returns a shallow copy of all recipes
        modifications to returned dict do not affect _ALL_RECIPES

    Returns:
        dict mapping recipe name -> Recipe object
    """
    return _ALL_RECIPES.copy()


def _is_recipe_enabled(recipe_name: str, enablement_set: set[str] | None) -> bool:
    """Check if a recipe is enabled given an enablement set.

    Precondition:
        recipe_name is a non-empty string
        enablement_set is either None or a set of recipe names

    Postcondition:
        returns True if enablement_set is None or recipe_name is in the set

    Args:
        recipe_name: name of the recipe to check
        enablement_set: set of enabled recipe names, or None to enable all

    Returns:
        True if the recipe should be included
    """
    return not enablement_set or recipe_name in enablement_set


def _create_recipe_from_raw(machine: str, recipe_name: str) -> Recipe:
    """Create a Recipe object from raw JSON data without power consumption.

    Precondition:
        machine is a valid machine name in _RECIPES
        recipe_name is a valid recipe name for that machine
        _RECIPES is populated

    Postcondition:
        returns a Recipe object with inputs and outputs from raw data
        power consumption is NOT added to inputs

    Args:
        machine: machine type name
        recipe_name: recipe name

    Returns:
        Recipe object created from raw JSON data

    Note:
        This differs from _create_recipe_object which adds power consumption.
        Used when we need recipes without power for comparison/lookup.
    """
    raw_recipe = _RECIPES[machine][recipe_name]
    return Recipe(machine, raw_recipe["in"], raw_recipe["out"])


def get_recipes_for(
    output: str, enablement_set: set[str] | None = None
) -> dict[float, list[tuple[str, Recipe]]]:
    """Get all recipes that produce a given output material.

    Precondition:
        output is a non-empty string
        _BY_OUTPUT and _RECIPES are populated
        enablement_set is either None or a set of recipe names

    Postcondition:
        returns dict mapping output amounts to lists of (recipe_name, Recipe) tuples
        only includes recipes in enablement_set (if provided)
        recipes are created without power consumption in inputs

    Args:
        output: material name to find recipes for
        enablement_set: optional set of enabled recipe names (None = all enabled)

    Returns:
        dict mapping output amount -> list of (recipe_name, Recipe) tuples
        grouped by how much of the output they produce
    """
    results = defaultdict(list)
    for amount, machine_recipe_name_pairs in _BY_OUTPUT[output].items():
        for machine, recipe_name in machine_recipe_name_pairs:
            if _is_recipe_enabled(recipe_name, enablement_set):
                recipe = _create_recipe_from_raw(machine, recipe_name)
                results[amount].append((recipe_name, recipe))
    return results


def get_recipe_for(
    output: str, enablement_set: set[str] | None = None
) -> tuple[float, str, Recipe]:
    """Get the highest production rate recipe for a given output material.

    Precondition:
        output is a non-empty string representing a valid material
        enablement_set is either None or a set of recipe names
        at least one recipe exists that produces the output

    Postcondition:
        returns tuple of (production_rate, recipe_name, Recipe)
        the recipe has the highest production rate among enabled recipes

    Args:
        output: material name to find recipe for
        enablement_set: optional set of enabled recipe names (None = all enabled)

    Returns:
        tuple of (amount per minute, recipe_name, Recipe object)

    Raises:
        ValueError: if no recipes produce the output
    """
    amount, recipes = max(
        get_recipes_for(output, enablement_set).items(), key=lambda x: x[0]
    )
    return amount, *recipes[0]


def find_recipe_name(recipe: Recipe) -> str:
    """Find the name of a given Recipe object.

    Precondition:
        recipe is a Recipe object that exists in _RECIPE_NAMES
        _RECIPE_NAMES is populated

    Postcondition:
        returns the string name of the recipe

    Args:
        recipe: Recipe object to look up

    Returns:
        name of the recipe as a string

    Raises:
        KeyError: if recipe is not in _RECIPE_NAMES
    """
    return _RECIPE_NAMES[recipe]


def get_base_parts() -> set[str]:
    """Get all base materials (materials with no crafting recipe).

    Precondition:
        _BASE_PARTS is populated with base material names

    Postcondition:
        returns a copy of base parts set
        modifications to returned set do not affect _BASE_PARTS

    Returns:
        set of base material names (ores, water, oil, etc.)
    """
    return _BASE_PARTS.copy()


def get_terminal_parts() -> set[str]:
    """Get all terminal materials (materials not consumed by any recipe).

    Precondition:
        _TERMINAL_PARTS is populated with terminal material names

    Postcondition:
        returns a copy of terminal parts set
        modifications to returned set do not affect _TERMINAL_PARTS

    Returns:
        set of terminal material names (end products)
    """
    return _TERMINAL_PARTS.copy()


def get_default_enablement_set() -> set[str]:
    """Get the default set of enabled recipes.

    Precondition:
        _DEFAULT_ENABLEMENT_SET is populated with recipe names

    Postcondition:
        returns a copy of default enabled recipes
        modifications to returned set do not affect _DEFAULT_ENABLEMENT_SET

    Returns:
        set of recipe names that should be enabled by default
        (excludes power generators and packager recipes)
    """
    return _DEFAULT_ENABLEMENT_SET.copy()


def get_fluids() -> list[str]:
    """Get all fluid material names.

    Precondition:
        _FLUIDS is populated with fluid names and colors

    Postcondition:
        returns a list of all fluid names

    Returns:
        list of fluid material names (water, oil, etc.)
    """
    return list(_FLUIDS.keys())


def get_fluid_color(fluid: str) -> str:
    """Get the hex color code for a given fluid.

    Precondition:
        fluid is a non-empty string
        _FLUIDS is populated with fluid colors

    Postcondition:
        returns hex color string for the fluid

    Args:
        fluid: fluid material name

    Returns:
        hex color code as string (e.g., "#0066FF")

    Raises:
        KeyError: if fluid is not in _FLUIDS
    """
    return _FLUIDS[fluid]
