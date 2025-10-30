/**
 * Factory design system for Satisfactory production chains.
 * Ported from Python factory.py
 */

import { design_balancer } from './balancer.js';
import { Purity, get_mining_rate, Recipe, get_all_recipes, get_fluids, get_fluid_color, normalize_material_names, normalize_input_array } from './recipes.js';
import { optimize_recipes } from './optimize.js';
import { Digraph } from './graphviz-builder.js';

// ============================================================================
// Helper functions
// ============================================================================

/**
 * Check if a material is a fluid.
 * @param {string} material - material name to check
 * @returns {boolean} whether material is a fluid
 */
function _isFluid(material) {
    return get_fluids().includes(material);
}

/**
 * Determine which conveyor mark is needed for a given flow rate.
 * Mark 1: 60/min, Mark 2: 120/min, Mark 3: 270/min, Mark 4: 480/min
 * @param {number} flowRate - items per minute to transport
 * @returns {number} conveyor belt mark number (1-4)
 */
function _getConveyorMark(flowRate) {
    const conveyorSpeeds = [60, 120, 270, 480];
    for (let mark = 1; mark <= conveyorSpeeds.length; mark++) {
        if (flowRate <= conveyorSpeeds[mark - 1]) {
            return mark;
        }
    }
    return 4;  // default to mark 4 for anything higher
}

/**
 * Determine which pipeline mark is needed for a given flow rate.
 * Mark 1: 300/min, Mark 2: 600/min
 * @param {number} flowRate - units of fluid per minute to transport
 * @returns {number} pipeline mark number (1-2)
 */
function _getPipelineMark(flowRate) {
    const pipelineSpeeds = [300, 600];
    for (let mark = 1; mark <= pipelineSpeeds.length; mark++) {
        if (flowRate <= pipelineSpeeds[mark - 1]) {
            return mark;
        }
    }
    return 2;  // default to mark 2 for anything higher
}

/**
 * Generate graphviz color string with alternating black and white stripes.
 * Mark 1: "black"
 * Mark 2: "black:white:black"
 * Mark 3: "black:white:black:white:black"
 * Mark 4: "black:white:black:white:black:white:black"
 * @param {number} mark - conveyor belt mark number
 * @returns {string} graphviz color specification string
 */
function _getConveyorStripeColor(mark) {
    const stripes = [];
    for (let i = 0; i < mark; i++) {
        stripes.push("black");
        if (i < mark - 1) {  // don't add white after the last black
            stripes.push("white");
        }
    }
    return stripes.join(":");
}

/**
 * Generate graphviz color string with grey and fluid color stripes.
 * Mark 1: "grey:color:color:grey"
 * Mark 2: "grey:color:color:color:color:color:grey"
 * @param {number} mark - pipeline mark number
 * @param {string} fluid - fluid name for color lookup
 * @returns {string} graphviz color specification string
 */
function _getPipelineStripeColor(mark, fluid) {
    const color = get_fluid_color(fluid);
    if (mark === 1) {
        return `grey:${color}:${color}:grey`;
    } else {  // mark 2
        return `grey:${color}:${color}:${color}:${color}:${color}:grey`;
    }
}

/**
 * Get the edge color for a given material and flow rate.
 * @param {string} material - material name
 * @param {number} flowRate - units per minute
 * @returns {string} graphviz color specification string
 */
function _getEdgeColor(material, flowRate) {
    if (_isFluid(material)) {
        const mark = _getPipelineMark(flowRate);
        return _getPipelineStripeColor(mark, material);
    } else {
        const mark = _getConveyorMark(flowRate);
        return _getConveyorStripeColor(mark);
    }
}

/**
 * Initialize material balance with inputs, mines, and output requirements.
 * Inputs and mines contribute positive flow, outputs contribute negative flow.
 * Mining rates assume Mk.3 miners.
 * @param {Object<string, number>} outputs - required output materials and amounts
 * @param {Array<[string, number]>} inputs - list of [material, flowRate] tuples
 * @param {Array<[string, string]>} mines - list of [resource, Purity] tuples
 * @returns {Object<string, number>} material balance dictionary
 */
function _initializeBalance(outputs, inputs, mines) {
    const balance = {};

    for (const [material, flowRate] of inputs) {
        balance[material] = (balance[material] || 0) + flowRate;
    }

    for (const [resource, purity] of mines) {
        balance[resource] = (balance[resource] || 0) + get_mining_rate(2, purity);  // Assume Mk.3 miner
    }

    for (const [outputItem, amount] of Object.entries(outputs)) {
        balance[outputItem] = (balance[outputItem] || 0) - amount;
    }

    return balance;
}

/**
 * Build input materials dict for optimizer from inputs and mines.
 * @param {Array<[string, number]>} inputs - available input materials and rates
 * @param {Array<[string, string]>} mines - resource mines with purity levels
 * @returns {Object<string, number>} dict of material names to flow rates
 */
function _buildOptimizerInputs(inputs, mines) {
    const inputsDict = {};
    
    for (const [material, flowRate] of inputs) {
        inputsDict[material] = (inputsDict[material] || 0) + flowRate;
    }
    
    for (const [resource, purity] of mines) {
        inputsDict[resource] = (inputsDict[resource] || 0) + get_mining_rate(2, purity);
    }
    
    return inputsDict;
}

