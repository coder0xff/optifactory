/**
 * Controller for factory design logic - no GUI dependencies
 * Ported from Python factory_controller.py
 */

import { design_factory } from './factory.js';
import { parse_material_rate } from './parsing-utils.js';
import { get_all_recipes_by_machine, get_recipes_for } from './recipes.js';

// ============================================================================
// Data Classes
// ============================================================================

/**
 * Configuration for factory generation
 */
class FactoryConfig {
    /**
     * @param {Object.<string, number>} outputs - dict of output materials to rates
     * @param {Array.<[string, number]>} inputs - list of [material, rate] tuples
     * @param {Array.<[string, string]>} mines - list of [resource, purity] tuples
     * @param {Set<string>} enabled_recipes - set of enabled recipe names
     * @param {number} input_costs_weight - optimization weight for input costs
     * @param {number} machine_counts_weight - optimization weight for machine counts
     * @param {number} power_consumption_weight - optimization weight for power consumption
     * @param {boolean} design_power - whether to design power generation
     */
    constructor(outputs, inputs, mines, enabled_recipes, 
                input_costs_weight = 1.0, 
                machine_counts_weight = 0.0, 
                power_consumption_weight = 1.0, 
                design_power = false) {
        this.outputs = outputs;
        this.inputs = inputs;
        this.mines = mines;
        this.enabled_recipes = enabled_recipes;
        this.input_costs_weight = input_costs_weight;
        this.machine_counts_weight = machine_counts_weight;
        this.power_consumption_weight = power_consumption_weight;
        this.design_power = design_power;
    }
}

/**
 * Result of configuration validation
 */
class ValidationResult {
    /**
     * @param {boolean} is_valid - whether configuration is valid
     * @param {Array.<string>} warnings - list of warning messages
     * @param {Array.<string>} errors - list of error messages
     */
    constructor(is_valid, warnings, errors) {
        this.is_valid = is_valid;
        this.warnings = warnings;
        this.errors = errors;
    }
}

/**
 * Represents a recipe in the tree
 */
class RecipeTreeNode {
    /**
     * @param {string} tree_id - tree ID in format "recipe:{machine}:{recipe}"
     * @param {string} display_name - display name for the recipe
     * @param {boolean} is_enabled - whether recipe is enabled
     * @param {boolean} is_visible - whether recipe is visible (based on search)
     */
    constructor(tree_id, display_name, is_enabled, is_visible) {
        this.tree_id = tree_id;
        this.display_name = display_name;
        this.is_enabled = is_enabled;
        this.is_visible = is_visible;
    }
}

/**
 * Represents a machine group in the tree
 */
class MachineTreeNode {
    /**
     * @param {string} tree_id - tree ID in format "machine:{machine}"
     * @param {string} display_name - display name for the machine
     * @param {Array.<RecipeTreeNode>} recipes - list of recipe nodes
     * @param {string} check_state - 'checked', 'unchecked', or 'tristate'
     * @param {boolean} is_visible - whether machine is visible (based on search)
     */
    constructor(tree_id, display_name, recipes = [], check_state = 'unchecked', is_visible = true) {
        this.tree_id = tree_id;
        this.display_name = display_name;
        this.recipes = recipes;
        this.check_state = check_state;
        this.is_visible = is_visible;
    }
}

/**
 * Complete tree structure with all IDs and states
 */
class RecipeTreeStructure {
    /**
     * @param {Array.<MachineTreeNode>} machines - list of machine nodes
     */
    constructor(machines = []) {
        this.machines = machines;
    }
}

// ============================================================================
// FactoryController
// ============================================================================

/**
 * Stateful controller for factory design - single source of truth for all application state
 */
class FactoryController {
    /**
     * Initialize controller with economy values.
     * 
     * Precondition:
     *     economy is a dict mapping item names to float values
     * 
     * Postcondition:
     *     this.economy references the provided economy
     *     this._outputs_text is initialized to default "Concrete:480"
     *     this._inputs_text is initialized to comment template
     *     this._mines_text is initialized to empty string
     *     this.enabled_recipes is initialized to default enabled recipes
     *     this._recipe_search_text is empty string
     *     this._input_costs_weight is 1.0
     *     this._machine_counts_weight is 0.0
     *     this._power_consumption_weight is 1.0
     *     this._design_power is false
     *     this._current_factory is null
     * 
     * @param {Object.<string, number>} economy - dict of item names to values
     */
    constructor(economy) {
        this.economy = economy;
        
        // configuration text state
        this._outputs_text = "Concrete:480";
        this._inputs_text = (
            "# Leave empty to auto-detect\n" +
            "# Or specify like:\n" +
            "# Limestone:480\n" +
            "# Limestone:480\n" +
            "# Limestone:480"
        );
        this._mines_text = "";
        
        // recipe state
        this.enabled_recipes = FactoryController._get_default_enabled_recipes();
        this._recipe_search_text = "";
        
        // optimization weights
        this._input_costs_weight = 1.0;
        this._machine_counts_weight = 0.0;
        this._power_consumption_weight = 1.0;
        this._design_power = false;
        
        // generated factory (result)
        this._current_factory = null;
    }
    
