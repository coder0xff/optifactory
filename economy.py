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


def _compute_economy_values(recipes: dict[str, Recipe], pinned_values: dict[str, float] | None = None) -> dict[str, float]:
    """compute values for all items in a single economy using iterative convergence
    
    Args:
        recipes: dict of recipes that form a single interconnected economy
        pinned_values: dict of item names to fixed values that won't change during convergence
    
    Returns:
        dict mapping item names to their computed values
    """
    pinned_values = pinned_values or {}

    # collect all parts
    all_parts: set[str] = set()
    for recipe in recipes.values():
        all_parts.update(recipe.inputs.keys())
        all_parts.update(recipe.outputs.keys())
    
    _LOGGER.info("Computing economies for %s recipes. This will take a moment...", len(recipes))

    sorted_parts = sorted(all_parts)
    parts_to_index = {part: index for index, part in enumerate(sorted_parts)}
    # Map indices to their pinned values
    pinned_index_values = {parts_to_index[part]: value for part, value in pinned_values.items() if part in parts_to_index}

    def recipe_to_lookup(recipe: Recipe) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
        inputs = [(parts_to_index[input_part], amount) for input_part, amount in recipe.inputs.items()]
        outputs = [(parts_to_index[output_part], amount) for output_part, amount in recipe.outputs.items()]
        return inputs, outputs

    # initialize values
    values = [1] * len(all_parts)
    # set pinned values in initial state
    for index, value in pinned_index_values.items():
        values[index] = value

    # organize recipes by their outputs for efficient lookup
    recipes_producing_dict = defaultdict(list)
    for recipe in recipes.values():
        for output_part in recipe.outputs.keys():
            recipes_producing_dict[output_part].append(recipe_to_lookup(recipe))
    
    recipes_producing = [recipes_producing_dict[part] for part in sorted_parts]

    # organize recipes by their inputs
    recipes_consuming_dict = defaultdict(list)
    for recipe in recipes.values():
        for input_part in recipe.inputs.keys():
            recipes_consuming_dict[input_part].append(recipe_to_lookup(recipe))
    
    recipes_consuming = [recipes_consuming_dict[part] for part in sorted_parts]

    # iterative convergence
    temperature = 0.5
    iterations = 0
    recent_errors = []
    recent_changes = []
    temperature_cap = 0.5
    temperature_cap_rate = 3
    while True:
        # print("\033[H", end="")
        iterations += 1
        
        # print(f"{'='*120}")
        # print(f"Iteration {iterations:5d} | Temperature: {temperature:.11f}")
        # print(f"{'='*120}")
        # print(f"{'Part':<40} {'Previous Value':>12} {'Value':>12} {'Change':>12} {'Error':>12} {'Direction':<10}")
        # print(f"{'-'*120}")

        new_values, changes, errors = _step(recipes_producing, recipes_consuming, values, temperature, pinned_index_values)

        # for part, original_value, new_value, change, error in zip(sorted_parts, values, new_values, changes, errors):
        #     direction = '▲ UP' if change > 0 else '▼ DOWN' if change < 0 else '═ FLAT'
        #     print(f"{part:<40} {original_value:>+12.6f} {new_value:>12.6f} {change:>+12.6f} {error:>12.6f} {direction:<10}")

        values = new_values

        error = sum(error**2 for error in errors)
        change = sum(abs(change) for change in changes)

        recent_errors.append(error)
        recent_changes.append(change)

        # keep only last 100 values
        if len(recent_errors) > 100:
            recent_errors.pop(0)
            recent_changes.pop(0)

        # compute the trend by comparing first 50 vs last 50
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
        
        # print(f"{'='*120}")
        # print(f"Summary: Error {error:5.8f} | Error Trend = {error_trend:5.8f} | Change {change:5.8f} | Change Trend = {change_trend:5.8f} | {observation} | Temperature = {temperature:1.8f} | Temperature Cap = {temperature_cap:1.8f} | Temperature Cap Rate = {temperature_cap_rate:5.8f}                    ")
        # print(f"{'='*120}")
        
        if change <= 0.00000001:
            # print(f"Converged after {iterations} iterations")
            break

    values = _relax(recipes_producing, recipes_consuming, values, sorted_parts, pinned_index_values)
    
    min_value = min(values)
    normalization = 1 / min_value
    values = [value * normalization for value in values]
    for index, value in pinned_index_values.items():
        values[index] = value
    
    values = [round(value, 8) for value in values]
    return dict(zip(sorted_parts, values))


