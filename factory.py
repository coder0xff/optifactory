"""Factory design system for Satisfactory production chains."""

import re
from dataclasses import dataclass
from collections import defaultdict

import graphviz
from balancer import design_balancer
from recipes import Purity, get_mining_rate, Recipe, get_all_recipes, get_fluids, get_fluid_color
from optimize import optimize_recipes


def _is_fluid(material: str) -> bool:
    """Check if a material is a fluid.

    Precondition:
        material is a string

    Postcondition:
        returns True if material is in the fluids set
        returns False otherwise

    Args:
        material: material name to check

    Returns:
        True if material is a fluid, False otherwise
    """
    return material in get_fluids()


def _get_conveyor_mark(flow_rate: float) -> int:
    """Determine which conveyor mark is needed for a given flow rate.

    Precondition:
        flow_rate is a non-negative float

    Postcondition:
        returns mark (1-4) that can handle the flow_rate
        Mark 1: 60/min, Mark 2: 120/min, Mark 3: 270/min, Mark 4: 480/min
        returns 4 for rates exceeding 480/min

    Args:
        flow_rate: items per minute to transport

    Returns:
        conveyor belt mark number (1-4)
    """
    conveyor_speeds = [60, 120, 270, 480]
    for mark, speed in enumerate(conveyor_speeds, start=1):
        if flow_rate <= speed:
            return mark
    return 4  # default to mark 4 for anything higher


def _get_pipeline_mark(flow_rate: float) -> int:
    """Determine which pipeline mark is needed for a given flow rate.

    Precondition:
        flow_rate is a non-negative float

    Postcondition:
        returns mark (1-2) that can handle the flow_rate
        Mark 1: 300/min, Mark 2: 600/min
        returns 2 for rates exceeding 600/min

    Args:
        flow_rate: units of fluid per minute to transport

    Returns:
        pipeline mark number (1-2)
    """
    pipeline_speeds = [300, 600]
    for mark, speed in enumerate(pipeline_speeds, start=1):
        if flow_rate <= speed:
            return mark
    return 2  # default to mark 2 for anything higher


def _get_conveyor_stripe_color(mark: int) -> str:
    """Generate graphviz color string with alternating black and white stripes.

    Precondition:
        mark is a positive integer (1-4)

    Postcondition:
        returns colon-separated color string for graphviz
        number of black stripes equals mark number
        white stripes are between black stripes
        Mark 1: "black"
        Mark 2: "black:white:black"
        Mark 3: "black:white:black:white:black"
        Mark 4: "black:white:black:white:black:white:black"

    Args:
        mark: conveyor belt mark number

    Returns:
        graphviz color specification string
    """
    stripes = []
    for i in range(mark):
        stripes.append("black")
        if i < mark - 1:  # don't add white after the last black
            stripes.append("white")
    return ":".join(stripes)


def _get_pipeline_stripe_color(mark: int, fluid: str) -> str:
    """Generate graphviz color string with grey and fluid color stripes.

    Precondition:
        mark is 1 or 2
        fluid is a valid fluid name

    Postcondition:
        returns colon-separated color string for graphviz
        includes fluid's color surrounded by grey markers
        Mark 1: "grey:color:color:grey"
        Mark 2: "grey:color:color:color:color:color:grey"

    Args:
        mark: pipeline mark number
        fluid: fluid name for color lookup

    Returns:
        graphviz color specification string
    """
    color = get_fluid_color(fluid)
    if mark == 1:
        return f"grey:{color}:{color}:grey"
    else:  # mark 2
        return f"grey:{color}:{color}:{color}:{color}:{color}:grey"


def _get_edge_color(material: str, flow_rate: float) -> str:
    """Get the edge color for a given material and flow rate.

    Precondition:
        material is a string (material name)
        flow_rate is a non-negative float

    Postcondition:
        if material is a fluid, returns pipeline stripe color
        if material is not a fluid, returns conveyor stripe color
        returned string is a graphviz color specification

    Args:
        material: material name
        flow_rate: units per minute

    Returns:
        graphviz color specification string
    """
    if _is_fluid(material):
        mark = _get_pipeline_mark(flow_rate)
        return _get_pipeline_stripe_color(mark, material)
    else:
        mark = _get_conveyor_mark(flow_rate)
        return _get_conveyor_stripe_color(mark)


