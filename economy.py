import csv
import logging
from collections import defaultdict
from functools import cache
from itertools import chain

from frozendict import frozendict
from tarjan import tarjan

from recipes import Recipe, get_all_recipes
from freezeargs import freezeargs

_LOGGER = logging.getLogger("satisgraphery")
_LOGGER.setLevel(logging.DEBUG)


def _collect_all_parts(recipes: dict[str, Recipe]) -> set[str]:
    """Collect all unique parts from recipes.

    Precondition:
        recipes is dict mapping recipe names to Recipe objects

    Postcondition:
        returns set of all unique part names appearing in inputs or outputs
    """
    all_parts: set[str] = set()
    for recipe in recipes.values():
        all_parts.update(recipe.inputs.keys())
        all_parts.update(recipe.outputs.keys())
    return all_parts


def _create_index_mappings(sorted_parts: list[str], pinned_values: dict[str, float]) -> tuple[dict[str, int], dict[int, float]]:
    """Create mappings between part names and indices.

    Precondition:
        sorted_parts is list of unique part names in sorted order
        pinned_values is dict mapping part names to fixed values

    Postcondition:
        returns (parts_to_index dict, pinned_index_values dict)
        parts_to_index maps part names to their indices
        pinned_index_values maps indices to their pinned values
    """
    parts_to_index = {part: index for index, part in enumerate(sorted_parts)}
    pinned_index_values = {parts_to_index[part]: value for part, value in pinned_values.items() if part in parts_to_index}
    return parts_to_index, pinned_index_values


