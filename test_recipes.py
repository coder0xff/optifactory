"""Tests for recipes module"""

from recipes import (
    get_conveyor_rate,
    get_water_extraction_rate,
    get_oil_extraction_rate,
    get_load,
    get_recipe_for,
    get_recipes_for,
    find_recipe_name,
    get_terminal_parts,
    get_base_parts,
    get_all_recipes,
    Purity,
    Recipe,
)


def test_get_conveyor_rate():
    """conveyor rate lookup should return valid rates"""
    # Conveyor marks are 0-indexed: 0=Mk1, 1=Mk2, etc.
    rate_mk1 = get_conveyor_rate(0)
    assert rate_mk1 == 60.0
    
    rate_mk2 = get_conveyor_rate(1)
    assert rate_mk2 == 120.0
    
    rate_mk3 = get_conveyor_rate(2)
    assert rate_mk3 == 270.0
    
    rate_mk4 = get_conveyor_rate(3)
    assert rate_mk4 == 480.0
    
    print(f"✓ Conveyor rates: Mk1={rate_mk1}, Mk2={rate_mk2}, Mk3={rate_mk3}, Mk4={rate_mk4}")


def test_get_water_extraction_rate():
    """water extraction rate should be valid"""
    rate = get_water_extraction_rate()
    assert rate > 0
    assert isinstance(rate, (int, float))
    print(f"✓ Water extraction rate: {rate}/min")


def test_get_oil_extraction_rate():
    """oil extraction rates should vary by purity"""
    impure_rate = get_oil_extraction_rate(Purity.IMPURE)
    normal_rate = get_oil_extraction_rate(Purity.NORMAL)
    pure_rate = get_oil_extraction_rate(Purity.PURE)
    
    assert impure_rate > 0
    assert normal_rate > impure_rate
    assert pure_rate > normal_rate
    
    print(f"✓ Oil extraction rates: Impure={impure_rate}, Normal={normal_rate}, Pure={pure_rate}")


def test_get_load():
    """machine load lookup should return valid power values"""
    # Test some known machines
    smelter_load = get_load("Smelter")
    assert smelter_load > 0
    
    constructor_load = get_load("Constructor")
    assert constructor_load > 0
    
    print(f"✓ Machine loads: Smelter={smelter_load}MW, Constructor={constructor_load}MW")


def test_get_recipe_for():
    """get_recipe_for should return the highest rate recipe"""
    amount, recipe_name, recipe = get_recipe_for("Iron Plate")
    
    assert amount > 0
    assert isinstance(recipe_name, str)
    assert isinstance(recipe, Recipe)
    assert "Iron Ore" in recipe.inputs or "Iron Ingot" in recipe.inputs
    assert "Iron Plate" in recipe.outputs
    
    print(f"✓ Best recipe for Iron Plate: {recipe_name} at {amount}/min")


def test_get_recipe_for_with_enablement():
    """get_recipe_for should respect enablement set"""
    # Get all recipes for Iron Plate
    all_recipes = get_recipes_for("Iron Plate")
    
    # Pick a specific recipe to enable
    if all_recipes:
        # Get one recipe name from the available recipes
        sample_recipe_name = None
        for recipes_list in all_recipes.values():
            if recipes_list:
                sample_recipe_name = recipes_list[0][0]
                break
        
        if sample_recipe_name:
            # Get recipe with limited enablement set
            amount, recipe_name, recipe = get_recipe_for("Iron Plate", {sample_recipe_name})
            assert recipe_name == sample_recipe_name
            print(f"✓ Recipe with enablement: {recipe_name}")


def test_find_recipe_name():
    """find_recipe_name should locate recipe by its Recipe object with frozendicts"""
    # find_recipe_name requires Recipe objects created from the internal _RECIPES dict
    # which uses frozen dicts for hashability
    all_recipes = get_all_recipes()
    
    # Get a recipe with frozendicts from all_recipes
    if "Iron Plate" in all_recipes:
        recipe = all_recipes["Iron Plate"]
        found_name = find_recipe_name(recipe)
        assert found_name == "Iron Plate"
        print(f"✓ Found recipe name: {found_name}")
    else:
        # Fallback: just pick any recipe
        recipe_name = list(all_recipes.keys())[0]
        recipe = all_recipes[recipe_name]
        found_name = find_recipe_name(recipe)
        assert found_name == recipe_name
        print(f"✓ Found recipe name: {found_name}")


def test_get_terminal_parts():
    """terminal parts should be products with no consumers"""
    terminal_parts = get_terminal_parts()
    
    assert len(terminal_parts) > 0
    assert isinstance(terminal_parts, set)
    
    # Terminal parts should include end products
    # (exact contents depend on recipe data)
    
    print(f"✓ Found {len(terminal_parts)} terminal parts")


def test_get_base_parts():
    """base parts should be raw materials"""
    base_parts = get_base_parts()
    
    assert len(base_parts) > 0
    assert isinstance(base_parts, set)
    
    # Should include raw ores
    assert "Iron Ore" in base_parts
    assert "Copper Ore" in base_parts
    
    print(f"✓ Found {len(base_parts)} base parts")


def test_recipe_lookups_consistency():
    """recipe lookups should be internally consistent"""
    # Get all recipes
    all_recipes = get_all_recipes()
    assert len(all_recipes) > 0
    
    # Check that recipes_for works for some outputs
    iron_plate_recipes = get_recipes_for("Iron Plate")
    assert len(iron_plate_recipes) > 0
    
    # Check that get_recipe_for returns valid data
    amount, recipe_name, recipe = get_recipe_for("Iron Plate")
    assert amount > 0
    assert isinstance(recipe_name, str)
    assert isinstance(recipe, Recipe)
    
    print(f"✓ Recipe lookups are consistent ({len(all_recipes)} total recipes)")

