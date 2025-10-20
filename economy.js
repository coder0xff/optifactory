// Satisfactory economy system port from Python
// Computes item values based on recipe interconnections

import { Recipe, get_all_recipes } from './recipes.js';

// ============================================================================
// Logger
// ============================================================================

const _LOGGER = {
    info: (...args) => console.log('[economy]', ...args),
    debug: (...args) => console.debug('[economy]', ...args),
    warn: (...args) => console.warn('[economy]', ...args),
    error: (...args) => console.error('[economy]', ...args)
};

// ============================================================================
// Tarjan's Strongly Connected Components Algorithm
// ============================================================================

/**
 * Find strongly connected components in a directed graph using Tarjan's algorithm
 * 
 * @param {Object} graph - adjacency list mapping nodes to arrays/sets of neighbors
 * @returns {Array<Set>} - array of strongly connected components (each is a Set of nodes)
 */
function tarjan(graph) {
    let index = 0;
    const stack = [];
    const indices = new Map();
    const lowlinks = new Map();
    const onStack = new Set();
    const result = [];

    function strongconnect(v) {
        // Set the depth index for v to the smallest unused index
        indices.set(v, index);
        lowlinks.set(v, index);
        index++;
        stack.push(v);
        onStack.add(v);

        // Consider successors of v
        const neighbors = graph[v] || [];
        for (const w of neighbors) {
            if (!indices.has(w)) {
                // Successor w has not yet been visited; recurse on it
                strongconnect(w);
                lowlinks.set(v, Math.min(lowlinks.get(v), lowlinks.get(w)));
            } else if (onStack.has(w)) {
                // Successor w is in stack and hence in the current SCC
                lowlinks.set(v, Math.min(lowlinks.get(v), indices.get(w)));
            }
        }

        // If v is a root node, pop the stack and generate an SCC
        if (lowlinks.get(v) === indices.get(v)) {
            const component = new Set();
            let w;
            do {
                w = stack.pop();
                onStack.delete(w);
                component.add(w);
            } while (w !== v);
            result.push(component);
        }
    }

    // Call strongconnect for each node
    for (const v in graph) {
        if (!indices.has(v)) {
            strongconnect(v);
        }
    }

    return result;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Collect all unique parts from recipes
 * 
 * @param {Object} recipes - dict mapping recipe names to Recipe objects
 * @returns {Set<string>} - set of all unique part names appearing in inputs or outputs
 */
function _collect_all_parts(recipes) {
    const allParts = new Set();
    for (const recipe of Object.values(recipes)) {
        for (const inputPart of Object.keys(recipe.inputs)) {
            allParts.add(inputPart);
        }
        for (const outputPart of Object.keys(recipe.outputs)) {
            allParts.add(outputPart);
        }
    }
    return allParts;
}

/**
 * Create mappings between part names and indices
 * 
 * @param {Array<string>} sortedParts - list of unique part names in sorted order
 * @param {Object} pinnedValues - dict mapping part names to fixed values
 * @returns {Array} - [partsToIndex, pinnedIndexValues] where partsToIndex maps part names to indices and pinnedIndexValues maps indices to pinned values
 */
function _create_index_mappings(sortedParts, pinnedValues) {
    const partsToIndex = {};
    for (let index = 0; index < sortedParts.length; index++) {
        partsToIndex[sortedParts[index]] = index;
    }
    
    const pinnedIndexValues = {};
    for (const [part, value] of Object.entries(pinnedValues)) {
        if (part in partsToIndex) {
            pinnedIndexValues[partsToIndex[part]] = value;
        }
    }
    
    return [partsToIndex, pinnedIndexValues];
}

/**
 * Convert recipe to indexed form for efficient computation
 * 
 * @param {Object} recipe - Recipe object with inputs and outputs
 * @param {Object} partsToIndex - dict mapping part names to indices
 * @returns {Array} - [inputs, outputs] where inputs and outputs are arrays of [index, amount] pairs
 */
function _recipe_to_indexed_form(recipe, partsToIndex) {
    const inputs = [];
    for (const [inputPart, amount] of Object.entries(recipe.inputs)) {
        inputs.push([partsToIndex[inputPart], amount]);
    }
    
    const outputs = [];
    for (const [outputPart, amount] of Object.entries(recipe.outputs)) {
        outputs.push([partsToIndex[outputPart], amount]);
    }
    
    return [inputs, outputs];
}

/**
 * Organize recipes by their output parts for efficient lookup
 * 
 * @param {Object} recipes - dict mapping recipe names to Recipe objects
 * @param {Array<string>} sortedParts - list of part names in sorted order
 * @param {Object} partsToIndex - dict mapping part names to indices
 * @returns {Array<Array>} - list where index i contains recipes producing sortedParts[i], each in indexed form
 */
function _organize_recipes_by_outputs(recipes, sortedParts, partsToIndex) {
    const recipesProducingDict = {};
    
    for (const recipe of Object.values(recipes)) {
        const indexedRecipe = _recipe_to_indexed_form(recipe, partsToIndex);
        for (const outputPart of Object.keys(recipe.outputs)) {
            if (!recipesProducingDict[outputPart]) {
                recipesProducingDict[outputPart] = [];
            }
            recipesProducingDict[outputPart].push(indexedRecipe);
        }
    }
    
    return sortedParts.map(part => recipesProducingDict[part] || []);
}

/**
 * Organize recipes by their input parts for efficient lookup
 * 
 * @param {Object} recipes - dict mapping recipe names to Recipe objects
 * @param {Array<string>} sortedParts - list of part names in sorted order
 * @param {Object} partsToIndex - dict mapping part names to indices
 * @returns {Array<Array>} - list where index i contains recipes consuming sortedParts[i], each in indexed form
 */
function _organize_recipes_by_inputs(recipes, sortedParts, partsToIndex) {
    const recipesConsumingDict = {};
    
    for (const recipe of Object.values(recipes)) {
        const indexedRecipe = _recipe_to_indexed_form(recipe, partsToIndex);
        for (const inputPart of Object.keys(recipe.inputs)) {
            if (!recipesConsumingDict[inputPart]) {
                recipesConsumingDict[inputPart] = [];
            }
            recipesConsumingDict[inputPart].push(indexedRecipe);
        }
    }
    
    return sortedParts.map(part => recipesConsumingDict[part] || []);
}

/**
 * Initialize values array with defaults and pinned values
 * 
 * @param {number} numParts - number of parts
 * @param {Object} pinnedIndexValues - dict mapping indices to pinned values
 * @returns {Array<number>} - array of length numParts, all values default to 1.0, pinned indices set to their pinned values
 */
function _initialize_values_array(numParts, pinnedIndexValues) {
    const values = new Array(numParts).fill(1);
    for (const [index, value] of Object.entries(pinnedIndexValues)) {
        values[parseInt(index)] = value;
    }
    return values;
}

/**
 * Compute error and change trends from recent history
 * 
 * @param {Array<number>} recentErrors - list of recent errors
 * @param {Array<number>} recentChanges - list of recent changes
 * @returns {Array<number>} - [errorTrend, changeTrend]; if length >= 100, compares first 50 vs last 50, otherwise returns [0, 0]
 */
function _compute_trend_metrics(recentErrors, recentChanges) {
    if (recentErrors.length >= 100) {
        const firstHalfErrorTotal = recentErrors.slice(0, 50).reduce((a, b) => a + b, 0);
        const secondHalfErrorTotal = recentErrors.slice(50).reduce((a, b) => a + b, 0);
        const firstHalfChangeTotal = recentChanges.slice(0, 50).reduce((a, b) => a + b, 0);
        const secondHalfChangeTotal = recentChanges.slice(50).reduce((a, b) => a + b, 0);
        const errorTrend = secondHalfErrorTotal - firstHalfErrorTotal;
        const changeTrend = secondHalfChangeTotal - firstHalfChangeTotal;
        return [errorTrend, changeTrend];
    } else {
        return [0, 0];
    }
}

/**
 * Adjust temperature based on convergence trends
 * 
 * @param {number} temperature - current temperature
 * @param {number} temperatureCap - temperature cap
 * @param {number} temperatureCapRate - temperature cap rate
 * @param {number} errorTrend - error trend
 * @param {number} changeTrend - change trend
 * @returns {Array<number>} - [newTemperature, newTemperatureCap, newTemperatureCapRate]
 */
function _adjust_temperature(temperature, temperatureCap, temperatureCapRate, errorTrend, changeTrend) {
    if (errorTrend >= 0 && changeTrend >= 0) {
        // Looks like divergence, cool down
        temperature *= 0.999;
        temperatureCapRate = Math.max(temperatureCapRate + 0.01, 8);
        temperatureCap = Math.min(temperatureCap, temperature);
    } else if (changeTrend < 0) {
        // Looks like convergence, heat up
        temperature *= 1.01;
        temperatureCap = 1.0 - (1.0 - temperatureCap) * (1 - Math.pow(10, -temperatureCapRate));
        temperatureCapRate *= 0.999;
    }
    // else do nothing, seems to be hard to reach state anyway
    
    temperature = Math.min(temperature, temperatureCap);
    return [temperature, temperatureCap, temperatureCapRate];
}

/**
 * Normalize values to minimum of 1.0 and round
 * 
 * @param {Array<number>} values - list of values (all positive)
 * @param {Object} pinnedIndexValues - dict mapping indices to pinned values
 * @returns {Array<number>} - normalized and rounded values
 */
function _normalize_and_round_values(values, pinnedIndexValues) {
    const minValue = Math.min(...values);
    const normalization = 1 / minValue;
    values = values.map(value => value * normalization);
    
    for (const [index, value] of Object.entries(pinnedIndexValues)) {
        values[parseInt(index)] = value;
    }
    
    values = values.map(value => Math.round(value * 1e8) / 1e8);
    return values;
}

/**
 * Normalize list of values so minimum is 1.0
 * 
 * @param {Array<number>} values - list of positive floats
 * @returns {Array<number>} - normalized values
 */
function _normalize_values_list(values) {
    const normalization = 1 / Math.min(...values);
    return values.map(value => value * normalization);
}

/**
 * Interpolate between current and instantaneous values using temperature
 * 
 * @param {Array<number>} values - list of current values
 * @param {Array<number>} instantaneousValues - list of instantaneous values
 * @param {number} temperature - interpolation factor (0 to 1)
 * @param {Object} pinnedIndexValues - dict mapping indices to pinned values
 * @returns {Array<number>} - interpolated values
 */
function _interpolate_values(values, instantaneousValues, temperature, pinnedIndexValues) {
    const newValues = values.map((original, i) => 
        original * (1 - temperature) + instantaneousValues[i] * temperature
    );
    
    // Ensure pinned values stay exactly at their pinned value
    for (const [index, pinnedValue] of Object.entries(pinnedIndexValues)) {
        newValues[parseInt(index)] = pinnedValue;
    }
    
    return newValues;
}

/**
 * Compute errors and changes between iterations
 * 
 * @param {Array<number>} values - list of original values
 * @param {Array<number>} newValues - list of new values after interpolation
 * @param {Array<number>} instantaneousValues - list of instantaneous values
 * @returns {Array<Array<number>>} - [errors, changes] where errors[i] = abs(instantaneousValues[i] - newValues[i]) and changes[i] = newValues[i] - values[i]
 */
function _compute_errors_and_changes(values, newValues, instantaneousValues) {
    const errors = newValues.map((value, i) => Math.abs(instantaneousValues[i] - value));
    const changes = newValues.map((newVal, i) => newVal - values[i]);
    return [errors, changes];
}

/**
 * Compute value estimate from consuming recipes
 * 
 * @param {number} partIndex - index of the part
 * @param {Array} consumingRecipes - list of (inputs, outputs) tuples consuming this part
 * @param {Array<number>} values - list of current value estimates
 * @returns {number} - value estimate based on consumer outputs
 */
function _value_from_consumers(partIndex, consumingRecipes, values) {
    let valueOfAllConsumerOutputs = 0;
    for (const recipe of consumingRecipes) {
        for (const [outputPart, amount] of recipe[1]) {
            valueOfAllConsumerOutputs += values[outputPart] * amount;
        }
    }
    
    let numberOfAllInputsToConsumers = 0;
    for (const recipe of consumingRecipes) {
        for (const [, amount] of recipe[0]) {
            numberOfAllInputsToConsumers += amount;
        }
    }
    
    let numberOfPartInputsToConsumers = 0;
    for (const recipe of consumingRecipes) {
        for (const [inputPart, amount] of recipe[0]) {
            if (inputPart === partIndex) {
                numberOfPartInputsToConsumers += amount;
            }
        }
    }
    
    const proportionOfPartInputsToAllInputs = numberOfPartInputsToConsumers / numberOfAllInputsToConsumers;
    const valueOfPartInputsToConsumers = valueOfAllConsumerOutputs * proportionOfPartInputsToAllInputs;
    return valueOfPartInputsToConsumers / numberOfPartInputsToConsumers;
}

/**
 * Compute value estimate from producing recipes
 * 
 * @param {number} partIndex - index of the part
 * @param {Array} producingRecipes - list of (inputs, outputs) tuples producing this part
 * @param {Array<number>} values - list of current value estimates
 * @returns {number} - value estimate based on producer inputs
 */
function _value_from_producers(partIndex, producingRecipes, values) {
    let valueOfAllProducerInputs = 0;
    for (const recipe of producingRecipes) {
        for (const [inputPart, amount] of recipe[0]) {
            valueOfAllProducerInputs += values[inputPart] * amount;
        }
    }
    
    let numberOfAllOutputsFromProducers = 0;
    for (const recipe of producingRecipes) {
        for (const [, amount] of recipe[1]) {
            numberOfAllOutputsFromProducers += amount;
        }
    }
    
    let numberOfPartOutputsFromProducers = 0;
    for (const recipe of producingRecipes) {
        for (const [outputPart, amount] of recipe[1]) {
            if (outputPart === partIndex) {
                numberOfPartOutputsFromProducers += amount;
            }
        }
    }
    
    const proportionOfPartOutputsToAllOutputs = numberOfPartOutputsFromProducers / numberOfAllOutputsFromProducers;
    const valueOfPartOutputsFromProducers = valueOfAllProducerInputs * proportionOfPartOutputsToAllOutputs;
    return valueOfPartOutputsFromProducers / numberOfPartOutputsFromProducers;
}

/**
 * Compute instantaneous value estimate for a part
 * 
 * @param {number} partIndex - index of the part being updated
 * @param {Array} producingRecipes - recipes that produce this part
 * @param {Array} consumingRecipes - recipes that consume this part
 * @param {Array<number>} values - current value estimates for all parts
 * @returns {number} - new instantaneous value estimate for the part
 */
function _instantaneous_value(partIndex, producingRecipes, consumingRecipes, values) {
    let counter = 0;
    let accumulator = 0;
    
    if (consumingRecipes.length > 0) {
        counter += 1;
        accumulator += _value_from_consumers(partIndex, consumingRecipes, values);
    }
    
    if (producingRecipes.length > 0) {
        counter += 1;
        accumulator += _value_from_producers(partIndex, producingRecipes, values);
    }
    
    return accumulator / counter;
}

/**
 * Compute instantaneous values for all parts
 * 
 * @param {Array} recipesProducing - list of recipes producing each part
 * @param {Array} recipesConsuming - list of recipes consuming each part
 * @param {Array<number>} values - list of current value estimates
 * @param {Object} pinnedIndexValues - dict mapping indices to pinned values
 * @returns {Array<number>} - list of instantaneous values
 */
function _compute_all_instantaneous_values(recipesProducing, recipesConsuming, values, pinnedIndexValues) {
    const instantaneousValues = [];
    for (let partIndex = 0; partIndex < recipesProducing.length; partIndex++) {
        if (partIndex in pinnedIndexValues) {
            instantaneousValues.push(pinnedIndexValues[partIndex]);
        } else {
            const instantaneous = _instantaneous_value(
                partIndex,
                recipesProducing[partIndex],
                recipesConsuming[partIndex],
                values
            );
            instantaneousValues.push(instantaneous);
        }
    }
    return instantaneousValues;
}

/**
 * Perform one iteration step of value convergence
 * 
 * @param {Array} recipesProducing - list of recipes producing each part
 * @param {Array} recipesConsuming - list of recipes consuming each part
 * @param {Array<number>} values - list of current value estimates
 * @param {number} temperature - interpolation factor
 * @param {Object} pinnedIndexValues - dict mapping indices to pinned values
 * @returns {Array} - [newValues, changes, errors]
 */
function _step(recipesProducing, recipesConsuming, values, temperature, pinnedIndexValues) {
    let instantaneousValues = _compute_all_instantaneous_values(
        recipesProducing, recipesConsuming, values, pinnedIndexValues
    );
    instantaneousValues = _normalize_values_list(instantaneousValues);
    const newValues = _interpolate_values(values, instantaneousValues, temperature, pinnedIndexValues);
    const [errors, changes] = _compute_errors_and_changes(values, newValues, instantaneousValues);
    return [newValues, changes, errors];
}

/**
 * Compute two-way ranks for all parts (distance from base/terminal items)
 * 
 * @param {Array} recipesProducing - list of recipes producing each part
 * @param {Array} recipesConsuming - list of recipes consuming each part
 * @param {number} numParts - number of parts
 * @returns {Array<number>} - list of ranks (rank 0 for base/terminal items)
 */
function _compute_two_way_ranks(recipesProducing, recipesConsuming, numParts) {
    const twoWayRanks = new Array(numParts).fill(numParts);
    let twoWayRanksDone = false;
    
    while (!twoWayRanksDone) {
        twoWayRanksDone = true;
        for (let partIndex = 0; partIndex < numParts; partIndex++) {
            const producingRecipes = recipesProducing[partIndex];
            const consumingRecipes = recipesConsuming[partIndex];
            
            if (producingRecipes.length === 0 || consumingRecipes.length === 0) {
                if (1 < twoWayRanks[partIndex]) {
                    twoWayRanks[partIndex] = 0;
                    twoWayRanksDone = false;
                }
                continue;
            }
            
            for (const [inputs, outputs] of producingRecipes) {
                // Chain inputs and outputs together
                const allParts = [...inputs, ...outputs];
                for (const [otherPartIndex, ] of allParts) {
                    const plusOne = twoWayRanks[otherPartIndex] + 1;
                    if (plusOne < twoWayRanks[partIndex]) {
                        twoWayRanks[partIndex] = plusOne;
                        twoWayRanksDone = false;
                    }
                }
            }
        }
    }
    
    return twoWayRanks;
}

/**
 * Relax values by processing parts in reverse rank order
 * 
 * @param {Array} recipesProducing - list of recipes producing each part
 * @param {Array} recipesConsuming - list of recipes consuming each part
 * @param {Array<number>} values - list of current value estimates
 * @param {Array<number>} twoWayRanks - list of ranks for each part
 * @param {Object} pinnedIndexValues - dict mapping indices to pinned values
 * @returns {Array<number>} - relaxed values
 */
function _relax_by_ranks(recipesProducing, recipesConsuming, values, twoWayRanks, pinnedIndexValues) {
    const maxRank = Math.max(...twoWayRanks);
    for (let rank = maxRank - 1; rank >= 0; rank--) {
        let newValues = [...values];
        const partsWithRank = [];
        for (let partIndex = 0; partIndex < twoWayRanks.length; partIndex++) {
            if (twoWayRanks[partIndex] === rank) {
                partsWithRank.push(partIndex);
            }
        }
        
        for (const partIndex of partsWithRank) {
            newValues[partIndex] = _instantaneous_value(
                partIndex,
                recipesProducing[partIndex],
                recipesConsuming[partIndex],
                values
            );
        }
        
        for (const [index, value] of Object.entries(pinnedIndexValues)) {
            newValues[parseInt(index)] = value;
        }
        
        values = newValues;
    }
    return values;
}

/**
 * Compute values for all items in a single economy using iterative convergence
 * 
 * @param {Object} recipes - dict mapping recipe names to Recipe objects (all recipes form single interconnected economy)
 * @param {Object} pinnedValues - dict mapping item names to fixed values that won't change during convergence (optional)
 * @returns {Object} - dict mapping item names to computed values
 */
function _compute_economy_values(recipes, pinnedValues = null) {
    pinnedValues = pinnedValues || {};
    
    // Setup phase
    const allParts = _collect_all_parts(recipes);
    _LOGGER.info(`Computing economies for ${Object.keys(recipes).length} recipes. This will take a moment...`);
    
    const sortedParts = Array.from(allParts).sort();
    const [partsToIndex, pinnedIndexValues] = _create_index_mappings(sortedParts, pinnedValues);
    
    // Organize recipes for efficient lookup
    const recipesProducing = _organize_recipes_by_outputs(recipes, sortedParts, partsToIndex);
    const recipesConsuming = _organize_recipes_by_inputs(recipes, sortedParts, partsToIndex);
    
    // Initialize values
    let values = _initialize_values_array(allParts.size, pinnedIndexValues);
    
    // Iterative convergence
    let temperature = 0.5;
    let temperatureCap = 0.5;
    let temperatureCapRate = 3;
    const recentErrors = [];
    const recentChanges = [];
    
    while (true) {
        const [newValues, changes, errors] = _step(recipesProducing, recipesConsuming, values, temperature, pinnedIndexValues);
        values = newValues;
        
        const error = errors.reduce((sum, e) => sum + e * e, 0);
        const change = changes.reduce((sum, c) => sum + Math.abs(c), 0);
        
        recentErrors.push(error);
        recentChanges.push(change);
        
        // Keep only last 100 values
        if (recentErrors.length > 100) {
            recentErrors.shift();
            recentChanges.shift();
        }
        
        // Adjust temperature based on trends
        const [errorTrend, changeTrend] = _compute_trend_metrics(recentErrors, recentChanges);
        [temperature, temperatureCap, temperatureCapRate] = _adjust_temperature(
            temperature, temperatureCap, temperatureCapRate, errorTrend, changeTrend
        );
        
        if (change <= 0.00000001) {
            break;
        }
    }
    
    // Post-processing
    values = _relax(recipesProducing, recipesConsuming, values, sortedParts, pinnedIndexValues);
    values = _normalize_and_round_values(values, pinnedIndexValues);
    
    // Convert back to dict
    const result = {};
    for (let i = 0; i < sortedParts.length; i++) {
        result[sortedParts[i]] = values[i];
    }
    return result;
}

/**
 * Perform relaxation to improve value estimates
 * 
 * @param {Array} recipesProducing - list of recipes producing each part
 * @param {Array} recipesConsuming - list of recipes consuming each part
 * @param {Array<number>} values - list of current value estimates
 * @param {Array<string>} sortedParts - list of part names (unused, for debugging)
 * @param {Object} pinnedIndexValues - dict mapping indices to pinned values
 * @returns {Array<number>} - relaxed values
 */
function _relax(recipesProducing, recipesConsuming, values, sortedParts, pinnedIndexValues) {
    const twoWayRanks = _compute_two_way_ranks(recipesProducing, recipesConsuming, values.length);
    values = _relax_by_ranks(recipesProducing, recipesConsuming, values, twoWayRanks, pinnedIndexValues);
    return values;
}

// ============================================================================
// Public API Functions
// ============================================================================

/**
 * Separate recipes into disconnected economies using Tarjan's algorithm
 * 
 * @param {Object} recipes - dict mapping recipe names to Recipe objects
 * @returns {Array<Object>} - list of economy dicts, each containing interconnected recipes
 */
function separate_economies(recipes) {
    const partsToParts = {};
    const partsToRecipes = {};
    
    for (const [name, recipe] of Object.entries(recipes)) {
        for (const part of Object.keys(recipe.inputs)) {
            if (!partsToParts[part]) {
                partsToParts[part] = new Set();
            }
            if (!partsToRecipes[part]) {
                partsToRecipes[part] = [];
            }
            
            for (const inputPart of Object.keys(recipe.inputs)) {
                partsToParts[part].add(inputPart);
            }
            for (const outputPart of Object.keys(recipe.outputs)) {
                partsToParts[part].add(outputPart);
            }
            partsToRecipes[part].push(name);
        }
        
        for (const part of Object.keys(recipe.outputs)) {
            if (!partsToParts[part]) {
                partsToParts[part] = new Set();
            }
            if (!partsToRecipes[part]) {
                partsToRecipes[part] = [];
            }
            
            for (const inputPart of Object.keys(recipe.inputs)) {
                partsToParts[part].add(inputPart);
            }
            for (const outputPart of Object.keys(recipe.outputs)) {
                partsToParts[part].add(outputPart);
            }
            partsToRecipes[part].push(name);
        }
    }
    
    const partEconomies = tarjan(partsToParts);
    
    const result = [];
    for (const partEconomy of partEconomies) {
        const recipeSet = new Set();
        for (const part of partEconomy) {
            if (partsToRecipes[part]) {
                for (const recipeName of partsToRecipes[part]) {
                    recipeSet.add(recipeName);
                }
            }
        }
        
        const economyRecipes = {};
        for (const recipeName of recipeSet) {
            economyRecipes[recipeName] = recipes[recipeName];
        }
        result.push(economyRecipes);
    }
    
    return result;
}

/**
 * Compute item values for all recipes, handling multiple separate economies
 * 
 * @param {Object} recipes - dict of all recipes to consider (if null, uses all available recipes)
 * @param {Object} pinnedValues - dict of item names to fixed values that won't change during convergence
 * @returns {Object} - dict mapping all item names to their computed values
 */
function compute_item_values(recipes = null, pinnedValues = null) {
    recipes = recipes || get_all_recipes();
    pinnedValues = pinnedValues || {};
    const economyRecipes = separate_economies(recipes);
    
    const result = {};
    for (const economy of economyRecipes) {
        const economyValues = _compute_economy_values(economy, pinnedValues);
        Object.assign(result, economyValues);
    }
    
    return result;
}

/**
 * Get the default economies for a given set of recipes
 * 
 * @param {Object} recipes - dict of recipes (if null, uses all available recipes)
 * @returns {Array<Object>} - array of economy dicts, each mapping item names to values
 */
function get_default_economies(recipes = null) {
    recipes = recipes || get_all_recipes();
    const economyRecipes = separate_economies(recipes);
    return economyRecipes.map(economy => _compute_economy_values(economy));
}

/**
 * Get the default economy combining all separate economies into one dict
 * 
 * @param {Object} recipes - dict of recipes (if null, uses all available recipes)
 * @returns {Object} - dict mapping all item names to values
 */
function get_default_economy(recipes = null) {
    return compute_item_values(recipes);
}

/**
 * Compute the total cost of recipe inputs
 * 
 * @param {Object} recipes - dict mapping recipe names to counts
 * @param {Object} economy - dict mapping item names to values (if null, uses default economy)
 * @returns {number} - total cost
 */
function cost_of_recipes(recipes, economy = null) {
    economy = economy || get_default_economy();
    
    let cost = 0;
    const allRecipes = get_all_recipes();
    for (const [recipeName, amount] of Object.entries(recipes)) {
        const recipe = allRecipes[recipeName];
        for (const [inputPart, inputAmount] of Object.entries(recipe.inputs)) {
            cost += economy[inputPart] * inputAmount * amount;
        }
    }
    return cost;
}

/**
 * Convert economy values and pinned status to CSV string
 * 
 * @param {Object} economy - dict mapping item names to values
 * @param {Set} pinnedItems - set of item names that are pinned (optional)
 * @returns {string} - CSV string with header and data rows
 */
function economy_to_csv(economy, pinnedItems = null) {
    pinnedItems = pinnedItems || new Set();
    
    const rows = ['Item,Value,Pinned'];
    
    for (const item of Object.keys(economy).sort()) {
        const value = economy[item];
        const pinned = pinnedItems.has(item) ? 'true' : 'false';
        rows.push(`${item},${value},${pinned}`);
    }
    
    return rows.join('\n');
}

/**
 * Parse economy values and pinned status from CSV string
 * 
 * @param {string} csvString - CSV string with Item, Value, Pinned columns
 * @returns {Array} - [economy, pinnedItems] where economy is dict and pinnedItems is Set
 */
function economy_from_csv(csvString) {
    const economy = {};
    const pinnedItems = new Set();
    
    const lines = csvString.trim().split('\n');
    // Skip header row
    for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(',');
        if (parts.length >= 3) {
            const item = parts[0];
            const value = parseFloat(parts[1]);
            const pinned = parts[2].toLowerCase() === 'true';
            
            economy[item] = value;
            if (pinned) {
                pinnedItems.add(item);
            }
        }
    }
    
    return [economy, pinnedItems];
}

export {
    tarjan,
    separate_economies,
    compute_item_values,
    get_default_economies,
    get_default_economy,
    cost_of_recipes,
    economy_to_csv,
    economy_from_csv
};
