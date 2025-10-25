/**
 * Satisfactory recipe system port from Python.
 * All quantities are "per minute".
 */

import { RECIPES_DATA } from './recipes-data.js';
import { LOADS_DATA } from './loads-data.js';
import { FLUIDS_DATA } from './fluids-data.js';

// ============================================================================
// Constants
// ============================================================================

// capacities of the conveyors in the game
const _CONVEYORS = [60, 120, 270, 480];

// capacities of the pipelines in the game
const _PIPELINES = [300, 600];

// resource node purity levels
const Purity = {
    IMPURE: 0,
    NORMAL: 1,
    PURE: 2
};

// speeds of the miners, major axis is miner version, second axis is purity
const _MINERS = [
    [30, 60, 120],  // Mk. 1
    [60, 120, 240],  // Mk. 2
    [120, 240, 480]  // Mk. 3
];

const _WATER_EXTRACTOR = 120;  // cubic meters per minute

const _OIL_EXTRACTORS = [60, 120, 240];  // impure, normal, pure

// ============================================================================
// Recipe Class
// ============================================================================

/**
 * A Satisfactory recipe.
 */
class Recipe {
    /**
     * @param {string} machine - machine type name
     * @param {Object<string, number>} inputs - dict mapping material names to amounts per minute
     * @param {Object<string, number>} outputs - dict mapping material names to amounts per minute
     */
    constructor(machine, inputs, outputs) {
        this.machine = machine;
        this.inputs = inputs;
        this.outputs = outputs;
    }
}

// ============================================================================
// Module-level data structures
// ============================================================================

// nested dict: output -> amount -> list of [machine, recipe_name]
const _BY_OUTPUT = {};

// dict: machine -> (recipe_name -> Recipe)
const _BY_MACHINE = {};

// set of all part names
const _ALL_PARTS = new Set();

// dict: recipe_name -> Recipe
const _ALL_RECIPES = {};

// reverse lookup: Recipe -> recipe_name (using Map since objects are keys)
const _RECIPE_NAMES = new Map();

// set of base parts (no recipe creates them)
const _BASE_PARTS = new Set();

// set of terminal parts (no recipe consumes them)
const _TERMINAL_PARTS = new Set();

// set of recipes enabled by default
const _DEFAULT_ENABLEMENT_SET = new Set();

// ============================================================================
// Helper functions for initialization
// ============================================================================

/**
 * Collect all input and output parts from a recipe into _ALL_PARTS.
 * @param {Object<string, Object<string, number>>} recipe_data - raw recipe dict with "in" and "out" keys
 */
function _collect_recipe_parts(recipe_data) {
    for (const part of Object.keys(recipe_data.in)) {
        _ALL_PARTS.add(part);
    }
    for (const part of Object.keys(recipe_data.out)) {
        _ALL_PARTS.add(part);
    }
}

/**
 * Add recipe to the _BY_OUTPUT index for each output material.
 * @param {Object<string, Object<string, number>>} recipe_data - raw recipe dict with "out" key
 * @param {string} machine - machine type name
 * @param {string} recipe_name - recipe name
 */
function _index_recipe_outputs(recipe_data, machine, recipe_name) {
    for (const [output, amount] of Object.entries(recipe_data.out)) {
        if (!_BY_OUTPUT[output]) {
            _BY_OUTPUT[output] = {};
        }
        if (!_BY_OUTPUT[output][amount]) {
            _BY_OUTPUT[output][amount] = [];
        }
        _BY_OUTPUT[output][amount].push([machine, recipe_name]);
    }
}

/**
 * Add machine power consumption to recipe inputs.
 * @param {Object<string, number>} inputs - recipe input materials
 * @param {string} machine - machine type name
 * @returns {Object<string, number>} inputs with power consumption added
 */
function _add_power_consumption(inputs, machine) {
    const result = { ...inputs };
    if (machine in LOADS_DATA) {
        result.MWm = (result.MWm || 0) + LOADS_DATA[machine];
    }
    return result;
}

/**
 * Create a Recipe object with power consumption added to inputs.
 * @param {string} machine - machine type name
 * @param {Object<string, Object<string, number>>} recipe_data - raw recipe dict with "in" and "out" keys
 * @returns {Recipe} new Recipe object
 */
function _create_recipe_object(machine, recipe_data) {
    const inputs_with_power = _add_power_consumption(recipe_data.in, machine);
    return new Recipe(machine, inputs_with_power, recipe_data.out);
}

/**
 * Register recipe in _ALL_RECIPES, _RECIPE_NAMES, and _BY_MACHINE.
 * @param {Recipe} recipe - Recipe object to register
 * @param {string} recipe_name - recipe name
 * @param {string} machine - machine type name
 */
function _register_recipe(recipe, recipe_name, machine) {
    if (!_BY_MACHINE[machine]) {
        _BY_MACHINE[machine] = {};
    }
    _BY_MACHINE[machine][recipe_name] = recipe;
    _ALL_RECIPES[recipe_name] = recipe;
    _RECIPE_NAMES.set(recipe, recipe_name);
}

