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
_RECIPES = json.load(open("recipes.json", "r", encoding="utf-8"))

_BY_OUTPUT = defaultdict(lambda: defaultdict(list))


# This is just to keep the global scope cleaner
def _populate_by_output():
    for machine, recipes in _RECIPES.items():
        for recipe_name, recipe in recipes.items():
            for output, amount in recipe["out"].items():
                _BY_OUTPUT[output][amount].append((machine, recipe_name))


_populate_by_output()


@dataclass
class Recipe:
    """a Satisfactory recipe"""
    machine: str
    inputs: dict[str, float]
    outputs: dict[str, float]


def get_recipes_for(output: str, enablement_set: set[str] | None=None) -> dict[float, list[Recipe]]:
    """Get all recipes for a given output."""
    results = defaultdict(list)
    for amount, machine_recipe_name_pairs in _BY_OUTPUT[output].items():
        for machine, recipe_name in machine_recipe_name_pairs:
            if not enablement_set or recipe_name in enablement_set:
                results[amount].append(Recipe(machine, (r:=_RECIPES[machine][recipe_name])["in"], r["out"]))
    return results


def get_recipe_for(output: str, enablement_set: set[str] | None=None) -> tuple[float, Recipe]:
    """Get the highest rate recipe for a given output."""
    amount, recipes = max(get_recipes_for(output, enablement_set).items(), key=lambda x: x[0])
    return amount, recipes[0]


@dataclass
class Factory:
    """A complete factory network with machines and balancers."""
    network: graphviz.Digraph
    inputs: list[tuple[str, float]]
    outputs: dict[str, float]
    mines: list[tuple[str, Purity]]


