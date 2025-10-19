"""Factory design system for Satisfactory production chains."""

import re
from dataclasses import dataclass
from collections import defaultdict

import graphviz
from balancer import design_balancer
from recipes import Purity, get_mining_rate, Recipe, get_all_recipes
from optimize import optimize_recipes


def _initialize_balance(
    outputs: dict[str, float],
    inputs: list[tuple[str, float]],
    mines: list[tuple[str, Purity]],
) -> dict:
    """Initialize material balance with inputs, mines, and output requirements."""
    balance = defaultdict(float)

    for material, flow_rate in inputs:
        balance[material] += flow_rate

    for resource, purity in mines:
        balance[resource] += get_mining_rate(2, purity)  # Assume Mk.3 miner

    for output_item, amount in outputs.items():
        balance[output_item] -= amount

    return balance


def _calculate_machines(
    outputs: dict[str, float],
    inputs: list[tuple[str, float]],
    mines: list[tuple[str, Purity]],
    enablement_set: set[str] | None,
) -> tuple[dict, dict, dict, dict]:
    """Calculate required machines and material balance.

    Returns:
        tuple of (machine_instances, recipes_used, required_raw_materials, total_production)
    """
    # Convert inputs list to dict for optimizer
    inputs_dict = defaultdict(float)
    for material, flow_rate in inputs:
        inputs_dict[material] += flow_rate
    
    # Add mine outputs to inputs_dict
    for resource, purity in mines:
        inputs_dict[resource] += get_mining_rate(2, purity)
    
    # Call optimizer - returns {recipe_name: machine_count}
    recipe_counts = optimize_recipes(
        inputs=dict(inputs_dict),
        outputs=outputs,
        enablement_set=enablement_set
    )
    
    # Transform optimizer output to existing format
    all_recipes = get_all_recipes()
    machine_instances = defaultdict(int)
    recipes_used = {}
    total_production = defaultdict(float)
    
    for recipe_name, count in recipe_counts.items():
        recipe = all_recipes[recipe_name]
        machine_key = (recipe.machine, recipe_name)
        
        machine_instances[machine_key] = int(count)
        recipes_used[machine_key] = recipe
        
        for output_item, amount in recipe.outputs.items():
            total_production[output_item] += amount * count
    
    # Compute required_raw_materials by checking final balance
    balance = _initialize_balance(outputs, inputs, mines)
    for recipe_name, count in recipe_counts.items():
        recipe = all_recipes[recipe_name]
        for input_item, amount in recipe.inputs.items():
            balance[input_item] -= amount * count
        for output_item, amount in recipe.outputs.items():
            balance[output_item] += amount * count
    
    required_raw_materials = defaultdict(float)
    for material, amount in balance.items():
        if amount < 0:
            required_raw_materials[material] = -amount
    
    return (
        machine_instances,
        recipes_used,
        required_raw_materials,
        total_production,
    )


def _compute_actual_outputs(
    outputs: dict[str, float], total_production: dict, balance: dict
) -> dict[str, float]:
    """Compute actual factory outputs including byproducts."""
    # Recompute balance for byproduct detection
    current_balance = defaultdict(float, balance)

    actual_outputs = {}
    for material in outputs.keys():
        if material in total_production:
            actual_outputs[material] = total_production[material]
    # Add byproducts (materials with excess that weren't requested)
    for material, excess in current_balance.items():
        if excess > 0 and material not in outputs:
            actual_outputs[material] = excess

    return actual_outputs


def _add_user_input_nodes(inputs_group, inputs: list, material_flows: dict):
    """Add user-provided input nodes."""
    for idx, (input_item, flow_rate) in enumerate(inputs):
        node_id = f"Input_{input_item.replace(' ', '_')}_{idx}"
        inputs_group.node(
            node_id,
            f"{input_item}\n{flow_rate}/min",
            shape="box",
            style="filled",
            fillcolor="orange",
        )
        material_flows[input_item]["sources"].append((node_id, flow_rate))


def _add_auto_input_nodes(
    inputs_group, inputs: list, required_raw_materials: dict, material_flows: dict
):
    """Add auto-generated input nodes for required raw materials."""
    for material, required_amount in required_raw_materials.items():
        provided_amount = sum(flow for item, flow in inputs if item == material)
        if provided_amount < required_amount:
            remaining = required_amount - provided_amount
            node_id = f"Input_{material.replace(' ', '_')}_auto"
            inputs_group.node(
                node_id,
                f"{material}\n{remaining}/min\n(auto)",
                shape="box",
                style="filled",
                fillcolor="orange",
            )
            material_flows[material]["sources"].append((node_id, remaining))