/**
 * Check if a part is a base part (has no recipe to create it).
 * @param {string} part - material name to check
 * @returns {boolean} true if part is a base part
 */
function _is_base_part(part) {
    if (!(part in _BY_OUTPUT)) {
        return true;
    }
    // check if all recipes that output this part have no inputs
    for (const recipe of Object.values(_ALL_RECIPES)) {
        if (part in recipe.outputs) {
            if (Object.keys(recipe.inputs).length > 0) {
                return false;
            }
        }
    }
    return true;
}

/**
 * Check if a part is a terminal part (no recipe consumes it).
 * @param {string} part - material name to check
 * @returns {boolean} true if part is not consumed by any recipe
 */
function _is_terminal_part(part) {
    for (const recipe of Object.values(_ALL_RECIPES)) {
        if (part in recipe.inputs) {
            return false;
        }
    }
    return true;
}

/**
 * Add hardcoded base materials to _BASE_PARTS.
 */
function _add_hardcoded_base_parts() {
    _BASE_PARTS.add("Iron Ore");
    _BASE_PARTS.add("Copper Ore");
    _BASE_PARTS.add("Limestone");
    _BASE_PARTS.add("Caterium Ore");
    _BASE_PARTS.add("Coal");
    _BASE_PARTS.add("Water");
    _BASE_PARTS.add("Crude Oil");
}

/**
 * Classify all parts as base parts and/or terminal parts.
 */
function _classify_parts() {
    for (const part of _ALL_PARTS) {
        if (_is_base_part(part)) {
            _BASE_PARTS.add(part);
        }
        if (_is_terminal_part(part)) {
            _TERMINAL_PARTS.add(part);
        }
    }
    _add_hardcoded_base_parts();
}

/**
 * Check if a recipe should be enabled by default.
 * @param {Recipe} recipe - Recipe to check
 * @param {string} machine - machine type for this recipe
 * @returns {boolean} true if recipe doesn't output MWm and isn't from Packager
 */
function _should_enable_recipe_by_default(recipe, machine) {
    return !("MWm" in recipe.outputs) && machine !== "Packager";
}

/**
 * Build the set of recipes enabled by default.
 */
function _build_default_enablement_set() {
    for (const [machine, recipes] of Object.entries(_BY_MACHINE)) {
        for (const [name, recipe] of Object.entries(recipes)) {
            if (_should_enable_recipe_by_default(recipe, machine)) {
                _DEFAULT_ENABLEMENT_SET.add(name);
            }
        }
    }
}

/**
 * Process a single recipe: collect parts, index outputs, create and register Recipe.
 * @param {string} machine - machine type name
 * @param {string} recipe_name - recipe name
 * @param {Object<string, Object<string, number>>} recipe_data - raw recipe dict with "in" and "out" keys
 */
function _process_single_recipe(machine, recipe_name, recipe_data) {
    _collect_recipe_parts(recipe_data);
    _index_recipe_outputs(recipe_data, machine, recipe_name);
    const recipe_obj = _create_recipe_object(machine, recipe_data);
    _register_recipe(recipe_obj, recipe_name, machine);
}

/**
 * Initialize all module-level lookup tables from recipe data.
 */
function _populate_lookups() {
    for (const [machine, recipes] of Object.entries(RECIPES_DATA)) {
        for (const [recipe_name, recipe_data] of Object.entries(recipes)) {
            _process_single_recipe(machine, recipe_name, recipe_data);
        }
    }
    
    _classify_parts();
    _build_default_enablement_set();
}

// Initialize on module load
_populate_lookups();

// ============================================================================
// Public API functions
// ============================================================================

/**
 * Get the conveyor belt capacity for a given speed tier.
 * @param {number} speed - conveyor speed tier (0-3)
 * @returns {number} capacity in items per minute
 */
function get_conveyor_rate(speed) {
    return _CONVEYORS[speed];
}

/**
 * Get the mining rate for a given miner tier and resource node purity.
 * @param {number} mark - miner mark (0=Mk.1, 1=Mk.2, 2=Mk.3)
 * @param {number} purity - purity level (0=Impure, 1=Normal, 2=Pure)
 * @returns {number} mining rate in items per minute
 */
function get_mining_rate(mark, purity) {
    return _MINERS[mark][purity];
}

/**
 * Get the water extraction rate for water extractors.
 * @returns {number} water extraction rate in cubic meters per minute
 */
function get_water_extraction_rate() {
    return _WATER_EXTRACTOR;
}

/**
 * Get the oil extraction rate for a given resource node purity.
 * @param {number} purity - purity level (0=Impure, 1=Normal, 2=Pure)
 * @returns {number} oil extraction rate in cubic meters per minute
 */
function get_oil_extraction_rate(purity) {
    return _OIL_EXTRACTORS[purity];
}

