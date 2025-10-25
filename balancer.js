/**
 * Design balancer networks for Satisfactory using splitters and mergers.
 */

import { Digraph } from './graphviz-builder.js';

// ============================================================================
// Helper utilities
// ============================================================================

/**
 * Creates a nested defaultdict-like object.
 * Returns a Proxy that auto-creates nested objects on access.
 */
function createNestedDefaultDict() {
    const handler = {
        get: (target, prop) => {
            if (!(prop in target)) {
                target[prop] = {};
            }
            return target[prop];
        }
    };
    return new Proxy({}, handler);
}

// ============================================================================
// Flow assignment functions
// ============================================================================

/**
 * Assign flow from a single input to an output.
 * 
 * Precondition:
 *     in_flow > 0
 *     remaining > 0
 *     flow_matrix is a nested defaultdict
 *     available_inputs is a list of [input_idx, flow] tuples
 * 
 * Postcondition:
 *     flow_matrix[in_idx][out_idx] is updated with the assigned flow
 *     if input is not fully consumed, remainder is added back to available_inputs
 *     returns the new remaining requirement after assignment
 * 
 * @param {number} in_idx - index of the input being assigned
 * @param {number} in_flow - available flow from this input
 * @param {number} remaining - remaining flow requirement for the output
 * @param {number} out_idx - index of the output being satisfied
 * @param {Object} flow_matrix - nested dict tracking assignments
 * @param {Array} available_inputs - list of available inputs (mutated if input not fully consumed)
 * @returns {number} remaining flow requirement after this assignment
 */
function _consume_input_flow(in_idx, in_flow, remaining, out_idx, flow_matrix, available_inputs) {
    if (in_flow <= remaining) {
        // input fully consumed
        flow_matrix[in_idx][out_idx] = in_flow;
        return remaining - in_flow;
    } else {
        // input partially consumed, return remainder to available inputs
        flow_matrix[in_idx][out_idx] = remaining;
        available_inputs.unshift([in_idx, in_flow - remaining]);
        return 0;
    }
}

/**
 * Phase 1: greedily assign inputs to outputs.
 * 
 * Precondition:
 *     inputs is a list of positive integers representing input flow rates
 *     outputs is a list of positive integers representing output requirements
 * 
 * Postcondition:
 *     returns a nested dict where flow_matrix[input_idx][output_idx] = flow_amount
 *     sum of assigned flows from each input <= original input flow
 *     flows are assigned greedily in output order
 * 
 * @param {Array<number>} inputs - list of input flow rates
 * @param {Array<number>} outputs - list of output flow requirements
 * @returns {Object} flow_matrix[input_idx][output_idx] = flow_amount
 */
function _assign_flows(inputs, outputs) {
    const flow_matrix = createNestedDefaultDict();
    const available_inputs = inputs.map((flow, idx) => [idx, flow]);

    for (let out_idx = 0; out_idx < outputs.length; out_idx++) {
        const required_flow = outputs[out_idx];
        let remaining = required_flow;

        while (remaining > 0 && available_inputs.length > 0) {
            const [in_idx, in_flow] = available_inputs.shift();
            remaining = _consume_input_flow(
                in_idx, in_flow, remaining, out_idx, flow_matrix, available_inputs
            );
        }
    }

    return flow_matrix;
}

// ============================================================================
// Graph building functions
// ============================================================================

/**
 * Add input and output nodes to the graph.
 * 
 * Precondition:
 *     dot is a Graphviz Digraph object
 *     inputs is a list (length determines number of input nodes)
 *     outputs is a list (length determines number of output nodes)
 * 
 * Postcondition:
 *     dot is mutated to include input nodes (I0, I1, ...) with green fill
 *     dot is mutated to include output nodes (O0, O1, ...) with blue fill
 * 
 * @param {Digraph} dot - Graphviz graph to add nodes to
 * @param {Array} inputs - list of input flows (length used for node count)
 * @param {Array} outputs - list of output flows (length used for node count)
 */
