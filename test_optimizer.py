from optimize import optimize_recipes
from economy import get_default_economy, cost_of_recipes

def test_simple_concrete_recipe():
    """Test that the simple concrete recipe is optimized to use the standard recipe when only the standard recipe is enabled."""
    actual = optimize_recipes({}, {"Concrete": 480}, enablement_set={"Concrete"})
    expected = {"Concrete": 32}
    assert actual == expected


def test_two_recipe_optimized_concrete_example_with_economy():
    """Test that the concrete recipe is optimized to use the alternate recipe when both recipes are enabled and the economy is contains no useful information."""
    actual = optimize_recipes({}, {"Concrete": 480}, enablement_set={"Concrete", "Alternate: Wet Concrete"}, economy={"foo": 1})
    expected = {"Alternate: Wet Concrete": 6}
    assert actual == expected


def test_optimized_concrete_example_no_economy():
    """Test that the concrete recipe is optimized to use the alternate recipe when all recipes are enabled and the default economy is used."""
    actual = optimize_recipes({}, {"Concrete": 480}, economy={"foo": 1})
    expected = {"Alternate: Wet Concrete": 6}
    assert actual == expected


def test_optimized_concrete_with_default_economy():
    """Test that the concrete recipe is optimized to use the standard recipe when all recipes are enabled and the default economy is used."""
    assert cost_of_recipes({"Concrete": 32}) < cost_of_recipes({"Alternate: Wet Concrete": 6}), "This test expects the standard recipe to be cheaper in the default economy."
    actual = optimize_recipes({}, {"Concrete": 480})
    expected = {"Concrete": 32}
    assert actual == expected