/**
 * Get the power consumption for a given machine type.
 * @param {string} machine - machine type name
 * @returns {number} power consumption in megawatts
 */
function get_load(machine) {
    return LOADS_DATA[machine];
}

/**
 * Get all recipes grouped by machine type.
 * @returns {Object<string, Object<string, Recipe>>} dict mapping machine names to recipe dicts
 */
function get_all_recipes_by_machine() {
    const result = {};
    for (const [machine, recipes] of Object.entries(_BY_MACHINE)) {
        result[machine] = { ...recipes };
    }
    return result;
}

/**
 * Get all recipes by name.
 * @returns {Object<string, Recipe>} dict mapping recipe names to Recipe objects
 */
function get_all_recipes() {
    return { ..._ALL_RECIPES };
}

/**
 * Check if a recipe is enabled given an enablement set.
 * @param {string} recipe_name - recipe name
 * @param {Set<string>|null} enablement_set - set of enabled recipe names or null for all enabled
 * @returns {boolean} true if recipe is enabled
 */
function _is_recipe_enabled(recipe_name, enablement_set) {
    return !enablement_set || enablement_set.has(recipe_name);
}

/**
 * Create a Recipe object from raw JSON data without power consumption.
 * @param {string} machine - machine type name
 * @param {string} recipe_name - recipe name
 * @returns {Recipe} new Recipe object without power consumption in inputs
 */
function _create_recipe_from_raw(machine, recipe_name) {
    const raw_recipe = RECIPES_DATA[machine][recipe_name];
    return new Recipe(machine, raw_recipe.in, raw_recipe.out);
}

/**
 * Get all recipes that produce a given output material.
 * @param {string} output - output material name
 * @param {Set<string>|null} enablement_set - set of enabled recipe names or null for all enabled
 * @returns {Object<number, Array<[string, Recipe]>>} dict mapping production amounts to arrays of [recipe_name, recipe] tuples
 */
function get_recipes_for(output, enablement_set = null) {
    const results = {};
    
    if (!(output in _BY_OUTPUT)) {
        return results;
    }
    
    for (const [amount, machine_recipe_name_pairs] of Object.entries(_BY_OUTPUT[output])) {
        for (const [machine, recipe_name] of machine_recipe_name_pairs) {
            if (_is_recipe_enabled(recipe_name, enablement_set)) {
                const recipe = _create_recipe_from_raw(machine, recipe_name);
                if (!results[amount]) {
                    results[amount] = [];
                }
                results[amount].push([recipe_name, recipe]);
            }
        }
    }
    return results;
}

/**
 * Get the highest production rate recipe for a given output material.
 * @param {string} output - output material name
 * @param {Set<string>|null} enablement_set - set of enabled recipe names or null for all enabled
 * @returns {[number, string, Recipe]} tuple of [amount, recipe_name, recipe]
 */
function get_recipe_for(output, enablement_set = null) {
    const recipes_for_output = get_recipes_for(output, enablement_set);
    const amounts = Object.keys(recipes_for_output).map(Number);
    const max_amount = Math.max(...amounts);
    const recipes = recipes_for_output[max_amount];
    return [max_amount, recipes[0][0], recipes[0][1]];
}

/**
 * Find the name of a given Recipe object.
 * @param {Recipe} recipe - Recipe object
 * @returns {string|undefined} recipe name or undefined if not found
 */
function find_recipe_name(recipe) {
    return _RECIPE_NAMES.get(recipe);
}

/**
 * Get all base materials (materials with no crafting recipe).
 * @returns {Set<string>} set of base material names
 */
function get_base_parts() {
    return new Set(_BASE_PARTS);
}

/**
 * Get all terminal materials (materials not consumed by any recipe).
 * @returns {Set<string>} set of terminal material names
 */
function get_terminal_parts() {
    return new Set(_TERMINAL_PARTS);
}

/**
 * Get the default set of enabled recipes.
 * @returns {Set<string>} set of default enabled recipe names
 */
function get_default_enablement_set() {
    return new Set(_DEFAULT_ENABLEMENT_SET);
}

/**
 * Get all fluid material names.
 * @returns {Array<string>} array of fluid names
 */
function get_fluids() {
    return Object.keys(FLUIDS_DATA);
}

/**
 * Get the hex color code for a given fluid.
 * @param {string} fluid - fluid name
 * @returns {string} hex color code
 */
function get_fluid_color(fluid) {
    return FLUIDS_DATA[fluid];
}

export {
    Purity,
    Recipe,
    get_conveyor_rate,
    get_mining_rate,
    get_water_extraction_rate,
    get_oil_extraction_rate,
    get_load,
    get_all_recipes_by_machine,
    get_all_recipes,
    get_recipes_for,
    get_recipe_for,
    find_recipe_name,
    get_base_parts,
    get_terminal_parts,
    get_default_enablement_set,
    get_fluids,
    get_fluid_color
};