/**
 * Transform optimizer output into machine instances, recipes, and total production.
 * @param {Object<string, number>} recipeCounts - optimizer output mapping recipe names to counts
 * @returns {[Object<string, number>, Object<string, Recipe>, Object<string, number>]} tuple of [machineInstances, recipesUsed, totalProduction] dicts
 */
function _transformOptimizerOutput(recipeCounts) {
    const allRecipes = get_all_recipes();
    const machineInstances = {};
    const recipesUsed = {};
    const totalProduction = {};
    
    for (const [recipeName, count] of Object.entries(recipeCounts)) {
        const recipe = allRecipes[recipeName];
        const machineKey = `${recipe.machine}|${recipeName}`;
        
        machineInstances[machineKey] = Math.floor(count);
        recipesUsed[machineKey] = recipe;
        
        for (const [outputItem, amount] of Object.entries(recipe.outputs)) {
            totalProduction[outputItem] = (totalProduction[outputItem] || 0) + amount * count;
        }
    }
    
    return [machineInstances, recipesUsed, totalProduction];
}

/**
 * Compute required raw materials from final balance.
 * Only includes materials with negative balance (shortfalls).
 * @param {Object<string, number>} recipeCounts - optimizer output
 * @param {Object<string, number>} outputs - required outputs
 * @param {Array<[string, number]>} inputs - available inputs
 * @param {Array<[string, string]>} mines - resource mines
 * @returns {Object<string, number>} dict of material shortfalls
 */
function _computeRequiredRawMaterials(recipeCounts, outputs, inputs, mines) {
    const balance = _initializeBalance(outputs, inputs, mines);
    const allRecipes = get_all_recipes();
    
    for (const [recipeName, count] of Object.entries(recipeCounts)) {
        const recipe = allRecipes[recipeName];
        for (const [inputItem, amount] of Object.entries(recipe.inputs)) {
            balance[inputItem] = (balance[inputItem] || 0) - amount * count;
        }
        for (const [outputItem, amount] of Object.entries(recipe.outputs)) {
            balance[outputItem] = (balance[outputItem] || 0) + amount * count;
        }
    }
    
    const requiredRawMaterials = {};
    for (const [material, amount] of Object.entries(balance)) {
        if (amount < 0) {
            requiredRawMaterials[material] = -amount;
        }
    }
    
    return requiredRawMaterials;
}

/**
 * Calculate required machines and material balance.
 * @param {Object<string, number>} outputs - required output materials and amounts
 * @param {Array<[string, number]>} inputs - available input materials and rates
 * @param {Array<[string, string]>} mines - resource mines with purity levels
 * @param {Set<string>|null} enablementSet - enabled recipes or null
 * @param {Object<string, number>|null} economy - material values or null
 * @param {number} inputCostsWeight - optimization weight
 * @param {number} machineCountsWeight - optimization weight
 * @param {number} powerConsumptionWeight - optimization weight
 * @param {boolean} designPower - whether to design power generation
 * @returns {[Object<string, number>, Object<string, Recipe>, Object<string, number>, Object<string, number>, Object<string, number>]} tuple of [machineInstances, recipesUsed, requiredRawMaterials, totalProduction, recipeCounts]
 */
async function _calculateMachines(
    outputs,
    inputs,
    mines,
    enablementSet,
    economy,
    inputCostsWeight,
    machineCountsWeight,
    powerConsumptionWeight,
    wasteProductsWeight,
    designPower,
    onProgress
) {
    // Build inputs dict for optimizer
    const inputsDict = _buildOptimizerInputs(inputs, mines);
    
    // Call optimizer - returns {recipe_name: machine_count}
    const recipeCounts = await optimize_recipes(
        inputsDict,
        outputs,
        {
            enablement_set: enablementSet,
            economy: economy,
            input_costs_weight: inputCostsWeight,
            machine_counts_weight: machineCountsWeight,
            power_consumption_weight: powerConsumptionWeight,
            waste_products_weight: wasteProductsWeight,
            design_power: designPower,
            on_progress: onProgress
        }
    );
    
    // Transform optimizer output to existing format
    const [machineInstances, recipesUsed, totalProduction] = _transformOptimizerOutput(recipeCounts);
    
    // Compute required_raw_materials by checking final balance
    const requiredRawMaterials = _computeRequiredRawMaterials(
        recipeCounts, outputs, inputs, mines
    );
    
    return [
        machineInstances,
        recipesUsed,
        requiredRawMaterials,
        totalProduction,
        recipeCounts,
    ];
}

/**
 * Compute actual factory outputs including byproducts.
 * @param {Object<string, number>} outputs - requested output materials
 * @param {Object<string, number>} totalProduction - total production rates
 * @param {Object<string, number>} balance - material balances (positive = excess)
 * @returns {Object<string, number>} dict mapping materials to output rates
 */
function _computeActualOutputs(outputs, totalProduction, balance) {
    // Recompute balance for byproduct detection
    const currentBalance = { ...balance };

    const actualOutputs = {};
    for (const material of Object.keys(outputs)) {
        if (material in totalProduction) {
            actualOutputs[material] = totalProduction[material];
        }
    }
    // Add byproducts (materials with excess that weren't requested)
    for (const [material, excess] of Object.entries(currentBalance)) {
        if (excess > 0 && !(material in outputs)) {
            actualOutputs[material] = excess;
        }
    }

    return actualOutputs;
}