def _add_mine_nodes(inputs_group, mines: list, material_flows: dict):
    """Add mine nodes."""
    for idx, (resource, purity) in enumerate(mines):
        node_id = f"Mine_{idx}"
        flow_rate = get_mining_rate(2, purity)  # Assume Mk.3 miner
        inputs_group.node(
            node_id,
            f"Miner\n{resource}\n{flow_rate}/min",
            shape="box",
            style="filled",
            fillcolor="brown",
        )
        material_flows[resource]["sources"].append((node_id, flow_rate))


def _add_input_nodes(
    dot: graphviz.Digraph,
    inputs: list[tuple[str, float]],
    mines: list[tuple[str, Purity]],
    required_raw_materials: dict,
    material_flows: dict,
):
    """Add input and mine nodes to the graph."""
    with dot.subgraph(name="inputs") as inputs_group:
        inputs_group.attr(rank="same")
        _add_user_input_nodes(inputs_group, inputs, material_flows)
        _add_auto_input_nodes(
            inputs_group, inputs, required_raw_materials, material_flows
        )
        _add_mine_nodes(inputs_group, mines, material_flows)


def _create_single_machine_node(
    cluster, machine_node_id: int, recipe: Recipe, material_flows: dict
) -> int:
    """Create a single machine node and track its flows."""
    node_id = f"Machine_{machine_node_id}"
    cluster.node(node_id, "", shape="box", style="filled", fillcolor="white")

    for input_item, flow_rate in recipe.inputs.items():
        material_flows[input_item]["sinks"].append((node_id, flow_rate))
    for output_item, flow_rate in recipe.outputs.items():
        material_flows[output_item]["sources"].append((node_id, flow_rate))

    return machine_node_id + 1


def _add_machine_nodes(
    dot: graphviz.Digraph,
    machine_instances: dict,
    recipes_used: dict,
    material_flows: dict,
):
    """Add machine nodes to the graph."""
    machine_node_id = 0
    cluster_id = 0

    for (machine_type, recipe_name), count in machine_instances.items():
        recipe = recipes_used[(machine_type, recipe_name)]

        with dot.subgraph(name=f"cluster_{cluster_id}") as cluster:
            inputs_str = ", ".join(f"{k}:{v}" for k, v in recipe.inputs.items())
            outputs_str = ", ".join(f"{k}:{v}" for k, v in recipe.outputs.items())
            cluster.attr(label=f"{machine_type}\n{inputs_str}\n→ {outputs_str}")
            cluster.attr(style="filled", fillcolor="lightblue")

            for _ in range(count):
                machine_node_id = _create_single_machine_node(
                    cluster, machine_node_id, recipe, material_flows
                )

        cluster_id += 1


def _add_requested_output_nodes(
    requested_group,
    outputs: dict,
    total_production: dict,
    material_flows: dict,
):
    """Add nodes for requested outputs."""
    for material in outputs.keys():
        if material in total_production:
            node_id = f"Output_{material.replace(' ', '_')}"
            internal_sinks = sum(flow for _, flow in material_flows[material]["sinks"])

            if internal_sinks > 0:
                sink_amount = max(0, total_production[material] - internal_sinks)
            else:
                sink_amount = total_production[material]

            if sink_amount > 0:
                requested_group.node(
                    node_id,
                    f"{material}\n{sink_amount}/min",
                    shape="box",
                    style="filled",
                    fillcolor="lightgreen",
                )
                material_flows[material]["sinks"].append((node_id, sink_amount))


def _add_byproduct_nodes(
    byproducts_group, outputs: dict, balance: dict, material_flows: dict
):
    """Add nodes for byproducts."""
    for material, excess in balance.items():
        if excess > 0 and material not in outputs:
            node_id = f"Output_{material.replace(' ', '_')}"
            byproducts_group.node(
                node_id,
                f"{material}\n{excess}/min",
                shape="box",
                style="filled",
                fillcolor="salmon",
            )
            material_flows[material]["sinks"].append((node_id, excess))


def _add_output_nodes(
    dot: graphviz.Digraph,
    outputs: dict[str, float],
    total_production: dict,
    balance: dict,
    material_flows: dict,
):
    """Add output nodes to the graph."""
    with dot.subgraph(name="cluster_outputs") as outputs_group:
        outputs_group.attr(label="", style="invis")
        with outputs_group.subgraph(
            name="cluster_requested_outputs"
        ) as requested_group:
            requested_group.attr(label="", style="invis")
            requested_group.attr(rank="same")
            _add_requested_output_nodes(
                requested_group, outputs, total_production, material_flows
            )

        with outputs_group.subgraph(name="cluster_byproducts") as byproducts_group:
            byproducts_group.attr(label="", style="invis")
            byproducts_group.attr(rank="same")
            _add_byproduct_nodes(byproducts_group, outputs, balance, material_flows)