def design_factory(outputs: dict[str, float], inputs: list[tuple[str, float]], mines: list[tuple[str, Purity]], enablement_set: set[str] | None=None) -> Factory:
    """Design a complete factory network with machines and balancers.
    
    Args:
        outputs: desired output materials and rates (e.g., {"Iron Plate": 100})
        inputs: list of (material, flow_rate) tuples for input conveyors (e.g., [("Iron Ore", 200), ("Iron Ore", 200)])
        mines: list of (resource_name, purity) tuples for mining nodes
        
    Returns:
        Factory with complete network graph including machines and balancers
    """
    # Phase 1: Determine required machines
    balance = defaultdict(float)
    # Add all inputs to balance
    for material, flow_rate in inputs:
        balance[material] += flow_rate
    
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

    # Track required raw materials that have no recipe
    required_raw_materials = defaultdict(float)
    
    # Track total production: {material: total_rate}
    total_production = defaultdict(float)
    
    while any(amount < 0 for amount in balance.values()):
        output_item, deficit = min(balance.items(), key=lambda x: x[1])
        
        # Check if we have a recipe for this item
        recipes_available = get_recipes_for(output_item, enablement_set)
        if not recipes_available:
            # No recipe - this is a raw material that needs to be supplied
            # Add it to required raw materials and update balance
            required_amount = -deficit
            required_raw_materials[output_item] += required_amount
            balance[output_item] += required_amount
            continue
        
        recipe_amount, recipe = get_recipe_for(output_item, enablement_set)
        machine_count = int((-deficit + recipe_amount - 1) // recipe_amount)
        
        # Find which recipe this is
        machine_type = recipe.machine
        recipe_name = None
        for name, r in _RECIPES[machine_type].items():
            if r["in"] == recipe.inputs and r["out"] == recipe.outputs:
                recipe_name = name
                break
        
        machine_key = (machine_type, recipe_name)
        machine_instances[machine_key] += machine_count
        recipes_used[machine_key] = recipe
        
        for input_item, amount in recipe.inputs.items():
            balance[input_item] -= amount * machine_count
        for output_item, amount in recipe.outputs.items():
            balance[output_item] += amount * machine_count
            total_production[output_item] += amount * machine_count

    # Compute actual outputs: include requested outputs at their production rate + byproducts at excess
    actual_outputs = {}
    for material in outputs.keys():
        if material in total_production:
            actual_outputs[material] = total_production[material]
    # Add byproducts (materials with excess that weren't requested)
    for material, excess in balance.items():
        if excess > 0 and material not in outputs:
            actual_outputs[material] = excess

    # Phase 2: Build network graph with balancers
    dot = graphviz.Digraph(comment="Factory Network")
    dot.attr(rankdir="LR")
    
    # Track material flows: {material: {"sources": [...], "sinks": [...]}}
    # Each source/sink is (node_id, flow_rate)
    material_flows = defaultdict(lambda: {"sources": [], "sinks": []})
    
    # Add input nodes in a subgraph to group them together
    with dot.subgraph(name='inputs') as inputs_group:
        inputs_group.attr(rank='same')
        # Add user-provided input nodes (each conveyor gets its own node)
        for idx, (input_item, flow_rate) in enumerate(inputs):
            node_id = f"Input_{input_item.replace(' ', '_')}_{idx}"
            inputs_group.node(node_id, f"{input_item}\n{flow_rate}/min",
                    shape='box', style='filled', fillcolor='orange')
            material_flows[input_item]["sources"].append((node_id, flow_rate))
        
        # Add auto-generated input nodes for required raw materials
        for material, required_amount in required_raw_materials.items():
            # Check if this material was already provided in inputs
            provided_amount = sum(flow for item, flow in inputs if item == material)
            if provided_amount < required_amount:
                # Need additional input
                remaining = required_amount - provided_amount
                node_id = f"Input_{material.replace(' ', '_')}_auto"
                inputs_group.node(node_id, f"{material}\n{remaining}/min\n(auto)",
                        shape='box', style='filled', fillcolor='orange')
                material_flows[material]["sources"].append((node_id, remaining))
        
        # Add mine nodes
        for idx, (resource, purity) in enumerate(mines):
            node_id = f"Mine_{idx}"
            # Assume Mk.3 miner for now
            flow_rate = _MINERS[2][purity]
            inputs_group.node(node_id, f"Miner\n{resource}\n{flow_rate}/min",
                    shape='box', style='filled', fillcolor='brown')
            material_flows[resource]["sources"].append((node_id, flow_rate))
    
    # Add machine nodes grouped by recipe
    machine_node_id = 0
    cluster_id = 0
    for (machine_type, recipe_idx), count in machine_instances.items():
        recipe = recipes_used[(machine_type, recipe_idx)]
        
        # Create subgraph for this recipe
        with dot.subgraph(name=f"cluster_{cluster_id}") as cluster:
            cluster.attr(label=f"{machine_type}\n{', '.join(f'{k}:{v}' for k, v in recipe.inputs.items())}\n→ {', '.join(f'{k}:{v}' for k, v in recipe.outputs.items())}")
            cluster.attr(style='filled', fillcolor='lightblue')
            
            for _ in range(count):
                node_id = f"Machine_{machine_node_id}"
                machine_node_id += 1
                
                # Simple label for individual machines within the subgraph
                cluster.node(node_id, "", shape='box', style='filled', fillcolor='white')
                
                # Track this machine's inputs and outputs
                for input_item, flow_rate in recipe.inputs.items():
                    material_flows[input_item]["sinks"].append((node_id, flow_rate))
                for output_item, flow_rate in recipe.outputs.items():
                    material_flows[output_item]["sources"].append((node_id, flow_rate))
        
        cluster_id += 1
    
    # Add output nodes in a parent cluster containing two child clusters
    with dot.subgraph(name='cluster_outputs') as outputs_group:
        outputs_group.attr(label='', style='invis')
        # Requested outputs cluster
        with outputs_group.subgraph(name='cluster_requested_outputs') as requested_group:
            requested_group.attr(label='', style='invis')
            requested_group.attr(rank='same')
            # Add output nodes for requested outputs
            for material in outputs.keys():
                if material in total_production:
                    node_id = f"Output_{material.replace(' ', '_')}"
                    # Check if material has internal consumers
                    internal_sinks = sum(flow for _, flow in material_flows[material]["sinks"])
                    
                    if internal_sinks > 0:
                        # Has internal consumption - sink what's available after internal needs
                        available = total_production[material] - internal_sinks
                        sink_amount = max(0, available)
                    else:
                        # No internal consumption - sink all production
                        sink_amount = total_production[material]
                    
                    if sink_amount > 0:
                        requested_group.node(node_id, f"{material}\n{sink_amount}/min",
                                shape='box', style='filled', fillcolor='lightgreen')
                        material_flows[material]["sinks"].append((node_id, sink_amount))
        
        # Byproducts cluster
        with outputs_group.subgraph(name='cluster_byproducts') as byproducts_group:
            byproducts_group.attr(label='', style='invis')
            byproducts_group.attr(rank='same')
            # Add output nodes for byproducts (materials with positive balance not requested)
            for material, excess in balance.items():
                if excess > 0 and material not in outputs:
                    node_id = f"Output_{material.replace(' ', '_')}"
                    byproducts_group.node(node_id, f"{material}\n{excess}/min",
                            shape='box', style='filled', fillcolor='salmon')
                    material_flows[material]["sinks"].append((node_id, excess))
    
    # Phase 3: Route materials with balancers
    balancer_counter = 0
    for material, flows in material_flows.items():
        sources = flows["sources"]
        sinks = flows["sinks"]
        
        if not sources or not sinks:
            continue
        
        # Get flow rates
        source_flows = [flow for _, flow in sources]
        sink_flows = [flow for _, flow in sinks]
        
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
            source_flows = [flow * scale for flow in source_flows]
            # Adjust for rounding - add remainder to first source
            remainder = total_sink - sum(source_flows)
            if abs(remainder) > 0.01 and source_flows:
                source_flows[0] += remainder
        
        # Create balancer for this material
        if len(sources) == 1 and len(sinks) == 1:
            # Direct connection
            source_id, _ = sources[0]
            sink_id, _ = sinks[0]
            # Format flow rate nicely (remove .0 for whole numbers)
            flow_label = int(sink_flows[0]) if sink_flows[0] == int(sink_flows[0]) else sink_flows[0]
            dot.edge(source_id, sink_id, label=f"{material}\n{flow_label}")
        else:
            # Need balancer (requires integer flows)
            # Round while preserving total
            source_total = sum(source_flows)
            sink_total = sum(sink_flows)
            target_total = min(int(source_total), int(sink_total))
            
            # Proportionally allocate integer flows
            source_flows_int = []
            remaining = target_total
            for i, flow in enumerate(source_flows):
                if i == len(source_flows) - 1:
                    # Last one gets remainder
                    source_flows_int.append(remaining)
                else:
                    allocated = int(flow * target_total / source_total)
                    source_flows_int.append(allocated)
                    remaining -= allocated
            
            sink_flows_int = []
            remaining = target_total
            for i, flow in enumerate(sink_flows):
                if i == len(sink_flows) - 1:
                    # Last one gets remainder
                    sink_flows_int.append(remaining)
                else:
                    allocated = int(flow * target_total / sink_total)
                    sink_flows_int.append(allocated)
                    remaining -= allocated
            
            balancer_graph = design_balancer(source_flows_int, sink_flows_int)
            
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
                    dot.node(new_id, "", shape='diamond', style='filled', fillcolor='thistle')
            
            # Copy edges with remapped node IDs
            for match in re.finditer(r'(\w+)\s+->\s+(\w+)\s+\[label=(\d+)\]', balancer_src):
                src = match.group(1)
                dst = match.group(2)
                flow = match.group(3)
                
                if src in node_mapping and dst in node_mapping:
                    dot.edge(node_mapping[src], node_mapping[dst], 
                            label=f"{material}\n{flow}")
            
            balancer_counter += 1
    
    return Factory(dot, inputs, actual_outputs, mines)


def build_graph(factory: Factory) -> graphviz.Digraph:
    dot = graphviz.Digraph(comment="Factory")
    dot.attr(rankdir="LR")
    dot.attr("node", shape="box", style="filled", fillcolor="lightblue")
    dot.attr("edge", color="gray")
    return dot


if __name__ == "__main__":
    factory = design_factory({"Iron Plate": 100}, {}, {})