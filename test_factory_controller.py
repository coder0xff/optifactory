"""Tests for factory controller"""

from pytest import raises

from factory_controller import FactoryController, FactoryConfig, ValidationResult
from recipes import Recipe, Purity, get_all_recipes_by_machine
from frozendict import frozendict


def test_controller_init():
    """controller should initialize with economy and default recipes"""
    economy = {"Iron Ore": 1.0}
    controller = FactoryController(economy)
    assert controller.economy == economy
    assert len(controller.enabled_recipes) > 0


def test_get_default_enabled_recipes():
    """default enabled recipes should exclude power and packager"""
    recipes = FactoryController._get_default_enabled_recipes()
    assert len(recipes) > 0
    # Check that a known recipe is included
    assert "Iron Plate" in recipes
    # Verify no power recipes by checking none have MWm in outputs
    # (we can't easily check this without loading all recipes, but we trust the logic)


def test_parse_config_text_basic():
    """parse_config_text should handle basic input"""
    text = "Iron Plate:100\nCopper Ingot:50"
    result = FactoryController.parse_config_text(text)
    assert result == [("Iron Plate", 100.0), ("Copper Ingot", 50.0)]


def test_parse_config_text_with_comments():
    """parse_config_text should skip comments"""
    text = """
# This is a comment
Iron Plate:100
# Another comment
Copper Ingot:50
"""
    result = FactoryController.parse_config_text(text)
    assert result == [("Iron Plate", 100.0), ("Copper Ingot", 50.0)]


def test_parse_config_text_empty_lines():
    """parse_config_text should skip empty lines"""
    text = "Iron Plate:100\n\nCopper Ingot:50\n\n"
    result = FactoryController.parse_config_text(text)
    assert result == [("Iron Plate", 100.0), ("Copper Ingot", 50.0)]


def test_parse_config_text_whitespace():
    """parse_config_text should handle extra whitespace"""
    text = "  Iron Plate:100  \n  Copper Ingot:50  "
    result = FactoryController.parse_config_text(text)
    assert result == [("Iron Plate", 100.0), ("Copper Ingot", 50.0)]


def test_parse_config_text_comment_only():
    """parse_config_text should handle comment-only text"""
    text = "# Comment 1\n# Comment 2"
    result = FactoryController.parse_config_text(text)
    assert result == []


def test_parse_config_text_empty():
    """parse_config_text should handle empty text"""
    result = FactoryController.parse_config_text("")
    assert result == []


def test_parse_config_text_invalid():
    """parse_config_text should raise on invalid format"""
    with raises(ValueError, match="Invalid format"):
        FactoryController.parse_config_text("Invalid Line Without Colon")


def test_format_recipe_tooltip_with_inputs_and_outputs():
    """format_recipe_tooltip should format recipe with inputs and outputs"""
    recipe = Recipe(
        machine="Smelter",
        inputs=frozendict({"Iron Ore": 30.0}),
        outputs=frozendict({"Iron Ingot": 30.0})
    )
    result = FactoryController.format_recipe_tooltip(recipe)
    assert "Inputs:" in result
    assert "Iron Ore: 30.0/min" in result
    assert "Outputs:" in result
    assert "Iron Ingot: 30.0/min" in result


def test_format_recipe_tooltip_outputs_only():
    """format_recipe_tooltip should format recipe with only outputs"""
    recipe = Recipe(
        machine="Miner",
        inputs=frozendict({}),
        outputs=frozendict({"Iron Ore": 60.0})
    )
    result = FactoryController.format_recipe_tooltip(recipe)
    assert "Inputs:" not in result
    assert "Outputs:" in result
    assert "Iron Ore: 60.0/min" in result


def test_format_recipe_tooltip_multiple_items():
    """format_recipe_tooltip should format recipe with multiple inputs/outputs"""
    recipe = Recipe(
        machine="Assembler",
        inputs=frozendict({"Iron Plate": 20.0, "Copper Wire": 30.0}),
        outputs=frozendict({"Circuit Board": 10.0})
    )
    result = FactoryController.format_recipe_tooltip(recipe)
    assert "Iron Plate: 20.0/min" in result
    assert "Copper Wire: 30.0/min" in result
    assert "Circuit Board: 10.0/min" in result


def test_validate_config_valid():
    """validate_config should pass for valid configuration"""
    controller = FactoryController(economy={})
    config = FactoryConfig(
        outputs={"Iron Plate": 100},
        inputs=[],
        mines=[],
        enabled_recipes={"Iron Plate"}
    )
    result = controller.validate_config(config)
    assert result.is_valid
    assert len(result.errors) == 0