// ============================================================================
// Graph building functions
// ============================================================================

/**
 * Add user-provided input nodes to graphviz graph.
 * @param {Object} inputsGroup - graphviz subgraph for inputs
 * @param {Array<[string, number]>} inputs - list of input materials and rates
 * @param {Object<string, {sources: Array<[string, number]>, sinks: Array<[string, number]>}>} materialFlows - dict tracking material sources
 */
function _addUserInputNodes(inputsGroup, inputs, materialFlows) {
    for (let idx = 0; idx < inputs.length; idx++) {
        const [inputItem, flowRate] = inputs[idx];
        const nodeId = `Input_${inputItem.replace(/ /g, '_')}_${idx}`;
        inputsGroup.node(
            nodeId,
            `${inputItem}\n${flowRate}/min`,
            { shape: "box", style: "filled", fillcolor: "orange" }
        );
        if (!materialFlows[inputItem]) {
            materialFlows[inputItem] = { sources: [], sinks: [] };
        }
        materialFlows[inputItem].sources.push([nodeId, flowRate]);
    }
}

/**
 * Add auto-generated input nodes for required raw materials.
 * @param {Object} inputsGroup - graphviz subgraph for inputs
 * @param {Array<[string, number]>} inputs - list of provided input materials and rates
 * @param {Object<string, number>} requiredRawMaterials - dict of material shortfalls
 * @param {Object<string, {sources: Array<[string, number]>, sinks: Array<[string, number]>}>} materialFlows - dict tracking material sources
 */
function _addAutoInputNodes(inputsGroup, inputs, requiredRawMaterials, materialFlows) {
    for (const [material, requiredAmount] of Object.entries(requiredRawMaterials)) {
        const providedAmount = inputs
            .filter(([item, _]) => item === material)
            .reduce((sum, [_, flow]) => sum + flow, 0);
        if (providedAmount < requiredAmount) {
            const remaining = requiredAmount - providedAmount;
            const nodeId = `Input_${material.replace(/ /g, '_')}_auto`;
            inputsGroup.node(
                nodeId,
                `${material}\n${remaining}/min\n(auto)`,
                { shape: "box", style: "filled", fillcolor: "orange" }
            );
            if (!materialFlows[material]) {
                materialFlows[material] = { sources: [], sinks: [] };
            }
            materialFlows[material].sources.push([nodeId, remaining]);
        }
    }
}

/**
 * Add mine nodes to graphviz graph.
 * Mining rates assume Mk.3 miners.
 * @param {Object} inputsGroup - graphviz subgraph for inputs
 * @param {Array<[string, string]>} mines - list of resource mines with purity levels
 * @param {Object<string, {sources: Array<[string, number]>, sinks: Array<[string, number]>}>} materialFlows - dict tracking material sources
 */
function _addMineNodes(inputsGroup, mines, materialFlows) {
    for (let idx = 0; idx < mines.length; idx++) {
        const [resource, purity] = mines[idx];
        const nodeId = `Mine_${idx}`;
        const flowRate = get_mining_rate(2, purity);  // Assume Mk.3 miner
        inputsGroup.node(
            nodeId,
            `Miner\n${resource}\n${flowRate}/min`,
            { shape: "box", style: "filled", fillcolor: "brown" }
        );
        if (!materialFlows[resource]) {
            materialFlows[resource] = { sources: [], sinks: [] };
        }
        materialFlows[resource].sources.push([nodeId, flowRate]);
    }
}

/**
 * Add input and mine nodes to the graph.
 * Creates "inputs" subgraph with rank="same".
 * @param {Digraph} dot - main graphviz digraph
 * @param {Array<[string, number]>} inputs - list of input materials and rates
 * @param {Array<[string, string]>} mines - list of resource mines with purity
 * @param {Object<string, number>} requiredRawMaterials - dict of material shortfalls
 * @param {Object<string, {sources: Array<[string, number]>, sinks: Array<[string, number]>}>} materialFlows - dict tracking material sources
 */
function _addInputNodes(dot, inputs, mines, requiredRawMaterials, materialFlows) {
    dot.subgraph("inputs", (inputsGroup) => {
        inputsGroup.attr("rank", "same");
        _addUserInputNodes(inputsGroup, inputs, materialFlows);
        _addAutoInputNodes(inputsGroup, inputs, requiredRawMaterials, materialFlows);
        _addMineNodes(inputsGroup, mines, materialFlows);
    });
}

/**
 * Create a single machine node and track its flows.
 * @param {Object} cluster - graphviz subgraph/cluster for machine group
 * @param {number} machineNodeId - current machine ID counter
 * @param {Recipe} recipe - Recipe defining inputs and outputs
 * @param {Object} materialFlows - dict tracking material sources and sinks
 * @returns {number} incremented machineNodeId
 */