def _handle_direct_connection(
    dot: graphviz.Digraph, material: str, sources: list, sinks: list, sink_flows: list
):
    """Handle direct connection when there's one source and one sink."""
    source_id, _ = sources[0]
    sink_id, _ = sinks[0]
    flow_label = (
        int(sink_flows[0]) if sink_flows[0] == int(sink_flows[0]) else sink_flows[0]
    )
    dot.edge(source_id, sink_id, label=f"{material}\n{flow_label}")


def _compute_integer_flows(flows: list, target_total: int) -> list[int]:
    """Proportionally allocate integer flows ensuring they sum to target_total."""
    flows_int = []
    source_total = sum(flows)
    remaining = target_total

    for i, flow in enumerate(flows):
        if i == len(flows) - 1:
            flows_int.append(remaining)
        else:
            allocated = int(flow * target_total / source_total)
            flows_int.append(allocated)
            remaining -= allocated

    return flows_int


def _build_node_mapping(sources: list, sinks: list) -> dict:
    """Build mapping from balancer IDs to factory IDs."""
    node_mapping = {}
    for idx, (source_id, _) in enumerate(sources):
        node_mapping[f"I{idx}"] = source_id
    for idx, (sink_id, _) in enumerate(sinks):
        node_mapping[f"O{idx}"] = sink_id
    return node_mapping


def _copy_balancer_nodes(
    dot: graphviz.Digraph,
    balancer_src: str,
    material: str,
    balancer_counter: int,
    node_mapping: dict,
):
    """Copy balancer nodes (splitters/mergers) to factory graph."""
    for match in re.finditer(r'(S\d+|M\d+)\s+\[label="[^"]*"[^\]]*\]', balancer_src):
        old_id = match.group(1)
        new_id = f"{material}_{old_id}_{balancer_counter}"
        node_mapping[old_id] = new_id

        fillcolor = "lightyellow" if old_id.startswith("S") else "thistle"
        dot.node(new_id, "", shape="diamond", style="filled", fillcolor=fillcolor)


def _copy_balancer_edges(
    balancer_src: str, material: str, node_mapping: dict, dot: graphviz.Digraph
):
    """Copy balancer edges to factory graph."""
    for match in re.finditer(r"(\w+)\s+->\s+(\w+)\s+\[label=(\d+)\]", balancer_src):
        src, dst, flow = match.group(1), match.group(2), match.group(3)
        if src in node_mapping and dst in node_mapping:
            dot.edge(node_mapping[src], node_mapping[dst], label=f"{material}\n{flow}")


def _normalize_flows(source_flows: list, sink_flows: list) -> tuple[list, float, float]:
    """Normalize flows and check balance.

    Returns: (normalized_source_flows, total_source, total_sink)
    """
    total_source = sum(source_flows)
    total_sink = sum(sink_flows)

    if total_source > total_sink:
        scale = total_sink / total_source
        source_flows = [flow * scale for flow in source_flows]
        remainder = total_sink - sum(source_flows)
        if abs(remainder) > 0.01 and source_flows:
            source_flows[0] += remainder

    return source_flows, total_source, total_sink


def _create_material_balancer(
    dot: graphviz.Digraph,
    material: str,
    sources_with_flows: tuple[list, list],
    sinks_with_flows: tuple[list, list],
    balancer_counter: int,
):
    """Create and copy balancer for routing material.

    Args:
        sources_with_flows: tuple of (sources, source_flows)
        sinks_with_flows: tuple of (sinks, sink_flows)
    """
    sources, source_flows = sources_with_flows
    sinks, sink_flows = sinks_with_flows

    target_total = min(int(sum(source_flows)), int(sum(sink_flows)))
    source_flows_int = _compute_integer_flows(source_flows, target_total)
    sink_flows_int = _compute_integer_flows(sink_flows, target_total)
    balancer_graph = design_balancer(source_flows_int, sink_flows_int)

    # Copy balancer to factory graph
    balancer_src = balancer_graph.source
    node_mapping = _build_node_mapping(sources, sinks)
    _copy_balancer_nodes(dot, balancer_src, material, balancer_counter, node_mapping)
    _copy_balancer_edges(balancer_src, material, node_mapping, dot)


