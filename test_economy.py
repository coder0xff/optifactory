"""Tests for economy module"""

import os
import tempfile

from economy import (
    compute_item_values,
    get_default_economy,
    save_economy_to_csv,
    load_economy_from_csv,
)


def test_get_default_economy():
    """default economy should return values for all items"""
    economy = get_default_economy()
    assert len(economy) > 0
    assert all(isinstance(v, float) for v in economy.values())
    assert all(v > 0 for v in economy.values())
    print(f"✓ Default economy has {len(economy)} items")


def test_compute_item_values_with_pinning():
    """compute_item_values should accept pinned values and complete successfully"""
    # Get default values
    default_economy = get_default_economy()
    
    # Pin some items to specific values
    # Note: values get normalized at the end, so exact values won't match
    # but pinning influences the gradient descent convergence
    pinned_values = {
        'Iron Ore': 1.0,
        'Copper Ore': 2.0,
    }
    
    # Compute with pinning
    economy = compute_item_values(pinned_values=pinned_values)
    
    # Check that we got values for all items
    assert len(economy) == len(default_economy)
    
    for name, value in pinned_values.items():
        assert economy[name] == value

    # Check that all values are positive
    assert all(v > 0 for v in economy.values())
    
    # Verify the function runs without errors
    print(f"✓ Computed {len(economy)} items with {len(pinned_values)} pinned")


def test_save_and_load_economy():
    """save and load should roundtrip economy data correctly"""
    # Get test data
    economy = get_default_economy()
    pinned_items = {'Iron Ore', 'Copper Ore', 'Coal'}
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        temp_path = f.name
    
    try:
        save_economy_to_csv(temp_path, economy, pinned_items)
        
        # Load it back
        loaded_economy, loaded_pinned = load_economy_from_csv(temp_path)
        
        # Verify data matches
        assert len(loaded_economy) == len(economy)
        assert loaded_pinned == pinned_items
        
        # Check a few specific values
        for item in ['Iron Ore', 'Copper Ore', 'Coal']:
            assert abs(loaded_economy[item] - economy[item]) < 1e-6
        
        print(f"✓ Saved and loaded {len(loaded_economy)} items, {len(loaded_pinned)} pinned")
        
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_csv_format():
    """CSV should have correct format"""
    economy = {'Iron Ore': 1.0, 'Copper Ore': 2.5}
    pinned_items = {'Iron Ore'}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        temp_path = f.name
    
    try:
        save_economy_to_csv(temp_path, economy, pinned_items)
        
        # Read the raw CSV
        with open(temp_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Check header
        assert 'Item' in lines[0]
        assert 'Value' in lines[0]
        assert 'Pinned' in lines[0]
        
        # Check data rows exist
        assert len(lines) >= 3  # header + 2 items
        
        print("✓ CSV format is correct")
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