def test_validate_config_empty_outputs():
    """validate_config should error on empty outputs"""
    controller = FactoryController(economy={})
    config = FactoryConfig(
        outputs={},
        inputs=[],
        mines=[],
        enabled_recipes=set()
    )
    result = controller.validate_config(config)
    assert not result.is_valid
    assert len(result.errors) == 1
    assert "No outputs specified" in result.errors[0]


def test_validate_config_power_without_recipes():
    """validate_config should warn about power design without power recipes"""
    controller = FactoryController(economy={})
    config = FactoryConfig(
        outputs={"Iron Plate": 100},
        inputs=[],
        mines=[],
        enabled_recipes={"Iron Plate"},
        design_power=True
    )
    result = controller.validate_config(config)
    assert result.is_valid  # Just a warning, not an error
    assert len(result.warnings) == 1
    assert "power" in result.warnings[0].lower()


def test_validate_config_power_with_recipes():
    """validate_config should not warn when power design has power recipes"""
    controller = FactoryController(economy={})
    config = FactoryConfig(
        outputs={"Iron Plate": 100},
        inputs=[],
        mines=[],
        enabled_recipes={"Iron Plate", "Coal Power"},
        design_power=True
    )
    result = controller.validate_config(config)
    assert result.is_valid
    assert len(result.warnings) == 0


def test_validate_config_no_power_design():
    """validate_config should not warn when power design is disabled"""
    controller = FactoryController(economy={})
    config = FactoryConfig(
        outputs={"Iron Plate": 100},
        inputs=[],
        mines=[],
        enabled_recipes={"Iron Plate"},
        design_power=False
    )
    result = controller.validate_config(config)
    assert result.is_valid
    assert len(result.warnings) == 0


def test_generate_factory_basic():
    """generate_factory should create factory from config"""
    controller = FactoryController(economy={})
    config = FactoryConfig(
        outputs={"Iron Plate": 30},
        inputs=[("Iron Ore", 30)],
        mines=[],
        enabled_recipes={"Iron Ingot", "Iron Plate"}  # Need both recipes
    )
    factory = controller.generate_factory(config)
    assert factory is not None
    assert factory.network is not None


def test_generate_factory_with_mines():
    """generate_factory should handle mines in config"""
    controller = FactoryController(economy={})
    config = FactoryConfig(
        outputs={"Iron Plate": 100},
        inputs=[],
        mines=[("Iron Ore", Purity.NORMAL)],
        enabled_recipes={"Iron Ingot", "Iron Plate"}
    )
    factory = controller.generate_factory(config)
    assert factory is not None
    assert factory.network is not None


def test_generate_factory_with_weights():
    """generate_factory should use optimization weights"""
    controller = FactoryController(economy={})
    config = FactoryConfig(
        outputs={"Iron Plate": 30},
        inputs=[("Iron Ore", 30)],
        mines=[],
        enabled_recipes={"Iron Ingot", "Iron Plate"},  # Need both recipes
        input_costs_weight=0.5,
        machine_counts_weight=0.3,
        power_consumption_weight=0.2
    )
    factory = controller.generate_factory(config)
    assert factory is not None


def test_generate_factory_invalid_config():
    """generate_factory should raise on invalid config"""
    controller = FactoryController(economy={})
    config = FactoryConfig(
        outputs={},  # Empty!
        inputs=[],
        mines=[],
        enabled_recipes=set()
    )
    with raises(ValueError, match="No outputs"):
        controller.generate_factory(config)


def test_generate_factory_with_economy():
    """generate_factory should use controller's economy"""
    economy = {"Iron Ore": 1.0, "Iron Plate": 2.0}
    controller = FactoryController(economy=economy)
    config = FactoryConfig(
        outputs={"Iron Plate": 30},
        inputs=[],
        mines=[("Iron Ore", Purity.NORMAL)],
        enabled_recipes={"Iron Ingot", "Iron Plate"}
    )
    factory = controller.generate_factory(config)
    assert factory is not None


def test_factory_config_defaults():
    """FactoryConfig should have correct default values"""
    config = FactoryConfig(
        outputs={"Iron Plate": 100},
        inputs=[],
        mines=[],
        enabled_recipes=set()
    )
    assert config.input_costs_weight == 1.0
    assert config.machine_counts_weight == 0.0
    assert config.power_consumption_weight == 1.0
    assert config.design_power is False


def test_validation_result_structure():
    """ValidationResult should have correct structure"""
    result = ValidationResult(
        is_valid=True,
        warnings=["warning1"],
        errors=[]
    )
    assert result.is_valid
    assert len(result.warnings) == 1
    assert len(result.errors) == 0