function _createSingleMachineNode(cluster, machineNodeId, recipe, materialFlows) {
    const nodeId = `Machine_${machineNodeId}`;
    cluster.node(nodeId, "", { shape: "box", style: "filled", fillcolor: "white" });

    for (const [inputItem, flowRate] of Object.entries(recipe.inputs)) {
        if (!materialFlows[inputItem]) {
            materialFlows[inputItem] = { sources: [], sinks: [] };
        }
        materialFlows[inputItem].sinks.push([nodeId, flowRate]);
    }
    for (const [outputItem, flowRate] of Object.entries(recipe.outputs)) {
        if (!materialFlows[outputItem]) {
            materialFlows[outputItem] = { sources: [], sinks: [] };
        }
        materialFlows[outputItem].sources.push([nodeId, flowRate]);
    }

    return machineNodeId + 1;
}

/**
 * Add machine nodes to the graph.
 * Creates labeled lightblue clusters for each machine type/recipe.
 * @param {Digraph} dot - main graphviz digraph
 * @param {Object} machineInstances - dict mapping "machine|recipe" to counts
 * @param {Object} recipesUsed - dict mapping "machine|recipe" to Recipe objects
 * @param {Object} materialFlows - dict tracking material sources and sinks
 */
function _addMachineNodes(dot, machineInstances, recipesUsed, materialFlows) {
    let machineNodeId = 0;
    let clusterId = 0;

    for (const [machineKey, count] of Object.entries(machineInstances)) {
        const recipe = recipesUsed[machineKey];
        const [machineType, recipeName] = machineKey.split('|');

        dot.subgraph(`cluster_${clusterId}`, (cluster) => {
            const inputsStr = Object.entries(recipe.inputs)
                .map(([k, v]) => `${k}:${v}`)
                .join(", ");
            const outputsStr = Object.entries(recipe.outputs)
                .map(([k, v]) => `${k}:${v}`)
                .join(", ");
            cluster.attr("label", `${machineType} - ${recipeName}\n${inputsStr}\n→ ${outputsStr}`);
            cluster.attr("style", "filled");
            cluster.attr("fillcolor", "lightblue");

            for (let i = 0; i < count; i++) {
                machineNodeId = _createSingleMachineNode(
                    cluster, machineNodeId, recipe, materialFlows
                );
            }
        });

        clusterId += 1;
    }
}

/**
 * Add nodes for requested outputs.
 * Sink amounts account for internal consumption.
 * @param {Object} requestedGroup - graphviz subgraph for requested outputs
 * @param {Object} outputs - dict of requested output materials
 * @param {Object} totalProduction - dict of total production rates
 * @param {Object} materialFlows - dict tracking material sources and sinks
 */
function _addRequestedOutputNodes(requestedGroup, outputs, totalProduction, materialFlows) {
    for (const material of Object.keys(outputs)) {
        if (material in totalProduction) {
            const nodeId = `Output_${material.replace(/ /g, '_')}`;
            const internalSinks = materialFlows[material] && materialFlows[material].sinks
                ? materialFlows[material].sinks.reduce((sum, [_, flow]) => sum + flow, 0)
                : 0;

            let sinkAmount;
            if (internalSinks > 0) {
                sinkAmount = Math.max(0, totalProduction[material] - internalSinks);
            } else {
                sinkAmount = totalProduction[material];
            }

            if (sinkAmount > 0) {
                requestedGroup.node(
                    nodeId,
                    `${material}\n${sinkAmount}/min`,
                    { shape: "box", style: "filled", fillcolor: "lightgreen" }
                );
                if (!materialFlows[material]) {
                    materialFlows[material] = { sources: [], sinks: [] };
                }
                materialFlows[material].sinks.push([nodeId, sinkAmount]);
            }
        }
    }
}

/**
 * Add nodes for byproducts (excess unrequested materials).
 * @param {Object} byproductsGroup - graphviz subgraph for byproducts
 * @param {Object} outputs - dict of requested output materials
 * @param {Object} balance - dict of material balances (positive = excess)
 * @param {Object} materialFlows - dict tracking material sources and sinks
 */
function _addByproductNodes(byproductsGroup, outputs, balance, materialFlows) {
    for (const [material, excess] of Object.entries(balance)) {
        if (excess > 0 && !(material in outputs)) {
            const nodeId = `Output_${material.replace(/ /g, '_')}`;
            byproductsGroup.node(
                nodeId,
                `${material}\n${excess}/min`,
                { shape: "box", style: "filled", fillcolor: "salmon" }
            );
            if (!materialFlows[material]) {
                materialFlows[material] = { sources: [], sinks: [] };
            }
            materialFlows[material].sinks.push([nodeId, excess]);
        }
    }
}

/**
 * Add output nodes to the graph.
 * Creates invisible output cluster containing requested outputs and byproducts subgraphs.
 * @param {Digraph} dot - main graphviz digraph
 * @param {Object} outputs - dict of requested output materials
 * @param {Object} totalProduction - dict of total production rates
 * @param {Object} balance - dict of material balances
 * @param {Object} materialFlows - dict tracking material sources and sinks
 */