function _add_io_nodes(dot, inputs, outputs) {
    for (let idx = 0; idx < inputs.length; idx++) {
        dot.node(
            `I${idx}`,
            `Input ${idx}`,
            {
                shape: "box",
                style: "filled",
                fillcolor: "lightgreen"
            }
        );
    }

    for (let idx = 0; idx < outputs.length; idx++) {
        dot.node(
            `O${idx}`,
            `Output ${idx}`,
            {
                shape: "box",
                style: "filled",
                fillcolor: "lightblue"
            }
        );
    }
}

/**
 * Connect a child node to its parent splitter.
 * 
 * Precondition:
 *     child_id is either a leaf node (starts with "_leaf_") or a regular node ID
 *     child_dests maps destination IDs to flow amounts
 *     splitter_id is the ID of the splitter node being created
 *     dest_sources tracks which node feeds each destination (mutated for leaves)
 *     dot is the Graphviz graph (mutated for non-leaves)
 * 
 * Postcondition:
 *     for leaf nodes: dest_sources is updated with splitter as source
 *     for non-leaf nodes: an edge is added from splitter to child in dot
 * 
 * @param {string} child_id - ID of the child node
 * @param {Object} child_dests - mapping of destination IDs to flow amounts for this child
 * @param {string} splitter_id - ID of the parent splitter node
 * @param {Object} dest_sources - dict tracking source nodes for each destination
 * @param {Digraph} dot - Graphviz graph
 */
function _connect_child_to_splitter(child_id, child_dests, splitter_id, dest_sources, dot) {
    const child_flow = Object.values(child_dests).reduce((a, b) => a + b, 0);

    if (child_id.startsWith("_leaf_")) {
        // leaf node - record splitter as direct source
        for (const dest_id in child_dests) {
            dest_sources[dest_id] = [splitter_id, child_dests[dest_id]];
        }
    } else {
        // regular node - add edge from splitter to child
        dot.edge(splitter_id, child_id, { label: String(child_flow) });
    }
}

/**
 * Group roots under a new splitter, return [splitter_id, merged_dests].
 * 
 * Precondition:
 *     roots is a list of [node_id, destinations_dict] tuples
 *     group_size is a positive integer <= len(roots)
 *     device_counter is a single-element list containing next device ID number
 *     dot is a Graphviz Digraph
 *     dest_sources tracks destination sources
 * 
 * Postcondition:
 *     a new splitter node is added to dot
 *     device_counter[0] is incremented
 *     returns [splitter_id, merged_destinations_dict]
 *     dest_sources may be mutated if group contains leaf nodes
 * 
 * @param {Array} roots - list of [node_id, destinations] tuples to group
 * @param {number} group_size - number of roots to group together
 * @param {Array} device_counter - mutable counter for generating unique device IDs
 * @param {Digraph} dot - Graphviz graph to add nodes/edges to
 * @param {Object} dest_sources - dict tracking which node feeds each destination
 * @returns {Array} [splitter_id, merged_destinations_dict]
 */
function _group_roots_into_splitter(roots, group_size, device_counter, dot, dest_sources) {
    const group = roots.slice(0, group_size);

    const splitter_id = `S${device_counter[0]}`;
    device_counter[0] += 1;
    dot.node(splitter_id, "", {
        shape: "diamond",
        style: "filled",
        fillcolor: "lightyellow"
    });

    const merged_dests = {};
    for (const [child_id, child_dests] of group) {
        _connect_child_to_splitter(child_id, child_dests, splitter_id, dest_sources, dot);
        Object.assign(merged_dests, child_dests);
    }

    return [splitter_id, merged_dests];
}

