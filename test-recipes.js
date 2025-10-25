import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
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
} from './recipes.js';

describe('Recipes', () => {
    it('get_conveyor_rate(0) returns 60', () => {
        assert.strictEqual(get_conveyor_rate(0), 60);
    });
    
    it('get_conveyor_rate(3) returns 480', () => {
        assert.strictEqual(get_conveyor_rate(3), 480);
    });
    
    it('get_mining_rate(0, Purity.IMPURE) returns 30', () => {
        assert.strictEqual(get_mining_rate(0, Purity.IMPURE), 30);
    });
    
    it('get_mining_rate(2, Purity.PURE) returns 480', () => {
        assert.strictEqual(get_mining_rate(2, Purity.PURE), 480);
    });
    
    it('get_water_extraction_rate() returns 120', () => {
        assert.strictEqual(get_water_extraction_rate(), 120);
    });
    
    it('get_oil_extraction_rate(Purity.NORMAL) returns 120', () => {
        assert.strictEqual(get_oil_extraction_rate(Purity.NORMAL), 120);
    });
    
    it('get_load("Constructor") returns 4', () => {
        assert.strictEqual(get_load("Constructor"), 4);
    });
    
    it('get_all_recipes() returns object with recipes', () => {
        const recipes = get_all_recipes();
        assert.ok(recipes != null);
        assert.ok(Object.keys(recipes).length > 50);
    });
    
    it('get_all_recipes_by_machine() groups recipes by machine', () => {
        const by_machine = get_all_recipes_by_machine();
        assert.ok(by_machine != null);
        assert.ok(by_machine['Smelter'] != null);
        assert.ok(by_machine['Constructor'] != null);
    });
    
    it('get_base_parts() includes raw materials', () => {
        const base_parts = get_base_parts();
        if (!base_parts.has('Iron Ore')) throw new Error('Missing Iron Ore');
        if (!base_parts.has('Copper Ore')) throw new Error('Missing Copper Ore');
        if (!base_parts.has('Water')) throw new Error('Missing Water');
    });
    
    it('get_terminal_parts() includes end products', () => {
        const terminal_parts = get_terminal_parts();
        assert.ok(terminal_parts.size > 0);
    });
    
    it('get_default_enablement_set() returns recipe names', () => {
        const enabled = get_default_enablement_set();
        assert.ok(enabled.size > 50);
    });
    
    it('get_recipes_for("Iron Plate") returns recipes', () => {
        const recipes = get_recipes_for("Iron Plate");
        assert.ok(recipes != null);
        const amounts = Object.keys(recipes);
        assert.ok(amounts.length > 0);
    });
    
    it('get_recipe_for("Iron Ingot") returns highest rate recipe', () => {
        const [amount, name, recipe] = get_recipe_for("Iron Ingot");
        assert.ok(amount != null);
        assert.ok(name != null);
        assert.ok(recipe != null);
    });
    
    it('Recipe object has correct structure', () => {
        const [amount, name, recipe] = get_recipe_for("Iron Ingot");
        assert.ok(recipe.machine != null);
        assert.ok(recipe.inputs != null);
        assert.ok(recipe.outputs != null);
    });
    
    it('get_fluids() returns fluid list', () => {
        const fluids = get_fluids();
        assert.ok(fluids.length > 5);
        if (!fluids.includes('Water')) throw new Error('Missing Water in fluids');
        if (!fluids.includes('Crude Oil')) throw new Error('Missing Crude Oil in fluids');
    });
    
    it('get_fluid_color("Water") returns hex color', () => {
        const color = get_fluid_color("Water");
        if (!color.startsWith('#')) throw new Error('Color does not start with #');
    });
    
    it('Purity enum has correct values', () => {
        assert.strictEqual(Purity.IMPURE, 0);
        assert.strictEqual(Purity.NORMAL, 1);
        assert.strictEqual(Purity.PURE, 2);
    });

    // ====================================================================
    // Tests ported from test_recipes.py
    // ====================================================================

    it('test_get_conveyor_rate: conveyor rate lookup should return valid rates', () => {
        // Conveyor marks are 0-indexed: 0=Mk1, 1=Mk2, etc.
        const rate_mk1 = get_conveyor_rate(0);
        assert.strictEqual(rate_mk1, 60.0);
        
        const rate_mk2 = get_conveyor_rate(1);
        assert.strictEqual(rate_mk2, 120.0);
        
        const rate_mk3 = get_conveyor_rate(2);
        assert.strictEqual(rate_mk3, 270.0);
        
        const rate_mk4 = get_conveyor_rate(3);
        assert.strictEqual(rate_mk4, 480.0);
    });

    it('test_get_water_extraction_rate: water extraction rate should be valid', () => {
        const rate = get_water_extraction_rate();
        assert.ok(rate > 0);
        if (typeof rate !== 'number') throw new Error('Rate is not a number');
    });

    it('test_get_oil_extraction_rate: oil extraction rates should vary by purity', () => {
        const impure_rate = get_oil_extraction_rate(Purity.IMPURE);
        const normal_rate = get_oil_extraction_rate(Purity.NORMAL);
        const pure_rate = get_oil_extraction_rate(Purity.PURE);
        
        assert.ok(impure_rate > 0);
        assert.ok(normal_rate > impure_rate);
        assert.ok(pure_rate > normal_rate);
    });

    it('test_get_load: machine load lookup should return valid power values', () => {
        // Test some known machines
        const smelter_load = get_load("Smelter");
        assert.ok(smelter_load > 0);
        
        const constructor_load = get_load("Constructor");
        assert.ok(constructor_load > 0);
    });

    it('test_get_recipe_for: should return the highest rate recipe', () => {
        const [amount, recipe_name, recipe] = get_recipe_for("Iron Plate");
        
        assert.ok(amount > 0);
        if (typeof recipe_name !== 'string') throw new Error('Recipe name is not a string');
        if (!(recipe instanceof Recipe)) throw new Error('Recipe is not a Recipe instance');
        if (!("Iron Ore" in recipe.inputs || "Iron Ingot" in recipe.inputs)) {
            throw new Error('Recipe should have Iron Ore or Iron Ingot as input');
        }
        if (!("Iron Plate" in recipe.outputs)) throw new Error('Recipe should output Iron Plate');
    });

    it('test_get_recipe_for_with_enablement: should respect enablement set', () => {
        // Get all recipes for Iron Plate
        const all_recipes = get_recipes_for("Iron Plate");
        
        // Pick a specific recipe to enable
        let sample_recipe_name = null;
        for (const [amount, recipes_list] of Object.entries(all_recipes)) {
            if (recipes_list.length > 0) {
                sample_recipe_name = recipes_list[0][0];
                break;
            }
        }
        
        if (!sample_recipe_name) throw new Error('No recipes found for Iron Plate');
        
        // Get recipe with limited enablement set
        const [amount, recipe_name, recipe] = get_recipe_for("Iron Plate", new Set([sample_recipe_name]));
        assert.strictEqual(recipe_name, sample_recipe_name);
    });

    it('test_find_recipe_name: should locate recipe by its Recipe object', () => {
        // find_recipe_name requires Recipe objects created from the internal lookups
        const all_recipes = get_all_recipes();
        
        // Get a recipe from all_recipes
        let recipe_name, recipe;
        if ("Iron Plate" in all_recipes) {
            recipe_name = "Iron Plate";
            recipe = all_recipes["Iron Plate"];
        } else {
            // Fallback: just pick any recipe
            recipe_name = Object.keys(all_recipes)[0];
            recipe = all_recipes[recipe_name];
        }
        
        const found_name = find_recipe_name(recipe);
        assert.strictEqual(found_name, recipe_name);
    });

    it('test_get_terminal_parts: terminal parts should be products with no consumers', () => {
        const terminal_parts = get_terminal_parts();
        
        assert.ok(terminal_parts.size > 0);
        if (!(terminal_parts instanceof Set)) throw new Error('Terminal parts is not a Set');
    });

    it('test_get_base_parts: base parts should be raw materials', () => {
        const base_parts = get_base_parts();
        
        assert.ok(base_parts.size > 0);
        if (!(base_parts instanceof Set)) throw new Error('Base parts is not a Set');
        
        // Should include raw ores
        if (!base_parts.has("Iron Ore")) throw new Error('Missing Iron Ore');
        if (!base_parts.has("Copper Ore")) throw new Error('Missing Copper Ore');
    });

    it('test_recipe_lookups_consistency: recipe lookups should be internally consistent', () => {
        // Get all recipes
        const all_recipes = get_all_recipes();
        assert.ok(Object.keys(all_recipes).length > 0);
        
        // Check that recipes_for works for some outputs
        const iron_plate_recipes = get_recipes_for("Iron Plate");
        assert.ok(Object.keys(iron_plate_recipes).length > 0);
        
        // Check that get_recipe_for returns valid data
        const [amount, recipe_name, recipe] = get_recipe_for("Iron Plate");
        assert.ok(amount > 0);
        if (typeof recipe_name !== 'string') throw new Error('Recipe name is not a string');
        if (!(recipe instanceof Recipe)) throw new Error('Recipe is not a Recipe instance');
    });

    it('test_power_recipes: power recipes should produce MWm', () => {
        // Get all recipes that produce MWm (power)
        const power_recipes = get_recipes_for("MWm");
        assert.ok(Object.keys(power_recipes).length > 0);
        
        // Get the best recipe for MWm
        const [amount, recipe_name, recipe] = get_recipe_for("MWm");
        assert.ok(recipe != null);
        assert.ok(amount > 0);
        
        // Verify the recipe outputs MWm
        if (!("MWm" in recipe.outputs)) {
            throw new Error('Power recipe should output MWm');
        }
        assert.ok(recipe.outputs.MWm > 0);
        
        // Verify it's from a known power generator
        const powerMachines = ['Biomass Burner', 'Coal-Powered Generator', 'Fuel-Powered Generator'];
        if (!powerMachines.includes(recipe.machine)) {
            throw new Error(`Expected power generator, got: ${recipe.machine}`);
        }
        
        // Count total power recipes
        let totalPowerRecipes = 0;
        for (const recipes_list of Object.values(power_recipes)) {
            totalPowerRecipes += recipes_list.length;
        }
    });
});
