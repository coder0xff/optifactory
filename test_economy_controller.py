"""Tests for economy controller"""

import tempfile
import os
from pytest import raises

from economy_controller import EconomyController, EconomyItem, EconomyTableStructure


def test_controller_init():
    """init should create controller with default economy"""
    controller = EconomyController()
    
    assert isinstance(controller, EconomyController)
    assert isinstance(controller.economy, dict)
    assert len(controller.economy) > 0  # should have some items
    assert isinstance(controller.pinned_items, set)
    assert len(controller.pinned_items) == 0  # no items pinned by default
    assert controller.get_filter_text() == ""


def test_get_set_filter_text():
    """controller should manage filter text state"""
    controller = EconomyController()
    assert controller.get_filter_text() == ""
    
    controller.set_filter_text("iron")
    assert controller.get_filter_text() == "iron"


def test_get_sort_state():
    """controller should track sort state"""
    controller = EconomyController()
    
    sort_col, sort_asc = controller.get_sort_state()
    assert sort_col == 'item'
    assert sort_asc is True


def test_set_sort_new_column():
    """set_sort should set new column and default to ascending"""
    controller = EconomyController()
    
    controller.set_sort('value')
    sort_col, sort_asc = controller.get_sort_state()
    
    assert sort_col == 'value'
    assert sort_asc is True


def test_set_sort_toggle_direction():
    """set_sort on same column should toggle direction"""
    controller = EconomyController()
    
    controller.set_sort('value')
    sort_col1, sort_asc1 = controller.get_sort_state()
    
    controller.set_sort('value')  # Same column again
    sort_col2, sort_asc2 = controller.get_sort_state()
    
    assert sort_col1 == sort_col2 == 'value'
    assert sort_asc1 is True
    assert sort_asc2 is False


def test_get_header_texts():
    """get_header_texts should return header display texts with sort indicators"""
    controller = EconomyController()
    
    # Default state (sorted by item ascending)
    texts = controller.get_header_texts()
    assert texts['item'] == 'Item ▲'
    assert texts['value'] == 'Value'
    assert texts['locked'] == 'Locked'
    
    # Click item again to reverse sort
    controller.set_sort('item')
    texts = controller.get_header_texts()
    assert texts['item'] == 'Item ▼'
    assert texts['value'] == 'Value'
    assert texts['locked'] == 'Locked'
    
    # Sort by value descending
    controller.set_sort('value')
    controller.set_sort('value')  # second click reverses
    texts = controller.get_header_texts()
    assert texts['item'] == 'Item'
    assert texts['value'] == 'Value ▼'
    assert texts['locked'] == 'Locked'
    
    # Sort by locked ascending
    controller.set_sort('locked')
    texts = controller.get_header_texts()
    assert texts['item'] == 'Item'
    assert texts['value'] == 'Value'
    assert texts['locked'] == 'Locked ▲'


def test_set_item_value():
    """set_item_value should update economy"""
    controller = EconomyController()
    controller.economy = {"Iron Ore": 1.0}
    
    controller.set_item_value("Iron Ore", 5.0)
    
    assert controller.economy["Iron Ore"] == 5.0


def test_set_item_value_nonexistent():
    """set_item_value should handle nonexistent items gracefully"""
    controller = EconomyController()
    
    # Should not raise or add item
    controller.set_item_value("Nonexistent", 10.0)
    assert "Nonexistent" not in controller.economy


def test_set_item_pinned():
    """set_item_pinned should update pinned state"""
    controller = EconomyController()
    
    controller.set_item_pinned("Iron Ore", True)
    assert "Iron Ore" in controller.pinned_items
    
    controller.set_item_pinned("Iron Ore", False)
    assert "Iron Ore" not in controller.pinned_items


def test_make_item_id():
    """_make_item_id should generate stable IDs"""
    id1 = EconomyController._make_item_id("Iron Ore")
    id2 = EconomyController._make_item_id("Iron Ore")
    
    assert id1 == id2
    assert id1 == "item:Iron Ore"


def test_get_economy_table_structure_basic():
    """get_economy_table_structure should return complete structure"""
    controller = EconomyController()
    controller.economy = {"Iron Ore": 1.0, "Copper Ore": 2.0, "Coal": 0.5}
    controller.pinned_items = {"Iron Ore"}
    
    structure = controller.get_economy_table_structure()
    
    assert len(structure.items) == 3
    assert all(item.item_id.startswith("item:") for item in structure.items)


def test_table_structure_with_filter():
    """table structure should filter items"""
    controller = EconomyController()
    controller.economy = {"Iron Ore": 1.0, "Copper Ore": 2.0, "Coal": 0.5}
    
    controller.set_filter_text("ore")
    structure = controller.get_economy_table_structure()
    
    assert len(structure.items) == 2  # Iron Ore and Copper Ore
    assert all("ore" in item.display_name.lower() for item in structure.items)


def test_table_structure_filter_case_insensitive():
    """table filtering should be case-insensitive"""
    controller = EconomyController()
    controller.economy = {"Iron Ore": 1.0}
    
    controller.set_filter_text("IRON")
    structure = controller.get_economy_table_structure()
    
    assert len(structure.items) == 1