function _addOutputNodes(dot, outputs, totalProduction, balance, materialFlows) {
    dot.subgraph("cluster_outputs", (outputsGroup) => {
        outputsGroup.attr("label", "");
        outputsGroup.attr("style", "invis");
        
        outputsGroup.subgraph("cluster_requested_outputs", (requestedGroup) => {
            requestedGroup.attr("label", "");
            requestedGroup.attr("style", "invis");
            requestedGroup.attr("rank", "same");
            _addRequestedOutputNodes(requestedGroup, outputs, totalProduction, materialFlows);
        });

        outputsGroup.subgraph("cluster_byproducts", (byproductsGroup) => {
            byproductsGroup.attr("label", "");
            byproductsGroup.attr("style", "invis");
            byproductsGroup.attr("rank", "same");
            _addByproductNodes(byproductsGroup, outputs, balance, materialFlows);
        });
    });
}

// ============================================================================
// Material routing functions
// ============================================================================

/**
 * Handle direct connection when there's one source and one sink.
 * Adds edge from source to sink with material label and colored by flow rate.
 * @param {Digraph} dot - graphviz digraph
 * @param {string} material - material name
 * @param {Array<[string, number]>} sources - list with one [node_id, flow] tuple
 * @param {Array<[string, number]>} sinks - list with one [node_id, flow] tuple
 * @param {Array<number>} sinkFlows - list with one flow rate
 */
function _handleDirectConnection(dot, material, sources, sinks, sinkFlows) {
    const [sourceId, _] = sources[0];
    const [sinkId, __] = sinks[0];
    const flowLabel = Number.isInteger(sinkFlows[0]) ? sinkFlows[0] : sinkFlows[0];
    const color = _getEdgeColor(material, sinkFlows[0]);
    dot.edge(sourceId, sinkId, { label: `${material}\n${flowLabel}`, color: color, penwidth: "2" });
}

/**
 * Proportionally allocate integer flows ensuring they sum to targetTotal.
 * Proportions maintained as closely as possible; last element gets any remaining to ensure exact sum.
 * @param {Array<number>} flows - list of flow rates to allocate
 * @param {number} targetTotal - target sum for integer flows
 * @returns {Array<number>} list of integer flows summing to targetTotal
 */
function _computeIntegerFlows(flows, targetTotal) {
    const flowsInt = [];
    const sourceTotal = flows.reduce((sum, flow) => sum + flow, 0);
    let remaining = targetTotal;

    for (let i = 0; i < flows.length; i++) {
        if (i === flows.length - 1) {
            flowsInt.push(remaining);
        } else {
            const allocated = Math.floor(flows[i] * targetTotal / sourceTotal);
            flowsInt.push(allocated);
            remaining -= allocated;
        }
    }

    return flowsInt;
}

/**
 * Build mapping from balancer IDs to factory IDs.
 * "I{idx}" maps to source node_ids, "O{idx}" maps to sink node_ids.
 * @param {Array<[string, number]>} sources - list of source [node_id, flow] tuples
 * @param {Array<[string, number]>} sinks - list of sink [node_id, flow] tuples
 * @returns {Object<string, string>} dict mapping balancer IDs to factory node IDs
 */
function _buildNodeMapping(sources, sinks) {
    const nodeMapping = {};
    for (let idx = 0; idx < sources.length; idx++) {
        const [sourceId, _] = sources[idx];
        nodeMapping[`I${idx}`] = sourceId;
    }
    for (let idx = 0; idx < sinks.length; idx++) {
        const [sinkId, _] = sinks[idx];
        nodeMapping[`O${idx}`] = sinkId;
    }
    return nodeMapping;
}

/**
 * Copy balancer nodes (splitters/mergers) to factory graph.
 * Diamond nodes added to dot for each splitter/merger.
 * Lightyellow for splitters (S prefix), thistle for mergers (M prefix).
 * @param {Digraph} dot - main graphviz digraph
 * @param {string} balancerSrc - graphviz source string from balancer
 * @param {string} material - material name for node ID
 * @param {number} balancerCounter - counter for unique IDs
 * @param {Object<string, string>} nodeMapping - dict to update with ID mappings
 */
function _copyBalancerNodes(dot, balancerSrc, material, balancerCounter, nodeMapping) {
    // Match node definitions but not edges (which contain ->)
    // Node lines look like: S0 [label="", ...]
    // Edge lines look like: I0 -> S0 [label="60"]
    // We need to match only lines that start with the node ID (after optional whitespace)
    const nodeRegex = /^\s*(S\d+|M\d+)\s+\[label="[^"]*"[^\]]*\]/gm;
    let match;
    while ((match = nodeRegex.exec(balancerSrc)) !== null) {
        const oldId = match[1];
        const newId = `${material}_${oldId}_${balancerCounter}`;
        nodeMapping[oldId] = newId;

        const fillcolor = oldId.startsWith("S") ? "lightyellow" : "thistle";
        dot.node(newId, "", { shape: "diamond", style: "filled", fillcolor: fillcolor });
    }
}

/**
 * Copy balancer edges to factory graph.
 * Colored edges added to dot for each balancer connection.
 * Labels include material name and flow rate.
 * @param {string} balancerSrc - graphviz source string from balancer
 * @param {string} material - material name
 * @param {Object<string, string>} nodeMapping - dict mapping old IDs to new IDs
 * @param {Digraph} dot - main graphviz digraph
 */
