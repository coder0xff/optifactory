import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
    EconomyItem,
    EconomyTableStructure,
    EconomyController
} from '../economy-controller.js';
import {
    get_default_economy,
    compute_item_values,
    economy_to_csv,
    economy_from_csv
} from '../economy.js';

describe('EconomyController', () => {
    it('init should create controller with default economy', () => {
        const controller = new EconomyController();
        
        assert.ok(controller instanceof EconomyController);
        assert.ok(typeof controller.economy === 'object');
        assert.ok(Object.keys(controller.economy).length > 0);
        assert.ok(controller.pinned_items instanceof Set);
        assert.strictEqual(controller.pinned_items.size, 0);
        assert.strictEqual(controller.get_filter_text(), "");
    });

    it('controller should manage filter text state', () => {
        const controller = new EconomyController();
        assert.strictEqual(controller.get_filter_text(), "");
        
        controller.set_filter_text("iron");
        assert.strictEqual(controller.get_filter_text(), "iron");
    });

    it('controller should track sort state', () => {
        const controller = new EconomyController();
        
        const [sort_col, sort_asc] = controller.get_sort_state();
        assert.strictEqual(sort_col, 'item');
        assert.ok(sort_asc);
    });

    it('set_sort should set new column and default to ascending', () => {
        const controller = new EconomyController();
        
        controller.set_sort('value');
        const [sort_col, sort_asc] = controller.get_sort_state();
        
        assert.strictEqual(sort_col, 'value');
        assert.ok(sort_asc);
    });

    it('set_sort on same column should toggle direction', () => {
        const controller = new EconomyController();
        
        controller.set_sort('value');
        const [sort_col1, sort_asc1] = controller.get_sort_state();
        
        controller.set_sort('value');  // Same column again
        const [sort_col2, sort_asc2] = controller.get_sort_state();
        
        assert.strictEqual(sort_col1, 'value');
        assert.strictEqual(sort_col2, 'value');
        assert.ok(sort_asc1);
        assert.ok(!sort_asc2);
    });

    it('get_header_texts should return header display texts with sort indicators', () => {
        const controller = new EconomyController();
        
        // Default state (sorted by item ascending)
        let texts = controller.get_header_texts();
        assert.strictEqual(texts['item'], 'Item ▲');
        assert.strictEqual(texts['value'], 'Value');
        assert.strictEqual(texts['locked'], 'Locked');
        
        // Click item again to reverse sort
        controller.set_sort('item');
        texts = controller.get_header_texts();
        assert.strictEqual(texts['item'], 'Item ▼');
        assert.strictEqual(texts['value'], 'Value');
        assert.strictEqual(texts['locked'], 'Locked');
        
        // Sort by value descending
        controller.set_sort('value');
        controller.set_sort('value');  // second click reverses
        texts = controller.get_header_texts();
        assert.strictEqual(texts['item'], 'Item');
        assert.strictEqual(texts['value'], 'Value ▼');
        assert.strictEqual(texts['locked'], 'Locked');
        
        // Sort by locked ascending
        controller.set_sort('locked');
        texts = controller.get_header_texts();
        assert.strictEqual(texts['item'], 'Item');
        assert.strictEqual(texts['value'], 'Value');
        assert.strictEqual(texts['locked'], 'Locked ▲');
    });

    it('set_item_value should update economy', () => {
        const controller = new EconomyController();
        controller.economy = {"Iron Ore": 1.0};
        
        controller.set_item_value("Iron Ore", 5.0);
        
        assert.strictEqual(controller.economy["Iron Ore"], 5.0);
    });

    it('set_item_value should handle nonexistent items gracefully', () => {
        const controller = new EconomyController();
        
        // Should not raise or add item
        controller.set_item_value("Nonexistent", 10.0);
        assert.ok(!("Nonexistent" in controller.economy));
    });

    it('set_item_pinned should update pinned state', () => {
        const controller = new EconomyController();
        
        controller.set_item_pinned("Iron Ore", true);
        assert.ok(controller.pinned_items.has("Iron Ore"));
        
        controller.set_item_pinned("Iron Ore", false);
        assert.ok(!controller.pinned_items.has("Iron Ore"));
    });

    it('_make_item_id should generate stable IDs', () => {
        const id1 = EconomyController._make_item_id("Iron Ore");
        const id2 = EconomyController._make_item_id("Iron Ore");
        
        assert.strictEqual(id1, id2);
        assert.strictEqual(id1, "item:Iron Ore");
    });

    it('get_economy_table_structure should return complete structure', () => {
        const controller = new EconomyController();
        controller.economy = {"Iron Ore": 1.0, "Copper Ore": 2.0, "Coal": 0.5};
        controller.pinned_items = new Set(["Iron Ore"]);
        
        const structure = controller.get_economy_table_structure();
        
        assert.strictEqual(structure.items.length, 3);
        assert.ok(structure.items.every(item => item.item_id.startsWith("item:")));
    });

    it('table structure should filter items', () => {
        const controller = new EconomyController();
        controller.economy = {"Iron Ore": 1.0, "Copper Ore": 2.0, "Coal": 0.5};
        
        controller.set_filter_text("ore");
        const structure = controller.get_economy_table_structure();
        
        assert.strictEqual(structure.items.length, 2);
        assert.ok(structure.items.every(item => item.display_name.toLowerCase().includes("ore")));
    });

    it('table filtering should be case-insensitive', () => {
        const controller = new EconomyController();
        controller.economy = {"Iron Ore": 1.0};
        
        controller.set_filter_text("IRON");
        const structure = controller.get_economy_table_structure();
        
        assert.strictEqual(structure.items.length, 1);
    });

    it('table should sort by item name', () => {
        const controller = new EconomyController();
        controller.economy = {"Zinc": 1.0, "Aluminum": 2.0, "Copper": 3.0};
        
        // Default is already sorted by item ascending
        let structure = controller.get_economy_table_structure();
        let names = structure.items.map(item => item.display_name);
        assert.strictEqual(names[0], "Aluminum");
        assert.strictEqual(names[1], "Copper");
        assert.strictEqual(names[2], "Zinc");
        
        // Toggle to descending
        controller.set_sort('item');
        structure = controller.get_economy_table_structure();
        names = structure.items.map(item => item.display_name);
        assert.strictEqual(names[0], "Zinc");
        assert.strictEqual(names[1], "Copper");
        assert.strictEqual(names[2], "Aluminum");
    });

    it('table should sort by value', () => {
        const controller = new EconomyController();
        controller.economy = {"A": 3.0, "B": 1.0, "C": 2.0};
        
        controller.set_sort('value');
        const structure = controller.get_economy_table_structure();
        
        const values = structure.items.map(item => item.value);
        assert.strictEqual(values[0], 1.0);
        assert.strictEqual(values[1], 2.0);
        assert.strictEqual(values[2], 3.0);
    });

    it('table should sort by pinned state', () => {
        const controller = new EconomyController();
        controller.economy = {"A": 1.0, "B": 2.0, "C": 3.0};
        controller.pinned_items = new Set(["B"]);
        
        controller.set_sort('locked');
        const structure = controller.get_economy_table_structure();
        
        // Pinned items should come first (or last depending on direction)
        const pinned_states = structure.items.map(item => item.is_pinned);
        const has_correct_grouping = 
            (pinned_states[0] === false && pinned_states[1] === false && pinned_states[2] === true) ||
            (pinned_states[0] === true && pinned_states[1] === false && pinned_states[2] === false);
        assert.ok(has_correct_grouping);
    });

    it('table should default to item name sort', () => {
        const controller = new EconomyController();
        controller.economy = {"Zinc": 1.0, "Aluminum": 2.0};
        
        const structure = controller.get_economy_table_structure();
        
        const names = structure.items.map(item => item.display_name);
        assert.strictEqual(names[0], "Aluminum");
        assert.strictEqual(names[1], "Zinc");
    });

    it('table items should include all metadata', () => {
        const controller = new EconomyController();
        controller.economy = {"Iron Ore": 5.0};
        controller.pinned_items = new Set(["Iron Ore"]);
        
        const structure = controller.get_economy_table_structure();
        
        const item = structure.items[0];
        assert.strictEqual(item.item_id, "item:Iron Ore");
        assert.strictEqual(item.display_name, "Iron Ore");
        assert.strictEqual(item.value, 5.0);
        assert.ok(item.is_pinned);
        assert.ok(item.is_visible);
    });

    it('reset_to_default should restore default economy', () => {
        const controller = new EconomyController();
        controller.economy = {"Custom": 999.0};
        controller.pinned_items = new Set(["Custom"]);
        
        controller.reset_to_default();
        
        // Should have default items
        assert.ok(Object.keys(controller.economy).length > 1);
        assert.ok(!("Custom" in controller.economy));
        const has_default_item = "Iron Ore" in controller.economy || "Copper Ore" in controller.economy;
        assert.ok(has_default_item);
        assert.strictEqual(controller.pinned_items.size, 0);
    });

    it('recompute_values should recalculate with pinned values', () => {
        const controller = new EconomyController();
        const original_iron_ore = controller.economy["Iron Ore"] || 0;
        controller.pinned_items = new Set(["Iron Ore"]);
        
        controller.recompute_values();
        
        // Pinned value should remain the same
        assert.strictEqual(controller.economy["Iron Ore"], original_iron_ore);
        // Other values may change (gradient descent)
        assert.ok("Iron Plate" in controller.economy);
    });

    it('load_from_csv should load economy from CSV string', () => {
        const controller = new EconomyController();
        
        // Create CSV string
        const test_economy = {"Iron Ore": 1.0, "Copper Ore": 2.0};
        const test_pinned = new Set(["Iron Ore"]);
        const csv_string = economy_to_csv(test_economy, test_pinned);
        
        // Load into controller
        controller.load_from_csv(csv_string);
        
        assert.strictEqual(Object.keys(controller.economy).length, 2);
        assert.strictEqual(controller.economy["Iron Ore"], 1.0);
        assert.strictEqual(controller.economy["Copper Ore"], 2.0);
        assert.ok(controller.pinned_items.has("Iron Ore"));
        assert.strictEqual(controller.pinned_items.size, 1);
    });

    it('save_to_csv should save economy to CSV string', () => {
        const controller = new EconomyController();
        controller.economy = {"Iron Ore": 1.0, "Copper Ore": 2.0};
        controller.pinned_items = new Set(["Iron Ore"]);
        
        const csv_string = controller.save_to_csv();
        
        // Verify CSV string was created
        assert.ok(typeof csv_string === 'string');
        assert.ok(csv_string.length > 0);
        
        // Load it back to verify
        const [loaded_economy, loaded_pinned] = economy_from_csv(csv_string);
        
        assert.strictEqual(loaded_economy["Iron Ore"], controller.economy["Iron Ore"]);
        assert.strictEqual(loaded_economy["Copper Ore"], controller.economy["Copper Ore"]);
        assert.ok(loaded_pinned.has("Iron Ore"));
        assert.strictEqual(loaded_pinned.size, controller.pinned_items.size);
    });

    it('filter and sort should work together', () => {
        const controller = new EconomyController();
        controller.economy = {"Iron Ore": 3.0, "Iron Plate": 1.0, "Copper Ore": 2.0};
        
        controller.set_filter_text("iron");
        controller.set_sort('value');
        
        const structure = controller.get_economy_table_structure();
        
        assert.strictEqual(structure.items.length, 2);
        assert.strictEqual(structure.items[0].display_name, "Iron Plate");
        assert.strictEqual(structure.items[1].display_name, "Iron Ore");
    });

    // ====================================================================
    // Serialization / Deserialization Tests
    // ====================================================================

    describe('Serialization', () => {
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

    describe('Deserialization', () => {
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
        it('should preserve state through serialize/deserialize cycle', () => {
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

        it('should handle empty economy', () => {
            const controller = new EconomyController();
            controller.economy = {};
            
            const csv = controller.save_to_csv();
            
            // Should have header only
            const lines = csv.split('\n').filter(line => line.trim());
            assert.strictEqual(lines.length, 1);
            assert.strictEqual(lines[0], 'Item,Value,Pinned');
        });
    });
});
