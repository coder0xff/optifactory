"""Tests for parsing_utils module"""

from pytest import raises

from parsing_utils import parse_material_rate


def test_parse_material_rate_basic():
    """parse_material_rate should parse basic Material:Rate strings"""
    material, rate = parse_material_rate("Iron Ore:120")
    assert material == "Iron Ore"
    assert rate == 120.0
    
    print(f"✓ Parsed: {material} at {rate}/min")


def test_parse_material_rate_with_spaces():
    """parse_material_rate should handle extra whitespace"""
    material, rate = parse_material_rate("  Copper Ingot : 60.5  ")
    assert material == "Copper Ingot"
    assert rate == 60.5
    
    print(f"✓ Parsed with spaces: {material} at {rate}/min")


def test_parse_material_rate_float():
    """parse_material_rate should handle floating point rates"""
    material, rate = parse_material_rate("Water:37.5")
    assert material == "Water"
    assert rate == 37.5
    
    print(f"✓ Parsed float rate: {material} at {rate}/min")


def test_parse_material_rate_no_colon():
    """parse_material_rate should raise error without colon"""
    with raises(ValueError, match="Invalid format"):
        parse_material_rate("Iron Ore 120")


def test_parse_material_rate_invalid_rate():
    """parse_material_rate should raise error for non-numeric rate"""
    with raises(ValueError, match="Invalid rate"):
        parse_material_rate("Iron Ore:not_a_number")


def test_parse_material_rate_multiple_colons():
    """parse_material_rate should raise error when rate part contains colon"""
    # split(":", 1) splits only on first colon
    # So "Material:With:Colon:100" becomes ("Material", "With:Colon:100")
    # And "With:Colon:100" will fail to parse as float
    with raises(ValueError, match="Invalid rate"):
        parse_material_rate("Material:With:Colon:100")


def test_parse_material_rate_complex_material_name():
    """parse_material_rate should handle complex material names"""
    material, rate = parse_material_rate("Alternate Wet Concrete:240")
    assert material == "Alternate Wet Concrete"
    assert rate == 240.0
    
    print(f"✓ Parsed complex name: {material} at {rate}/min")


def test_parse_material_rate_zero():
    """parse_material_rate should handle zero rate"""
    material, rate = parse_material_rate("Coal:0")
    assert material == "Coal"
    assert rate == 0.0
    
    print(f"✓ Parsed zero rate: {material} at {rate}/min")


def test_parse_material_rate_negative():
    """parse_material_rate should handle negative rates (consumption)"""
    material, rate = parse_material_rate("Power:-100")
    assert material == "Power"
    assert rate == -100.0
    
    print(f"✓ Parsed negative rate: {material} at {rate}/min")