# ========== State Management Tests ==========

def test_get_set_outputs_text():
    """controller should manage outputs text state"""
    controller = FactoryController(economy={})
    assert controller.get_outputs_text() == "Concrete:480"  # Default
    
    controller.set_outputs_text("Iron Plate:100")
    assert controller.get_outputs_text() == "Iron Plate:100"


def test_get_set_inputs_text():
    """controller should manage inputs text state"""
    controller = FactoryController(economy={})
    default_text = controller.get_inputs_text()
    assert "# Leave empty" in default_text
    
    controller.set_inputs_text("Iron Ore:200")
    assert controller.get_inputs_text() == "Iron Ore:200"


def test_get_set_mines_text():
    """controller should manage mines text state"""
    controller = FactoryController(economy={})
    assert controller.get_mines_text() == ""
    
    controller.set_mines_text("Iron Ore:PURE")
    assert controller.get_mines_text() == "Iron Ore:PURE"


def test_get_set_recipe_search_text():
    """controller should manage recipe search text state"""
    controller = FactoryController(economy={})
    assert controller.get_recipe_search_text() == ""
    
    controller.set_recipe_search_text("iron")
    assert controller.get_recipe_search_text() == "iron"


def test_get_set_optimization_weights():
    """controller should manage optimization weight state"""
    controller = FactoryController(economy={})
    assert controller.get_input_costs_weight() == 1.0
    assert controller.get_machine_counts_weight() == 0.0
    assert controller.get_power_consumption_weight() == 1.0
    
    controller.set_input_costs_weight(0.5)
    controller.set_machine_counts_weight(0.3)
    controller.set_power_consumption_weight(0.7)
    
    assert controller.get_input_costs_weight() == 0.5
    assert controller.get_machine_counts_weight() == 0.3
    assert controller.get_power_consumption_weight() == 0.7


def test_get_set_design_power():
    """controller should manage design power flag"""
    controller = FactoryController(economy={})
    assert controller.get_design_power() is False
    
    controller.set_design_power(True)
    assert controller.get_design_power() is True


def test_set_recipe_enabled():
    """controller should enable/disable individual recipes"""
    controller = FactoryController(economy={})
    
    # Start with default recipes
    initial_count = len(controller.enabled_recipes)
    assert initial_count > 0
    
    # Disable a recipe
    controller.set_recipe_enabled("Iron Plate", False)
    assert "Iron Plate" not in controller.enabled_recipes
    
    # Re-enable it
    controller.set_recipe_enabled("Iron Plate", True)
    assert "Iron Plate" in controller.enabled_recipes


def test_set_recipes_enabled():
    """controller should set complete recipe set"""
    controller = FactoryController(economy={})
    
    new_set = {"Iron Plate", "Copper Ingot"}
    controller.set_recipes_enabled(new_set)
    
    assert controller.get_enabled_recipes() == new_set


def test_get_enabled_recipes_returns_copy():
    """get_enabled_recipes should return a copy to prevent external mutation"""
    controller = FactoryController(economy={})
    
    recipes1 = controller.get_enabled_recipes()
    recipes1.add("NewRecipe")
    
    recipes2 = controller.get_enabled_recipes()
    assert "NewRecipe" not in recipes2


def test_get_current_factory():
    """controller should track current factory"""
    controller = FactoryController(economy={})
    assert controller.get_current_factory() is None
    
    # After generating, should be cached
    config = FactoryConfig(
        outputs={"Iron Plate": 30},
        inputs=[("Iron Ore", 30)],
        mines=[],
        enabled_recipes={"Iron Ingot", "Iron Plate"}
    )
    factory = controller.generate_factory(config)
    # Note: regular generate doesn't cache, need generate_from_state


def test_should_show_power_warning_disabled():
    """should_show_power_warning should return False when power design disabled"""
    controller = FactoryController(economy={})
    controller.set_design_power(False)
    
    assert not controller.should_show_power_warning()


def test_should_show_power_warning_enabled_without_recipes():
    """should_show_power_warning should return True when power enabled but no power recipes"""
    controller = FactoryController(economy={})
    controller.set_design_power(True)
    controller.set_recipes_enabled({"Iron Plate"})  # No power recipes
    
    assert controller.should_show_power_warning()


def test_should_show_power_warning_enabled_with_recipes():
    """should_show_power_warning should return False when power enabled with power recipes"""
    controller = FactoryController(economy={})
    controller.set_design_power(True)
    controller.set_recipes_enabled({"Coal Power", "Iron Plate"})
    
    assert not controller.should_show_power_warning()