def _initialize_balance(
    outputs: dict[str, float],
    inputs: list[tuple[str, float]],
    mines: list[tuple[str, Purity]],
) -> dict:
    """Initialize material balance with inputs, mines, and output requirements.

    Precondition:
        outputs is a dict mapping material names to required amounts
        inputs is a list of (material, flow_rate) tuples
        mines is a list of (resource, Purity) tuples

    Postcondition:
        returns defaultdict(float) with material balances
        inputs and mines contribute positive flow
        outputs contribute negative flow
        mining rates assume Mk.3 miners

    Args:
        outputs: required output materials and amounts
        inputs: available input materials and rates
        mines: resource mines with purity levels

    Returns:
        material balance dictionary
    """
    balance = defaultdict(float)

    for material, flow_rate in inputs:
        balance[material] += flow_rate

    for resource, purity in mines:
        balance[resource] += get_mining_rate(2, purity)  # Assume Mk.3 miner

    for output_item, amount in outputs.items():
        balance[output_item] -= amount

    return balance


def _build_optimizer_inputs(
    inputs: list[tuple[str, float]], mines: list[tuple[str, Purity]]
) -> dict[str, float]:
    """Build input materials dict for optimizer from inputs and mines.

    Precondition:
        inputs is a list of (material, flow_rate) tuples
        mines is a list of (resource, Purity) tuples

    Postcondition:
        returns dict mapping materials to available flow rates
        includes both provided inputs and calculated mine outputs

    Args:
        inputs: available input materials and rates
        mines: resource mines with purity levels

    Returns:
        dict of material names to flow rates
    """
    inputs_dict = defaultdict(float)
    for material, flow_rate in inputs:
        inputs_dict[material] += flow_rate
    
    for resource, purity in mines:
        inputs_dict[resource] += get_mining_rate(2, purity)
    
    return dict(inputs_dict)


def _transform_optimizer_output(
    recipe_counts: dict[str, float]
) -> tuple[dict, dict, dict]:
    """Transform optimizer output into machine instances, recipes, and total production.

    Precondition:
        recipe_counts is a dict mapping recipe names to machine counts

    Postcondition:
        returns tuple of (machine_instances, recipes_used, total_production)
        machine_instances maps (machine, recipe_name) to int count
        recipes_used maps (machine, recipe_name) to Recipe object
        total_production maps materials to total output rates

    Args:
        recipe_counts: optimizer output mapping recipe names to counts

    Returns:
        tuple of (machine_instances, recipes_used, total_production) dicts
    """
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
    
    return machine_instances, recipes_used, total_production


def _compute_required_raw_materials(
    recipe_counts: dict[str, float],
    outputs: dict[str, float],
    inputs: list[tuple[str, float]],
    mines: list[tuple[str, Purity]],
) -> dict[str, float]:
    """Compute required raw materials from final balance.

    Precondition:
        recipe_counts maps recipe names to machine counts
        outputs is dict of required output materials
        inputs is list of available inputs
        mines is list of resource mines

    Postcondition:
        returns dict mapping materials to required amounts
        only includes materials with negative balance (shortfalls)

    Args:
        recipe_counts: optimizer output
        outputs: required outputs
        inputs: available inputs
        mines: resource mines

    Returns:
        dict of material shortfalls
    """
    balance = _initialize_balance(outputs, inputs, mines)
    all_recipes = get_all_recipes()
    
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
    
    return required_raw_materials