    // ========== State Getters ==========
    
    /**
     * Get outputs configuration text.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns current outputs text string
     * 
     * @returns {string} outputs configuration text
     */
    get_outputs_text() {
        return this._outputs_text;
    }
    
    /**
     * Get inputs configuration text.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns current inputs text string
     * 
     * @returns {string} inputs configuration text
     */
    get_inputs_text() {
        return this._inputs_text;
    }
    
    /**
     * Get mines configuration text.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns current mines text string
     * 
     * @returns {string} mines configuration text
     */
    get_mines_text() {
        return this._mines_text;
    }
    
    /**
     * Get recipe search filter text.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns current recipe search text string
     * 
     * @returns {string} recipe search filter text
     */
    get_recipe_search_text() {
        return this._recipe_search_text;
    }
    
    /**
     * Get input costs optimization weight.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns current input costs weight
     * 
     * @returns {number} input costs optimization weight
     */
    get_input_costs_weight() {
        return this._input_costs_weight;
    }
    
    /**
     * Get machine counts optimization weight.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns current machine counts weight
     * 
     * @returns {number} machine counts optimization weight
     */
    get_machine_counts_weight() {
        return this._machine_counts_weight;
    }
    
    /**
     * Get power consumption optimization weight.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns current power consumption weight
     * 
     * @returns {number} power consumption optimization weight
     */
    get_power_consumption_weight() {
        return this._power_consumption_weight;
    }
    
    /**
     * Get design power flag.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns current design power setting
     * 
     * @returns {boolean} design power flag
     */
    get_design_power() {
        return this._design_power;
    }
    
    /**
     * Get currently generated factory.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns current factory or null
     * 
     * @returns {Factory|null} currently generated Factory, or null if not generated
     */
    get_current_factory() {
        return this._current_factory;
    }
    
    /**
     * Get set of enabled recipe names.
     * 
     * Precondition:
     *     this.enabled_recipes is initialized
     * 
     * Postcondition:
     *     returns copy of enabled recipes set
     *     modifications to returned set do not affect controller state
     * 
     * @returns {Set<string>} copy of enabled recipe names
     */
    get_enabled_recipes() {
        return new Set(this.enabled_recipes);
    }
    
    /**
     * Get graphviz source from current factory.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns Graphviz source string if factory and network exist
     *     returns null if no factory generated or network is null
     * 
     * @returns {string|null} Graphviz source string, or null if no factory generated
     */
    get_graphviz_source() {
        if (this._current_factory === null || this._current_factory.network === null) {
            return null;
        }
        return this._current_factory.network.source;
    }
    
    /**
     * Get all recipes organized by machine.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns dict of all recipes grouped by machine
     *     delegates to recipes module function
     * 
     * @returns {Object.<string, Object.<string, Recipe>>} dict of {machine_name: {recipe_name: Recipe}}
     */
    get_all_recipes_by_machine() {
        return get_all_recipes_by_machine();
    }
    
    /**
     * Find a recipe by name across all machines.
     * 
     * Precondition:
     *     recipe_name is a string
     * 
     * Postcondition:
     *     returns Recipe if found, null otherwise
     *     searches across all machines
     * 
     * @param {string} recipe_name - name of the recipe to find
     * @returns {Recipe|null} Recipe object or null
     */
    _find_recipe(recipe_name) {
        const all_recipes = get_all_recipes_by_machine();
        for (const machine_recipes of Object.values(all_recipes)) {
            if (recipe_name in machine_recipes) {
                return machine_recipes[recipe_name];
            }
        }
        return null;
    }
    