def _step(
    recipes_producing: list[list[tuple[list[str, float], list[str, float]]]],
    recipes_consuming: list[list[tuple[list[str, float], list[str, float]]]],
    values: list[float],
    temperature: float,
    pinned_index_values: dict[int, float],
) -> tuple[list[float], list[float], list[float]]:
    instantaneous_values = []

    for part_index, (producing_recipes, consuming_recipes) in enumerate(zip(recipes_producing, recipes_consuming)):
        if part_index in pinned_index_values:
            # for pinned items, use their pinned value
            instantaneous_values.append(pinned_index_values[part_index])
        else:
            instantaneous = _instantaneous_value(
                part_index,
                producing_recipes,
                consuming_recipes,
                values,
            )
            instantaneous_values.append(instantaneous)

    normalization = 1 / min(instantaneous_values)
    instantaneous_values = [instantaneous * normalization for instantaneous in instantaneous_values]

    new_values = [original * (1 - temperature) + instantaneous * temperature for original, instantaneous in zip(values, instantaneous_values)]
    
    # Ensure pinned values stay exactly at their pinned value after interpolation
    for index, pinned_value in pinned_index_values.items():
        new_values[index] = pinned_value
    
    errors = [abs(instantaneous - value) for value, instantaneous in zip(new_values, instantaneous_values)]
    changes = [new - original for original, new in zip(values, new_values)]

    return new_values, changes, errors
        

def _relax(
    recipes_producing: list[list[tuple[list[str, float], list[str, float]]]],
    recipes_consuming: list[list[tuple[list[str, float], list[str, float]]]],
    values: list[float],
    _sorted_parts: list[str],
    pinned_index_values: dict[int, float],
) -> list[float]:
    two_way_ranks = [len(values)] * len(values)
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
                        # print(f"{_sorted_parts[part_index]} ({two_way_ranks[part_index]}) <- {_sorted_parts[other_part_index]} ({plus_one})")
                        two_way_ranks[part_index] = plus_one
                        two_way_ranks_done = False
    
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
            # print(f"Relaxed {_sorted_parts[part_index]} from {values[part_index]:.6f} to {new_values[part_index]:.6f}")
        for index, value in pinned_index_values.items():
            new_values[index] = value
        values = new_values
    
    return values


def _instantaneous_value(
    part_index: int,
    producing_recipes: list[tuple[list[str, float], list[str, float]]],
    consuming_recipes: list[tuple[list[str, float], list[str, float]]],
    values: list[float],
) -> tuple[float, float]:
    """update the value estimate for a part
    
    Args:
        part: the part being updated
        producing_recipes: list of Recipe objects that produce this part
        consuming_recipes: list of Recipe objects that consume this part
        current_value: current value estimate for this part
        all_values: dict of all current part values
    Returns:
        new value estimate for the part
    """
    counter = 0
    accumulator = 0
    
    if consuming_recipes:
        counter += 1
        value_of_all_consumer_outputs = sum(values[output_part] * amount for recipe in consuming_recipes for output_part, amount in recipe[1])
        number_of_all_inputs_to_consumers = sum(amount for recipe in consuming_recipes for _, amount in recipe[0])
        number_of_part_inputs_to_consumers = sum(amount for recipe in consuming_recipes for input_part, amount in recipe[0] if input_part == part_index)
        proportion_of_part_inputs_to_all_inputs = number_of_part_inputs_to_consumers / number_of_all_inputs_to_consumers
        value_of_part_inputs_to_consumers = value_of_all_consumer_outputs * proportion_of_part_inputs_to_all_inputs
        accumulator += value_of_part_inputs_to_consumers / number_of_part_inputs_to_consumers

    if producing_recipes:
        counter += 1
        value_of_all_producer_inputs = sum(values[input_part] * amount for recipe in producing_recipes for input_part, amount in recipe[0])
        number_of_all_outputs_from_producers = sum(amount for recipe in producing_recipes for _, amount in recipe[1])
        number_of_part_outputs_from_producers = sum(amount for recipe in producing_recipes for output_part, amount in recipe[1] if output_part == part_index)
        proportion_of_part_outputs_to_all_outputs = number_of_part_outputs_from_producers / number_of_all_outputs_from_producers
        value_of_part_outputs_from_producers = value_of_all_producer_inputs * proportion_of_part_outputs_to_all_outputs
        accumulator += value_of_part_outputs_from_producers / number_of_part_outputs_from_producers
        
    return accumulator / counter


def separate_economies(recipes: dict[str, Recipe]) -> list[dict[str, Recipe]]:
    """separate recipes into economies"""

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
    """Get the default economies for a given set of recipes."""
    recipes = recipes or get_all_recipes()
    economy_recipes = separate_economies(recipes)
    return tuple(frozendict(_compute_economy_values(economy)) for economy in economy_recipes)


@freezeargs
@cache
def get_default_economy(recipes: dict[str, Recipe] | None=None) -> frozendict[str, float]:
    """Get the default economy for a given set of recipes and naively combine all economies into a single dictionary. The relationships between items in different economies are chosen arbitrarily."""
    return frozendict(compute_item_values(recipes))


def cost_of_recipes(recipes: dict[str, int], economy: dict[str, float] | None=None) -> float:
    """Compute the cost of a number of recipes."""
    economy = economy or get_default_economy()
    
    cost = 0
    for recipe, amount in recipes.items():
        for input_part, input_amount in get_all_recipes()[recipe].inputs.items():
            cost += economy[input_part] * input_amount * amount
    return cost


def save_economy_to_csv(filepath: str, economy: dict[str, float], pinned_items: set[str] | None = None) -> None:
    """Save economy values and pinned status to CSV file.
    
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
