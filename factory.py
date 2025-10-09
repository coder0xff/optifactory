import json
from dataclasses import dataclass
from collections import defaultdict
from enum import IntEnum

import graphviz
from balancer import design_balancer

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
    amount, recipes = max(get_recipes_for(output).items(), key=lambda x: x[0])
    return amount, recipes[0]


@dataclass
class Factory:
    network: graphviz.Digraph
    inputs: dict[str, float]
    outputs: dict[str, float]
    mines: list[tuple[str, Purity]]


def design_factory(outputs: dict[str, float], inputs: dict[str, float], mines: list[tuple[str, Purity]]) -> Factory:
    """Design a complete factory network with machines and balancers.
    
    Args:
        outputs: desired output materials and rates (e.g., {"Iron Plate": 100})
        inputs: available input materials and rates (e.g., {"Iron Ore": 200})
        mines: list of (resource_name, purity) tuples for mining nodes
        
    Returns:
        Factory with complete network graph including machines and balancers
    """
    # Phase 1: Determine required machines
    balance = defaultdict(float)
    balance.update(inputs)
    
    # Add mines to balance
    for resource, purity in mines:
        # Assume Mk.3 miner
        flow_rate = _MINERS[2][purity]
        balance[resource] += flow_rate
    
    for output_item, amount in outputs.items():
        balance[output_item] -= amount

    # Track machines: {(machine_type, recipe_idx): count}
    machine_instances = defaultdict(int)
    # Track actual recipes used: {(machine_type, recipe_idx): Recipe}
    recipes_used = {}

    while any(amount < 0 for amount in balance.values()):
        output_item, deficit = min(balance.items(), key=lambda x: x[1])
        
        # Check if we have a recipe for this item
        recipes_available = get_recipes_for(output_item)
        if not recipes_available:
            # No recipe - this is a raw material that needs to be supplied
            raise ValueError(f"No recipe found for '{output_item}'. This material must be provided as input or from mines.")
        
        recipe_amount, recipe = get_recipe_for(output_item)
        machine_count = int((-deficit + recipe_amount - 1) // recipe_amount)
        
        # Find which recipe this is
        machine_type = recipe.machine
        recipe_idx = None
        for idx, r in enumerate(_RECIPES[machine_type]):
            if r["in"] == recipe.inputs and r["out"] == recipe.outputs:
                recipe_idx = idx
                break
        
        machine_key = (machine_type, recipe_idx)
        machine_instances[machine_key] += machine_count
        recipes_used[machine_key] = recipe
        
        for input_item, amount in recipe.inputs.items():
            balance[input_item] -= amount * machine_count
        for output_item, amount in recipe.outputs.items():
            balance[output_item] += amount * machine_count

    # Phase 2: Build network graph with balancers
    dot = graphviz.Digraph(comment="Factory Network")
    dot.attr(rankdir="LR")
    
    # Track material flows: {material: {"sources": [...], "sinks": [...]}}
    # Each source/sink is (node_id, flow_rate)
    material_flows = defaultdict(lambda: {"sources": [], "sinks": []})
    
    # Add input nodes
    for input_item, flow_rate in inputs.items():
        node_id = f"Input_{input_item.replace(' ', '_')}"
        dot.node(node_id, f"{input_item}\n{flow_rate}/min",
                shape='box', style='filled', fillcolor='lightgreen')
        material_flows[input_item]["sources"].append((node_id, flow_rate))
    
    # Add mine nodes
    for idx, (resource, purity) in enumerate(mines):
        node_id = f"Mine_{idx}"
        # Assume Mk.3 miner for now
        flow_rate = _MINERS[2][purity]
        dot.node(node_id, f"Miner\n{resource}\n{flow_rate}/min",
                shape='box', style='filled', fillcolor='brown')
        material_flows[resource]["sources"].append((node_id, flow_rate))
    
    # Add machine nodes
    machine_node_id = 0
    for (machine_type, recipe_idx), count in machine_instances.items():
        recipe = recipes_used[(machine_type, recipe_idx)]
        
        for _ in range(count):
            node_id = f"Machine_{machine_node_id}"
            machine_node_id += 1
            
            # Create label showing machine and recipe
            inputs_str = ", ".join(f"{k}:{v}" for k, v in recipe.inputs.items())
            outputs_str = ", ".join(f"{k}:{v}" for k, v in recipe.outputs.items())
            label = f"{machine_type}\n{inputs_str}\n→ {outputs_str}"
            
            dot.node(node_id, label,
                    shape='box', style='filled', fillcolor='lightblue')
            
            # Track this machine's inputs and outputs
            for input_item, flow_rate in recipe.inputs.items():
                material_flows[input_item]["sinks"].append((node_id, flow_rate))
            for output_item, flow_rate in recipe.outputs.items():
                material_flows[output_item]["sources"].append((node_id, flow_rate))
    
    # Add output nodes
    for output_item, flow_rate in outputs.items():
        node_id = f"Output_{output_item.replace(' ', '_')}"
        dot.node(node_id, f"{output_item}\n{flow_rate}/min",
                shape='box', style='filled', fillcolor='lightcoral')
        material_flows[output_item]["sinks"].append((node_id, flow_rate))
    
    # Phase 3: Route materials with balancers
    balancer_counter = 0
    for material, flows in material_flows.items():
        sources = flows["sources"]
        sinks = flows["sinks"]
        
        if not sources or not sinks:
            continue
        
        # Get flow rates
        source_flows = [int(flow) for _, flow in sources]
        sink_flows = [int(flow) for _, flow in sinks]
        
        # Check if balancing is needed
        total_source = sum(source_flows)
        total_sink = sum(sink_flows)
        
        if total_source < total_sink:
            # Not enough material - this shouldn't happen if design_factory worked correctly
            print(f"Warning: Insufficient {material}: {total_source} < {total_sink}")
            continue
        
        # Handle excess source material by reducing flows proportionally
        if total_source > total_sink:
            # Scale down source flows to match sink needs
            scale = total_sink / total_source
            source_flows = [int(flow * scale) for flow in source_flows]
            # Adjust for rounding - add remainder to first source
            remainder = total_sink - sum(source_flows)
            if remainder > 0 and source_flows:
                source_flows[0] += remainder
        
        # Create balancer for this material
        if len(sources) == 1 and len(sinks) == 1:
            # Direct connection
            source_id, _ = sources[0]
            sink_id, _ = sinks[0]
            dot.edge(source_id, sink_id, label=f"{material}\n{sink_flows[0]}")
        else:
            # Need balancer
            balancer_graph = design_balancer(source_flows, sink_flows)
            
            # Extract balancer nodes and edges, renaming them with material prefix
            balancer_src = balancer_graph.source
            
            # Map balancer node IDs to factory node IDs
            node_mapping = {}
            for idx, (source_id, _) in enumerate(sources):
                node_mapping[f"I{idx}"] = source_id
            for idx, (sink_id, _) in enumerate(sinks):
                node_mapping[f"O{idx}"] = sink_id
            
            # Copy balancer nodes (splitters and mergers) to factory graph
            import re
            # Find all splitter and merger nodes
            for match in re.finditer(r'(S\d+|M\d+)\s+\[label="[^"]*"[^\]]*\]', balancer_src):
                old_id = match.group(1)
                new_id = f"{material}_{old_id}_{balancer_counter}"
                node_mapping[old_id] = new_id
                
                # Add node to main graph
                if old_id.startswith('S'):
                    dot.node(new_id, "", shape='diamond', style='filled', fillcolor='lightyellow')
                else:
                    dot.node(new_id, "", shape='diamond', style='filled', fillcolor='lightcoral')
            
            # Copy edges with remapped node IDs
            for match in re.finditer(r'(\w+)\s+->\s+(\w+)\s+\[label=(\d+)\]', balancer_src):
                src = match.group(1)
                dst = match.group(2)
                flow = match.group(3)
                
                if src in node_mapping and dst in node_mapping:
                    dot.edge(node_mapping[src], node_mapping[dst], 
                            label=f"{material}\n{flow}")
            
            balancer_counter += 1
    
    return Factory(dot, inputs, outputs, mines)


def build_graph(factory: Factory) -> graphviz.Digraph:
    dot = graphviz.Digraph(comment="Factory")
    dot.attr(rankdir="LR")
    dot.attr("node", shape="box", style="filled", fillcolor="lightblue")
    dot.attr("edge", color="gray")
    return dot


if __name__ == "__main__":
    factory = design_factory({"Iron Plate": 100}, {}, {})