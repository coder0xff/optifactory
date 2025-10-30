import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { Recipe } from '../recipes.js';
import { 
    tarjan, 
    separate_economies, 
    compute_item_values,
    get_default_economies, 
    get_default_economy, 
    cost_of_recipes, 
    economy_to_csv, 
    economy_from_csv 
} from '../economy.js';
import { get_all_recipes } from '../recipes.js';

describe('Economy', () => {
    // Test Tarjan's strongly connected components algorithm
    it('Tarjan: single node', () => {
        const graph = { 'A': [] };
        const sccs = tarjan(graph);
        assert.strictEqual(sccs.length, 1);
        assert.ok(sccs[0].has('A'));
    });
    
    it('Tarjan: two disconnected nodes', () => {
        const graph = { 'A': [], 'B': [] };
        const sccs = tarjan(graph);
        assert.strictEqual(sccs.length, 2);
    });
    
    it('Tarjan: simple cycle', () => {
        const graph = { 'A': ['B'], 'B': ['C'], 'C': ['A'] };
        const sccs = tarjan(graph);
        assert.strictEqual(sccs.length, 1);
        assert.ok(sccs[0].has('A') && sccs[0].has('B') && sccs[0].has('C'));
    });
    
    it('Tarjan: complex graph', () => {
        const graph = {
            'A': ['B'],
            'B': ['C'],
            'C': ['A'],
            'D': ['E'],
            'E': ['F'],
            'F': ['D']
        };
        const sccs = tarjan(graph);
        assert.strictEqual(sccs.length, 2);
    });
    
    // Test simple economy with a few recipes
    it('Simple economy computation', () => {
        const simpleRecipes = {
            'IronOre': new Recipe('IronOre', {}, { 'Iron Ore': 30 }),
            'IronIngot': new Recipe('IronIngot', { 'Iron Ore': 30 }, { 'Iron Ingot': 30 }),
            'IronPlate': new Recipe('IronPlate', { 'Iron Ingot': 30 }, { 'Iron Plate': 20 })
        };
        const economy = compute_item_values(simpleRecipes);
        assert.ok(economy['Iron Ore'] != null);
        assert.ok(economy['Iron Ingot'] != null);
        assert.ok(economy['Iron Plate'] != null);
        // Iron Ingot should be at least as valuable as ore (equal due to 1:1 ratio)
        assert.ok(economy['Iron Ingot'] >= economy['Iron Ore']);
        // Iron Plate should be more valuable (30 ingots -> 20 plates)
        assert.ok(economy['Iron Plate'] > economy['Iron Ingot']);
    });
    
    // Test economy with pinned values
    it('Economy with pinned values', () => {
        const simpleRecipes = {
            'IronOre': new Recipe('IronOre', {}, { 'Iron Ore': 30 }),
            'IronIngot': new Recipe('IronIngot', { 'Iron Ore': 30 }, { 'Iron Ingot': 30 }),
            'IronPlate': new Recipe('IronPlate', { 'Iron Ingot': 30 }, { 'Iron Plate': 20 })
        };
        
        // First compute without pinning
        const unpinnedEconomy = compute_item_values(simpleRecipes);
        
        // Then compute with pinning Iron Ore to 1.0 (minimum)
        const pinnedValues = { 'Iron Ore': 1.0 };
        const economy = compute_item_values(simpleRecipes, pinnedValues);
        
        // Verify the pinned value is maintained
        assert.strictEqual(economy['Iron Ore'], 1.0);
        
        // All values should still be positive
        for (const value of Object.values(economy)) {
            assert.ok(value > 0);
        }
        
        // The relative ordering should be maintained
        assert.ok(economy['Iron Plate'] > economy['Iron Ingot']);
    });
    
    // Test separate economies
    it('Separate economies detection', () => {
        const multiEconomyRecipes = {
            'IronOre': new Recipe('IronOre', {}, { 'Iron Ore': 30 }),
            'IronIngot': new Recipe('IronIngot', { 'Iron Ore': 30 }, { 'Iron Ingot': 30 }),
            'CopperOre': new Recipe('CopperOre', {}, { 'Copper Ore': 30 }),
            'CopperIngot': new Recipe('CopperIngot', { 'Copper Ore': 30 }, { 'Copper Ingot': 30 })
        };
        const economies = separate_economies(multiEconomyRecipes);
        assert.strictEqual(economies.length, 2);
    });
    
    // Test CSV export/import
    it('CSV export and import', () => {
        const economy = { 'Iron Ore': 1.0, 'Iron Ingot': 1.5 };
        const pinnedItems = new Set(['Iron Ore']);
        const csvString = economy_to_csv(economy, pinnedItems);
        assert.ok(csvString.includes('Item,Value,Pinned'));
        assert.ok(csvString.includes('Iron Ore,1,true'));
        assert.ok(csvString.includes('Iron Ingot,1.5,false'));
        
        const [parsedEconomy, parsedPinned] = economy_from_csv(csvString);
        assert.strictEqual(parsedEconomy['Iron Ore'], 1.0);
        assert.strictEqual(parsedEconomy['Iron Ingot'], 1.5);
        assert.ok(parsedPinned.has('Iron Ore'));
        assert.ok(!parsedPinned.has('Iron Ingot'));
    });
    
    // Test cost_of_recipes
    it('Recipe cost calculation', () => {
        // Use real game recipes
        const allRecipes = get_all_recipes();
        const economy = get_default_economy();
        
        // Pick a simple recipe we know exists (Iron Ingot from Iron Ore)
        // The recipe should have a positive cost
        const recipeSelection = { 'Iron Ingot': 1 };
        const cost = cost_of_recipes(recipeSelection, economy);
        
        assert.ok(cost > 0);
        assert.ok(typeof cost === 'number');
        assert.ok(isFinite(cost));
    });
    
    // Test with actual game data (smaller subset for performance)
    it('Real game data computation', () => {
        // This will use get_all_recipes() from recipes.js
        const economy = get_default_economy();
        assert.ok(economy != null);
        assert.ok(Object.keys(economy).length > 10);
        
        // Check some basic constraints
        for (const [item, value] of Object.entries(economy)) {
            assert.ok(value > 0, `${item} has positive value`);
        }
    });
    
    // Test from test_economy.py: test_get_default_economy
    it('get_default_economy returns positive values', () => {
        const economy = get_default_economy();
        assert.ok(Object.keys(economy).length > 0);
        for (const value of Object.values(economy)) {
            assert.ok(typeof value === 'number');
            assert.ok(value > 0);
        }
    });
    
    // Test from test_economy.py: test_get_default_economies
    it('get_default_economies returns separate economies', () => {
        const economies = get_default_economies();
        assert.ok(economies.length > 0);
        for (const economy of economies) {
            assert.ok(Object.keys(economy).length > 0);
            for (const value of Object.values(economy)) {
                assert.ok(typeof value === 'number');
                assert.ok(value > 0);
            }
        }
        const totalItems = economies.reduce((sum, e) => sum + Object.keys(e).length, 0);
    });
    
    // Test from test_economy.py: test_compute_item_values_with_pinning
    it('compute_item_values with pinning', () => {
        const defaultEconomy = get_default_economy();
        
        const pinnedValues = {
            'Iron Ore': 1.0,
            'Copper Ore': 2.0
        };
        
        const economy = compute_item_values(null, pinnedValues);
        
        assert.strictEqual(Object.keys(economy).length, Object.keys(defaultEconomy).length);
        
        for (const [name, value] of Object.entries(pinnedValues)) {
            assert.strictEqual(economy[name], value, `${name} is pinned to ${value}`);
        }
        
        for (const value of Object.values(economy)) {
            assert.ok(value > 0);
        }
    });
    
    // Test CSV format details
    it('CSV format validation', () => {
        const economy = { 'Iron Ore': 1.0, 'Copper Ore': 2.5 };
        const pinnedItems = new Set(['Iron Ore']);
        
        const csv = economy_to_csv(economy, pinnedItems);
        const lines = csv.split('\n');
        
        assert.ok(lines[0].includes('Item'));
        assert.ok(lines[0].includes('Value'));
        assert.ok(lines[0].includes('Pinned'));
        assert.ok(lines.length > 2);
    });
});
