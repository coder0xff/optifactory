"""Tests for path.py split_merge_path function"""

from path import split_merge_path
import re
import math


def count_devices(graph_source):
    """Count splitters and mergers in a graph"""
    splitters = len(set(re.findall(r'S\d+', graph_source)))
    mergers = len(set(re.findall(r'M\d+', graph_source)))
    return splitters, mergers


def test_basic_split():
    """Test basic 3-way split"""
    g = split_merge_path([100], [40, 30, 30])
    s, m = count_devices(g.source)
    assert s == 1 and m == 0, f"Expected 1S + 0M, got {s}S + {m}M"
    print("PASS: Basic split test")


def test_basic_merge():
    """Test basic 3-way merge"""
    g = split_merge_path([50, 30, 20], [100])
    s, m = count_devices(g.source)
    assert s == 0 and m == 1, f"Expected 0S + 1M, got {s}S + {m}M"
    print("PASS: Basic merge test")


def test_split_and_merge():
    """Test combined split and merge"""
    g = split_merge_path([120, 60], [90, 90])
    s, m = count_devices(g.source)
    assert s == 1 and m == 1, f"Expected 1S + 1M, got {s}S + {m}M"
    print("PASS: Split and merge test")


def test_perfect_3way_split():
    """Test perfect 3-way split with equal outputs"""
    g = split_merge_path([90], [30, 30, 30])
    s, m = count_devices(g.source)
    assert s == 1 and m == 0, f"Expected 1S + 0M, got {s}S + {m}M"
    
    # Verify it's actually a 3-way split (one splitter connected to all 3 outputs)
    assert 'S0 -> O0' in g.source
    assert 'S0 -> O1' in g.source
    assert 'S0 -> O2' in g.source
    print("PASS: Perfect 3-way split test")


def test_large_example():
    """Test the large example: [480]*3 -> [45]*32"""
    g = split_merge_path([480]*3, [45]*32)
    s, m = count_devices(g.source)
    
    # With 3 inputs going to 32 outputs, each input feeds ~10-11 outputs
    # Optimal splits: for 11 outputs we need ceil((11-1)/2) = 5 splitters per input
    # So roughly 15 splitters total (actual may vary based on exact distribution)
    # The algorithm achieves 16 which is near optimal
    assert s == 16 and m == 2, f"Expected 16S + 2M, got {s}S + {m}M"
    print("PASS: Large example test")


def test_optimal_split_counts():
    """Test that split counts are optimal for various output counts"""
    print("\nTesting optimal split counts:")
    
    for n in range(2, 12):
        g = split_merge_path([n*30], [30]*n)
        s, m = count_devices(g.source)
        optimal = math.ceil((n-1)/2)
        
        assert s == optimal and m == 0, \
            f"N={n}: Expected {optimal}S + 0M, got {s}S + {m}M"
        print(f"  N={n:2d} outputs: {s} splitters (optimal)")
    
    print("PASS: All optimal split count tests")


def test_optimal_merge_counts():
    """Test that merge counts are optimal for various input counts"""
    print("\nTesting optimal merge counts:")
    
    for n in range(2, 12):
        g = split_merge_path([30]*n, [n*30])
        s, m = count_devices(g.source)
        optimal = math.ceil((n-1)/2)
        
        assert s == 0 and m == optimal, \
            f"N={n}: Expected 0S + {optimal}M, got {s}S + {m}M"
        print(f"  N={n:2d} inputs: {m} mergers (optimal)")
    
    print("PASS: All optimal merge count tests")


def test_feasibility_check():
    """Test that mismatched flows are rejected"""
    try:
        split_merge_path([100], [90])
        assert False, "Should have raised ValueError for mismatched flows"
    except ValueError as e:
        assert "must equal" in str(e)
        print("PASS: Feasibility check test")


def test_direct_connection():
    """Test direct connection when possible"""
    g = split_merge_path([100], [100])
    s, m = count_devices(g.source)
    assert s == 0 and m == 0, f"Expected 0S + 0M for direct connection, got {s}S + {m}M"
    assert 'I0 -> O0' in g.source
    print("PASS: Direct connection test")


def test_graph_structure():
    """Test graph has proper structure with colored nodes"""
    g = split_merge_path([120, 60], [90, 90])
    source = g.source
    
    # Check for input nodes (green)
    assert 'fillcolor=lightgreen' in source, "Missing green input nodes"
    
    # Check for output nodes (blue)
    assert 'fillcolor=lightblue' in source, "Missing blue output nodes"
    
    # Check for splitter (yellow)
    assert 'fillcolor=lightyellow' in source, "Missing yellow splitter nodes"
    
    # Check for merger (coral)
    assert 'fillcolor=lightcoral' in source, "Missing coral merger nodes"
    
    # Check for left-to-right layout
    assert 'rankdir=LR' in source, "Missing LR layout"
    
    print("PASS: Graph structure test")


def test_complex_routing():
    """Test a complex routing scenario"""
    # 2 inputs to 5 outputs requires splits and merges
    g = split_merge_path([150, 150], [60, 60, 60, 60, 60])
    s, m = count_devices(g.source)
    
    # Each input feeds 2.5 outputs
    # Input 0 -> 3 outputs needs 1 splitter
    # Input 1 -> 3 outputs needs 1 splitter  
    # Some outputs need mergers
    # Total should be around 2 splitters + some mergers
    assert s + m <= 5, f"Expected <= 5 total devices, got {s}S + {m}M = {s+m}"
    print(f"PASS: Complex routing test ({s}S + {m}M)")


def run_all_tests():
    """Run all tests"""
    print("Running split_merge_path tests...\n")
    
    test_basic_split()
    test_basic_merge()
    test_split_and_merge()
    test_perfect_3way_split()
    test_direct_connection()
    test_feasibility_check()
    test_graph_structure()
    test_optimal_split_counts()
    test_optimal_merge_counts()
    test_complex_routing()
    test_large_example()
    
    print("\n" + "="*50)
    print("All tests passed!")
    print("="*50)


if __name__ == "__main__":
    run_all_tests()

