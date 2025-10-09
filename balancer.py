from graphviz import Digraph
from collections import defaultdict

def design_balancer(inputs: list[int], outputs: list[int]) -> Digraph:
    """Design an optimal balancer network using splitters and mergers.
    
    Args:
        inputs: list of input flow rates
        outputs: list of output flow rates
        
    Returns:
        Digraph representing the optimal balancer network
        
    Raises:
        ValueError: if total input flow doesn't equal total output flow
    """
    # Check feasibility
    if sum(inputs) != sum(outputs):
        raise ValueError(f"Total input flow {sum(inputs)} must equal total output flow {sum(outputs)}")

    # Phase 1: Flow assignment - greedily assign inputs to outputs
    flow_matrix = defaultdict(lambda: defaultdict(int))  # flow_matrix[input_idx][output_idx] = flow_amount

    available_inputs = [(idx, flow) for idx, flow in enumerate(inputs)]

    for out_idx, required_flow in enumerate(outputs):
        remaining = required_flow

        while remaining > 0 and available_inputs:
            in_idx, in_flow = available_inputs.pop(0)

            if in_flow <= remaining:
                flow_matrix[in_idx][out_idx] = in_flow
                remaining -= in_flow
            else:
                flow_matrix[in_idx][out_idx] = remaining
                available_inputs.insert(0, (in_idx, in_flow - remaining))
                remaining = 0

    # Phase 2: Build graph with optimal split/merge trees
    dot = Digraph()
    dot.attr(rankdir='LR')

    # Add input nodes without flow labels
    for idx in range(len(inputs)):
        dot.node(f"I{idx}", f"Input {idx}",
                shape='box', style='filled', fillcolor='lightgreen')

    # Add output nodes without flow labels
    for idx in range(len(outputs)):
        dot.node(f"O{idx}", f"Output {idx}",
                shape='box', style='filled', fillcolor='lightblue')

    device_counter = [0]  # Use list for mutability in nested function

    def build_split_tree(source_id: str, flows_dict: dict[int, int]) -> dict[int, tuple[str, int]]:
        """Build optimal split tree for one source feeding multiple destinations.
        Build bottom-up: each output starts as a root, group 3 at a time until one root remains.
        flows_dict: {dest_id: flow_amount}
        Returns: {dest_id: (node_id, flow)} mapping destinations to their immediate source nodes
        """
        if len(flows_dict) == 1:
            dest_id = list(flows_dict.keys())[0]
            flow = flows_dict[dest_id]
            return {dest_id: (source_id, flow)}

        # Sort destinations for consistent output
        destinations = sorted(flows_dict.items(), key=lambda x: (x[1], x[0]), reverse=True)
        
        # Build tree bottom-up: start with leaves (conceptual outputs)
        # Each root is (node_id, {dest_id: flow, ...})
        # We use placeholder IDs for leaves, then replace with actual splitters
        roots: list[tuple[str, dict[int, int]]] = []
        for dest_id, flow in destinations:
            roots.append((f"_leaf_{dest_id}", {dest_id: flow}))
        
        # Track which actual node feeds each destination
        dest_sources: dict[int, tuple[str, int]] = {}
        
        # Group roots together until only one remains
        while len(roots) > 1:
            remaining = len(roots)
            
            if remaining >= 3:
                # Group first 3 roots under a new splitter
                group = roots[:3]
                roots = roots[3:]
                
                splitter_id = f"S{device_counter[0]}"
                device_counter[0] += 1
                dot.node(splitter_id, "",
                        shape='diamond', style='filled', fillcolor='lightyellow')
                
                # Create edges from splitter to children and track destinations
                merged_dests = {}
                for child_id, child_dests in group:
                    child_flow = sum(child_dests.values())
                    
                    # If child is a leaf, we're connecting splitter -> (eventual output)
                    # If child is another splitter, create edge splitter -> splitter
                    if child_id.startswith("_leaf_"):
                        # This is a direct connection to a destination
                        # Record that this splitter feeds this destination
                        for dest_id in child_dests.keys():
                            dest_sources[dest_id] = (splitter_id, child_dests[dest_id])
                    else:
                        # Edge to another splitter
                        dot.edge(splitter_id, child_id, label=str(child_flow))
                    
                    merged_dests.update(child_dests)
                
                # Add new root
                roots.append((splitter_id, merged_dests))
            else:
                # remaining == 2, use 2-way split
                group = roots[:2]
                roots = roots[2:]
                
                splitter_id = f"S{device_counter[0]}"
                device_counter[0] += 1
                dot.node(splitter_id, "",
                        shape='diamond', style='filled', fillcolor='lightyellow')
                
                merged_dests = {}
                for child_id, child_dests in group:
                    child_flow = sum(child_dests.values())
                    
                    if child_id.startswith("_leaf_"):
                        for dest_id in child_dests.keys():
                            dest_sources[dest_id] = (splitter_id, child_dests[dest_id])
                    else:
                        dot.edge(splitter_id, child_id, label=str(child_flow))
                    
                    merged_dests.update(child_dests)
                
                roots.append((splitter_id, merged_dests))
        
        # Now we have one root - connect it to the source
        root_id, root_dests = roots[0]
        root_flow = sum(root_dests.values())
        dot.edge(source_id, root_id, label=str(root_flow))
        
        # Return mapping - for each destination, record which node feeds it
        result: dict[int, tuple[str, int]] = {}
        for dest_id, flow in flows_dict.items():
            if dest_id in dest_sources:
                result[dest_id] = dest_sources[dest_id]
            else:
                # Single root case - the root itself feeds this destination
                result[dest_id] = (root_id, flow)
        
        return result

    def build_merge_tree(flows_dict, _dest_id):
        """Build optimal merge tree for multiple sources feeding one destination.
        flows_dict: {source_id: flow_amount}
        Returns: node_id of the merged flow
        """
        if len(flows_dict) == 1:
            return list(flows_dict.keys())[0]

        # Sort sources for consistent output
        sources = sorted(flows_dict.items(), key=lambda x: (x[1], x[0]), reverse=True)

        # Build optimal merge tree using greedy approach
        # Start with all sources as separate streams
        streams = [(src_id, flow) for src_id, flow in sources]

        # Merge streams until we have just one
        while len(streams) > 1:
            remaining = len(streams)

            if remaining >= 3:
                # Use 3-way merge
                merger_id = f"M{device_counter[0]}"
                device_counter[0] += 1
                # Take first 3 streams
                to_merge = streams[:3]
                streams = streams[3:]
                merge_flow = sum(flow for _, flow in to_merge)
                dot.node(merger_id, "",
                        shape='diamond', style='filled', fillcolor='lightcoral')
                for source_id, flow in to_merge:
                    dot.edge(source_id, merger_id, label=str(flow))
                # Add merged stream back
                streams.append((merger_id, merge_flow))
            else:
                # remaining == 2, use 2-way merge
                merger_id = f"M{device_counter[0]}"
                device_counter[0] += 1
                to_merge = streams[:2]
                streams = streams[2:]
                merge_flow = sum(flow for _, flow in to_merge)
                dot.node(merger_id, "",
                        shape='diamond', style='filled', fillcolor='lightcoral')
                for source_id, flow in to_merge:
                    dot.edge(source_id, merger_id, label=str(flow))
                streams.append((merger_id, merge_flow))

        return streams[0][0]

    # Build split trees for each input
    input_outputs = {}  # {input_idx: {output_idx: (source_node_id, flow)}}
    for in_idx, out_flows in flow_matrix.items():
        input_outputs[in_idx] = build_split_tree(f"I{in_idx}", out_flows)

    # Build merge trees for each output and create final edges
    for out_idx in range(len(outputs)):
        # Collect all sources for this output (from split trees)
        sources = {}
        for in_idx, out_flows in flow_matrix.items():
            if out_idx in out_flows:
                source_node, flow = input_outputs[in_idx][out_idx]
                sources[source_node] = flow

        if len(sources) == 1:
            # Direct connection - no merge needed
            source_node = list(sources.keys())[0]
            flow = sources[source_node]
            dot.edge(source_node, f"O{out_idx}", label=str(flow))
        elif len(sources) > 1:
            # Need to merge
            merged_node = build_merge_tree(sources, f"O{out_idx}")
            final_flow = sum(sources.values())
            dot.edge(merged_node, f"O{out_idx}", label=str(final_flow))

    return dot