def _route_single_material(
    dot: graphviz.Digraph, material: str, flows: dict, balancer_counter: int
) -> int:
    """Route a single material and return updated balancer_counter."""
    sources, sinks = flows["sources"], flows["sinks"]

    if not sources or not sinks:
        return balancer_counter

    source_flows = [flow for _, flow in sources]
    sink_flows = [flow for _, flow in sinks]

    source_flows, total_source, total_sink = _normalize_flows(source_flows, sink_flows)

    if total_source < total_sink:
        print(f"Warning: Insufficient {material}: {total_source} < {total_sink}")
        return balancer_counter

    if len(sources) == 1 and len(sinks) == 1:
        _handle_direct_connection(dot, material, sources, sinks, sink_flows)
    else:
        _create_material_balancer(
            dot,
            material,
            (sources, source_flows),
            (sinks, sink_flows),
            balancer_counter,
        )
        return balancer_counter + 1

    return balancer_counter


def _route_materials_with_balancers(dot: graphviz.Digraph, material_flows: dict):
    """Route materials between sources and sinks using balancers."""
    balancer_counter = 0
    for material, flows in material_flows.items():
        balancer_counter = _route_single_material(
            dot, material, flows, balancer_counter
        )


@dataclass
class Factory:
    """A complete factory network with machines and balancers."""

    network: graphviz.Digraph
    inputs: list[tuple[str, float]]
    outputs: dict[str, float]
    mines: list[tuple[str, Purity]]


def _apply_machine_balance(balance: dict, machine_instances: dict, recipes_used: dict):
    """Apply machine inputs/outputs to balance."""
    for (machine_type, recipe_name), count in machine_instances.items():
        recipe = recipes_used[(machine_type, recipe_name)]
        for input_item, amount in recipe.inputs.items():
            balance[input_item] -= amount * count
        for output_item, amount in recipe.outputs.items():
            balance[output_item] += amount * count


def _recompute_balance_for_outputs(
    inputs: list[tuple[str, float]],
    mines: list[tuple[str, Purity]],
    outputs: dict[str, float],
    machine_instances: dict,
    recipes_used: dict,
) -> dict:
    """Recompute material balance after machine calculation."""
    balance = _initialize_balance(outputs, inputs, mines)
    _apply_machine_balance(balance, machine_instances, recipes_used)
    return balance


def design_factory(
    outputs: dict[str, float],
    inputs: list[tuple[str, float]],
    mines: list[tuple[str, Purity]],
    enablement_set: set[str] | None = None,
) -> Factory:
    """Design a complete factory network with machines and balancers.

    Args:
        outputs: desired output materials and rates (e.g., {"Iron Plate": 100})
        inputs: list of (material, flow_rate) tuples for input conveyors
            (e.g., [("Iron Ore", 200), ("Iron Ore", 200)])
        mines: list of (resource_name, purity) tuples for mining nodes

    Returns:
        Factory with complete network graph including machines and balancers
    """
    # Phase 1: Calculate required machines
    machine_instances, recipes_used, required_raw_materials, total_production = (
        _calculate_machines(outputs, inputs, mines, enablement_set)
    )

    # Recompute balance for output calculation
    balance = _recompute_balance_for_outputs(
        inputs, mines, outputs, machine_instances, recipes_used
    )

    # Compute actual outputs
    actual_outputs = _compute_actual_outputs(outputs, total_production, balance)

    # Phase 2: Build network graph with balancers
    dot = graphviz.Digraph(comment="Factory Network")
    dot.attr(rankdir="LR")

    # Track material flows: {material: {"sources": [...], "sinks": [...]}}
    material_flows = defaultdict(lambda: {"sources": [], "sinks": []})

    # Add input and mine nodes
    _add_input_nodes(dot, inputs, mines, required_raw_materials, material_flows)

    # Add machine nodes
    _add_machine_nodes(dot, machine_instances, recipes_used, material_flows)

    # Add output nodes
    _add_output_nodes(dot, outputs, total_production, balance, material_flows)

    # Phase 3: Route materials with balancers
    _route_materials_with_balancers(dot, material_flows)

    return Factory(dot, inputs, actual_outputs, mines)


def build_graph() -> graphviz.Digraph:
    """Build a simple factory graph with default styling."""
    dot = graphviz.Digraph(comment="Factory")
    dot.attr(rankdir="LR")
    dot.attr("node", shape="box", style="filled", fillcolor="lightblue")
    dot.attr("edge", color="gray")
    return dot


if __name__ == "__main__":
    result_factory = design_factory({"Iron Plate": 100}, {}, {})
