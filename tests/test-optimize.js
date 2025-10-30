import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { optimize_recipes } from '../optimize.js';

describe('Optimize', () => {
    it('optimize_recipes is a function', () => {
        assert.strictEqual(typeof optimize_recipes, 'function');
    });

    // ====================================================================
    // Tests ported from test_optimize.py
    // ====================================================================

    it('test_concrete_recipe_sanity_check: optimizer gives right answer when handed the solution', async () => {
        const actual = await optimize_recipes({}, {"Concrete": 480}, {enablement_set: new Set(["Concrete"]), economy: {}});
        const expected = {"Concrete": 32};
        
        assert.strictEqual(Object.keys(actual).length, Object.keys(expected).length);
        assert.strictEqual(actual["Concrete"], expected["Concrete"]);
    });

    it('test_two_recipe_concrete: concrete optimized to use standard recipe with default economy', async () => {
        // Import cost_of_recipes for the check
        const { cost_of_recipes } = await import('../economy.js');
        
        if (cost_of_recipes({"Concrete": 32}) > cost_of_recipes({"Alternate: Wet Concrete": 6})) {
            throw new Error("This test expects the standard recipe to be cheaper in the default economy.");
        }
        const actual = await optimize_recipes({}, {"Concrete": 480}, {enablement_set: new Set(["Concrete", "Alternate: Wet Concrete"])});
        const expected = {"Concrete": 32.0};
        
        assert.strictEqual(actual["Concrete"], expected["Concrete"]);
    });

    it('test_input_utilization: optimizer uses inputs as much as possible', async () => {
        const actual = await optimize_recipes({"Copper Ingot": 15}, {"Wire": 30}, {enablement_set: new Set(["Copper Ingot", "Wire"]), economy: {}});
        const expected = {"Wire": 1.0};
        
        assert.strictEqual(actual["Wire"], expected["Wire"]);
    });

    it('test_invalid_output: optimizer raises error for unrecognized parts', async () => {
        try {
            await optimize_recipes({"Copper Ingot": 15}, {"Copper Wire": 30}, {enablement_set: new Set(["Copper Ingot", "Wire"]), economy: {}});
            throw new Error('Should have thrown an error');
        } catch (e) {
            if (!e.message.includes("Outputs contain unrecognized parts")) {
                throw new Error(`Expected error about unrecognized parts, got: ${e.message}`);
            }
        }
    });

    it('test_input_utilization_with_economy: optimizer uses inputs with economy', async () => {
        const actual = await optimize_recipes({"Copper Ingot": 15}, {"Wire": 30}, {enablement_set: new Set(["Copper Ingot", "Wire"])});
        const expected = {"Wire": 1};
        
        assert.strictEqual(actual["Wire"], expected["Wire"]);
    });

    it('test_quickwire: quickwire recipe optimized with default economy', async () => {
        const actual = await optimize_recipes({}, {"Quickwire": 20});
        const expected = {"Caterium Ingot": 1.0, "Quickwire": 1.0};
        
        assert.strictEqual(actual["Caterium Ingot"], expected["Caterium Ingot"]);
        assert.strictEqual(actual["Quickwire"], expected["Quickwire"]);
    });

    it('test_concrete_with_power_design: concrete with power design enabled', async () => {
        const actual = await optimize_recipes({}, {"Concrete": 480}, {enablement_set: new Set(["Concrete", "Coal Power"]), design_power: true});
        const expected = {"Concrete": 32.0, "Coal Power": 2.0};
        
        assert.strictEqual(actual["Concrete"], expected["Concrete"]);
        assert.strictEqual(actual["Coal Power"], expected["Coal Power"]);
    });

    it('test_concrete_with_input_water: concrete with input water', async () => {
        const actual = await optimize_recipes({"Water": 100}, {"Concrete": 80}, {enablement_set: new Set(["Concrete", "Alternate: Wet Concrete"])});
        const expected = {"Alternate: Wet Concrete": 1.0};
        
        assert.strictEqual(actual["Alternate: Wet Concrete"], expected["Alternate: Wet Concrete"]);
    });

    it('test_concrete_with_not_enough_water: concrete with insufficient water', async () => {
        const actual = await optimize_recipes({"Water": 100}, {"Concrete": 95}, {enablement_set: new Set(["Concrete", "Alternate: Wet Concrete"])});
        const expected = {"Alternate: Wet Concrete": 1.0, "Concrete": 1.0};
        
        assert.strictEqual(actual["Alternate: Wet Concrete"], expected["Alternate: Wet Concrete"]);
        assert.strictEqual(actual["Concrete"], expected["Concrete"]);
    });

    it('test_dont_design_power_when_disabled: optimizer does not design power when disabled', async () => {
        const actual = await optimize_recipes({}, {"Concrete": 480}, {enablement_set: new Set(["Concrete", "Biomass (Mycelia)", "Solid Biofuel", "Power (Biomass)"]), power_consumption_weight: 1.0, design_power: false});
        const expected = {"Concrete": 32.0};
        
        assert.strictEqual(actual["Concrete"], expected["Concrete"]);
        assert.strictEqual(Object.keys(actual).length, 1);
    });

    it('test_power_generation: power generation works', async () => {
        const actual = await optimize_recipes({}, {"MWm": 1}, {enablement_set: new Set(["Coal Power"])});
        const expected = {"Coal Power": 1.0};
        
        assert.strictEqual(actual["Coal Power"], expected["Coal Power"]);
    });

    it('test_invalid_enablement_set: invalid recipe names raise error', async () => {
        try {
            await optimize_recipes({}, {"Iron Plate": 100}, {enablement_set: new Set(["NonExistentRecipe", "Iron Plate"])});
            throw new Error('Should have thrown an error');
        } catch (e) {
            if (!e.message.includes("Enablement set contains invalid recipes")) {
                throw new Error(`Expected error about invalid recipes, got: ${e.message}`);
            }
        }
    });

    it('test_zero_input_costs_weight: input_costs_weight=0 works correctly', async () => {
        const actual = await optimize_recipes(
            {},
            {"Iron Plate": 30},
            {
                enablement_set: new Set(["Iron Ingot", "Iron Plate"]),
                input_costs_weight: 0.0,
                economy: {}
            }
        );
        const expected = {"Iron Ingot": 2.0, "Iron Plate": 2.0};
        
        assert.strictEqual(actual["Iron Ingot"], expected["Iron Ingot"]);
        assert.strictEqual(actual["Iron Plate"], expected["Iron Plate"]);
    });

    it('test_part_not_in_economy: warning when part not found in provided economy', async () => {
        // provide a minimal economy that doesn't include all parts
        const minimal_economy = {"Iron Ore": 1.0};  // missing many parts like Iron Ingot
        
        // this should trigger the warning for missing parts but still work
        const actual = await optimize_recipes(
            {},
            {"Iron Plate": 30},
            {
                enablement_set: new Set(["Iron Ingot", "Iron Plate"]),
                economy: minimal_economy
            }
        );
        
        // should still produce valid output despite warnings
        if (!("Iron Plate" in actual)) {
            throw new Error('Iron Plate not in result');
        }
        assert.strictEqual(actual["Iron Plate"], 2.0);
    });

    it('test_infeasible_optimization: infeasible optimization raises error', async () => {
        // try to produce something with insufficient recipes
        // enable only the final recipe but not the intermediate ones
        try {
            await optimize_recipes(
                {},
                {"Iron Plate": 100},
                {
                    enablement_set: new Set(["Iron Plate"]),  // missing Iron Ingot recipe!
                    economy: {}
                }
            );
            throw new Error('Should have thrown an error');
        } catch (e) {
            if (!e.message.includes("Couldn't design the factory")) {
                throw new Error(`Expected error about infeasible factory, got: ${e.message}`);
            }
        }
    });

    it('test_infeasible_optimization_with_power_design: infeasible optimization with power design', async () => {
        try {
            await optimize_recipes(
                {},
                {"MWm": 1},
                {
                    enablement_set: new Set(["Power (Biomass)"]),
                    design_power: true
                }
            );
            throw new Error('Should have thrown an error');
        } catch (e) {
            if (!e.message.includes("Couldn't design the factory")) {
                throw new Error(`Expected error about infeasible factory, got: ${e.message}`);
            }
        }
    });
});