function _copyBalancerEdges(balancerSrc, material, nodeMapping, dot) {
    // Match edges with either quoted or unquoted labels: label="123" or label=123
    const edgeRegex = /(\w+)\s+->\s+(\w+)\s+\[label="?(\d+)"?\]/g;
    let match;
    while ((match = edgeRegex.exec(balancerSrc)) !== null) {
        const src = match[1];
        const dst = match[2];
        const flow = match[3];
        if (src in nodeMapping && dst in nodeMapping) {
            const flowRate = parseFloat(flow);
            const color = _getEdgeColor(material, flowRate);
            dot.edge(nodeMapping[src], nodeMapping[dst], { label: `${material}\n${flow}`, color: color, penwidth: "2" });
        }
    }
}

/**
 * Create and copy balancer for routing material.
 * Balancer nodes and edges added to dot.
 * Flows converted to integers for balancer design.
 * @param {Digraph} dot - main graphviz digraph
 * @param {string} material - material name
 * @param {[Array<[string, number]>, Array<number>]} sourcesWithFlows - tuple of [sources, sourceFlows]
 * @param {[Array<[string, number]>, Array<number>]} sinksWithFlows - tuple of [sinks, sinkFlows]
 * @param {number} balancerCounter - counter for unique IDs
 */
function _createMaterialBalancer(dot, material, sourcesWithFlows, sinksWithFlows, balancerCounter) {
    const [sources, sourceFlows] = sourcesWithFlows;
    const [sinks, sinkFlows] = sinksWithFlows;

    const targetTotal = Math.min(Math.floor(sourceFlows.reduce((a, b) => a + b, 0)), 
                                  Math.floor(sinkFlows.reduce((a, b) => a + b, 0)));
    const sourceFlowsInt = _computeIntegerFlows(sourceFlows, targetTotal);
    const sinkFlowsInt = _computeIntegerFlows(sinkFlows, targetTotal);
    const balancerGraph = design_balancer(sourceFlowsInt, sinkFlowsInt);

    // Copy balancer to factory graph
    const balancerSrc = balancerGraph.source;
    const nodeMapping = _buildNodeMapping(sources, sinks);
    _copyBalancerNodes(dot, balancerSrc, material, balancerCounter, nodeMapping);
    _copyBalancerEdges(balancerSrc, material, nodeMapping, dot);
}

/**
 * Route a single material and return updated balancerCounter.
 * @param {Digraph} dot - main graphviz digraph
 * @param {string} material - material name
 * @param {Object} flows - dict with "sources" and "sinks" lists
 * @param {number} balancerCounter - current counter value
 * @returns {number} updated balancerCounter
 */
function _routeSingleMaterial(dot, material, flows, balancerCounter) {
    const sources = flows.sources;
    const sinks = flows.sinks;

    // Skip materials with no sources or sinks (e.g., perfectly balanced internal flows)
    if (!sources || sources.length === 0 || !sinks || sinks.length === 0) {
        return balancerCounter;
    }

    const sourceFlows = sources.map(([_, flow]) => flow);
    const sinkFlows = sinks.map(([_, flow]) => flow);

    const totalSource = sourceFlows.reduce((a, b) => a + b, 0);
    const totalSink = sinkFlows.reduce((a, b) => a + b, 0);

    if (totalSource < totalSink) {
        console.log(`Warning: Insufficient ${material}: ${totalSource} < ${totalSink}`);
        return balancerCounter;
    }

    if (sources.length === 1 && sinks.length === 1) {
        _handleDirectConnection(dot, material, sources, sinks, sinkFlows);
    } else {
        _createMaterialBalancer(
            dot,
            material,
            [sources, sourceFlows],
            [sinks, sinkFlows],
            balancerCounter
        );
        return balancerCounter + 1;
    }

    return balancerCounter;
}

/**
 * Route materials between sources and sinks using balancers.
 * All materials (except MWm/electricity) are routed.
 * @param {Digraph} dot - main graphviz digraph
 * @param {Object} materialFlows - dict mapping materials to source/sink flows
 */
function _routeMaterialsWithBalancers(dot, materialFlows) {
    let balancerCounter = 0;
    for (const [material, flows] of Object.entries(materialFlows)) {
        if (material === "MWm") {  // skip electricity - doesn't need balancing
            continue;
        }
        balancerCounter = _routeSingleMaterial(dot, material, flows, balancerCounter);
    }
}

/**
 * Route materials between sources and sinks using simple hub nodes.
 * All materials (except MWm/electricity) are routed through circular hub nodes.
 * @param {Digraph} dot - main graphviz digraph
 * @param {Object} materialFlows - dict mapping materials to source/sink flows
 */
