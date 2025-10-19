from pytest import raises

from economy import cost_of_recipes
from optimize import optimize_recipes
from recipes import get_default_enablement_set


def test_concrete_recipe_sanity_check():
    """Test that the optimizer gives the right answer when we hand it the solution."""
    actual = optimize_recipes({}, {"Concrete": 480}, enablement_set={"Concrete"}, economy={})
    expected = {"Concrete": 32}
    assert actual == expected


def test_two_recipe_concrete():
    """Test that concrete is optimized to use the standard recipe when all recipes are enabled and the default economy is used. Keep the test small by only enabling two recipes."""
    if cost_of_recipes({"Concrete": 32}) > cost_of_recipes({"Alternate: Wet Concrete": 6}):
        raise RuntimeError("This test expects the standard recipe to be cheaper in the default economy.")
    actual = optimize_recipes({}, {"Concrete": 480}, enablement_set={"Concrete", "Alternate: Wet Concrete"})
    expected = {"Concrete": 32.0}
    assert actual == expected


def test_input_utilization():
    """Test that the optimizer uses inputs as much as possible. Allow it to demand copper ore to produce copper ingots, but expect it to use the ingots we already have. Exclude the economy for simplicity."""
    actual = optimize_recipes({"Copper Ingot": 15}, {"Wire": 30}, enablement_set={"Copper Ingot", "Wire"}, economy={})
    expected = {"Wire": 1.0}
    assert actual == expected


def test_invalid_output():
    """Test that the optimizer raises an error when the outputs contain unrecognized parts."""
    with raises(ValueError, match="Outputs contain unrecognized parts: {'Copper Wire'}"):
        optimize_recipes({"Copper Ingot": 15}, {"Copper Wire": 30}, enablement_set={"Copper Ingot", "Wire"}, economy={})


def test_input_utilization_with_economy():
    """Test that the optimizer uses inputs as much as possible. Allow it to demand copper ore to produce copper ingots, but expect it to use the ingots we already have. Exclude the economy for simplicity."""
    actual = optimize_recipes({"Copper Ingot": 15}, {"Wire": 30}, enablement_set={"Copper Ingot", "Wire"})
    expected = {"Wire": 1}
    assert actual == expected


def test_quickwire():
    """Test that the quickwire recipe is optimized to use the standard recipe when all recipes are enabled and the default economy is used."""
    actual = optimize_recipes({}, {"Quickwire": 20})
    expected = {"Caterium Ingot": 1.0, "Quickwire": 1.0}
    assert actual == expected


def test_concrete_with_power_design():
    actual = optimize_recipes({}, {"Concrete": 480}, enablement_set={"Concrete", "Coal Power"}, design_power=True)
    expected = {"Concrete": 32.0, "Coal Power": 2.0}
    assert actual == expected


def test_concrete_with_input_water():
    actual = optimize_recipes({"Water": 100}, {"Concrete": 80}, enablement_set={"Concrete", "Alternate: Wet Concrete"})
    expected = {"Alternate: Wet Concrete": 1.0}
    assert actual == expected


def test_concrete_with_not_enough_water():
    actual = optimize_recipes({"Water": 100}, {"Concrete": 95}, enablement_set={"Concrete", "Alternate: Wet Concrete"})
    expected = {"Alternate: Wet Concrete": 1.0, "Concrete": 1.0}
    assert actual == expected


def test_dont_design_power_when_disabled():
    """Test that, when given the means to design power, and when weighing power consumption, the optimizer doesn't design power when power design is disabled."""
    actual = optimize_recipes({}, {"Concrete": 480}, enablement_set={"Concrete", "Biomass (Mycelia)", "Solid Biofuel", "Power (Biomass)"}, power_consumption_weight=1.0, design_power=False)
    expected = {"Concrete": 32.0}
    assert actual == expected


def test_power_generation():
    actual = optimize_recipes({}, {"MWm": 1}, enablement_set={"Coal Power"})
    expected = {"Coal Power": 1.0}
    assert actual == expected