def _calculate_machines(
    outputs: dict[str, float],
    inputs: list[tuple[str, float]],
    mines: list[tuple[str, Purity]],
    enablement_set: set[str] | None,
    economy: dict[str, float] | None,
    input_costs_weight: float,
    machine_counts_weight: float,
    power_consumption_weight: float,
    design_power: bool,
) -> tuple[dict, dict, dict, dict]:
    """Calculate required machines and material balance.

    Precondition:
        outputs is dict of required output materials and amounts
        inputs is list of available input materials and rates
        mines is list of resource mines with purity
        enablement_set is set of enabled recipes or None
        economy is dict of material values or None
        weights are floats for optimization
        design_power is bool

    Postcondition:
        returns tuple of (machine_instances, recipes_used, required_raw_materials, total_production)
        machine_instances maps (machine, recipe) to counts
        recipes_used maps (machine, recipe) to Recipe objects
        required_raw_materials maps materials to shortfall amounts
        total_production maps materials to total output rates

    Args:
        outputs: required output materials and amounts
        inputs: available input materials and rates
        mines: resource mines with purity levels
        enablement_set: enabled recipes or None
        economy: material values or None
        input_costs_weight: optimization weight
        machine_counts_weight: optimization weight
        power_consumption_weight: optimization weight
        design_power: whether to design power generation

    Returns:
        tuple of (machine_instances, recipes_used, required_raw_materials, total_production)
    """
    # Build inputs dict for optimizer
    inputs_dict = _build_optimizer_inputs(inputs, mines)
    
    # Call optimizer - returns {recipe_name: machine_count}
    recipe_counts = optimize_recipes(
        inputs=inputs_dict,
        outputs=outputs,
        enablement_set=enablement_set,
        economy=economy,
        input_costs_weight=input_costs_weight,
        machine_counts_weight=machine_counts_weight,
        power_consumption_weight=power_consumption_weight,
        design_power=design_power,
    )
    
    # Transform optimizer output to existing format
    machine_instances, recipes_used, total_production = _transform_optimizer_output(recipe_counts)
    
    # Compute required_raw_materials by checking final balance
    required_raw_materials = _compute_required_raw_materials(
        recipe_counts, outputs, inputs, mines
    )
    
    return (
        machine_instances,
        recipes_used,
        required_raw_materials,
        total_production,
    )