def _recipe_to_indexed_form(recipe: Recipe, parts_to_index: dict[str, int]) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Convert recipe to indexed form for efficient computation.

    Precondition:
        recipe is Recipe object
        parts_to_index is dict mapping part names to indices
        all parts in recipe exist in parts_to_index

    Postcondition:
        returns (inputs list, outputs list)
        inputs is list of (index, amount) tuples
        outputs is list of (index, amount) tuples
    """
    inputs = [(parts_to_index[input_part], amount) for input_part, amount in recipe.inputs.items()]
    outputs = [(parts_to_index[output_part], amount) for output_part, amount in recipe.outputs.items()]
    return inputs, outputs


def _organize_recipes_by_outputs(recipes: dict[str, Recipe], sorted_parts: list[str], parts_to_index: dict[str, int]) -> list[list[tuple[list[tuple[int, int]], list[tuple[int, int]]]]]:
    """Organize recipes by their output parts for efficient lookup.

    Precondition:
        recipes is dict mapping recipe names to Recipe objects
        sorted_parts is list of part names in sorted order
        parts_to_index is dict mapping part names to indices

    Postcondition:
        returns list where index i contains recipes producing sorted_parts[i]
        each recipe is in indexed form (inputs, outputs)
    """
    recipes_producing_dict = defaultdict(list)
    for recipe in recipes.values():
        indexed_recipe = _recipe_to_indexed_form(recipe, parts_to_index)
        for output_part in recipe.outputs.keys():
            recipes_producing_dict[output_part].append(indexed_recipe)
    return [recipes_producing_dict[part] for part in sorted_parts]


def _organize_recipes_by_inputs(recipes: dict[str, Recipe], sorted_parts: list[str], parts_to_index: dict[str, int]) -> list[list[tuple[list[tuple[int, int]], list[tuple[int, int]]]]]:
    """Organize recipes by their input parts for efficient lookup.

    Precondition:
        recipes is dict mapping recipe names to Recipe objects
        sorted_parts is list of part names in sorted order
        parts_to_index is dict mapping part names to indices

    Postcondition:
        returns list where index i contains recipes consuming sorted_parts[i]
        each recipe is in indexed form (inputs, outputs)
    """
    recipes_consuming_dict = defaultdict(list)
    for recipe in recipes.values():
        indexed_recipe = _recipe_to_indexed_form(recipe, parts_to_index)
        for input_part in recipe.inputs.keys():
            recipes_consuming_dict[input_part].append(indexed_recipe)
    return [recipes_consuming_dict[part] for part in sorted_parts]


def _initialize_values_array(num_parts: int, pinned_index_values: dict[int, float]) -> list[float]:
    """Initialize values array with defaults and pinned values.

    Precondition:
        num_parts >= 0
        pinned_index_values is dict mapping indices to pinned values
        all indices in pinned_index_values are < num_parts

    Postcondition:
        returns list of length num_parts
        all values default to 1.0
        pinned indices set to their pinned values
    """
    values = [1] * num_parts
    for index, value in pinned_index_values.items():
        values[index] = value
    return values


def _compute_trend_metrics(recent_errors: list[float], recent_changes: list[float]) -> tuple[float, float]:
    """Compute error and change trends from recent history.

    Precondition:
        recent_errors is list of floats (length >= 0)
        recent_changes is list of floats (same length as recent_errors)

    Postcondition:
        returns (error_trend, change_trend)
        if length >= 100, compares first 50 vs last 50
        otherwise returns (0, 0)
    """
    if len(recent_errors) >= 100:
        first_half_error_total = sum(recent_errors[:50])
        second_half_error_total = sum(recent_errors[50:])
        first_half_change_total = sum(recent_changes[:50])
        second_half_change_total = sum(recent_changes[50:])
        error_trend = second_half_error_total - first_half_error_total
        change_trend = second_half_change_total - first_half_change_total
    else:
        error_trend = 0
        change_trend = 0
    return error_trend, change_trend


def _adjust_temperature(temperature: float, temperature_cap: float, temperature_cap_rate: float, error_trend: float, change_trend: float) -> tuple[float, float, float]:
    """Adjust temperature based on convergence trends.

    Precondition:
        temperature > 0
        temperature_cap > 0
        temperature_cap_rate > 0
        error_trend is float
        change_trend is float

    Postcondition:
        returns (new_temperature, new_temperature_cap, new_temperature_cap_rate)
        if diverging (error_trend >= 0 and change_trend >= 0), cools down
        if converging (change_trend < 0), heats up
        temperature <= temperature_cap always
    """
    if error_trend >= 0 and change_trend >= 0:
        # Looks like divergence, cool down
        temperature *= 0.999
        temperature_cap_rate = max(temperature_cap_rate + 0.01, 8)
        temperature_cap = min(temperature_cap, temperature)
    elif change_trend < 0:
        # Looks like convergence, heat up
        temperature *= 1.01
        temperature_cap = 1.0 - (1.0 - temperature_cap) * (1 - 10**(-temperature_cap_rate))
        temperature_cap_rate *= 0.999
    # else do nothing, seems to be hard to reach state anyway

    temperature = min(temperature, temperature_cap)
    return temperature, temperature_cap, temperature_cap_rate


def _normalize_and_round_values(values: list[float], pinned_index_values: dict[int, float]) -> list[float]:
    """Normalize values to minimum of 1.0 and round.

    Precondition:
        values is list of floats (all positive)
        pinned_index_values is dict mapping indices to pinned values

    Postcondition:
        returns list same length as values
        all values scaled so minimum is 1.0
        pinned values restored to their exact pinned values
        all values rounded to 8 decimal places
    """
    min_value = min(values)
    normalization = 1 / min_value
    values = [value * normalization for value in values]
    for index, value in pinned_index_values.items():
        values[index] = value
    values = [round(value, 8) for value in values]
    return values


def _compute_economy_values(recipes: dict[str, Recipe], pinned_values: dict[str, float] | None = None) -> dict[str, float]:
    """Compute values for all items in a single economy using iterative convergence.

    Precondition:
        recipes is dict mapping recipe names to Recipe objects
        all recipes form single interconnected economy
        pinned_values is None or dict mapping item names to fixed values

    Postcondition:
        returns dict mapping item names to computed values
        all values >= 1.0
        pinned items have exactly their pinned values
        algorithm converged (change <= 0.00000001)
    
    Args:
        recipes: dict of recipes that form a single interconnected economy
        pinned_values: dict of item names to fixed values that won't change during convergence
    
    Returns:
        dict mapping item names to their computed values
    """
    pinned_values = pinned_values or {}

    # Setup phase
    all_parts = _collect_all_parts(recipes)
    _LOGGER.info("Computing economies for %s recipes. This will take a moment...", len(recipes))
    
    sorted_parts = sorted(all_parts)
    parts_to_index, pinned_index_values = _create_index_mappings(sorted_parts, pinned_values)
    
    # Organize recipes for efficient lookup
    recipes_producing = _organize_recipes_by_outputs(recipes, sorted_parts, parts_to_index)
    recipes_consuming = _organize_recipes_by_inputs(recipes, sorted_parts, parts_to_index)
    
    # Initialize values
    values = _initialize_values_array(len(all_parts), pinned_index_values)
    
    # Iterative convergence
    temperature = 0.5
    temperature_cap = 0.5
    temperature_cap_rate = 3
    recent_errors = []
    recent_changes = []
    
    while True:
        new_values, changes, errors = _step(recipes_producing, recipes_consuming, values, temperature, pinned_index_values)
        values = new_values

        error = sum(error**2 for error in errors)
        change = sum(abs(change) for change in changes)

        recent_errors.append(error)
        recent_changes.append(change)

        # Keep only last 100 values
        if len(recent_errors) > 100:
            recent_errors.pop(0)
            recent_changes.pop(0)

        # Adjust temperature based on trends
        error_trend, change_trend = _compute_trend_metrics(recent_errors, recent_changes)
        temperature, temperature_cap, temperature_cap_rate = _adjust_temperature(
            temperature, temperature_cap, temperature_cap_rate, error_trend, change_trend
        )
        
        if change <= 0.00000001:
            break

    # Post-processing
    values = _relax(recipes_producing, recipes_consuming, values, sorted_parts, pinned_index_values)
    values = _normalize_and_round_values(values, pinned_index_values)
    
    return dict(zip(sorted_parts, values))


def _compute_all_instantaneous_values(
    recipes_producing: list[list[tuple[list[str, float], list[str, float]]]],
    recipes_consuming: list[list[tuple[list[str, float], list[str, float]]]],
    values: list[float],
    pinned_index_values: dict[int, float],
) -> list[float]:
    """Compute instantaneous values for all parts.

    Precondition:
        recipes_producing is list of recipes producing each part
        recipes_consuming is list of recipes consuming each part
        values is list of current value estimates
        all three lists have same length
        pinned_index_values is dict mapping indices to pinned values

    Postcondition:
        returns list of instantaneous values
        pinned indices have their pinned values
        other indices have computed instantaneous values
    """
    instantaneous_values = []
    for part_index, (producing_recipes, consuming_recipes) in enumerate(zip(recipes_producing, recipes_consuming)):
        if part_index in pinned_index_values:
            instantaneous_values.append(pinned_index_values[part_index])
        else:
            instantaneous = _instantaneous_value(
                part_index,
                producing_recipes,
                consuming_recipes,
                values,
            )
            instantaneous_values.append(instantaneous)
    return instantaneous_values


def _normalize_values_list(values: list[float]) -> list[float]:
    """Normalize list of values so minimum is 1.0.

    Precondition:
        values is list of positive floats (length > 0)

    Postcondition:
        returns list same length as values
        all values scaled so minimum is 1.0
    """
    normalization = 1 / min(values)
    return [value * normalization for value in values]


def _interpolate_values(values: list[float], instantaneous_values: list[float], temperature: float, pinned_index_values: dict[int, float]) -> list[float]:
    """Interpolate between current and instantaneous values using temperature.

    Precondition:
        values is list of current values
        instantaneous_values is list of instantaneous values
        both lists have same length
        0 <= temperature <= 1
        pinned_index_values is dict mapping indices to pinned values

    Postcondition:
        returns list of interpolated values
        values = original * (1 - temperature) + instantaneous * temperature
        pinned indices forced to their exact pinned values
    """
    new_values = [
        original * (1 - temperature) + instantaneous * temperature
        for original, instantaneous in zip(values, instantaneous_values)
    ]
    # Ensure pinned values stay exactly at their pinned value
    for index, pinned_value in pinned_index_values.items():
        new_values[index] = pinned_value
    return new_values


def _compute_errors_and_changes(values: list[float], new_values: list[float], instantaneous_values: list[float]) -> tuple[list[float], list[float]]:
    """Compute errors and changes between iterations.

    Precondition:
        values is list of original values
        new_values is list of new values after interpolation
        instantaneous_values is list of instantaneous values
        all three lists have same length

    Postcondition:
        returns (errors list, changes list)
        errors[i] = abs(instantaneous_values[i] - new_values[i])
        changes[i] = new_values[i] - values[i]
    """
    errors = [abs(instantaneous - value) for value, instantaneous in zip(new_values, instantaneous_values)]
    changes = [new - original for original, new in zip(values, new_values)]
    return errors, changes


def _step(
    recipes_producing: list[list[tuple[list[str, float], list[str, float]]]],
    recipes_consuming: list[list[tuple[list[str, float], list[str, float]]]],
    values: list[float],
    temperature: float,
    pinned_index_values: dict[int, float],
) -> tuple[list[float], list[float], list[float]]:
    """Perform one iteration step of value convergence.

    Precondition:
        recipes_producing is list of recipes producing each part
        recipes_consuming is list of recipes consuming each part
        values is list of current value estimates
        all three lists have same length
        0 <= temperature <= 1
        pinned_index_values is dict mapping indices to pinned values

    Postcondition:
        returns (new_values, changes, errors)
        new_values are interpolated between values and instantaneous
        changes[i] = new_values[i] - values[i]
        errors[i] = abs(instantaneous_values[i] - new_values[i])
    """
    instantaneous_values = _compute_all_instantaneous_values(
        recipes_producing, recipes_consuming, values, pinned_index_values
    )
    instantaneous_values = _normalize_values_list(instantaneous_values)
    new_values = _interpolate_values(values, instantaneous_values, temperature, pinned_index_values)
    errors, changes = _compute_errors_and_changes(values, new_values, instantaneous_values)
    return new_values, changes, errors
        

def _compute_two_way_ranks(
    recipes_producing: list[list[tuple[list[str, float], list[str, float]]]],
    recipes_consuming: list[list[tuple[list[str, float], list[str, float]]]],
    num_parts: int,
) -> list[int]:
    """Compute two-way ranks for all parts (distance from base/terminal items).

    Precondition:
        recipes_producing is list of recipes producing each part
        recipes_consuming is list of recipes consuming each part
        both lists have length num_parts
        num_parts > 0

    Postcondition:
        returns list of ranks (length num_parts)
        rank 0 for base/terminal items (no producers or no consumers)
        rank n for items n steps away from base/terminal items
    """
    two_way_ranks = [num_parts] * num_parts
    two_way_ranks_done = False
    while not two_way_ranks_done:
        two_way_ranks_done = True
        for part_index, (producing_recipes, consuming_recipes) in enumerate(zip(recipes_producing, recipes_consuming)):
            if not producing_recipes or not consuming_recipes:
                if 1 < two_way_ranks[part_index]:
                    two_way_ranks[part_index] = 0
                    two_way_ranks_done = False
                continue

            for inputs, outputs in producing_recipes:
                for other_part_index, _amount in chain(inputs, outputs):
                    plus_one = two_way_ranks[other_part_index] + 1
                    if plus_one < two_way_ranks[part_index]:
                        two_way_ranks[part_index] = plus_one
                        two_way_ranks_done = False
    return two_way_ranks


def _relax_by_ranks(
    recipes_producing: list[list[tuple[list[str, float], list[str, float]]]],
    recipes_consuming: list[list[tuple[list[str, float], list[str, float]]]],
    values: list[float],
    two_way_ranks: list[int],
    pinned_index_values: dict[int, float],
) -> list[float]:
    """Relax values by processing parts in reverse rank order.

    Precondition:
        recipes_producing is list of recipes producing each part
        recipes_consuming is list of recipes consuming each part
        values is list of current value estimates
        two_way_ranks is list of ranks for each part
        all four lists have same length
        pinned_index_values is dict mapping indices to pinned values

    Postcondition:
        returns list of relaxed values
        parts processed from highest rank to lowest
        pinned values restored after each rank
    """
    for rank in range(max(two_way_ranks) - 1, -1, -1):
        new_values = values.copy()
        parts_with_rank = [part_index for part_index, two_way_rank in enumerate(two_way_ranks) if two_way_rank == rank]
        for part_index in parts_with_rank:
            new_values[part_index] = _instantaneous_value(
                part_index,
                recipes_producing[part_index],
                recipes_consuming[part_index],
                values,
            )
        for index, value in pinned_index_values.items():
            new_values[index] = value
        values = new_values
    return values


def _relax(
    recipes_producing: list[list[tuple[list[str, float], list[str, float]]]],
    recipes_consuming: list[list[tuple[list[str, float], list[str, float]]]],
    values: list[float],
    _sorted_parts: list[str],
    pinned_index_values: dict[int, float],
) -> list[float]:
    """Perform relaxation to improve value estimates.

    Precondition:
        recipes_producing is list of recipes producing each part
        recipes_consuming is list of recipes consuming each part
        values is list of current value estimates
        all three lists have same length
        _sorted_parts is list of part names (for debugging, unused)
        pinned_index_values is dict mapping indices to pinned values

    Postcondition:
        returns list of relaxed values
        values refined by processing parts in dependency order
        pinned values maintained exactly
    """
    two_way_ranks = _compute_two_way_ranks(recipes_producing, recipes_consuming, len(values))
    values = _relax_by_ranks(recipes_producing, recipes_consuming, values, two_way_ranks, pinned_index_values)
    return values


def _value_from_consumers(
    part_index: int,
    consuming_recipes: list[tuple[list[str, float], list[str, float]]],
    values: list[float],
) -> float:
    """Compute value estimate from consuming recipes.

    Precondition:
        part_index >= 0
        consuming_recipes is list of (inputs, outputs) tuples
        consuming_recipes is non-empty
        values is list of current value estimates

    Postcondition:
        returns value estimate based on consumer outputs
        proportionally allocates consumer output value to this part's inputs
    """
    value_of_all_consumer_outputs = sum(
        values[output_part] * amount
        for recipe in consuming_recipes
        for output_part, amount in recipe[1]
    )
    number_of_all_inputs_to_consumers = sum(
        amount for recipe in consuming_recipes for _, amount in recipe[0]
    )
    number_of_part_inputs_to_consumers = sum(
        amount
        for recipe in consuming_recipes
        for input_part, amount in recipe[0]
        if input_part == part_index
    )
    proportion_of_part_inputs_to_all_inputs = (
        number_of_part_inputs_to_consumers / number_of_all_inputs_to_consumers
    )
    value_of_part_inputs_to_consumers = (
        value_of_all_consumer_outputs * proportion_of_part_inputs_to_all_inputs
    )
    return value_of_part_inputs_to_consumers / number_of_part_inputs_to_consumers


def _value_from_producers(
    part_index: int,
    producing_recipes: list[tuple[list[str, float], list[str, float]]],
    values: list[float],
) -> float:
    """Compute value estimate from producing recipes.

    Precondition:
        part_index >= 0
        producing_recipes is list of (inputs, outputs) tuples
        producing_recipes is non-empty
        values is list of current value estimates

    Postcondition:
        returns value estimate based on producer inputs
        proportionally allocates producer input value to this part's outputs
    """
    value_of_all_producer_inputs = sum(
        values[input_part] * amount
        for recipe in producing_recipes
        for input_part, amount in recipe[0]
    )
    number_of_all_outputs_from_producers = sum(
        amount for recipe in producing_recipes for _, amount in recipe[1]
    )
    number_of_part_outputs_from_producers = sum(
        amount
        for recipe in producing_recipes
        for output_part, amount in recipe[1]
        if output_part == part_index
    )
    proportion_of_part_outputs_to_all_outputs = (
        number_of_part_outputs_from_producers / number_of_all_outputs_from_producers
    )
    value_of_part_outputs_from_producers = (
        value_of_all_producer_inputs * proportion_of_part_outputs_to_all_outputs
    )
    return value_of_part_outputs_from_producers / number_of_part_outputs_from_producers


def _instantaneous_value(
    part_index: int,
    producing_recipes: list[tuple[list[str, float], list[str, float]]],
    consuming_recipes: list[tuple[list[str, float], list[str, float]]],
    values: list[float],
) -> float:
    """Compute instantaneous value estimate for a part.

    Precondition:
        part_index >= 0
        producing_recipes is list of (inputs, outputs) tuples producing this part
        consuming_recipes is list of (inputs, outputs) tuples consuming this part
        values is list of current value estimates
        at least one of producing_recipes or consuming_recipes is non-empty

    Postcondition:
        returns instantaneous value estimate
        averages value from consumers and producers (if both exist)
        uses only available source if one is empty
    
    Args:
        part_index: index of the part being updated
        producing_recipes: recipes that produce this part
        consuming_recipes: recipes that consume this part
        values: current value estimates for all parts
    
    Returns:
        new instantaneous value estimate for the part
    """
    counter = 0
    accumulator = 0
    
    if consuming_recipes:
        counter += 1
        accumulator += _value_from_consumers(part_index, consuming_recipes, values)

    if producing_recipes:
        counter += 1
        accumulator += _value_from_producers(part_index, producing_recipes, values)
        
    return accumulator / counter


def separate_economies(recipes: dict[str, Recipe]) -> list[dict[str, Recipe]]:
    """Separate recipes into disconnected economies using Tarjan's algorithm.

    Precondition:
        recipes is dict mapping recipe names to Recipe objects

    Postcondition:
        returns list of economy dicts
        each economy is dict of recipes that are interconnected
        recipes in different economies share no parts
        union of all economies equals original recipes
    """
    parts_to_parts = defaultdict(set)
    parts_to_recipes = defaultdict(list)
    for name, recipe in recipes.items():
        for part in recipe.inputs.keys():
            parts_to_parts[part].update(recipe.inputs.keys())
            parts_to_parts[part].update(recipe.outputs.keys())
            parts_to_recipes[part].append(name)
        for part in recipe.outputs.keys():
            parts_to_parts[part].update(recipe.inputs.keys())
            parts_to_parts[part].update(recipe.outputs.keys())
            parts_to_recipes[part].append(name)

    part_economies = tarjan(parts_to_parts)
    result = [{recipe: recipes[recipe] for recipe in {recipe for part in part_economy for recipe in parts_to_recipes[part]}} for part_economy in part_economies]
    return result


def compute_item_values(recipes: dict[str, Recipe] | None = None, pinned_values: dict[str, float] | None = None) -> dict[str, float]:
    """Compute item values for all recipes, handling multiple separate economies.

    Precondition:
        recipes is None or dict mapping recipe names to Recipe objects
        pinned_values is None or dict mapping item names to fixed values

    Postcondition:
        returns dict mapping all item names to computed values
        all values >= 1.0
        pinned items have exactly their pinned values
        separate economies computed independently
    
    Args:
        recipes: dict of all recipes to consider. If None, uses all available recipes.
        pinned_values: dict of item names to fixed values that won't change during convergence
    
    Returns:
        dict mapping all item names to their computed values
    """
    recipes = recipes or get_all_recipes()
    pinned_values = pinned_values or {}
    economy_recipes = separate_economies(recipes)
    
    result = {}
    for economy in economy_recipes:
        economy_values = _compute_economy_values(economy, pinned_values)
        result.update(economy_values)
    
    return result


@freezeargs
@cache
def get_default_economies(recipes: dict[str, Recipe] | None=None) -> tuple[frozendict[str, float], ...]:
    """Get the default economies for a given set of recipes.

    Precondition:
        recipes is None or dict mapping recipe names to Recipe objects

    Postcondition:
        returns tuple of frozendicts
        each frozendict maps item names to values for one economy
        result is cached for performance
    """
    recipes = recipes or get_all_recipes()
    economy_recipes = separate_economies(recipes)
    return tuple(frozendict(_compute_economy_values(economy)) for economy in economy_recipes)


@freezeargs
@cache
def get_default_economy(recipes: dict[str, Recipe] | None=None) -> frozendict[str, float]:
    """Get the default economy combining all separate economies into one dict.

    Precondition:
        recipes is None or dict mapping recipe names to Recipe objects

    Postcondition:
        returns frozendict mapping all item names to values
        separate economies naively combined
        relative values between disconnected economies are arbitrary
        result is cached for performance
    """
    return frozendict(compute_item_values(recipes))


def cost_of_recipes(recipes: dict[str, int], economy: dict[str, float] | None=None) -> float:
    """Compute the total cost of recipe inputs.

    Precondition:
        recipes is dict mapping recipe names to counts
        economy is None or dict mapping item names to values
        all recipe names in recipes exist in get_all_recipes()
        all input items in recipes exist in economy

    Postcondition:
        returns total cost (float >= 0)
        cost = sum over all recipes of (input_value * input_amount * recipe_count)
    """
    economy = economy or get_default_economy()
    
    cost = 0
    for recipe, amount in recipes.items():
        for input_part, input_amount in get_all_recipes()[recipe].inputs.items():
            cost += economy[input_part] * input_amount * amount
    return cost


def save_economy_to_csv(filepath: str, economy: dict[str, float], pinned_items: set[str] | None = None) -> None:
    """Save economy values and pinned status to CSV file.

    Precondition:
        filepath is valid writable path
        economy is dict mapping item names to values
        pinned_items is None or set of item names

    Postcondition:
        CSV file created at filepath with header row and data rows
        items sorted alphabetically
        each row: Item, Value, Pinned (true/false)
    
    Args:
        filepath: path to CSV file
        economy: dict mapping item names to values
        pinned_items: set of item names that are pinned
    """
    pinned_items = pinned_items or set()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Item', 'Value', 'Pinned'])
        
        for item in sorted(economy.keys()):
            value = economy[item]
            pinned = 'true' if item in pinned_items else 'false'
            writer.writerow([item, value, pinned])


def load_economy_from_csv(filepath: str) -> tuple[dict[str, float], set[str]]:
    """Load economy values and pinned status from CSV file.

    Precondition:
        filepath is valid readable path to CSV file
        CSV has header row with Item, Value, Pinned columns
        Value column contains parseable floats
        Pinned column contains 'true'/'false' (case-insensitive)

    Postcondition:
        returns (economy dict, pinned_items set)
        economy maps item names to values
        pinned_items contains items with Pinned='true'
    
    Args:
        filepath: path to CSV file
    
    Returns:
        tuple of (economy dict, pinned_items set)
    """
    economy = {}
    pinned_items = set()
    
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = row['Item']
            value = float(row['Value'])
            pinned = row['Pinned'].lower() == 'true'
            
            economy[item] = value
            if pinned:
                pinned_items.add(item)
    
    return economy, pinned_items