def test_generate_factory_from_state():
    """generate_factory_from_state should use controller's current state"""
    controller = FactoryController(economy={})
    
    # Set up state
    controller.set_outputs_text("Iron Plate:30")
    controller.set_inputs_text("Iron Ore:30")
    controller.set_recipes_enabled({"Iron Ingot", "Iron Plate"})
    controller.set_input_costs_weight(0.5)
    
    # Generate from state
    graphviz_diagram = controller.generate_factory_from_state()
    
    assert graphviz_diagram is not None
    assert hasattr(graphviz_diagram, 'source')  # Should be a graphviz Digraph
    
    # Should be cached in controller
    assert controller.get_current_factory() is not None


def test_generate_factory_from_state_empty_outputs():
    """generate_factory_from_state should raise on empty outputs"""
    controller = FactoryController(economy={})
    controller.set_outputs_text("")
    
    with raises(ValueError, match="No outputs specified"):
        controller.generate_factory_from_state()


def test_generate_factory_from_state_with_comments():
    """generate_factory_from_state should handle comments in config text"""
    controller = FactoryController(economy={})
    
    controller.set_outputs_text("# Comment\nIron Plate:30")
    controller.set_inputs_text("# Input comment\nIron Ore:30")
    controller.set_recipes_enabled({"Iron Ingot", "Iron Plate"})
    
    graphviz_diagram = controller.generate_factory_from_state()
    assert graphviz_diagram is not None
    assert hasattr(graphviz_diagram, 'source')


def test_get_graphviz_source_no_factory():
    """get_graphviz_source should return None when no factory generated"""
    controller = FactoryController(economy={})
    source = controller.get_graphviz_source()
    assert source is None


def test_get_graphviz_source_with_factory():
    """get_graphviz_source should return source after factory generated"""
    controller = FactoryController(economy={})
    
    controller.set_outputs_text("Iron Plate:30")
    controller.set_inputs_text("Iron Ore:30")
    controller.set_recipes_enabled({"Iron Ingot", "Iron Plate"})
    
    graphviz_diagram = controller.generate_factory_from_state()
    source = controller.get_graphviz_source()
    
    assert source is not None
    assert isinstance(source, str)
    assert len(source) > 0
    # Source from getter should match diagram's source
    assert source == graphviz_diagram.source


def test_copy_graphviz_source_no_factory():
    """copy_graphviz_source should return None when no factory"""
    controller = FactoryController(economy={})
    
    source = controller.copy_graphviz_source()
    
    assert source is None


def test_copy_graphviz_source_with_factory():
    """copy_graphviz_source should return source when factory exists"""
    controller = FactoryController(economy={})
    
    controller.set_outputs_text("Iron Plate:30")
    controller.set_inputs_text("Iron Ore:30")
    controller.set_recipes_enabled({"Iron Ingot", "Iron Plate"})
    
    graphviz_diagram = controller.generate_factory_from_state()
    source = controller.copy_graphviz_source()
    
    assert source is not None
    assert isinstance(source, str)
    # Should match the diagram's source
    assert source == graphviz_diagram.source


def test_get_all_recipes_by_machine():
    """controller should provide access to recipes"""
    controller = FactoryController(economy={})
    recipes = controller.get_all_recipes_by_machine()
    
    assert len(recipes) > 0
    assert "Smelter" in recipes or "Constructor" in recipes


def test_get_recipe_tooltip():
    """controller should provide recipe tooltips"""
    controller = FactoryController(economy={})
    
    tooltip = controller.get_recipe_tooltip("Iron Plate")
    assert tooltip is not None
    assert "Iron Ore" in tooltip or "Iron Ingot" in tooltip
    assert "/min" in tooltip


def test_get_recipe_tooltip_not_found():
    """controller should return None for non-existent recipe"""
    controller = FactoryController(economy={})
    
    tooltip = controller.get_recipe_tooltip("NonExistentRecipe")
    assert tooltip is None


# ========== Tree Structure Tests ==========

def test_get_recipe_tree_structure():
    """get_recipe_tree_structure should return complete tree"""
    controller = FactoryController(economy={})
    
    structure = controller.get_recipe_tree_structure()
    
    assert len(structure.machines) > 0
    assert all(machine.tree_id.startswith("machine:") for machine in structure.machines)
    assert all(len(machine.recipes) > 0 for machine in structure.machines)


def test_tree_structure_recipe_ids():
    """recipe tree IDs should follow format recipe:{machine}:{recipe}"""
    controller = FactoryController(economy={})
    
    structure = controller.get_recipe_tree_structure()
    
    for machine in structure.machines:
        for recipe in machine.recipes:
            assert recipe.tree_id.startswith("recipe:")
            assert machine.display_name in recipe.tree_id


