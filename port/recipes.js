// Satisfactory recipe system port from Python
// All quantities are "per minute"

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

class Recipe {
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

function _collect_recipe_parts(recipe_data) {
    // collect all input and output parts from a recipe into _ALL_PARTS
    for (const part of Object.keys(recipe_data.in)) {
        _ALL_PARTS.add(part);
    }
    for (const part of Object.keys(recipe_data.out)) {
        _ALL_PARTS.add(part);
    }
}

function _index_recipe_outputs(recipe_data, machine, recipe_name) {
    // add recipe to the _BY_OUTPUT index for each output material
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

function _add_power_consumption(inputs, machine) {
    // add machine power consumption to recipe inputs
    const result = { ...inputs };
    if (machine in LOADS_DATA) {
        result.MWm = (result.MWm || 0) + LOADS_DATA[machine];
    }
    return result;
}

function _create_recipe_object(machine, recipe_data) {
    // create a Recipe object with power consumption added to inputs
    const inputs_with_power = _add_power_consumption(recipe_data.in, machine);
    return new Recipe(machine, inputs_with_power, recipe_data.out);
}

function _register_recipe(recipe, recipe_name, machine) {
    // register a recipe in multiple lookup tables
    if (!_BY_MACHINE[machine]) {
        _BY_MACHINE[machine] = {};
    }
    _BY_MACHINE[machine][recipe_name] = recipe;
    _ALL_RECIPES[recipe_name] = recipe;
    _RECIPE_NAMES.set(recipe, recipe_name);
}

function _is_base_part(part) {
    // check if a part is a base part (has no recipe to create it)
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

function _is_terminal_part(part) {
    // check if a part is a terminal part (no recipe consumes it)
    for (const recipe of Object.values(_ALL_RECIPES)) {
        if (part in recipe.inputs) {
            return false;
        }
    }
    return true;
}

function _add_hardcoded_base_parts() {
    // add hardcoded base materials to _BASE_PARTS
    _BASE_PARTS.add("Iron Ore");
    _BASE_PARTS.add("Copper Ore");
    _BASE_PARTS.add("Limestone");
    _BASE_PARTS.add("Caterium Ore");
    _BASE_PARTS.add("Coal");
    _BASE_PARTS.add("Water");
    _BASE_PARTS.add("Crude Oil");
}

function _classify_parts() {
    // classify all parts as base parts and/or terminal parts
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

function _should_enable_recipe_by_default(recipe, machine) {
    // check if a recipe should be enabled by default
    return !("MWm" in recipe.outputs) && machine !== "Packager";
}

function _build_default_enablement_set() {
    // build the set of recipes enabled by default
    for (const [machine, recipes] of Object.entries(_BY_MACHINE)) {
        for (const [name, recipe] of Object.entries(recipes)) {
            if (_should_enable_recipe_by_default(recipe, machine)) {
                _DEFAULT_ENABLEMENT_SET.add(name);
            }
        }
    }
}

function _process_single_recipe(machine, recipe_name, recipe_data) {
    // process a single recipe: collect parts, index outputs, create and register Recipe
    _collect_recipe_parts(recipe_data);
    _index_recipe_outputs(recipe_data, machine, recipe_name);
    const recipe_obj = _create_recipe_object(machine, recipe_data);
    _register_recipe(recipe_obj, recipe_name, machine);
}

function _populate_lookups() {
    // initialize all module-level lookup tables from recipe data
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

function get_conveyor_rate(speed) {
    // get the conveyor belt capacity for a given speed tier
    return _CONVEYORS[speed];
}

function get_mining_rate(mark, purity) {
    // get the mining rate for a given miner tier and resource node purity
    return _MINERS[mark][purity];
}

function get_water_extraction_rate() {
    // get the water extraction rate for water extractors
    return _WATER_EXTRACTOR;
}

function get_oil_extraction_rate(purity) {
    // get the oil extraction rate for a given resource node purity
    return _OIL_EXTRACTORS[purity];
}

function get_load(machine) {
    // get the power consumption for a given machine type
    return LOADS_DATA[machine];
}

function get_all_recipes_by_machine() {
    // get all recipes grouped by machine type
    const result = {};
    for (const [machine, recipes] of Object.entries(_BY_MACHINE)) {
        result[machine] = { ...recipes };
    }
    return result;
}

function get_all_recipes() {
    // get all recipes by name
    return { ..._ALL_RECIPES };
}

function _is_recipe_enabled(recipe_name, enablement_set) {
    // check if a recipe is enabled given an enablement set
    return !enablement_set || enablement_set.has(recipe_name);
}

function _create_recipe_from_raw(machine, recipe_name) {
    // create a Recipe object from raw JSON data without power consumption
    const raw_recipe = RECIPES_DATA[machine][recipe_name];
    return new Recipe(machine, raw_recipe.in, raw_recipe.out);
}

function get_recipes_for(output, enablement_set = null) {
    // get all recipes that produce a given output material
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

function get_recipe_for(output, enablement_set = null) {
    // get the highest production rate recipe for a given output material
    const recipes_for_output = get_recipes_for(output, enablement_set);
    const amounts = Object.keys(recipes_for_output).map(Number);
    const max_amount = Math.max(...amounts);
    const recipes = recipes_for_output[max_amount];
    return [max_amount, recipes[0][0], recipes[0][1]];
}

function find_recipe_name(recipe) {
    // find the name of a given Recipe object
    return _RECIPE_NAMES.get(recipe);
}

function get_base_parts() {
    // get all base materials (materials with no crafting recipe)
    return new Set(_BASE_PARTS);
}

function get_terminal_parts() {
    // get all terminal materials (materials not consumed by any recipe)
    return new Set(_TERMINAL_PARTS);
}

function get_default_enablement_set() {
    // get the default set of enabled recipes
    return new Set(_DEFAULT_ENABLEMENT_SET);
}

function get_fluids() {
    // get all fluid material names
    return Object.keys(FLUIDS_DATA);
}

function get_fluid_color(fluid) {
    // get the hex color code for a given fluid
    return FLUIDS_DATA[fluid];
}