function _routeMaterialsWithNodes(dot, materialFlows) {
    for (const [material, flows] of Object.entries(materialFlows)) {
        if (material === "MWm") {  // skip electricity - doesn't need routing
            continue;
        }
        
        const sources = flows.sources;
        const sinks = flows.sinks;

        // Skip materials with no sources or sinks
        if (!sources || sources.length === 0 || !sinks || sinks.length === 0) {
            continue;
        }

        const sourceFlows = sources.map(([_, flow]) => flow);
        const sinkFlows = sinks.map(([_, flow]) => flow);

        const totalSource = sourceFlows.reduce((a, b) => a + b, 0);
        const totalSink = sinkFlows.reduce((a, b) => a + b, 0);

        if (totalSource < totalSink) {
            console.log(`Warning: Insufficient ${material}: ${totalSource} < ${totalSink}`);
            continue;
        }

        // Direct connection for single source and single sink
        if (sources.length === 1 && sinks.length === 1) {
            _handleDirectConnection(dot, material, sources, sinks, sinkFlows);
        } else {
            // Create hub node and connect all sources and sinks to it
            const hubId = `${material.replace(/ /g, '_')}_Hub`;
            dot.node(hubId, "", { shape: "circle", style: "filled", fillcolor: "lightgrey" });

            // Connect all sources to hub
            for (const [sourceId, flowRate] of sources) {
                const color = _getEdgeColor(material, flowRate);
                dot.edge(sourceId, hubId, { label: `${material}\n${flowRate}`, color: color, penwidth: "2" });
            }

            // Connect hub to all sinks
            for (const [sinkId, flowRate] of sinks) {
                const color = _getEdgeColor(material, flowRate);
                dot.edge(hubId, sinkId, { label: `${material}\n${flowRate}`, color: color, penwidth: "2" });
            }
        }
    }
}

// ============================================================================
// Factory class
// ============================================================================

/**
 * A complete factory network with machines and balancers.
 */
class Factory {
    constructor(network, inputs, outputs, mines, recipeCounts = null) {
        this.network = network;
        this.inputs = inputs;
        this.outputs = outputs;
        this.mines = mines;
        this.recipeCounts = recipeCounts;
    }
}

// ============================================================================
// Balance computation helpers
// ============================================================================

/**
 * Apply machine inputs/outputs to balance (mutates balance in-place).
 * Input materials decreased by consumption amounts, output materials increased by production amounts.
 * @param {Object} balance - dict mapping materials to float
 * @param {Object} machineInstances - dict mapping "machine|recipe" to count
 * @param {Object} recipesUsed - dict mapping "machine|recipe" to Recipe
 */
function _applyMachineBalance(balance, machineInstances, recipesUsed) {
    for (const [machineKey, count] of Object.entries(machineInstances)) {
        const recipe = recipesUsed[machineKey];
        for (const [inputItem, amount] of Object.entries(recipe.inputs)) {
            balance[inputItem] = (balance[inputItem] || 0) - amount * count;
        }
        for (const [outputItem, amount] of Object.entries(recipe.outputs)) {
            balance[outputItem] = (balance[outputItem] || 0) + amount * count;
        }
    }
}

/**
 * Recompute material balance after machine calculation.
 * Negative values indicate deficit (need input), positive values indicate surplus (available as output).
 * @param {Array<[string, number]>} inputs - list of [material, rate] tuples
 * @param {Array<[string, string]>} mines - list of [resource, Purity] tuples
 * @param {Object<string, number>} outputs - dict mapping materials to desired rates
 * @param {Object<string, number>} machineInstances - dict mapping "machine|recipe" to count
 * @param {Object<string, Recipe>} recipesUsed - dict mapping "machine|recipe" to Recipe
 * @returns {Object<string, number>} dict mapping materials to net flow
 */
function _recomputeBalanceForOutputs(inputs, mines, outputs, machineInstances, recipesUsed) {
    const balance = _initializeBalance(outputs, inputs, mines);
    _applyMachineBalance(balance, machineInstances, recipesUsed);
    return balance;
}

// ============================================================================
// Main public API
// ============================================================================

/**
 * Design a complete factory network with machines and balancers.
 * @param {Object<string, number>} outputs - desired output materials and rates (e.g., {"Iron Plate": 100})
 * @param {Array<[string, number]>} inputs - list of [material, flowRate] tuples for input conveyors
 * @param {Array<[string, string]>} mines - list of [resourceName, purity] tuples for mining nodes
 * @param {Set<string>|null} enablementSet - set of enabled recipe names or null for defaults
 * @param {Object<string, number>|null} economy - dict of material values for cost optimization
 * @param {number} inputCostsWeight - optimization weight for input costs
 * @param {number} machineCountsWeight - optimization weight for machine counts
 * @param {number} powerConsumptionWeight - optimization weight for power usage
 * @param {boolean} designPower - whether to include power generation in the design
 * @param {boolean} disableBalancers - if true, use simple hub nodes instead of balancer networks
 * @returns {Promise<Factory>} Factory with complete network graph including machines and balancers
 */