    /**
     * Get formatted tooltip text for a recipe.
     * 
     * Precondition:
     *     recipe_name is a string
     * 
     * Postcondition:
     *     returns formatted tooltip if recipe found
     *     returns null if recipe not found
     * 
     * @param {string} recipe_name - name of the recipe
     * @returns {string|null} formatted tooltip string, or null if recipe not found
     */
    get_recipe_tooltip(recipe_name) {
        const recipe = this._find_recipe(recipe_name);
        if (recipe !== null) {
            return FactoryController.format_recipe_tooltip(recipe);
        }
        return null;
    }
    
    // ========== State Setters ==========
    
    /**
     * Set outputs configuration text.
     * 
     * Precondition:
     *     text is a string
     * 
     * Postcondition:
     *     this._outputs_text is updated to text
     * 
     * @param {string} text - new outputs configuration text
     */
    set_outputs_text(text) {
        this._outputs_text = text;
    }
    
    /**
     * Set inputs configuration text.
     * 
     * Precondition:
     *     text is a string
     * 
     * Postcondition:
     *     this._inputs_text is updated to text
     * 
     * @param {string} text - new inputs configuration text
     */
    set_inputs_text(text) {
        this._inputs_text = text;
    }
    
    /**
     * Set mines configuration text.
     * 
     * Precondition:
     *     text is a string
     * 
     * Postcondition:
     *     this._mines_text is updated to text
     * 
     * @param {string} text - new mines configuration text
     */
    set_mines_text(text) {
        this._mines_text = text;
    }
    
    /**
     * Set recipe search filter text.
     * 
     * Precondition:
     *     text is a string
     * 
     * Postcondition:
     *     this._recipe_search_text is updated to text
     * 
     * @param {string} text - new recipe search filter text
     */
    set_recipe_search_text(text) {
        this._recipe_search_text = text;
    }
    
    /**
     * Set input costs optimization weight.
     * 
     * Precondition:
     *     value is a number
     * 
     * Postcondition:
     *     this._input_costs_weight is updated to value
     * 
     * @param {number} value - new input costs weight
     */
    set_input_costs_weight(value) {
        this._input_costs_weight = value;
    }
    
    /**
     * Set machine counts optimization weight.
     * 
     * Precondition:
     *     value is a number
     * 
     * Postcondition:
     *     this._machine_counts_weight is updated to value
     * 
     * @param {number} value - new machine counts weight
     */
    set_machine_counts_weight(value) {
        this._machine_counts_weight = value;
    }
    
    /**
     * Set power consumption optimization weight.
     * 
     * Precondition:
     *     value is a number
     * 
     * Postcondition:
     *     this._power_consumption_weight is updated to value
     * 
     * @param {number} value - new power consumption weight
     */
    set_power_consumption_weight(value) {
        this._power_consumption_weight = value;
    }
    
    /**
     * Set design power flag.
     * 
     * Precondition:
     *     value is a boolean
     * 
     * Postcondition:
     *     this._design_power is updated to value
     * 
     * @param {boolean} value - new design power flag
     */
    set_design_power(value) {
        this._design_power = value;
    }
    
    /**
     * Enable or disable a recipe.
     * 
     * Precondition:
     *     recipe_name is a string
     *     enabled is a boolean
     *     this.enabled_recipes is initialized
     * 
     * Postcondition:
     *     if enabled is true, recipe_name is added to this.enabled_recipes
     *     if enabled is false, recipe_name is removed from this.enabled_recipes
     * 
     * @param {string} recipe_name - name of recipe to modify
     * @param {boolean} enabled - true to enable, false to disable
     */
    set_recipe_enabled(recipe_name, enabled) {
        if (enabled) {
            this.enabled_recipes.add(recipe_name);
        } else {
            this.enabled_recipes.delete(recipe_name);
        }
    }
    
    /**
     * Set the complete set of enabled recipes.
     * 
     * Precondition:
     *     recipe_names is a Set of strings
     * 
     * Postcondition:
     *     this.enabled_recipes is replaced with a copy of recipe_names
     * 
     * @param {Set<string>} recipe_names - set of recipe names to enable (all others disabled)
     */
    set_recipes_enabled(recipe_names) {
        this.enabled_recipes = new Set(recipe_names);
    }
    
    // ========== Derived State / Queries ==========
    