/**
 * Collect all source nodes feeding a specific output.
 * 
 * Precondition:
 *     out_idx is a valid output index
 *     flow_matrix maps input_idx -> {output_idx -> flow}
 *     input_outputs maps input_idx -> {output_idx -> [node_id, flow]}
 * 
 * Postcondition:
 *     returns dict mapping source_node_id -> flow_amount for this output
 * 
 * @param {number} out_idx - index of the output to collect sources for
 * @param {Object} flow_matrix - flow assignments from inputs to outputs
 * @param {Object} input_outputs - mapping of split tree results
 * @returns {Object} dict mapping source node IDs to flow amounts feeding this output
 */
function _collect_sources_for_output(out_idx, flow_matrix, input_outputs) {
    const sources = {};
    for (const in_idx in flow_matrix) {
        const out_flows = flow_matrix[in_idx];
        if (out_idx in out_flows) {
            const [source_node, flow] = input_outputs[in_idx][out_idx];
            sources[source_node] = flow;
        }
    }
    return sources;
}

/**
 * Connect sources to an output, using merge tree if needed.
 * 
 * Precondition:
 *     out_idx is a valid output index
 *     flow_matrix contains flow assignments
 *     input_outputs contains split tree results
 *     build_merge_tree_func is a callable that builds merge trees
 *     dot is a Graphviz Digraph
 * 
 * Postcondition:
 *     dot is mutated to include edges connecting sources to output
 *     single source creates direct edge
 *     multiple sources create merge tree
 * 
 * @param {number} out_idx - index of the output to connect
 * @param {Object} flow_matrix - flow assignments from inputs to outputs
 * @param {Object} input_outputs - split tree results
 * @param {Function} build_merge_tree_func - function to build merge trees
 * @param {Digraph} dot - Graphviz graph
 */
function _connect_output(out_idx, flow_matrix, input_outputs, build_merge_tree_func, dot) {
    const sources = _collect_sources_for_output(out_idx, flow_matrix, input_outputs);

    if (Object.keys(sources).length === 1) {
        // direct connection - no merge needed
        const source_node = Object.keys(sources)[0];
        const flow = sources[source_node];
        dot.edge(source_node, `O${out_idx}`, { label: String(flow) });
    } else if (Object.keys(sources).length > 1) {
        // need to merge
        const merged_node = build_merge_tree_func(sources, `O${out_idx}`);
        const final_flow = Object.values(sources).reduce((a, b) => a + b, 0);
        dot.edge(merged_node, `O${out_idx}`, { label: String(final_flow) });
    }
}

// ============================================================================
// Main balancer design function
// ============================================================================

/**
 * Design an optimal balancer network using splitters and mergers.
 * 
 * Precondition:
 *     inputs is a list of positive integers
 *     outputs is a list of positive integers
 *     sum(inputs) must equal sum(outputs)
 * 
 * Postcondition:
 *     returns a Graphviz Digraph with nodes and edges for balancer network
 *     all inputs are connected to outputs via split/merge trees
 *     splitters group max 3 outputs, mergers group max 3 inputs
 * 
 * @param {Array<number>} inputs - list of input flow rates
 * @param {Array<number>} outputs - list of output flow rates
 * @returns {Digraph} Digraph representing the optimal balancer network
 * @throws {Error} if total input flow doesn't equal total output flow
 */