def _compute_actual_outputs(
    outputs: dict[str, float], total_production: dict, balance: dict
) -> dict[str, float]:
    """Compute actual factory outputs including byproducts.

    Precondition:
        outputs is dict of requested output materials
        total_production is dict of materials to production rates
        balance is dict of material balances (positive = excess)

    Postcondition:
        returns dict of all factory outputs
        includes requested outputs from total_production
        includes byproducts (excess materials not requested)

    Args:
        outputs: requested output materials
        total_production: total production rates
        balance: material balances

    Returns:
        dict mapping materials to output rates
    """
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
    """Add user-provided input nodes to graphviz graph.

    Precondition:
        inputs_group is graphviz subgraph
        inputs is list of (material, flow_rate) tuples
        material_flows is dict with "sources" lists

    Postcondition:
        orange box nodes are added to inputs_group for each input
        material_flows["sources"] lists are updated with node IDs and rates

    Args:
        inputs_group: graphviz subgraph for inputs
        inputs: list of input materials and rates
        material_flows: dict tracking material sources
    """
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
    """Add auto-generated input nodes for required raw materials.

    Precondition:
        inputs_group is graphviz subgraph
        inputs is list of provided inputs
        required_raw_materials is dict of material shortfalls
        material_flows is dict with "sources" lists

    Postcondition:
        orange "(auto)" nodes are added for materials with shortfalls
        material_flows["sources"] lists are updated with node IDs and rates

    Args:
        inputs_group: graphviz subgraph for inputs
        inputs: list of provided input materials and rates
        required_raw_materials: dict of material shortfalls
        material_flows: dict tracking material sources
    """
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
    """Add mine nodes to graphviz graph.

    Precondition:
        inputs_group is graphviz subgraph
        mines is list of (resource, Purity) tuples
        material_flows is dict with "sources" lists

    Postcondition:
        brown box miner nodes are added for each mine
        mining rates assume Mk.3 miners
        material_flows["sources"] lists are updated with node IDs and rates

    Args:
        inputs_group: graphviz subgraph for inputs
        mines: list of resource mines with purity levels
        material_flows: dict tracking material sources
    """
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
    """Add input and mine nodes to the graph.

    Precondition:
        dot is graphviz.Digraph
        inputs is list of input materials
        mines is list of resource mines
        required_raw_materials is dict of shortfalls
        material_flows is dict with "sources" lists

    Postcondition:
        creates "inputs" subgraph with rank="same"
        calls helpers to add user inputs, auto inputs, and mines

    Args:
        dot: main graphviz digraph
        inputs: list of input materials and rates
        mines: list of resource mines with purity
        required_raw_materials: dict of material shortfalls
        material_flows: dict tracking material sources
    """
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
    """Create a single machine node and track its flows.

    Precondition:
        cluster is graphviz subgraph
        machine_node_id is int counter
        recipe is Recipe object with inputs and outputs
        material_flows is dict with "sources" and "sinks" lists

    Postcondition:
        white box machine node is added to cluster
        material_flows["sinks"] updated with recipe inputs
        material_flows["sources"] updated with recipe outputs
        returns incremented machine_node_id

    Args:
        cluster: graphviz subgraph/cluster for machine group
        machine_node_id: current machine ID counter
        recipe: Recipe defining inputs and outputs
        material_flows: dict tracking material sources and sinks

    Returns:
        incremented machine_node_id
    """
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
    """Add machine nodes to the graph.

    Precondition:
        dot is graphviz.Digraph
        machine_instances maps (machine, recipe) to counts
        recipes_used maps (machine, recipe) to Recipe objects
        material_flows is dict with "sources" and "sinks" lists

    Postcondition:
        creates labeled lightblue clusters for each machine type/recipe
        adds individual machine nodes within each cluster
        material_flows updated with all machine flows

    Args:
        dot: main graphviz digraph
        machine_instances: dict mapping (machine, recipe) to counts
        recipes_used: dict mapping (machine, recipe) to Recipe objects
        material_flows: dict tracking material sources and sinks
    """
    machine_node_id = 0
    cluster_id = 0

    for (machine_type, recipe_name), count in machine_instances.items():
        recipe = recipes_used[(machine_type, recipe_name)]

        with dot.subgraph(name=f"cluster_{cluster_id}") as cluster:
            inputs_str = ", ".join(f"{k}:{v}" for k, v in recipe.inputs.items())
            outputs_str = ", ".join(f"{k}:{v}" for k, v in recipe.outputs.items())
            cluster.attr(label=f"{machine_type} - {recipe_name}\n{inputs_str}\n→ {outputs_str}")
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
    """Add nodes for requested outputs.

    Precondition:
        requested_group is graphviz subgraph
        outputs is dict of requested output materials
        total_production is dict of production rates
        material_flows is dict with "sinks" lists

    Postcondition:
        lightgreen box nodes are added for requested outputs
        sink amounts account for internal consumption
        material_flows["sinks"] lists are updated

    Args:
        requested_group: graphviz subgraph for requested outputs
        outputs: dict of requested output materials
        total_production: dict of total production rates
        material_flows: dict tracking material sources and sinks
    """
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
    """Add nodes for byproducts.

    Precondition:
        byproducts_group is graphviz subgraph
        outputs is dict of requested outputs
        balance is dict of material balances
        material_flows is dict with "sinks" lists

    Postcondition:
        salmon box nodes are added for byproducts (excess unrequested materials)
        material_flows["sinks"] lists are updated

    Args:
        byproducts_group: graphviz subgraph for byproducts
        outputs: dict of requested output materials
        balance: dict of material balances (positive = excess)
        material_flows: dict tracking material sources and sinks
    """
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
    """Add output nodes to the graph.

    Precondition:
        dot is graphviz.Digraph
        outputs is dict of requested outputs
        total_production is dict of production rates
        balance is dict of material balances
        material_flows is dict tracking material flows

    Postcondition:
        creates invisible output cluster containing:
            - requested outputs subgraph
            - byproducts subgraph

    Args:
        dot: main graphviz digraph
        outputs: dict of requested output materials
        total_production: dict of total production rates
        balance: dict of material balances
        material_flows: dict tracking material sources and sinks
    """
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
    """Handle direct connection when there's one source and one sink.

    Precondition:
        dot is graphviz.Digraph
        material is string
        sources has exactly 1 element (node_id, flow)
        sinks has exactly 1 element (node_id, flow)
        sink_flows has exactly 1 element

    Postcondition:
        adds edge from source to sink with material label and colored by flow rate
        flow label is integer if possible, otherwise float

    Args:
        dot: graphviz digraph
        material: material name
        sources: list with one (node_id, flow) tuple
        sinks: list with one (node_id, flow) tuple
        sink_flows: list with one flow rate
    """
    source_id, _ = sources[0]
    sink_id, _ = sinks[0]
    flow_label = (
        int(sink_flows[0]) if sink_flows[0] == int(sink_flows[0]) else sink_flows[0]
    )
    color = _get_edge_color(material, sink_flows[0])
    dot.edge(source_id, sink_id, label=f"{material}\n{flow_label}", color=color, penwidth="2")