    /**
     * Check if power warning should be displayed.
     * 
     * Precondition:
     *     this._design_power is a boolean
     *     this.enabled_recipes is initialized
     * 
     * Postcondition:
     *     returns true if design_power enabled but no power recipes enabled
     *     returns false otherwise
     * 
     * @returns {boolean} true if design_power is enabled but no power recipes are enabled
     */
    should_show_power_warning() {
        if (!this._design_power) {
            return false;
        }
        
        const power_recipes = get_recipes_for("MWm", this.enabled_recipes);
        return Object.keys(power_recipes).length === 0;
    }
    
    // ========== Tree ID Management ==========
    
    /**
     * Generate stable tree ID for machine.
     * 
     * Precondition:
     *     machine_name is a non-empty string
     * 
     * Postcondition:
     *     returns string in format "machine:{machine_name}"
     * 
     * @param {string} machine_name - name of the machine
     * @returns {string} stable tree ID string
     */
    static _make_machine_id(machine_name) {
        return `machine:${machine_name}`;
    }
    
    /**
     * Generate stable tree ID for recipe.
     * 
     * Precondition:
     *     machine_name is a non-empty string
     *     recipe_name is a non-empty string
     * 
     * Postcondition:
     *     returns string in format "recipe:{machine}:{recipe}"
     * 
     * @param {string} machine_name - name of the machine
     * @param {string} recipe_name - name of the recipe
     * @returns {string} stable tree ID string
     */
    static _make_recipe_id(machine_name, recipe_name) {
        return `recipe:${machine_name}:${recipe_name}`;
    }
    
    /**
     * Parse recipe tree ID into [machine_name, recipe_name].
     * 
     * Precondition:
     *     tree_id is a string
     * 
     * Postcondition:
     *     if tree_id starts with "recipe:" and has valid format, returns array
     *     otherwise returns null
     * 
     * @param {string} tree_id - tree ID in format "recipe:{machine}:{recipe}"
     * @returns {Array<string>|null} array of [machine_name, recipe_name] or null if not a recipe ID
     */
    static _parse_recipe_id(tree_id) {
        if (tree_id.startsWith("recipe:")) {
            const parts = tree_id.substring(7).split(":", 2);
            if (parts.length === 2) {
                return parts;
            }
        }
        return null;
    }
    
    /**
     * Check if recipe matches search text.
     * 
     * Precondition:
     *     recipe_name is a string
     *     recipe is a Recipe object
     *     search_text is a lowercase string
     * 
     * Postcondition:
     *     returns true if recipe_name, inputs, or outputs contain search_text
     *     returns false otherwise
     * 
     * @param {string} recipe_name - name of the recipe
     * @param {Recipe} recipe - Recipe object
     * @param {string} search_text - lowercase search text
     * @returns {boolean} true if recipe matches search criteria
     */
    _recipe_matches_search(recipe_name, recipe, search_text) {
        if (!search_text) {
            return true;
        }
        
        return (
            recipe_name.toLowerCase().includes(search_text) ||
            Object.keys(recipe.inputs).some(inp => inp.toLowerCase().includes(search_text)) ||
            Object.keys(recipe.outputs).some(out => out.toLowerCase().includes(search_text))
        );
    }
    
    /**
     * Get complete tree structure with IDs, states, and visibility.
     * 
     * Precondition:
     *     this._recipe_search_text is a string
     *     this.enabled_recipes is initialized
     * 
     * Postcondition:
     *     returns RecipeTreeStructure with machine and recipe nodes
     *     visibility is based on search text
     *     check states reflect enabled/disabled recipes
     * 
     * @returns {RecipeTreeStructure} RecipeTreeStructure ready for rendering
     */
    get_recipe_tree_structure() {
        const search_text = this._recipe_search_text.toLowerCase();
        const machines = [];
        
        for (const [machine_name, recipes_dict] of Object.entries(get_all_recipes_by_machine())) {
            const recipe_nodes = [];
            
            for (const [recipe_name, recipe] of Object.entries(recipes_dict)) {
                // determine visibility based on search
                const is_visible = this._recipe_matches_search(recipe_name, recipe, search_text);
                
                const recipe_node = new RecipeTreeNode(
                    FactoryController._make_recipe_id(machine_name, recipe_name),
                    recipe_name,
                    this.enabled_recipes.has(recipe_name),
                    is_visible
                );
                recipe_nodes.push(recipe_node);
            }
            
            // calculate machine state from visible recipes
            const visible_recipes = recipe_nodes.filter(r => r.is_visible);
            let check_state;
            let is_visible;
            if (visible_recipes.length === 0) {
                check_state = 'unchecked';
                is_visible = false;
            } else {
                const enabled_count = visible_recipes.filter(r => r.is_enabled).length;
                if (enabled_count === 0) {
                    check_state = 'unchecked';
                } else if (enabled_count === visible_recipes.length) {
                    check_state = 'checked';
                } else {
                    check_state = 'tristate';
                }
                is_visible = true;
            }
            
            const machine_node = new MachineTreeNode(
                FactoryController._make_machine_id(machine_name),
                machine_name,
                recipe_nodes,
                check_state,
                is_visible
            );
            machines.push(machine_node);
        }
        
        return new RecipeTreeStructure(machines);
    }
    