def test_table_structure_sort_by_item():
    """table should sort by item name"""
    controller = EconomyController()
    controller.economy = {"Zinc": 1.0, "Aluminum": 2.0, "Copper": 3.0}
    
    # Default is already sorted by item ascending
    structure = controller.get_economy_table_structure()
    names = [item.display_name for item in structure.items]
    assert names == ["Aluminum", "Copper", "Zinc"]  # Ascending
    
    # Toggle to descending
    controller.set_sort('item')
    structure = controller.get_economy_table_structure()
    names = [item.display_name for item in structure.items]
    assert names == ["Zinc", "Copper", "Aluminum"]  # Descending


def test_table_structure_sort_by_value():
    """table should sort by value"""
    controller = EconomyController()
    controller.economy = {"A": 3.0, "B": 1.0, "C": 2.0}
    
    controller.set_sort('value')
    structure = controller.get_economy_table_structure()
    
    values = [item.value for item in structure.items]
    assert values == [1.0, 2.0, 3.0]  # Ascending


def test_table_structure_sort_by_locked():
    """table should sort by pinned state"""
    controller = EconomyController()
    controller.economy = {"A": 1.0, "B": 2.0, "C": 3.0}
    controller.pinned_items = {"B"}
    
    controller.set_sort('locked')
    structure = controller.get_economy_table_structure()
    
    # Pinned items should come first (or last depending on direction)
    # Check that B is grouped by pinned status
    pinned_states = [item.is_pinned for item in structure.items]
    assert pinned_states == [False, False, True] or pinned_states == [True, False, False]


def test_table_structure_default_sort():
    """table should default to item name sort"""
    controller = EconomyController()
    controller.economy = {"Zinc": 1.0, "Aluminum": 2.0}
    
    structure = controller.get_economy_table_structure()
    
    names = [item.display_name for item in structure.items]
    assert names == ["Aluminum", "Zinc"]


def test_table_structure_includes_metadata():
    """table items should include all metadata"""
    controller = EconomyController()
    controller.economy = {"Iron Ore": 5.0}
    controller.pinned_items = {"Iron Ore"}
    
    structure = controller.get_economy_table_structure()
    
    item = structure.items[0]
    assert item.item_id == "item:Iron Ore"
    assert item.display_name == "Iron Ore"
    assert item.value == 5.0
    assert item.is_pinned is True
    assert item.is_visible is True


def test_reset_to_default():
    """reset_to_default should restore default economy"""
    controller = EconomyController()
    controller.economy = {"Custom": 999.0}
    controller.pinned_items = {"Custom"}
    
    controller.reset_to_default()
    
    # Should have default items
    assert len(controller.economy) > 1
    assert "Custom" not in controller.economy
    assert "Iron Ore" in controller.economy or "Copper Ore" in controller.economy
    assert len(controller.pinned_items) == 0


def test_recompute_values():
    """recompute_values should recalculate with pinned values"""
    controller = EconomyController()
    original_iron_ore = controller.economy.get("Iron Ore", 0)
    controller.pinned_items = {"Iron Ore"}
    
    controller.recompute_values()
    
    # Pinned value should remain the same
    assert controller.economy["Iron Ore"] == original_iron_ore
    # Other values may change (gradient descent)
    assert "Iron Plate" in controller.economy


def test_load_from_csv():
    """load_from_csv should load economy from file"""
    from economy import save_economy_to_csv
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        temp_path = f.name
    
    try:
        # Save some data
        test_economy = {"Iron Ore": 1.0, "Copper Ore": 2.0}
        test_pinned = {"Iron Ore"}
        save_economy_to_csv(temp_path, test_economy, test_pinned)
        
        # Load into controller
        controller = EconomyController()
        
        controller.load_from_csv(temp_path)
        
        assert len(controller.economy) == 2
        assert controller.economy["Iron Ore"] == 1.0
        assert controller.economy["Copper Ore"] == 2.0
        assert controller.pinned_items == {"Iron Ore"}
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_save_to_csv():
    """save_to_csv should save economy to file"""
    controller = EconomyController()
    controller.economy = {"Iron Ore": 1.0, "Copper Ore": 2.0}
    controller.pinned_items = {"Iron Ore"}
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        temp_path = f.name
    
    try:
        controller.save_to_csv(temp_path)
        
        # Verify file was created
        assert os.path.exists(temp_path)
        
        # Load it back to verify
        from economy import load_economy_from_csv
        loaded_economy, loaded_pinned = load_economy_from_csv(temp_path)
        
        assert loaded_economy == controller.economy
        assert loaded_pinned == controller.pinned_items
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_filter_and_sort_combined():
    """filter and sort should work together"""
    controller = EconomyController()
    controller.economy = {"Iron Ore": 3.0, "Iron Plate": 1.0, "Copper Ore": 2.0}
    
    controller.set_filter_text("iron")
    controller.set_sort('value')
    
    structure = controller.get_economy_table_structure()
    
    assert len(structure.items) == 2
    assert structure.items[0].display_name == "Iron Plate"  # Lower value first
    assert structure.items[1].display_name == "Iron Ore"