def _compute_integer_flows(flows: list, target_total: int) -> list[int]:
    """Proportionally allocate integer flows ensuring they sum to target_total.

    Precondition:
        flows is list of numeric flow rates
        target_total is positive integer

    Postcondition:
        returns list of integers same length as flows
        sum of returned list equals target_total
        proportions maintained as closely as possible
        last element gets any remaining to ensure exact sum

    Args:
        flows: list of flow rates to allocate
        target_total: target sum for integer flows

    Returns:
        list of integer flows summing to target_total
    """
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
    """Build mapping from balancer IDs to factory IDs.

    Precondition:
        sources is list of (node_id, flow) tuples
        sinks is list of (node_id, flow) tuples

    Postcondition:
        returns dict mapping balancer IDs to factory node IDs
        "I{idx}" maps to source node_ids
        "O{idx}" maps to sink node_ids

    Args:
        sources: list of source (node_id, flow) tuples
        sinks: list of sink (node_id, flow) tuples

    Returns:
        dict mapping balancer IDs to factory node IDs
    """
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
    """Copy balancer nodes (splitters/mergers) to factory graph.

    Precondition:
        dot is graphviz.Digraph
        balancer_src is graphviz source string
        material is string
        balancer_counter is int
        node_mapping is dict

    Postcondition:
        diamond nodes added to dot for each splitter/merger
        lightyellow for splitters (S prefix)
        thistle for mergers (M prefix)
        node_mapping updated with old_id -> new_id mappings

    Args:
        dot: main graphviz digraph
        balancer_src: graphviz source string from balancer
        material: material name for node ID
        balancer_counter: counter for unique IDs
        node_mapping: dict to update with ID mappings
    """
    for match in re.finditer(r'(S\d+|M\d+)\s+\[label="[^"]*"[^\]]*\]', balancer_src):
        old_id = match.group(1)
        new_id = f"{material}_{old_id}_{balancer_counter}"
        node_mapping[old_id] = new_id

        fillcolor = "lightyellow" if old_id.startswith("S") else "thistle"
        dot.node(new_id, "", shape="diamond", style="filled", fillcolor=fillcolor)


def _copy_balancer_edges(
    balancer_src: str, material: str, node_mapping: dict, dot: graphviz.Digraph
):
    """Copy balancer edges to factory graph.

    Precondition:
        balancer_src is graphviz source string
        material is string
        node_mapping is dict mapping old IDs to new IDs
        dot is graphviz.Digraph

    Postcondition:
        colored edges added to dot for each balancer connection
        labels include material name and flow rate
        colors based on flow rate and material type

    Args:
        balancer_src: graphviz source string from balancer
        material: material name
        node_mapping: dict mapping old IDs to new IDs
        dot: main graphviz digraph
    """
    for match in re.finditer(r"(\w+)\s+->\s+(\w+)\s+\[label=(\d+)\]", balancer_src):
        src, dst, flow = match.group(1), match.group(2), match.group(3)
        if src in node_mapping and dst in node_mapping:
            flow_rate = float(flow)
            color = _get_edge_color(material, flow_rate)
            dot.edge(node_mapping[src], node_mapping[dst], label=f"{material}\n{flow}", color=color, penwidth="2")


