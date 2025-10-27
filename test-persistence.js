import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { FactoryController } from './factory-controller.js';
import { EconomyController } from './economy-controller.js';

describe('State Persistence', () => {
    describe('FactoryController Serialization', () => {
        it('should serialize complete state to JSON string', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);
            
            factoryController.set_outputs_text('Concrete:480');
            factoryController.set_inputs_text('Limestone:240');
            factoryController.set_input_costs_weight(0.7);
            factoryController.set_machine_counts_weight(0.3);
            factoryController.set_power_consumption_weight(0.5);
            factoryController.set_design_power(true);
            factoryController.set_disable_balancers(false);
            
            const serialized = factoryController.serialize_state();
            
            assert.strictEqual(typeof serialized, 'string');
            
            const parsed = JSON.parse(serialized);
            assert.strictEqual(parsed.version, 1);
            assert.strictEqual(parsed.outputs_text, 'Concrete:480');
            assert.strictEqual(parsed.inputs_text, 'Limestone:240');
            assert.strictEqual(parsed.input_costs_weight, 0.7);
            assert.strictEqual(parsed.machine_counts_weight, 0.3);
            assert.strictEqual(parsed.power_consumption_weight, 0.5);
            assert.strictEqual(parsed.design_power, true);
            assert.strictEqual(parsed.disable_balancers, false);
            assert.ok(Array.isArray(parsed.enabled_recipes));
            assert.ok(parsed.enabled_recipes.length > 0);
        });

        it('should include enabled recipes in serialized state', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);
            
            // Enable specific recipes
            factoryController.set_recipes_enabled(new Set(['Steel Ingot', 'Steel Beam']));
            
            const serialized = factoryController.serialize_state();
            const parsed = JSON.parse(serialized);
            
            assert.ok(parsed.enabled_recipes.includes('Steel Ingot'));
            assert.ok(parsed.enabled_recipes.includes('Steel Beam'));
            assert.strictEqual(parsed.enabled_recipes.length, 2);
        });

        it('should include graphviz source when available', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);
            
            // Set cached graphviz source
            factoryController._cached_graphviz_source = 'digraph G { A -> B; }';
            
            const serialized = factoryController.serialize_state();
            const parsed = JSON.parse(serialized);
            
            assert.strictEqual(parsed.graphviz_source, 'digraph G { A -> B; }');
        });
    });

    describe('FactoryController Deserialization', () => {
        it('should deserialize complete state from JSON string', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);
            
            const testState = {
                version: 1,
                outputs_text: 'Steel Beam:45',
                inputs_text: 'Iron Ore:90',
                enabled_recipes: ['Steel Ingot', 'Steel Beam'],
                input_costs_weight: 0.8,
                machine_counts_weight: 0.2,
                power_consumption_weight: 0.5,
                design_power: false,
                disable_balancers: true,
                graphviz_source: 'digraph G { A -> B; }'
            };
            
            factoryController.deserialize_state(JSON.stringify(testState));
            
            assert.strictEqual(factoryController.get_outputs_text(), 'Steel Beam:45');
            assert.strictEqual(factoryController.get_inputs_text(), 'Iron Ore:90');
            assert.strictEqual(factoryController.get_input_costs_weight(), 0.8);
            assert.strictEqual(factoryController.get_machine_counts_weight(), 0.2);
            assert.strictEqual(factoryController.get_power_consumption_weight(), 0.5);
            assert.strictEqual(factoryController.get_design_power(), false);
            assert.strictEqual(factoryController.get_disable_balancers(), true);
            assert.strictEqual(factoryController.get_graphviz_source(), 'digraph G { A -> B; }');
        });

        it('should restore enabled recipes from state', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);
            
            const testState = {
                version: 1,
                outputs_text: 'Iron Plate:100',
                inputs_text: '',
                enabled_recipes: ['Iron Plate', 'Iron Rod'],
                input_costs_weight: 1.0,
                machine_counts_weight: 0.0,
                power_consumption_weight: 1.0,
                design_power: false,
                disable_balancers: false,
                graphviz_source: null
            };
            
            factoryController.deserialize_state(JSON.stringify(testState));
            
            const enabledRecipes = factoryController.get_enabled_recipes();
            assert.ok(enabledRecipes.has('Iron Plate'));
            assert.ok(enabledRecipes.has('Iron Rod'));
            assert.strictEqual(enabledRecipes.size, 2);
        });

        it('should throw error for invalid JSON', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);
            
            assert.throws(
                () => factoryController.deserialize_state('not valid json'),
                /Invalid JSON/
            );
        });

        it('should throw error for unsupported version', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);
            
            const testState = {
                version: 999,
                outputs_text: 'Iron Plate:100',
                inputs_text: ''
            };
            
            assert.throws(
                () => factoryController.deserialize_state(JSON.stringify(testState)),
                /Unsupported state version/
            );
        });

        it('should clear current factory on deserialization', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);
            
            // Set a fake current factory
            factoryController._current_factory = { network: { source: 'test' } };
            
            const testState = {
                version: 1,
                outputs_text: 'Iron Plate:100',
                inputs_text: '',
                enabled_recipes: ['Iron Plate'],
                input_costs_weight: 1.0,
                machine_counts_weight: 0.0,
                power_consumption_weight: 1.0,
                design_power: false,
                disable_balancers: false,
                graphviz_source: null
            };
            
            factoryController.deserialize_state(JSON.stringify(testState));
            
            assert.strictEqual(factoryController._current_factory, null);
        });
    });

    describe('EconomyController Serialization', () => {
        it('should serialize to CSV string', () => {
            const controller = new EconomyController();
            
            controller.economy = { 'Iron Ore': 1.0, 'Copper Ore': 2.0 };
            controller.set_item_pinned('Iron Ore', true);
            controller.set_filter_text('Iron');
            
            const csv = controller.save_to_csv();
            
            assert.strictEqual(typeof csv, 'string');
            assert.ok(csv.includes('Iron Ore'));
            assert.ok(csv.includes('Copper Ore'));
            assert.ok(csv.includes('true'));
            assert.ok(csv.includes('false'));
        });

        it('should include pinned status in CSV', () => {
            const controller = new EconomyController();
            
            controller.economy = { 'A': 1.0, 'B': 2.0, 'C': 3.0 };
            controller.set_item_pinned('A', true);
            controller.set_item_pinned('C', true);
            
            const csv = controller.save_to_csv();
            const lines = csv.split('\n');
            
            // Should have header + 3 items (CSV doesn't have trailing newline)
            assert.strictEqual(lines.length, 4);  // header + 3 items
            
            // Check that pinned items are marked
            const aLine = lines.find(line => line.startsWith('A,'));
            const bLine = lines.find(line => line.startsWith('B,'));
            const cLine = lines.find(line => line.startsWith('C,'));
            
            assert.ok(aLine?.endsWith('true'));
            assert.ok(bLine?.endsWith('false'));
            assert.ok(cLine?.endsWith('true'));
        });
    });

    describe('EconomyController Deserialization', () => {
        it('should deserialize from CSV string', () => {
            const controller = new EconomyController();
            
            const testCsv = 'Item,Value,Pinned\nIron Ore,15,true\nCopper Ore,10,false';
            controller.load_from_csv(testCsv);
            
            assert.strictEqual(controller.economy['Iron Ore'], 15);
            assert.strictEqual(controller.economy['Copper Ore'], 10);
            assert.ok(controller.pinned_items.has('Iron Ore'));
            assert.ok(!controller.pinned_items.has('Copper Ore'));
        });

        it('should handle pinned items correctly', () => {
            const controller = new EconomyController();
            
            const testCsv = 'Item,Value,Pinned\nA,1,true\nB,2,true\nC,3,false';
            controller.load_from_csv(testCsv);
            
            assert.strictEqual(controller.pinned_items.size, 2);
            assert.ok(controller.pinned_items.has('A'));
            assert.ok(controller.pinned_items.has('B'));
            assert.ok(!controller.pinned_items.has('C'));
        });
    });

    describe('Round-trip Persistence', () => {
        it('should preserve factory controller state through serialize/deserialize cycle', () => {
            const economyController1 = new EconomyController();
            const factoryController1 = new FactoryController(economyController1.economy);
            
            // Configure state
            factoryController1.set_outputs_text('Modular Frame:2');
            factoryController1.set_inputs_text('Iron Ingot:100\nCopper Ingot:50');
            factoryController1.set_input_costs_weight(0.6);
            factoryController1.set_machine_counts_weight(0.4);
            factoryController1.set_design_power(true);
            factoryController1.set_recipes_enabled(new Set(['Modular Frame', 'Reinforced Iron Plate']));
            
            // Serialize
            const serialized = factoryController1.serialize_state();
            
            // Deserialize into new controller
            const economyController2 = new EconomyController();
            const factoryController2 = new FactoryController(economyController2.economy);
            factoryController2.deserialize_state(serialized);
            
            // Verify all state matches
            assert.strictEqual(
                factoryController2.get_outputs_text(),
                factoryController1.get_outputs_text()
            );
            assert.strictEqual(
                factoryController2.get_inputs_text(),
                factoryController1.get_inputs_text()
            );
            assert.strictEqual(
                factoryController2.get_input_costs_weight(),
                factoryController1.get_input_costs_weight()
            );
            assert.strictEqual(
                factoryController2.get_machine_counts_weight(),
                factoryController1.get_machine_counts_weight()
            );
            assert.strictEqual(
                factoryController2.get_design_power(),
                factoryController1.get_design_power()
            );
            
            const recipes1 = factoryController1.get_enabled_recipes();
            const recipes2 = factoryController2.get_enabled_recipes();
            assert.strictEqual(recipes2.size, recipes1.size);
            for (const recipe of recipes1) {
                assert.ok(recipes2.has(recipe));
            }
        });

        it('should preserve economy controller state through serialize/deserialize cycle', () => {
            const controller1 = new EconomyController();
            
            // Configure state
            controller1.economy = { 
                'Iron Ore': 5.0, 
                'Copper Ore': 10.0,
                'Concrete': 2.0
            };
            controller1.set_item_pinned('Iron Ore', true);
            controller1.set_item_pinned('Concrete', true);
            controller1.set_filter_text('Ore');
            controller1.set_sort('value');
            
            // Serialize
            const csv = controller1.save_to_csv();
            
            // Deserialize into new controller
            const controller2 = new EconomyController();
            controller2.load_from_csv(csv);
            
            // Verify economy values match
            assert.strictEqual(controller2.economy['Iron Ore'], 5.0);
            assert.strictEqual(controller2.economy['Copper Ore'], 10.0);
            assert.strictEqual(controller2.economy['Concrete'], 2.0);
            
            // Verify pinned items match
            assert.ok(controller2.pinned_items.has('Iron Ore'));
            assert.ok(controller2.pinned_items.has('Concrete'));
            assert.ok(!controller2.pinned_items.has('Copper Ore'));
            assert.strictEqual(controller2.pinned_items.size, 2);
        });

        it('should handle complete application state cycle', () => {
            // Simulate full application state save/restore
            const economyController1 = new EconomyController();
            const factoryController1 = new FactoryController(economyController1.economy);
            
            // Configure both controllers
            factoryController1.set_outputs_text('Computer:5');
            factoryController1.set_input_costs_weight(0.75);
            economyController1.set_item_value('Iron Ore', 20);
            economyController1.set_item_pinned('Iron Ore', true);
            
            // Create application state
            const appState = {
                version: 1,
                activeTab: 'economy',
                factoryState: factoryController1.serialize_state(),
                economyState: economyController1.save_to_csv()
            };
            
            // Restore into new controllers
            const economyController2 = new EconomyController();
            const factoryController2 = new FactoryController(economyController2.economy);
            
            economyController2.load_from_csv(appState.economyState);
            factoryController2.deserialize_state(appState.factoryState);
            factoryController2.economy = economyController2.economy;
            
            // Verify factory state
            assert.strictEqual(
                factoryController2.get_outputs_text(),
                'Computer:5'
            );
            assert.strictEqual(
                factoryController2.get_input_costs_weight(),
                0.75
            );
            
            // Verify economy state
            assert.strictEqual(economyController2.economy['Iron Ore'], 20);
            assert.ok(economyController2.pinned_items.has('Iron Ore'));
            
            // Verify active tab
            assert.strictEqual(appState.activeTab, 'economy');
        });
    });

    describe('Edge Cases', () => {
        it('should handle empty enabled recipes set', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);
            
            factoryController.set_recipes_enabled(new Set());
            
            const serialized = factoryController.serialize_state();
            const parsed = JSON.parse(serialized);
            
            assert.strictEqual(parsed.enabled_recipes.length, 0);
            
            // Deserialize back
            const factoryController2 = new FactoryController(economyController.economy);
            factoryController2.deserialize_state(serialized);
            
            assert.strictEqual(factoryController2.get_enabled_recipes().size, 0);
        });

        it('should handle null graphviz source', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);
            
            const serialized = factoryController.serialize_state();
            const parsed = JSON.parse(serialized);
            
            assert.strictEqual(parsed.graphviz_source, null);
        });

        it('should handle empty economy', () => {
            const controller = new EconomyController();
            controller.economy = {};
            
            const csv = controller.save_to_csv();
            
            // Should have header only
            const lines = csv.split('\n').filter(line => line.trim());
            assert.strictEqual(lines.length, 1);
            assert.strictEqual(lines[0], 'Item,Value,Pinned');
        });

        it('should handle default recipe search text', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);
            
            assert.strictEqual(factoryController.get_recipe_search_text(), '');
            
            const serialized = factoryController.serialize_state();
            const factoryController2 = new FactoryController(economyController.economy);
            factoryController2.deserialize_state(serialized);
            
            // Recipe search text is not persisted currently, but shouldn't cause errors
            assert.strictEqual(factoryController2.get_recipe_search_text(), '');
        });
    });
});