    /**
     * Handle recipe toggle event.
     * 
     * Precondition:
     *     recipe_tree_id is a string (may be in recipe format)
     *     is_checked is a boolean
     * 
     * Postcondition:
     *     if recipe_tree_id is valid recipe format, recipe enablement is updated
     *     if recipe_tree_id is not valid recipe format, no action taken
     * 
     * @param {string} recipe_tree_id - tree ID in format "recipe:{machine}:{recipe}"
     * @param {boolean} is_checked - new checked state
     */
    on_recipe_toggled(recipe_tree_id, is_checked) {
        const parsed = FactoryController._parse_recipe_id(recipe_tree_id);
        if (parsed) {
            const recipe_name = parsed[1];
            this.set_recipe_enabled(recipe_name, is_checked);
        }
    }
    
    /**
     * Get tooltip text for a tree ID.
     * 
     * Precondition:
     *     tree_id is a string
     * 
     * Postcondition:
     *     if tree_id is valid recipe format, returns formatted tooltip
     *     otherwise returns null
     * 
     * @param {string} tree_id - tree ID (machine or recipe format)
     * @returns {string|null} tooltip text or null
     */
    get_tooltip_for_tree_id(tree_id) {
        const parsed = FactoryController._parse_recipe_id(tree_id);
        if (parsed) {
            const recipe_name = parsed[1];
            return this.get_recipe_tooltip(recipe_name);
        }
        return null;
    }
    
    // ========== Actions ==========
    
    /**
     * Generate factory using current controller state.
     * 
     * Precondition:
     *     this._outputs_text, _inputs_text, _mines_text are initialized
     *     this.enabled_recipes is initialized
     *     this.economy is initialized
     *     optimization weights are set
     * 
     * Postcondition:
     *     this._current_factory is updated with generated Factory
     *     info messages are logged
     *     returns Graphviz diagram string
     * 
     * @returns {Object} graphviz diagram suitable for display
     * @throws {Error} if configuration is invalid or generation fails
     */
    async generate_factory_from_state() {
        console.log("Generating factory...");

        // parse configuration from text state
        const outputs_list = FactoryController.parse_config_text(this._outputs_text);
        const inputs_list = FactoryController.parse_config_text(this._inputs_text);
        
        // build config from current state
        const config = new FactoryConfig(
            Object.fromEntries(outputs_list),
            inputs_list,
            [],  // TODO: Parse mines if needed
            this.enabled_recipes,
            this._input_costs_weight,
            this._machine_counts_weight,
            this._power_consumption_weight,
            this._design_power
        );
        
        // generate and cache result (design_factory is async)
        const factory = await this.generate_factory(config);
        this._current_factory = factory;
        
        console.log("Factory generated successfully");
        
        // return graphviz diagram for display
        return factory.network.source;
    }
    
    /**
     * Get graphviz source for copying to clipboard.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     if factory exists with network, returns graphviz source
     *     if no factory, returns null
     *     info message is logged
     * 
     * @returns {string|null} graphviz source or null if no factory available
     */
    copy_graphviz_source() {
        const source = this.get_graphviz_source();
        if (source === null) {
            console.log("No graph to export");
            return null;
        }
        
        console.log("Graphviz source copied to clipboard");
        return source;
    }
    
    // ========== Static Helper Methods ==========
    
    /**
     * Get default set of enabled recipes.
     * 
     * Precondition:
     *     none
     * 
     * Postcondition:
     *     returns set of recipe names
     *     excludes power generation recipes (MWm in outputs)
     *     excludes Packager recipes
     * 
     * @returns {Set<string>} set of enabled recipe names
     */
    static _get_default_enabled_recipes() {
        const enabled = new Set();
        for (const [machine_name, recipes] of Object.entries(get_all_recipes_by_machine())) {
            for (const [recipe_name, recipe] of Object.entries(recipes)) {
                if (!("MWm" in recipe.outputs) && machine_name !== "Packager") {
                    enabled.add(recipe_name);
                }
            }
        }
        return enabled;
    }
    