function design_balancer(inputs, outputs) {
    // check feasibility
    const total_inputs = inputs.reduce((a, b) => a + b, 0);
    const total_outputs = outputs.reduce((a, b) => a + b, 0);
    if (total_inputs !== total_outputs) {
        throw new Error(
            `Total input flow ${total_inputs} must equal total output flow ${total_outputs}`
        );
    }

    // Phase 1: Flow assignment
    const flow_matrix = _assign_flows(inputs, outputs);

    // Phase 2: Build graph with optimal split/merge trees
    const dot = new Digraph();
    dot.attr({ rankdir: "LR" });

    _add_io_nodes(dot, inputs, outputs);

    const device_counter = [0];  // use list for mutability in nested function

    /**
     * Build optimal split tree for one source feeding multiple destinations.
     * Build bottom-up: each output starts as a root, group 3 at a time until one root remains.
     * @param {string} source_id - source node ID
     * @param {Object} flows_dict - {dest_id: flow_amount}
     * @returns {Object} {dest_id: [node_id, flow]} mapping destinations to their immediate source nodes
     */
    function build_split_tree(source_id, flows_dict) {
        if (Object.keys(flows_dict).length === 1) {
            const dest_id = Object.keys(flows_dict)[0];
            const flow = flows_dict[dest_id];
            return { [dest_id]: [source_id, flow] };
        }

        // Sort destinations for consistent output
        const destinations = Object.entries(flows_dict).sort((a, b) => {
            // Sort by flow (descending), then by dest_id (descending)
            if (a[1] !== b[1]) {
                return b[1] - a[1];  // descending by flow
            }
            return b[0] - a[0];  // descending by dest_id
        });

        // Build tree bottom-up: start with leaves (conceptual outputs)
        const roots = [];
        for (const [dest_id, flow] of destinations) {
            roots.push([`_leaf_${dest_id}`, { [dest_id]: flow }]);
        }

        // Track which actual node feeds each destination
        const dest_sources = {};

        // Group roots together until only one remains
        while (roots.length > 1) {
            const group_size = roots.length >= 3 ? 3 : 2;
            const [splitter_id, merged_dests] = _group_roots_into_splitter(
                roots, group_size, device_counter, dot, dest_sources
            );
            roots.splice(0, group_size);
            roots.push([splitter_id, merged_dests]);
        }

        // Now we have one root - connect it to the source
        const [root_id, root_dests] = roots[0];
        const root_flow = Object.values(root_dests).reduce((a, b) => a + b, 0);
        dot.edge(source_id, root_id, { label: String(root_flow) });

        // Return mapping - for each destination, record which node feeds it
        const result = {};
        for (const dest_id in flows_dict) {
            result[dest_id] = dest_sources[dest_id];
        }

        return result;
    }

    /**
     * Build optimal merge tree for multiple sources feeding one destination.
     * @param {Object} flows_dict - {source_id: flow_amount}
     * @param {string} _dest_id - destination ID (unused)
     * @returns {string} node_id of the merged flow
     */
    function build_merge_tree(flows_dict, _dest_id) {
        if (Object.keys(flows_dict).length <= 1) {
            throw new Error("Cannot merge a single source");
        }

        // Sort sources for consistent output
        const sources = Object.entries(flows_dict).sort((a, b) => {
            // Sort by flow (descending), then by source_id (descending)
            if (a[1] !== b[1]) {
                return b[1] - a[1];  // descending by flow
            }
            return b[0].localeCompare(a[0]) * -1;  // descending by source_id
        });
        const streams = [...sources];

        // Merge streams until we have just one
        while (streams.length > 1) {
            const group_size = streams.length >= 3 ? 3 : 2;
            const to_merge = streams.slice(0, group_size);
            streams.splice(0, group_size);

            const merger_id = `M${device_counter[0]}`;
            device_counter[0] += 1;
            const merge_flow = to_merge.reduce((sum, [_, flow]) => sum + flow, 0);
            dot.node(
                merger_id,
                "",
                {
                    shape: "diamond",
                    style: "filled",
                    fillcolor: "lightcoral"
                }
            );
            for (const [source_id, flow] of to_merge) {
                dot.edge(source_id, merger_id, { label: String(flow) });
            }
            streams.push([merger_id, merge_flow]);
        }

        return streams[0][0];
    }

    // Build split trees for each input
    const input_outputs = {};  // {input_idx: {output_idx: [source_node_id, flow]}}
    for (const in_idx in flow_matrix) {
        input_outputs[in_idx] = build_split_tree(`I${in_idx}`, flow_matrix[in_idx]);
    }

    // Build merge trees for each output and create final edges
    for (let out_idx = 0; out_idx < outputs.length; out_idx++) {
        _connect_output(out_idx, flow_matrix, input_outputs, build_merge_tree, dot);
    }

    return dot;
}

export { design_balancer };