async function design_factory(
    outputs,
    inputs,
    mines,
    enablementSet = null,
    economy = null,
    inputCostsWeight = 1.0,
    machineCountsWeight = 0.0,
    powerConsumptionWeight = 1.0,
    wasteProductsWeight = 0.0,
    designPower = false,
    disableBalancers = false,
    onProgress = null
) {
    const report_progress = (message) => {
        if (onProgress) {
            onProgress(message);
        }
    };

    // Normalize material names to canonical case
    outputs = normalize_material_names(outputs);
    inputs = normalize_input_array(inputs);

    // Phase 1: Calculate required machines
    report_progress("Optimizing recipe selection...");
    const [machineInstances, recipesUsed, requiredRawMaterials, totalProduction, recipeCounts] = 
        await _calculateMachines(
            outputs,
            inputs,
            mines,
            enablementSet,
            economy,
            inputCostsWeight,
            machineCountsWeight,
            powerConsumptionWeight,
            wasteProductsWeight,
            designPower,
            onProgress
        );

    report_progress("Building factory network...");

    // Recompute balance for output calculation
    const balance = _recomputeBalanceForOutputs(
        inputs, mines, outputs, machineInstances, recipesUsed
    );

    // Compute actual outputs
    const actualOutputs = _computeActualOutputs(outputs, totalProduction, balance);

    // Phase 2: Build network graph with balancers
    const dot = new Digraph("Factory Network");
    dot.attr({ rankdir: "LR", dpi: 50 });

    // Track material flows: {material: {"sources": [...], "sinks": [...]}}
    const materialFlows = {};

    // Add input and mine nodes
    _addInputNodes(dot, inputs, mines, requiredRawMaterials, materialFlows);

    // Add machine nodes
    _addMachineNodes(dot, machineInstances, recipesUsed, materialFlows);

    // Add output nodes
    _addOutputNodes(dot, outputs, totalProduction, balance, materialFlows);

    // Phase 3: Route materials with balancers or simple hub nodes
    if (disableBalancers) {
        _routeMaterialsWithNodes(dot, materialFlows);
    } else {
        _routeMaterialsWithBalancers(dot, materialFlows);
    }

    return new Factory(dot, inputs, actualOutputs, mines, recipeCounts);
}

/**
 * Rebuild factory network graphviz from saved recipe counts.
 * This is much faster than design_factory since it skips the optimizer.
 * 
 * @param {Object<string, number>} recipeCounts - recipe names to machine counts
 * @param {Object<string, number>} outputs - requested output materials
 * @param {Array<[string, number]>} inputs - available input materials
 * @param {Array<[string, string]>} mines - resource mines
 * @param {boolean} disableBalancers - whether to use simple hubs instead of balancers
 * @param {boolean} compact - whether to use compact node names (N0, N1, etc.)
 * @returns {string} graphviz DOT source
 */
function rebuild_graphviz_from_recipe_counts(
    recipeCounts,
    outputs,
    inputs,
    mines,
    disableBalancers = false,
    compact = false
) {
    // Normalize material names to canonical case
    outputs = normalize_material_names(outputs);
    inputs = normalize_input_array(inputs);
    
    // Transform recipeCounts to machineInstances and recipesUsed
    const [machineInstances, recipesUsed, totalProduction] = _transformOptimizerOutput(recipeCounts);
    
    // Compute required raw materials
    const requiredRawMaterials = _computeRequiredRawMaterials(
        recipeCounts, outputs, inputs, mines
    );
    
    // Recompute balance for output calculation
    const balance = _recomputeBalanceForOutputs(
        inputs, mines, outputs, machineInstances, recipesUsed
    );
    
    // Build network graph
    const dot = new Digraph("Factory Network");
    dot.attr({ rankdir: "LR", dpi: 50 });
    
    // Track material flows
    const materialFlows = {};
    
    // Add nodes
    _addInputNodes(dot, inputs, mines, requiredRawMaterials, materialFlows);
    _addMachineNodes(dot, machineInstances, recipesUsed, materialFlows);
    _addOutputNodes(dot, outputs, totalProduction, balance, materialFlows);
    
    // Route materials
    if (disableBalancers) {
        _routeMaterialsWithNodes(dot, materialFlows);
    } else {
        _routeMaterialsWithBalancers(dot, materialFlows);
    }
    
    // Return DOT source
    if (compact) {
        return _compactify_graphviz(dot.source);
    } else {
        return dot.source;
    }
}

/**
 * Convert verbose graphviz node names to compact format (N0, N1, etc.)
 * This significantly reduces the size of the DOT source for URL encoding.
 * 
 * @param {string} source - verbose graphviz DOT source
 * @returns {string} compact graphviz DOT source
 */
function _compactify_graphviz(source) {
    // Extract all node IDs (both quoted and unquoted)
    const nodeIdPattern = /(?:"([^"]+)"|([A-Za-z_]\w*))\s*\[/g;
    const nodeIds = new Set();
    let match;
    while ((match = nodeIdPattern.exec(source)) !== null) {
        const nodeId = match[1] || match[2];
        if (nodeId) {
            nodeIds.add(nodeId);
        }
    }
    
    // Create mapping from verbose names to compact names
    const nodeMapping = new Map();
    let nodeIndex = 0;
    for (const nodeId of Array.from(nodeIds).sort()) {
        nodeMapping.set(nodeId, `N${nodeIndex++}`);
    }
    
    // Replace all node references with compact names
    let compactSource = source;
    for (const [verbose, compact] of nodeMapping.entries()) {
        // Handle quoted node IDs
        const quotedPattern = new RegExp(`"${verbose.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"`, 'g');
        compactSource = compactSource.replace(quotedPattern, compact);
        
        // Handle unquoted node IDs (only if they're valid DOT identifiers)
        if (/^[A-Za-z_]\w*$/.test(verbose)) {
            const unquotedPattern = new RegExp(`\\b${verbose.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'g');
            compactSource = compactSource.replace(unquotedPattern, compact);
        }
    }
    
    return compactSource;
}

// ============================================================================
// Exports
// ============================================================================

export { Factory, design_factory, rebuild_graphviz_from_recipe_counts };