    /**
     * Parse configuration text into list of [material, rate] tuples.
     * 
     * Precondition:
     *     text is a string (may be multi-line)
     * 
     * Postcondition:
     *     returns list of [material, rate] tuples
     *     comments (lines starting with #) are ignored
     *     empty lines are ignored
     * 
     * Format: Material:Rate, one per line
     * Lines starting with # are comments and ignored
     * Empty lines are ignored
     * 
     * @param {string} text - multi-line configuration text
     * @returns {Array<[string, number]>} list of [material, rate] tuples
     * @throws {Error} if parsing fails for any line
     */
    static parse_config_text(text) {
        const items = [];
        for (const line of text.trim().split("\n")) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith("#")) {
                continue;
            }
            const [material, rate] = parse_material_rate(trimmed);
            items.push([material, rate]);
        }
        return items;
    }
    
    /**
     * Format recipe inputs/outputs for display.
     * 
     * Precondition:
     *     recipe is a Recipe object with inputs and outputs dicts
     * 
     * Postcondition:
     *     returns formatted multi-line string
     *     inputs section lists all input materials and rates
     *     outputs section lists all output materials and rates
     *     sections are separated by blank line
     * 
     * @param {Recipe} recipe - Recipe to format
     * @returns {string} formatted string with inputs and outputs
     */
    static format_recipe_tooltip(recipe) {
        const lines = [];
        
        if (Object.keys(recipe.inputs).length > 0) {
            lines.push("Inputs:");
            for (const [material, rate] of Object.entries(recipe.inputs)) {
                // ensure rate is displayed with at least one decimal place
                const rate_str = Number.isInteger(rate) ? rate.toFixed(1) : String(rate);
                lines.push(`  - ${material}: ${rate_str}/min`);
            }
        }
        
        if (Object.keys(recipe.outputs).length > 0) {
            if (lines.length > 0) {
                lines.push("");
            }
            lines.push("Outputs:");
            for (const [material, rate] of Object.entries(recipe.outputs)) {
                // ensure rate is displayed with at least one decimal place
                const rate_str = Number.isInteger(rate) ? rate.toFixed(1) : String(rate);
                lines.push(`  - ${material}: ${rate_str}/min`);
            }
        }
        
        return lines.join("\n");
    }
    
    /**
     * Validate factory configuration.
     * 
     * Precondition:
     *     config is a FactoryConfig object
     * 
     * Postcondition:
     *     returns ValidationResult with is_valid, warnings, errors
     *     checks for empty outputs (error)
     *     checks for power design without power recipes (warning)
     * 
     * @param {FactoryConfig} config - factory configuration to validate
     * @returns {ValidationResult} ValidationResult with any warnings or errors
     */
    validate_config(config) {
        const warnings = [];
        const errors = [];
        
        // check for empty outputs
        if (Object.keys(config.outputs).length === 0) {
            errors.push("No outputs specified");
        }
        
        // check for power design without power recipes
        if (config.design_power) {
            const power_recipes = get_recipes_for("MWm", config.enabled_recipes);
            if (Object.keys(power_recipes).length === 0) {
                warnings.push("Power design enabled but no power-generating recipes are enabled");
            }
        }
        
        return new ValidationResult(
            errors.length === 0,
            warnings,
            errors
        );
    }
    
    /**
     * Generate factory from configuration.
     * 
     * Precondition:
     *     config is a FactoryConfig object
     *     this.economy is initialized
     * 
     * Postcondition:
     *     configuration is validated before generation
     *     returns Factory object with network design
     * 
     * @param {FactoryConfig} config - factory configuration
     * @returns {Factory} generated Factory object
     * @throws {Error} if configuration is invalid or generation fails
     */
    async generate_factory(config) {
        // validate first
        const validation = this.validate_config(config);
        if (!validation.is_valid) {
            throw new Error(validation.errors.join("; "));
        }
        
        // generate factory (design_factory is async)
        return await design_factory(
            config.outputs,
            config.inputs,
            config.mines,
            config.enabled_recipes,
            this.economy,
            config.input_costs_weight,
            config.machine_counts_weight,
            config.power_consumption_weight,
            config.design_power
        );
    }
}

export { FactoryConfig, ValidationResult, RecipeTreeNode, MachineTreeNode, RecipeTreeStructure, FactoryController };