def _create_material_balancer(
    dot: graphviz.Digraph,
    material: str,
    sources_with_flows: tuple[list, list],
    sinks_with_flows: tuple[list, list],
    balancer_counter: int,
):
    """Create and copy balancer for routing material.

    Precondition:
        dot is graphviz.Digraph
        material is string
        sources_with_flows is tuple of (sources list, source_flows list)
        sinks_with_flows is tuple of (sinks list, sink_flows list)
        balancer_counter is int

    Postcondition:
        balancer nodes and edges added to dot
        flows converted to integers for balancer design
        node mapping created and used for ID translation

    Args:
        dot: main graphviz digraph
        material: material name
        sources_with_flows: tuple of (sources, source_flows)
        sinks_with_flows: tuple of (sinks, sink_flows)
        balancer_counter: counter for unique IDs
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
    """Route a single material and return updated balancer_counter.

    Precondition:
        dot is graphviz.Digraph
        material is string
        flows is dict with "sources" and "sinks" keys containing lists
        balancer_counter is int

    Postcondition:
        if insufficient material, prints warning and returns unchanged counter
        if 1 source and 1 sink, uses direct connection
        otherwise creates balancer and increments counter
        returns updated balancer_counter

    Args:
        dot: main graphviz digraph
        material: material name
        flows: dict with "sources" and "sinks" lists
        balancer_counter: current counter value

    Returns:
        updated balancer_counter
    """
    sources, sinks = flows["sources"], flows["sinks"]

    assert len(sources) > 0 and len(sinks) > 0, f"No sources or sinks for {material}"

    source_flows = [flow for _, flow in sources]
    sink_flows = [flow for _, flow in sinks]

    total_source = sum(source_flows)
    total_sink = sum(sink_flows)

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
    """Route materials between sources and sinks using balancers.

    Precondition:
        dot is graphviz.Digraph
        material_flows is dict mapping materials to flow dicts

    Postcondition:
        all materials (except MWm/electricity) are routed
        balancers created as needed for complex routing

    Args:
        dot: main graphviz digraph
        material_flows: dict mapping materials to source/sink flows
    """
    balancer_counter = 0
    for material, flows in material_flows.items():
        if material == "MWm":  # skip electricity - doesn't need balancing
            continue
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
    """Apply machine inputs/outputs to balance.

    Precondition:
        balance is dict mapping materials to float
        machine_instances is dict mapping (machine_type, recipe_name) to count
        recipes_used is dict mapping (machine_type, recipe_name) to Recipe
        all keys in machine_instances exist in recipes_used

    Postcondition:
        balance is mutated in-place
        input materials decreased by consumption amounts
        output materials increased by production amounts
    """
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
    """Recompute material balance after machine calculation.

    Precondition:
        inputs is list of (material, rate) tuples
        mines is list of (resource, Purity) tuples
        outputs is dict mapping materials to desired rates
        machine_instances is dict mapping (machine_type, recipe_name) to count
        recipes_used is dict mapping (machine_type, recipe_name) to Recipe

    Postcondition:
        returns dict mapping materials to net flow
        negative values indicate deficit (need input)
        positive values indicate surplus (available as output)
    """
    balance = _initialize_balance(outputs, inputs, mines)
    _apply_machine_balance(balance, machine_instances, recipes_used)
    return balance


def design_factory(
    outputs: dict[str, float],
    inputs: list[tuple[str, float]],
    mines: list[tuple[str, Purity]],
    enablement_set: set[str] | None = None,
    economy: dict[str, float] | None = None,
    input_costs_weight: float = 1.0,
    machine_counts_weight: float = 0.0,
    power_consumption_weight: float = 1.0,
    design_power: bool = False,
) -> Factory:
    """Design a complete factory network with machines and balancers.

    Precondition:
        outputs is dict mapping materials to desired rates (non-negative)
        inputs is list of (material, rate) tuples
        mines is list of (resource, Purity) tuples
        enablement_set is None or set of enabled recipe names
        economy is None or dict mapping materials to values
        input_costs_weight >= 0
        machine_counts_weight >= 0
        power_consumption_weight >= 0
        design_power is bool

    Postcondition:
        returns Factory with complete network graph
        Factory.network contains all nodes and edges with balancers
        Factory.inputs matches input parameter
        Factory.outputs reflects actual producible outputs
        Factory.mines matches mines parameter

    Args:
        outputs: desired output materials and rates (e.g., {"Iron Plate": 100})
        inputs: list of (material, flow_rate) tuples for input conveyors
            (e.g., [("Iron Ore", 200), ("Iron Ore", 200)])
        mines: list of (resource_name, purity) tuples for mining nodes
        enablement_set: set of enabled recipe names or None for defaults
        economy: dict of material values for cost optimization
        input_costs_weight: optimization weight for input costs
        machine_counts_weight: optimization weight for machine counts
        power_consumption_weight: optimization weight for power usage
        design_power: whether to include power generation in the design

    Returns:
        Factory with complete network graph including machines and balancers
    """
    # Phase 1: Calculate required machines
    machine_instances, recipes_used, required_raw_materials, total_production = (
        _calculate_machines(
            outputs,
            inputs,
            mines,
            enablement_set,
            economy,
            input_costs_weight,
            machine_counts_weight,
            power_consumption_weight,
            design_power,
        )
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
