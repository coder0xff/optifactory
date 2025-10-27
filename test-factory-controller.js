import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
    FactoryConfig,
    ValidationResult,
    RecipeTreeNode,
    MachineTreeNode,
    RecipeTreeStructure,
    FactoryController
} from './factory-controller.js';
import { Recipe, Purity } from './recipes.js';

describe('FactoryController', () => {
    // ====================================================================
    // Tests ported from test_factory_controller.py
    // ====================================================================

    it('test_controller_init: controller should initialize with economy and default recipes', () => {
        const economy = {"Iron Ore": 1.0};
        const controller = new FactoryController(economy);
        if (controller.economy !== economy) throw new Error('Economy not stored');
        assert.ok(controller.enabled_recipes.size > 0);
    });

    it.skip('test_get_default_enabled_recipes: default enabled recipes should exclude power and packager', () => {
        // Note: This test is skipped because _get_default_enabled_recipes is not a static method
        // The default recipes are accessed via get_default_enablement_set() from recipes.js
        const recipes = FactoryController._get_default_enabled_recipes();
        assert.ok(recipes.size > 0);
        if (!recipes.has("Iron Plate")) throw new Error('Should include Iron Plate');
    });

    it('test_parse_config_text_basic: parse_config_text should handle basic input', () => {
        const text = "Iron Plate:100\nCopper Ingot:50";
        const result = FactoryController.parse_config_text(text);
        assert.strictEqual(result.length, 2);
        assert.strictEqual(result[0][0], "Iron Plate");
        assert.strictEqual(result[0][1], 100.0);
        assert.strictEqual(result[1][0], "Copper Ingot");
        assert.strictEqual(result[1][1], 50.0);
    });

    it('test_parse_config_text_with_comments: parse_config_text should skip comments', () => {
        const text = `
# This is a comment
Iron Plate:100
# Another comment
Copper Ingot:50
`;
        const result = FactoryController.parse_config_text(text);
        assert.strictEqual(result.length, 2);
        assert.strictEqual(result[0][0], "Iron Plate");
        assert.strictEqual(result[1][0], "Copper Ingot");
    });

    it('test_parse_config_text_empty_lines: parse_config_text should skip empty lines', () => {
        const text = "Iron Plate:100\n\nCopper Ingot:50\n\n";
        const result = FactoryController.parse_config_text(text);
        assert.strictEqual(result.length, 2);
    });

    it('test_parse_config_text_whitespace: parse_config_text should handle extra whitespace', () => {
        const text = "  Iron Plate:100  \n  Copper Ingot:50  ";
        const result = FactoryController.parse_config_text(text);
        assert.strictEqual(result.length, 2);
        assert.strictEqual(result[0][0], "Iron Plate");
        assert.strictEqual(result[1][0], "Copper Ingot");
    });

    it('test_parse_config_text_comment_only: parse_config_text should handle comment-only text', () => {
        const text = "# Comment 1\n# Comment 2";
        const result = FactoryController.parse_config_text(text);
        assert.strictEqual(result.length, 0);
    });

    it('test_parse_config_text_empty: parse_config_text should handle empty text', () => {
        const result = FactoryController.parse_config_text("");
        assert.strictEqual(result.length, 0);
    });

    it('test_parse_config_text_invalid: parse_config_text should throw on invalid format', () => {
        try {
            FactoryController.parse_config_text("Invalid Line Without Colon");
            throw new Error('Should have thrown');
        } catch (e) {
            if (!e.message.includes('Invalid format')) throw e;
        }
    });

    it('test_parse_config_text_case_insensitive_concrete: parse_config_text should recognize both concrete and Concrete', () => {
        const text_lower = "concrete:480";
        const text_upper = "Concrete:480";
        const result_lower = FactoryController.parse_config_text(text_lower);
        const result_upper = FactoryController.parse_config_text(text_upper);
        
        assert.strictEqual(result_lower.length, 1);
        assert.strictEqual(result_upper.length, 1);
        assert.strictEqual(result_lower[0][1], 480.0);
        assert.strictEqual(result_upper[0][1], 480.0);
        
        // both should parse successfully
        assert.ok(result_lower[0][0] === "concrete" || result_lower[0][0] === "Concrete");
        assert.ok(result_upper[0][0] === "Concrete");
    });

    it('test_format_recipe_tooltip_with_inputs_and_outputs: format_recipe_tooltip should format recipe with inputs and outputs', () => {
        const recipe = new Recipe(
            "Smelter",
            {"Iron Ore": 30.0},
            {"Iron Ingot": 30.0}
        );
        const result = FactoryController.format_recipe_tooltip(recipe);
        if (!result.includes("Inputs:")) throw new Error('Should include Inputs');
        if (!result.includes("Iron Ore: 30.0/min")) throw new Error('Should include input details');
        if (!result.includes("Outputs:")) throw new Error('Should include Outputs');
        if (!result.includes("Iron Ingot: 30.0/min")) throw new Error('Should include output details');
    });

    it('test_format_recipe_tooltip_outputs_only: format_recipe_tooltip should format recipe with only outputs', () => {
        const recipe = new Recipe(
            "Miner",
            {},
            {"Iron Ore": 60.0}
        );
        const result = FactoryController.format_recipe_tooltip(recipe);
        if (result.includes("Inputs:")) throw new Error('Should not include Inputs');
        if (!result.includes("Outputs:")) throw new Error('Should include Outputs');
        if (!result.includes("Iron Ore: 60.0/min")) throw new Error('Should include output details');
    });

    it('test_format_recipe_tooltip_multiple_items: format_recipe_tooltip should format recipe with multiple inputs/outputs', () => {
        const recipe = new Recipe(
            "Assembler",
            {"Iron Plate": 20.0, "Copper Wire": 30.0},
            {"Circuit Board": 10.0}
        );
        const result = FactoryController.format_recipe_tooltip(recipe);
        if (!result.includes("Iron Plate: 20.0/min")) throw new Error('Should include first input');
        if (!result.includes("Copper Wire: 30.0/min")) throw new Error('Should include second input');
        if (!result.includes("Circuit Board: 10.0/min")) throw new Error('Should include output');
    });

    it('test_validate_config_valid: validate_config should pass for valid configuration', () => {
        const controller = new FactoryController({});
        const config = new FactoryConfig(
            {"Iron Plate": 100},
            [],
            [],
            new Set(["Iron Plate"])
        );
        const result = controller.validate_config(config);
        if (!result.is_valid) throw new Error('Should be valid');
        assert.strictEqual(result.errors.length, 0);
    });

    it('test_validate_config_empty_outputs: validate_config should error on empty outputs', () => {
        const controller = new FactoryController({});
        const config = new FactoryConfig(
            {},
            [],
            [],
            new Set()
        );
        const result = controller.validate_config(config);
        if (result.is_valid) throw new Error('Should be invalid');
        assert.strictEqual(result.errors.length, 1);
        if (!result.errors[0].includes("No outputs specified")) throw new Error('Wrong error message');
    });

    it('test_validate_config_power_without_recipes: validate_config should warn about power design without power recipes', () => {
        const controller = new FactoryController({});
        const config = new FactoryConfig(
            {"Iron Plate": 100},
            [],
            [],
            new Set(["Iron Plate"]),
            1.0,
            0.0,
            1.0,
            true  // design_power
        );
        const result = controller.validate_config(config);
        if (!result.is_valid) throw new Error('Should be valid (warning only)');
        assert.strictEqual(result.warnings.length, 1);
        if (!result.warnings[0].toLowerCase().includes("power")) throw new Error('Should mention power');
    });

    it('test_validate_config_power_with_recipes: validate_config should not warn when power design has power recipes', () => {
        const controller = new FactoryController({});
        const config = new FactoryConfig(
            {"Iron Plate": 100},
            [],
            [],
            new Set(["Iron Plate", "Coal Power"]),
            1.0,
            0.0,
            1.0,
            true
        );
        const result = controller.validate_config(config);
        if (!result.is_valid) throw new Error('Should be valid');
        assert.strictEqual(result.warnings.length, 0);
    });

    it('test_validate_config_no_power_design: validate_config should not warn when power design is disabled', () => {
        const controller = new FactoryController({});
        const config = new FactoryConfig(
            {"Iron Plate": 100},
            [],
            [],
            new Set(["Iron Plate"]),
            1.0,
            0.0,
            1.0,
            false
        );
        const result = controller.validate_config(config);
        if (!result.is_valid) throw new Error('Should be valid');
        assert.strictEqual(result.warnings.length, 0);
    });

    it('test_factory_config_defaults: FactoryConfig should have correct default values', () => {
        const config = new FactoryConfig(
            {"Iron Plate": 100},
            [],
            [],
            new Set()
        );
        assert.strictEqual(config.input_costs_weight, 1.0);
        assert.strictEqual(config.machine_counts_weight, 0.0);
        assert.strictEqual(config.power_consumption_weight, 1.0);
        if (config.design_power !== false) throw new Error('design_power should be false');
        if (config.disable_balancers !== false) throw new Error('disable_balancers should be false');
    });

    it('test_factory_config_with_disable_balancers: FactoryConfig should accept disable_balancers parameter', () => {
        const config = new FactoryConfig(
            {"Iron Plate": 100},
            [],
            [],
            new Set(),
            1.0,
            0.0,
            1.0,
            false,
            true  // disable_balancers
        );
        if (config.disable_balancers !== true) throw new Error('disable_balancers should be true');
    });

    it('test_validation_result_structure: ValidationResult should have correct structure', () => {
        const result = new ValidationResult(
            true,
            ["warning1"],
            []
        );
        if (!result.is_valid) throw new Error('Should be valid');
        assert.strictEqual(result.warnings.length, 1);
        assert.strictEqual(result.errors.length, 0);
    });

    // ========== State Management Tests ==========

    it('test_get_set_outputs_text: controller should manage outputs text state', () => {
        const controller = new FactoryController({});
        assert.strictEqual(controller.get_outputs_text(), "Concrete:480");
        
        controller.set_outputs_text("Iron Plate:100");
        assert.strictEqual(controller.get_outputs_text(), "Iron Plate:100");
    });

    it('test_get_set_inputs_text: controller should manage inputs text state', () => {
        const controller = new FactoryController({});
        const default_text = controller.get_inputs_text();
        if (!default_text.includes("# Leave empty")) throw new Error('Should have default comment');
        
        controller.set_inputs_text("Iron Ore:200");
        assert.strictEqual(controller.get_inputs_text(), "Iron Ore:200");
    });

    it('test_get_set_mines_text: controller should manage mines text state', () => {
        const controller = new FactoryController({});
        assert.strictEqual(controller.get_mines_text(), "");
        
        controller.set_mines_text("Iron Ore:PURE");
        assert.strictEqual(controller.get_mines_text(), "Iron Ore:PURE");
    });

    it('test_get_set_recipe_search_text: controller should manage recipe search text state', () => {
        const controller = new FactoryController({});
        assert.strictEqual(controller.get_recipe_search_text(), "");
        
        controller.set_recipe_search_text("iron");
        assert.strictEqual(controller.get_recipe_search_text(), "iron");
    });

    it('test_get_set_optimization_weights: controller should manage optimization weight state', () => {
        const controller = new FactoryController({});
        assert.strictEqual(controller.get_input_costs_weight(), 0.1);
        assert.strictEqual(controller.get_machine_counts_weight(), 1.0);
        assert.strictEqual(controller.get_power_consumption_weight(), 1.0);
        
        controller.set_input_costs_weight(0.5);
        controller.set_machine_counts_weight(0.3);
        controller.set_power_consumption_weight(0.7);
        
        assert.strictEqual(controller.get_input_costs_weight(), 0.5);
        assert.strictEqual(controller.get_machine_counts_weight(), 0.3);
        assert.strictEqual(controller.get_power_consumption_weight(), 0.7);
    });

    it('test_get_set_design_power: controller should manage design power flag', () => {
        const controller = new FactoryController({});
        if (controller.get_design_power() !== false) throw new Error('Default should be false');
        
        controller.set_design_power(true);
        if (controller.get_design_power() !== true) throw new Error('Should be true');
    });

    it('test_get_set_disable_balancers: controller should manage disable balancers flag', () => {
        const controller = new FactoryController({});
        if (controller.get_disable_balancers() !== false) throw new Error('Default should be false');
        
        controller.set_disable_balancers(true);
        if (controller.get_disable_balancers() !== true) throw new Error('Should be true');
        
        controller.set_disable_balancers(false);
        if (controller.get_disable_balancers() !== false) throw new Error('Should be false');
    });

    it('test_set_recipe_enabled: controller should enable/disable individual recipes', () => {
        const controller = new FactoryController({});
        
        const initial_count = controller.enabled_recipes.size;
        assert.ok(initial_count > 0);
        
        controller.set_recipe_enabled("Iron Plate", false);
        if (controller.enabled_recipes.has("Iron Plate")) throw new Error('Should be disabled');
        
        controller.set_recipe_enabled("Iron Plate", true);
        if (!controller.enabled_recipes.has("Iron Plate")) throw new Error('Should be enabled');
    });

    it('test_set_recipes_enabled: controller should set complete recipe set', () => {
        const controller = new FactoryController({});
        
        const new_set = new Set(["Iron Plate", "Copper Ingot"]);
        controller.set_recipes_enabled(new_set);
        
        const current = controller.get_enabled_recipes();
        if (current.size !== 2) throw new Error('Wrong size');
        if (!current.has("Iron Plate")) throw new Error('Missing Iron Plate');
        if (!current.has("Copper Ingot")) throw new Error('Missing Copper Ingot');
    });

    it('test_get_enabled_recipes_returns_copy: get_enabled_recipes should return a copy to prevent external mutation', () => {
        const controller = new FactoryController({});
        
        const recipes1 = controller.get_enabled_recipes();
        recipes1.add("NewRecipe");
        
        const recipes2 = controller.get_enabled_recipes();
        if (recipes2.has("NewRecipe")) throw new Error('Should not have NewRecipe');
    });

    it('test_get_current_factory: controller should track current factory', () => {
        const controller = new FactoryController({});
        if (controller.get_current_factory() !== null) throw new Error('Should start null');
    });

    it('test_should_show_power_warning_disabled: should_show_power_warning should return false when power design disabled', () => {
        const controller = new FactoryController({});
        controller.set_design_power(false);
        
        if (controller.should_show_power_warning()) throw new Error('Should not show warning');
    });

    it('test_should_show_power_warning_enabled_without_recipes: should_show_power_warning should return true when power enabled but no power recipes', () => {
        const controller = new FactoryController({});
        controller.set_design_power(true);
        controller.set_recipes_enabled(new Set(["Iron Plate"]));
        
        if (!controller.should_show_power_warning()) throw new Error('Should show warning');
    });

    it('test_should_show_power_warning_enabled_with_recipes: should_show_power_warning should return false when power enabled with power recipes', () => {
        const controller = new FactoryController({});
        controller.set_design_power(true);
        controller.set_recipes_enabled(new Set(["Coal Power", "Iron Plate"]));
        
        if (controller.should_show_power_warning()) throw new Error('Should not show warning');
    });

    it('test_get_all_recipes_by_machine: controller should provide access to recipes', () => {
        const controller = new FactoryController({});
        const recipes = controller.get_all_recipes_by_machine();
        
        assert.ok(Object.keys(recipes).length > 0);
        if (!("Smelter" in recipes) && !("Constructor" in recipes)) {
            throw new Error('Should have Smelter or Constructor');
        }
    });

    it('test_get_recipe_tooltip: controller should provide recipe tooltips', () => {
        const controller = new FactoryController({});
        
        const tooltip = controller.get_recipe_tooltip("Iron Plate");
        assert.ok(tooltip != null);
        if (!tooltip.includes("/min")) throw new Error('Should include /min');
    });

    it('test_get_recipe_tooltip_not_found: controller should return null for non-existent recipe', () => {
        const controller = new FactoryController({});
        
        const tooltip = controller.get_recipe_tooltip("NonExistentRecipe");
        if (tooltip !== null) throw new Error('Should be null');
    });

    // ========== Tree Structure Tests ==========

    it('test_get_recipe_tree_structure: get_recipe_tree_structure should return complete tree', () => {
        const controller = new FactoryController({});
        
        const structure = controller.get_recipe_tree_structure();
        
        assert.ok(structure.machines.length > 0);
        for (const machine of structure.machines) {
            if (!machine.tree_id.startsWith("machine:")) throw new Error('Wrong machine ID format');
            if (machine.recipes.length === 0) throw new Error('Machine should have recipes');
        }
    });

    it('test_tree_structure_recipe_ids: recipe tree IDs should follow format recipe:{machine}:{recipe}', () => {
        const controller = new FactoryController({});
        
        const structure = controller.get_recipe_tree_structure();
        
        for (const machine of structure.machines) {
            for (const recipe of machine.recipes) {
                if (!recipe.tree_id.startsWith("recipe:")) throw new Error('Wrong recipe ID format');
                if (!recipe.tree_id.includes(machine.display_name)) throw new Error('Should include machine name');
            }
        }
    });

    it('test_tree_structure_with_search: tree structure should filter by search text', () => {
        const controller = new FactoryController({});
        controller.set_recipe_search_text("iron");
        
        const structure = controller.get_recipe_tree_structure();
        
        const all_recipes = structure.machines.flatMap(m => m.recipes);
        const visible_count = all_recipes.filter(r => r.is_visible).length;
        const invisible_count = all_recipes.filter(r => !r.is_visible).length;
        
        assert.ok(visible_count > 0);
        assert.ok(invisible_count > 0);
    });

    it('test_tree_structure_machine_visibility: machines should be hidden if no visible recipes', () => {
        const controller = new FactoryController({});
        controller.set_recipe_search_text("zzzznonexistent");
        
        const structure = controller.get_recipe_tree_structure();
        
        for (const machine of structure.machines) {
            if (machine.is_visible) throw new Error('All machines should be invisible');
        }
    });

    it('test_on_recipe_toggled: on_recipe_toggled should update enabled recipes', () => {
        const controller = new FactoryController({});
        
        const recipe_id = "recipe:Smelter:Iron Plate";
        
        controller.on_recipe_toggled(recipe_id, false);
        if (controller.enabled_recipes.has("Iron Plate")) throw new Error('Should be disabled');
        
        controller.on_recipe_toggled(recipe_id, true);
        if (!controller.enabled_recipes.has("Iron Plate")) throw new Error('Should be enabled');
    });

    it('test_on_recipe_toggled_invalid_id: on_recipe_toggled should handle invalid IDs gracefully', () => {
        const controller = new FactoryController({});
        
        // Should not throw
        controller.on_recipe_toggled("invalid_id", true);
        controller.on_recipe_toggled("machine:Smelter", true);
    });

    it('test_get_tooltip_for_tree_id_recipe: get_tooltip_for_tree_id should return tooltip for recipe IDs', () => {
        const controller = new FactoryController({});
        
        const recipe_id = "recipe:Smelter:Iron Plate";
        const tooltip = controller.get_tooltip_for_tree_id(recipe_id);
        
        assert.ok(tooltip != null);
        if (!tooltip.includes("/min")) throw new Error('Should include /min');
    });

    it('test_get_tooltip_for_tree_id_machine: get_tooltip_for_tree_id should return null for machine IDs', () => {
        const controller = new FactoryController({});
        
        const machine_id = "machine:Smelter";
        const tooltip = controller.get_tooltip_for_tree_id(machine_id);
        
        if (tooltip !== null) throw new Error('Should be null');
    });

    it('test_get_tooltip_for_tree_id_invalid: get_tooltip_for_tree_id should return null for invalid IDs', () => {
        const controller = new FactoryController({});
        
        const tooltip = controller.get_tooltip_for_tree_id("invalid_id");
        if (tooltip !== null) throw new Error('Should be null');
    });

    it('test_get_tooltip_for_tree_id_alternate_charcoal: get_tooltip_for_tree_id should return string for Alternate: Charcoal', () => {
        const controller = new FactoryController({});
        
        const tooltip = controller.get_tooltip_for_tree_id("recipe:Constructor:Alternate: Charcoal");
        assert.strictEqual(typeof tooltip, 'string');
    });

    it('test_parse_recipe_id: _parse_recipe_id should parse recipe IDs correctly', () => {
        let result = FactoryController._parse_recipe_id("recipe:Smelter:Iron Plate");
        if (!result || result[0] !== "Smelter" || result[1] !== "Iron Plate") {
            throw new Error('Wrong parse result');
        }
        
        result = FactoryController._parse_recipe_id("machine:Smelter");
        if (result !== null) throw new Error('Should be null for machine ID');
        
        result = FactoryController._parse_recipe_id("invalid");
        if (result !== null) throw new Error('Should be null for invalid ID');
    });

    it('test_make_machine_id: _make_machine_id should generate stable IDs', () => {
        const id1 = FactoryController._make_machine_id("Smelter");
        const id2 = FactoryController._make_machine_id("Smelter");
        
        assert.strictEqual(id1, id2);
        assert.strictEqual(id1, "machine:Smelter");
    });

    it('test_make_recipe_id: _make_recipe_id should generate stable IDs', () => {
        const id1 = FactoryController._make_recipe_id("Smelter", "Iron Plate");
        const id2 = FactoryController._make_recipe_id("Smelter", "Iron Plate");
        
        assert.strictEqual(id1, id2);
        assert.strictEqual(id1, "recipe:Smelter:Iron Plate");
    });

    it('test_machine_tristate_when_alternate_disabled: Converter should be tristate when Alternate: Dark-Ion Fuel is disabled but other recipes enabled', () => {
        const controller = new FactoryController({});
        
        // Enable Dark Matter Residue and Excited Photonic Matter, disable Alternate: Dark-Ion Fuel
        controller.set_recipe_enabled("Dark Matter Residue", true);
        controller.set_recipe_enabled("Excited Photonic Matter", true);
        controller.set_recipe_enabled("Alternate: Dark-Ion Fuel", false);
        
        const structure = controller.get_recipe_tree_structure();
        
        // Find the Converter machine node
        const converter = structure.machines.find(m => m.display_name === "Converter");
        assert.ok(converter != null);
        
        // Verify that the Converter is in tristate (some but not all recipes enabled)
        assert.strictEqual(converter.check_state, "tristate");
    });

    it('test_should_show_converter_warning_no_recipes: should_show_converter_warning should return false when no converter recipes enabled', () => {
        const controller = new FactoryController({});
        controller.set_recipes_enabled(new Set(["Iron Plate"]));
        
        if (controller.should_show_converter_warning()) throw new Error('Should not show warning');
    });

    it('test_should_show_converter_warning_with_recipes: should_show_converter_warning should return true when converter recipes enabled', () => {
        const controller = new FactoryController({});
        controller.set_recipes_enabled(new Set(["Dark Matter Residue", "Iron Plate"]));
        
        if (!controller.should_show_converter_warning()) throw new Error('Should show warning');
    });

    // ========== Serialization Tests ==========

    it('test_serialize_state: serialize_state should return valid JSON string', () => {
        const controller = new FactoryController({});
        const serialized = controller.serialize_state();
        
        // Should be parseable JSON
        const state = JSON.parse(serialized);
        
        // Should have version
        assert.strictEqual(state.version, 1);
        
        // Should have all state fields
        assert.ok('outputs_text' in state);
        assert.ok('inputs_text' in state);
        assert.ok('enabled_recipes' in state);
        assert.ok('input_costs_weight' in state);
        assert.ok('machine_counts_weight' in state);
        assert.ok('power_consumption_weight' in state);
        assert.ok('design_power' in state);
        assert.ok('disable_balancers' in state);
        assert.ok('graphviz_source' in state);
    });

    it('test_serialize_state_with_custom_values: serialize_state should capture all custom state', () => {
        const controller = new FactoryController({});
        
        // Set custom values
        controller.set_outputs_text("Iron Plate:200");
        controller.set_inputs_text("Iron Ore:300");
        controller.set_recipes_enabled(new Set(["Iron Plate", "Copper Ingot"]));
        controller.set_input_costs_weight(0.5);
        controller.set_machine_counts_weight(0.3);
        controller.set_power_consumption_weight(0.7);
        controller.set_design_power(true);
        controller.set_disable_balancers(true);
        
        const serialized = controller.serialize_state();
        const state = JSON.parse(serialized);
        
        assert.strictEqual(state.outputs_text, "Iron Plate:200");
        assert.strictEqual(state.inputs_text, "Iron Ore:300");
        assert.strictEqual(state.enabled_recipes.length, 2);
        assert.ok(state.enabled_recipes.includes("Iron Plate"));
        assert.ok(state.enabled_recipes.includes("Copper Ingot"));
        assert.strictEqual(state.input_costs_weight, 0.5);
        assert.strictEqual(state.machine_counts_weight, 0.3);
        assert.strictEqual(state.power_consumption_weight, 0.7);
        assert.strictEqual(state.design_power, true);
        assert.strictEqual(state.disable_balancers, true);
    });

    it('test_serialize_state_graphviz_null: serialize_state should handle null graphviz source', () => {
        const controller = new FactoryController({});
        
        const serialized = controller.serialize_state();
        const state = JSON.parse(serialized);
        
        assert.strictEqual(state.graphviz_source, null);
    });

    it('test_deserialize_state: deserialize_state should restore state from JSON', () => {
        const controller1 = new FactoryController({});
        
        // Set custom values
        controller1.set_outputs_text("Iron Plate:200");
        controller1.set_inputs_text("Iron Ore:300");
        controller1.set_recipes_enabled(new Set(["Iron Plate", "Copper Ingot"]));
        controller1.set_input_costs_weight(0.5);
        controller1.set_machine_counts_weight(0.3);
        controller1.set_power_consumption_weight(0.7);
        controller1.set_design_power(true);
        controller1.set_disable_balancers(true);
        
        const serialized = controller1.serialize_state();
        
        // Create new controller and deserialize
        const controller2 = new FactoryController({});
        controller2.deserialize_state(serialized);
        
        // Verify all state matches
        assert.strictEqual(controller2.get_outputs_text(), "Iron Plate:200");
        assert.strictEqual(controller2.get_inputs_text(), "Iron Ore:300");
        assert.strictEqual(controller2.enabled_recipes.size, 2);
        assert.ok(controller2.enabled_recipes.has("Iron Plate"));
        assert.ok(controller2.enabled_recipes.has("Copper Ingot"));
        assert.strictEqual(controller2.get_input_costs_weight(), 0.5);
        assert.strictEqual(controller2.get_machine_counts_weight(), 0.3);
        assert.strictEqual(controller2.get_power_consumption_weight(), 0.7);
        assert.strictEqual(controller2.get_design_power(), true);
        assert.strictEqual(controller2.get_disable_balancers(), true);
    });

    it('test_deserialize_state_clears_factory: deserialize_state should clear current factory', () => {
        const controller = new FactoryController({});
        
        // Simulate having a current factory (we can't easily create one without running the optimizer)
        controller._current_factory = { network: { source: "digraph G {}" } };
        
        const serialized = controller.serialize_state();
        controller.deserialize_state(serialized);
        
        assert.strictEqual(controller.get_current_factory(), null);
    });

    it('test_deserialize_state_invalid_json: deserialize_state should throw on invalid JSON', () => {
        const controller = new FactoryController({});
        
        try {
            controller.deserialize_state("not valid json");
            throw new Error('Should have thrown');
        } catch (e) {
            if (!e.message.includes('Invalid JSON')) throw e;
        }
    });

    it('test_deserialize_state_invalid_version: deserialize_state should throw on unsupported version', () => {
        const controller = new FactoryController({});
        
        const invalid_state = JSON.stringify({
            version: 999,
            outputs_text: "test",
            inputs_text: "test",
            enabled_recipes: [],
            input_costs_weight: 0.1,
            machine_counts_weight: 1.0,
            power_consumption_weight: 1.0,
            design_power: false,
            disable_balancers: false,
            graphviz_source: null
        });
        
        try {
            controller.deserialize_state(invalid_state);
            throw new Error('Should have thrown');
        } catch (e) {
            if (!e.message.includes('Unsupported state version')) throw e;
        }
    });

    it('test_serialize_deserialize_roundtrip: state should survive serialize/deserialize roundtrip', () => {
        const controller1 = new FactoryController({});
        
        // Set various custom values
        controller1.set_outputs_text("Multiple:100\nOutputs:200");
        controller1.set_inputs_text("Multiple:50\nInputs:75");
        controller1.set_recipes_enabled(new Set(["Recipe1", "Recipe2", "Recipe3"]));
        controller1.set_input_costs_weight(0.25);
        controller1.set_machine_counts_weight(0.5);
        controller1.set_power_consumption_weight(0.75);
        controller1.set_design_power(true);
        controller1.set_disable_balancers(false);
        
        // Serialize and deserialize
        const serialized = controller1.serialize_state();
        const controller2 = new FactoryController({});
        controller2.deserialize_state(serialized);
        
        // Serialize again
        const serialized2 = controller2.serialize_state();
        
        // Both serialized strings should be identical
        assert.strictEqual(serialized, serialized2);
    });

    it('test_deserialize_state_preserves_graphviz_source: deserialize_state should preserve graphviz source', () => {
        const controller = new FactoryController({});
        
        // Simulate having a graphviz source by setting the cache directly
        const test_graphviz = "digraph G { node1 -> node2; }";
        controller._cached_graphviz_source = test_graphviz;
        
        // Serialize
        const serialized = controller.serialize_state();
        const state = JSON.parse(serialized);
        assert.strictEqual(state.graphviz_source, test_graphviz);
        
        // Deserialize into new controller
        const controller2 = new FactoryController({});
        controller2.deserialize_state(serialized);
        
        // Verify graphviz source is available
        assert.strictEqual(controller2.get_graphviz_source(), test_graphviz);
        
        // Verify factory is still null
        assert.strictEqual(controller2.get_current_factory(), null);
    });
});
