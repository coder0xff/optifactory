"""Tests for factory_cli module."""

import sys
import tempfile
import pytest
from factory import Purity
from factory_cli import parse_material_list, parse_input_list, parse_mine_list, main


def test_parse_material_list_basic():
    """parse_material_list should parse comma-separated material:rate pairs"""
    result = parse_material_list("Iron Plate:100, Copper Wire:50")
    
    assert result == {
        "Iron Plate": 100.0,
        "Copper Wire": 50.0
    }


def test_parse_material_list_empty():
    """parse_material_list should handle empty string"""
    assert parse_material_list("") == {}
    assert parse_material_list("   ") == {}
    assert parse_material_list(None) == {}


def test_parse_material_list_whitespace():
    """parse_material_list should strip whitespace"""
    result = parse_material_list(" Iron Plate : 100 ,  Copper Wire : 50 ")
    
    assert result == {
        "Iron Plate": 100.0,
        "Copper Wire": 50.0
    }


def test_parse_material_list_trailing_comma():
    """parse_material_list should handle trailing comma"""
    result = parse_material_list("Iron Plate:100,")
    
    assert result == {"Iron Plate": 100.0}


def test_parse_input_list_basic():
    """parse_input_list should parse comma-separated material:rate pairs into tuples"""
    result = parse_input_list("Iron Ore:200, Copper Ore:100")
    
    assert result == [
        ("Iron Ore", 200.0),
        ("Copper Ore", 100.0)
    ]


def test_parse_input_list_duplicate():
    """parse_input_list should handle duplicate materials"""
    result = parse_input_list("Iron Ore:200, Iron Ore:200")
    
    assert result == [
        ("Iron Ore", 200.0),
        ("Iron Ore", 200.0)
    ]


def test_parse_input_list_empty():
    """parse_input_list should handle empty string"""
    assert parse_input_list("") == []
    assert parse_input_list("   ") == []
    assert parse_input_list(None) == []


def test_parse_mine_list_basic():
    """parse_mine_list should parse comma-separated resource:purity pairs"""
    result = parse_mine_list("Iron Ore:NORMAL, Copper Ore:PURE")
    
    assert result == [
        ("Iron Ore", Purity.NORMAL),
        ("Copper Ore", Purity.PURE)
    ]


def test_parse_mine_list_lowercase():
    """parse_mine_list should handle lowercase purity"""
    result = parse_mine_list("Iron Ore:normal, Copper Ore:pure")
    
    assert result == [
        ("Iron Ore", Purity.NORMAL),
        ("Copper Ore", Purity.PURE)
    ]


def test_parse_mine_list_all_purities():
    """parse_mine_list should handle all purity levels"""
    result = parse_mine_list("A:IMPURE, B:NORMAL, C:PURE")
    
    assert result == [
        ("A", Purity.IMPURE),
        ("B", Purity.NORMAL),
        ("C", Purity.PURE)
    ]


def test_parse_mine_list_empty():
    """parse_mine_list should handle empty string"""
    assert parse_mine_list("") == []
    assert parse_mine_list("   ") == []
    assert parse_mine_list(None) == []


def test_parse_mine_list_invalid_format():
    """parse_mine_list should raise on invalid format"""
    with pytest.raises(ValueError, match="Invalid format"):
        parse_mine_list("Iron Ore NORMAL")


def test_parse_mine_list_invalid_purity():
    """parse_mine_list should raise on invalid purity"""
    with pytest.raises(ValueError, match="Invalid purity 'MEGA'"):
        parse_mine_list("Iron Ore:MEGA")


def test_main_basic_output(monkeypatch):
    """main should generate factory with basic outputs"""
    monkeypatch.setattr(sys, 'argv', ['factory_cli.py', '--outputs', 'Iron Plate:10'])
    
    result = main()
    
    assert result == 0


def test_main_with_inputs(monkeypatch):
    """main should handle inputs"""
    monkeypatch.setattr(sys, 'argv', [
        'factory_cli.py',
        '--outputs', 'Iron Plate:10',
        '--inputs', 'Iron Ore:100'
    ])
    
    result = main()
    
    assert result == 0


def test_main_with_mines(monkeypatch):
    """main should handle mining nodes"""
    monkeypatch.setattr(sys, 'argv', [
        'factory_cli.py',
        '--outputs', 'Iron Plate:10',
        '--mines', 'Iron Ore:PURE'
    ])
    
    result = main()
    
    assert result == 0


def test_main_with_output_file(monkeypatch):
    """main should write to file when --output-file specified"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.dot', delete=False) as f:
        temp_path = f.name
    
    try:
        monkeypatch.setattr(sys, 'argv', [
            'factory_cli.py',
            '--outputs', 'Iron Plate:10',
            '--output-file', temp_path
        ])
        
        result = main()
        
        assert result == 0
        
        # Verify file was written
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'digraph' in content
            assert 'Iron Plate' in content
    finally:
        import os
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_main_no_outputs(monkeypatch, capsys):
    """main should error when no outputs specified"""
    monkeypatch.setattr(sys, 'argv', [
        'factory_cli.py',
        '--outputs', ''
    ])
    
    result = main()
    
    assert result == 1
    captured = capsys.readouterr()
    assert 'No outputs specified' in captured.err


def test_main_invalid_output_format(monkeypatch, capsys):
    """main should error on invalid output format"""
    monkeypatch.setattr(sys, 'argv', [
        'factory_cli.py',
        '--outputs', 'InvalidFormat'
    ])
    
    result = main()
    
    assert result == 1
    captured = capsys.readouterr()
    assert 'Error:' in captured.err

