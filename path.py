from graphviz import Digraph
from collections import defaultdict

def split_merge_path(i: list[int], o: list[int]) -> Digraph:
    """Find the minimum number of 2 splits, 3 splits, 2 merges, and 3 merges to supply o outputs from i inputs."""
    # Check feasibility
    if sum(i) != sum(o):
        raise ValueError(f"Total input flow {sum(i)} must equal total output flow {sum(o)}")

    # Phase 1: Flow assignment - greedily assign inputs to outputs
    flow_matrix = defaultdict(lambda: defaultdict(int))  # flow_matrix[input_idx][output_idx] = flow_amount

    available_inputs = [(idx, flow) for idx, flow in enumerate(i)]

    for out_idx, required_flow in enumerate(o):
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

    # Add input nodes
    for idx, flow in enumerate(i):
        dot.node(f"I{idx}", f"Input {idx}\n{flow}",
                shape='box', style='filled', fillcolor='lightgreen')

    # Add output nodes
    for idx, flow in enumerate(o):
        dot.node(f"O{idx}", f"Output {idx}\n{flow}",
                shape='box', style='filled', fillcolor='lightblue')

    device_counter = [0]  # Use list for mutability in nested function

    def build_split_tree(source_id: str, flows_dict: dict[str, int]) -> dict[str, list[str]]:
        """Build optimal split tree for one source feeding multiple destinations.
        flows_dict: {dest_id: flow_amount}
        Returns: {dest_id: node_id} mapping destinations to their source nodes
        """
        if len(flows_dict) == 1:
            return {list(flows_dict.keys())[0]: source_id}

        # Sort destinations for consistent output
        destinations = sorted(flows_dict.items(), key=lambda x: (x[1], x[0]), reverse=True)
        n_outputs = len(destinations)

        # Build optimal tree using greedy leaf expansion
        # Start with source as single leaf
        leaves: list[str] = [source_id]  # nodes that haven't been assigned to destinations yet

        # Expand leaves until we have enough for all destinations
        while len(leaves) < n_outputs:
            # Take the first leaf and split it
            node_to_split = leaves.pop(0)
            remaining_needed = n_outputs - len(leaves)

            if remaining_needed >= 2:
                # Use 3-way split (creates 3 outputs from 1 input, net +2)
                splitter_id = f"S{device_counter[0]}"
                device_counter[0] += 1
                dot.node(splitter_id, "",
                        shape='diamond', style='filled', fillcolor='lightyellow')
                dot.edge(node_to_split, splitter_id)
                # Add 3 new leaves
                leaves.extend([splitter_id, splitter_id, splitter_id])
            else:
                # remaining_needed == 1, use 2-way split
                splitter_id = f"S{device_counter[0]}"
                device_counter[0] += 1
                dot.node(splitter_id, "",
                        shape='diamond', style='filled', fillcolor='lightyellow')
                dot.edge(node_to_split, splitter_id)
                # Add 2 new leaves
                leaves.extend([splitter_id, splitter_id])

        # Now assign the n_outputs leaves to destinations
        result: dict[str, list[str]] = {}
        for i, (dest_id, _) in enumerate(destinations):
            result[dest_id] = leaves[i]

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
                for source_id, _ in to_merge:
                    dot.edge(source_id, merger_id)
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
                for source_id, _ in to_merge:
                    dot.edge(source_id, merger_id)
                streams.append((merger_id, merge_flow))

        return streams[0][0]

    # Build split trees for each input
    input_outputs = {}  # {input_idx: {output_idx: source_node_id}}
    for in_idx, out_flows in flow_matrix.items():
        input_outputs[in_idx] = build_split_tree(f"I{in_idx}", out_flows)

    # Build merge trees for each output
    for out_idx in range(len(o)):
        # Collect all sources for this output
        sources = {}
        for in_idx, out_flows in flow_matrix.items():
            if out_idx in out_flows:
                source_node = input_outputs[in_idx][out_idx]
                sources[source_node] = out_flows[out_idx]

        if sources:
            merged_node = build_merge_tree(sources, f"O{out_idx}")
            dot.edge(merged_node, f"O{out_idx}")

    return dot