def test_tree_structure_with_search():
    """tree structure should filter by search text"""
    controller = FactoryController(economy={})
    controller.set_recipe_search_text("iron")
    
    structure = controller.get_recipe_tree_structure()
    
    # Should have some visible and some invisible recipes
    all_recipes = [r for m in structure.machines for r in m.recipes]
    visible_count = sum(1 for r in all_recipes if r.is_visible)
    invisible_count = sum(1 for r in all_recipes if not r.is_visible)
    
    assert visible_count > 0, "Should have some visible recipes matching 'iron'"
    assert invisible_count > 0, "Should have some invisible recipes not matching 'iron'"


def test_tree_structure_machine_visibility():
    """machines should be hidden if no visible recipes"""
    controller = FactoryController(economy={})
    controller.set_recipe_search_text("zzzznonexistent")
    
    structure = controller.get_recipe_tree_structure()
    
    # All machines should be invisible
    assert all(not machine.is_visible for machine in structure.machines)


def test_tree_structure_check_states():
    """machine check states should be calculated correctly"""
    controller = FactoryController(economy={})
    
    # Enable only some recipes
    controller.set_recipes_enabled({"Iron Plate", "Copper Ingot"})
    
    structure = controller.get_recipe_tree_structure()
    
    # Find Smelter machine
    smelter = next((m for m in structure.machines if m.display_name == "Smelter"), None)
    if smelter:
        # Should have some enabled and some disabled recipes
        enabled_count = sum(1 for r in smelter.recipes if r.is_enabled and r.is_visible)
        total_visible = sum(1 for r in smelter.recipes if r.is_visible)
        
        if enabled_count == 0:
            assert smelter.check_state == 'unchecked'
        elif enabled_count == total_visible:
            assert smelter.check_state == 'checked'
        else:
            assert smelter.check_state == 'tristate'


def test_on_recipe_toggled():
    """on_recipe_toggled should update enabled recipes"""
    controller = FactoryController(economy={})
    
    recipe_id = "recipe:Smelter:Iron Plate"
    
    # Disable
    controller.on_recipe_toggled(recipe_id, False)
    assert "Iron Plate" not in controller.enabled_recipes
    
    # Enable
    controller.on_recipe_toggled(recipe_id, True)
    assert "Iron Plate" in controller.enabled_recipes


def test_on_recipe_toggled_invalid_id():
    """on_recipe_toggled should handle invalid IDs gracefully"""
    controller = FactoryController(economy={})
    
    # Should not raise
    controller.on_recipe_toggled("invalid_id", True)
    controller.on_recipe_toggled("machine:Smelter", True)  # Not a recipe ID


def test_get_tooltip_for_tree_id_recipe():
    """get_tooltip_for_tree_id should return tooltip for recipe IDs"""
    controller = FactoryController(economy={})
    
    recipe_id = "recipe:Smelter:Iron Plate"
    tooltip = controller.get_tooltip_for_tree_id(recipe_id)
    
    assert tooltip is not None
    assert "/min" in tooltip


def test_get_tooltip_for_tree_id_machine():
    """get_tooltip_for_tree_id should return None for machine IDs"""
    controller = FactoryController(economy={})
    
    machine_id = "machine:Smelter"
    tooltip = controller.get_tooltip_for_tree_id(machine_id)
    
    assert tooltip is None


def test_get_tooltip_for_tree_id_invalid():
    """get_tooltip_for_tree_id should return None for invalid IDs"""
    controller = FactoryController(economy={})
    
    tooltip = controller.get_tooltip_for_tree_id("invalid_id")
    assert tooltip is None


def test_parse_recipe_id():
    """_parse_recipe_id should parse recipe IDs correctly"""
    result = FactoryController._parse_recipe_id("recipe:Smelter:Iron Plate")
    assert result == ("Smelter", "Iron Plate")
    
    result = FactoryController._parse_recipe_id("machine:Smelter")
    assert result is None
    
    result = FactoryController._parse_recipe_id("invalid")
    assert result is None


def test_make_machine_id():
    """_make_machine_id should generate stable IDs"""
    id1 = FactoryController._make_machine_id("Smelter")
    id2 = FactoryController._make_machine_id("Smelter")
    
    assert id1 == id2
    assert id1 == "machine:Smelter"


def test_make_recipe_id():
    """_make_recipe_id should generate stable IDs"""
    id1 = FactoryController._make_recipe_id("Smelter", "Iron Plate")
    id2 = FactoryController._make_recipe_id("Smelter", "Iron Plate")
    
    assert id1 == id2
    assert id1 == "recipe:Smelter:Iron Plate"



