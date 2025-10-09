import json
from dataclasses import dataclass
from collections import defaultdict
from enum import IntEnum

import graphviz

# The speeds of the conveyors in the game
_CONVEYORS = [60, 120, 270]

class Purity(IntEnum):
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

# All qunaities are "per minute"
_RECIPES = json.load(open("recipes.yaml"))

_BY_OUTPUT = defaultdict(lambda: defaultdict(list))

for machine, recipes in _RECIPES.items():
    for recipe_number, recipe in enumerate(recipes):
        for output, amount in recipe["out"].items():
            _BY_OUTPUT[output][amount].append((machine, recipe_number))


@dataclass
class Recipe:
    machine: str
    inputs: dict[str, float]
    outputs: dict[str, float]


def get_recipes_for(output: str) -> dict[float, Recipe]:
    return {amount: [Recipe(machine, (r:=_RECIPES[machine][recipe_number])["in"], r["out"]) for machine, recipe_number in machine_recipe_index_pairs] for amount, machine_recipe_index_pairs in _BY_OUTPUT[output].items()}


def get_recipe_for(output: str) -> tuple[float, Recipe]:
    return max(get_recipes_for(output).items(), key=lambda x: x[0])[1][0]


@dataclass
class Factory:
    network: graphviz.Digraph
    inputs: dict[str, float]
    outputs: dict[str, float]
    mines: list[tuple[str, Purity]]


def design_factory(outputs: dict[str, float], inputs: dict[str, float], mines: list[tuple[str, Purity]]) -> Factory:
    balance = defaultdict(float)
    balance.update(inputs)
    for input, amount in outputs.items():
        balance[input] -= amount

    recipe_counts = defaultdict(float)

    while any(amount < 0 for amount in balance.values()):
        output, deficit = min(balance.items(), key=lambda x: x[1])
        recipe_amount, machine, recipe = get_recipe_for(output)
        machine_count = (-deficit + recipe_amount - 1) // recipe_amount
        recipe_counts[machine] += machine_count
        for input, amount in recipe.inputs.items():
            balance[input] -= amount * machine_count
        for output, amount in recipe.outputs.items():
            balance[output] += amount * machine_count

        
    return Factory(network, inputs, outputs, mines)


def build_graph(factory: Factory) -> graphviz.Digraph:
    dot = graphviz.Digraph(comment="Factory")
    dot.attr(rankdir="LR")
    dot.attr("node", shape="box", style="filled", fillcolor="lightblue")
    dot.attr("edge", color="gray")
    return dot


if __name__ == "__main__":
    factory = design_factory({"Iron Plate": 100}, {}, {})