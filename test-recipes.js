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
import {
    TestRunner,
    assertEquals,
    assertNotNull,
    assertGreaterThan
} from './test-framework.js';

export async function runTests() {
    const runner = new TestRunner();
    const test = (name, fn) => runner.test(name, fn);

    // Run tests
    test('get_conveyor_rate(0) returns 60', () => {
        return assertEquals(get_conveyor_rate(0), 60, 'Mk.1 conveyor');
    });
    
    test('get_conveyor_rate(3) returns 480', () => {
        return assertEquals(get_conveyor_rate(3), 480, 'Mk.4 conveyor');
    });
    
    test('get_mining_rate(0, Purity.IMPURE) returns 30', () => {
        return assertEquals(get_mining_rate(0, Purity.IMPURE), 30, 'Mk.1 miner on impure node');
    });
    
    test('get_mining_rate(2, Purity.PURE) returns 480', () => {
        return assertEquals(get_mining_rate(2, Purity.PURE), 480, 'Mk.3 miner on pure node');
    });
    
    test('get_water_extraction_rate() returns 120', () => {
        return assertEquals(get_water_extraction_rate(), 120, 'Water extractor rate');
    });
    
    test('get_oil_extraction_rate(Purity.NORMAL) returns 120', () => {
        return assertEquals(get_oil_extraction_rate(Purity.NORMAL), 120, 'Oil extractor on normal node');
    });
    
    test('get_load("Constructor") returns 4', () => {
        return assertEquals(get_load("Constructor"), 4, 'Constructor power consumption');
    });
    
    test('get_all_recipes() returns object with recipes', () => {
        const recipes = get_all_recipes();
        assertNotNull(recipes, 'Recipes object exists');
        assertGreaterThan(Object.keys(recipes).length, 50, 'Has many recipes');
        return 'Recipe count: ' + Object.keys(recipes).length;
    });
    
    test('get_all_recipes_by_machine() groups recipes by machine', () => {
        const by_machine = get_all_recipes_by_machine();
        assertNotNull(by_machine, 'By machine object exists');
        assertNotNull(by_machine['Smelter'], 'Smelter recipes exist');
        assertNotNull(by_machine['Constructor'], 'Constructor recipes exist');
        return 'Machine types: ' + Object.keys(by_machine).length;
    });
    
    test('get_base_parts() includes raw materials', () => {
        const base_parts = get_base_parts();
        if (!base_parts.has('Iron Ore')) throw new Error('Missing Iron Ore');
        if (!base_parts.has('Copper Ore')) throw new Error('Missing Copper Ore');
        if (!base_parts.has('Water')) throw new Error('Missing Water');
        return 'Base parts count: ' + base_parts.size;
    });
    
    test('get_terminal_parts() includes end products', () => {
        const terminal_parts = get_terminal_parts();
        assertGreaterThan(terminal_parts.size, 0, 'Has terminal parts');
        return 'Terminal parts count: ' + terminal_parts.size;
    });
    
    test('get_default_enablement_set() returns recipe names', () => {
        const enabled = get_default_enablement_set();
        assertGreaterThan(enabled.size, 50, 'Has many enabled recipes');
        return 'Default enabled recipes: ' + enabled.size;
    });
    
    test('get_recipes_for("Iron Plate") returns recipes', () => {
        const recipes = get_recipes_for("Iron Plate");
        assertNotNull(recipes, 'Iron Plate recipes exist');
        const amounts = Object.keys(recipes);
        assertGreaterThan(amounts.length, 0, 'Has at least one recipe');
        return 'Iron Plate recipe variants: ' + amounts.length;
    });
    
    test('get_recipe_for("Iron Ingot") returns highest rate recipe', () => {
        const [amount, name, recipe] = get_recipe_for("Iron Ingot");
        assertNotNull(amount, 'Amount exists');
        assertNotNull(name, 'Recipe name exists');
        assertNotNull(recipe, 'Recipe object exists');
        return `Best Iron Ingot recipe: ${name} (${amount}/min)`;
    });
    
    test('Recipe object has correct structure', () => {
        const [amount, name, recipe] = get_recipe_for("Iron Ingot");
        assertNotNull(recipe.machine, 'Recipe has machine');
        assertNotNull(recipe.inputs, 'Recipe has inputs');
        assertNotNull(recipe.outputs, 'Recipe has outputs');
        return `Recipe structure: machine=${recipe.machine}`;
    });
    
    test('get_fluids() returns fluid list', () => {
        const fluids = get_fluids();
        assertGreaterThan(fluids.length, 5, 'Has multiple fluids');
        if (!fluids.includes('Water')) throw new Error('Missing Water in fluids');
        if (!fluids.includes('Crude Oil')) throw new Error('Missing Crude Oil in fluids');
        return 'Fluid count: ' + fluids.length;
    });
    
    test('get_fluid_color("Water") returns hex color', () => {
        const color = get_fluid_color("Water");
        if (!color.startsWith('#')) throw new Error('Color does not start with #');
        return `Water color: ${color}`;
    });
    
    test('Purity enum has correct values', () => {
        assertEquals(Purity.IMPURE, 0, 'IMPURE = 0');
        assertEquals(Purity.NORMAL, 1, 'NORMAL = 1');
        assertEquals(Purity.PURE, 2, 'PURE = 2');
        return 'Purity enum correct';
    });

    // ====================================================================
    // Tests ported from test_recipes.py
    // ====================================================================

    test('test_get_conveyor_rate: conveyor rate lookup should return valid rates', () => {
        // Conveyor marks are 0-indexed: 0=Mk1, 1=Mk2, etc.
        const rate_mk1 = get_conveyor_rate(0);
        assertEquals(rate_mk1, 60.0, 'Mk1 rate');
        
        const rate_mk2 = get_conveyor_rate(1);
        assertEquals(rate_mk2, 120.0, 'Mk2 rate');
        
        const rate_mk3 = get_conveyor_rate(2);
        assertEquals(rate_mk3, 270.0, 'Mk3 rate');
        
        const rate_mk4 = get_conveyor_rate(3);
        assertEquals(rate_mk4, 480.0, 'Mk4 rate');
        
        return `Conveyor rates: Mk1=${rate_mk1}, Mk2=${rate_mk2}, Mk3=${rate_mk3}, Mk4=${rate_mk4}`;
    });

    test('test_get_water_extraction_rate: water extraction rate should be valid', () => {
        const rate = get_water_extraction_rate();
        assertGreaterThan(rate, 0, 'Water rate > 0');
        if (typeof rate !== 'number') throw new Error('Rate is not a number');
        return `Water extraction rate: ${rate}/min`;
    });

    test('test_get_oil_extraction_rate: oil extraction rates should vary by purity', () => {
        const impure_rate = get_oil_extraction_rate(Purity.IMPURE);
        const normal_rate = get_oil_extraction_rate(Purity.NORMAL);
        const pure_rate = get_oil_extraction_rate(Purity.PURE);
        
        assertGreaterThan(impure_rate, 0, 'Impure rate > 0');
        assertGreaterThan(normal_rate, impure_rate, 'Normal > Impure');
        assertGreaterThan(pure_rate, normal_rate, 'Pure > Normal');
        
        return `Oil extraction rates: Impure=${impure_rate}, Normal=${normal_rate}, Pure=${pure_rate}`;
    });

    test('test_get_load: machine load lookup should return valid power values', () => {
        // Test some known machines
        const smelter_load = get_load("Smelter");
        assertGreaterThan(smelter_load, 0, 'Smelter load > 0');
        
        const constructor_load = get_load("Constructor");
        assertGreaterThan(constructor_load, 0, 'Constructor load > 0');
        
        return `Machine loads: Smelter=${smelter_load}MW, Constructor=${constructor_load}MW`;
    });

    test('test_get_recipe_for: should return the highest rate recipe', () => {
        const [amount, recipe_name, recipe] = get_recipe_for("Iron Plate");
        
        assertGreaterThan(amount, 0, 'Amount > 0');
        if (typeof recipe_name !== 'string') throw new Error('Recipe name is not a string');
        if (!(recipe instanceof Recipe)) throw new Error('Recipe is not a Recipe instance');
        if (!("Iron Ore" in recipe.inputs || "Iron Ingot" in recipe.inputs)) {
            throw new Error('Recipe should have Iron Ore or Iron Ingot as input');
        }
        if (!("Iron Plate" in recipe.outputs)) throw new Error('Recipe should output Iron Plate');
        
        return `Best recipe for Iron Plate: ${recipe_name} at ${amount}/min`;
    });

    test('test_get_recipe_for_with_enablement: should respect enablement set', () => {
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
        assertEquals(recipe_name, sample_recipe_name, 'Recipe name matches enablement');
        return `Recipe with enablement: ${recipe_name}`;
    });

    test('test_find_recipe_name: should locate recipe by its Recipe object', () => {
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
        assertEquals(found_name, recipe_name, 'Found name matches');
        return `Found recipe name: ${found_name}`;
    });

    test('test_get_terminal_parts: terminal parts should be products with no consumers', () => {
        const terminal_parts = get_terminal_parts();
        
        assertGreaterThan(terminal_parts.size, 0, 'Has terminal parts');
        if (!(terminal_parts instanceof Set)) throw new Error('Terminal parts is not a Set');
        
        // Terminal parts should include end products
        // (exact contents depend on recipe data)
        
        return `Found ${terminal_parts.size} terminal parts`;
    });

    test('test_get_base_parts: base parts should be raw materials', () => {
        const base_parts = get_base_parts();
        
        assertGreaterThan(base_parts.size, 0, 'Has base parts');
        if (!(base_parts instanceof Set)) throw new Error('Base parts is not a Set');
        
        // Should include raw ores
        if (!base_parts.has("Iron Ore")) throw new Error('Missing Iron Ore');
        if (!base_parts.has("Copper Ore")) throw new Error('Missing Copper Ore');
        
        return `Found ${base_parts.size} base parts`;
    });

    test('test_recipe_lookups_consistency: recipe lookups should be internally consistent', () => {
        // Get all recipes
        const all_recipes = get_all_recipes();
        assertGreaterThan(Object.keys(all_recipes).length, 0, 'Has recipes');
        
        // Check that recipes_for works for some outputs
        const iron_plate_recipes = get_recipes_for("Iron Plate");
        assertGreaterThan(Object.keys(iron_plate_recipes).length, 0, 'Has Iron Plate recipes');
        
        // Check that get_recipe_for returns valid data
        const [amount, recipe_name, recipe] = get_recipe_for("Iron Plate");
        assertGreaterThan(amount, 0, 'Amount > 0');
        if (typeof recipe_name !== 'string') throw new Error('Recipe name is not a string');
        if (!(recipe instanceof Recipe)) throw new Error('Recipe is not a Recipe instance');
        
        return `Recipe lookups are consistent (${Object.keys(all_recipes).length} total recipes)`;
    });

    test('test_power_recipes: power recipes should produce MWm', () => {
        // Get all recipes that produce MWm (power)
        const power_recipes = get_recipes_for("MWm");
        assertGreaterThan(Object.keys(power_recipes).length, 0, 'Has power-producing recipes');
        
        // Get the best recipe for MWm
        const [amount, recipe_name, recipe] = get_recipe_for("MWm");
        assertNotNull(recipe, 'Power recipe exists');
        assertGreaterThan(amount, 0, 'Power output > 0');
        
        // Verify the recipe outputs MWm
        if (!("MWm" in recipe.outputs)) {
            throw new Error('Power recipe should output MWm');
        }
        assertGreaterThan(recipe.outputs.MWm, 0, 'MWm output > 0');
        
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
        
        return `Found ${totalPowerRecipes} power recipes, best: ${recipe_name} (${amount} MWm)`;
    });

    return runner;
}

