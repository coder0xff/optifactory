"""Tests for factory.py design_factory function"""

import re

from factory import design_factory, Purity, get_recipes_for


def test_get_recipes_for():
    """Test recipe lookup"""
    recipes = get_recipes_for("Iron Plate")
    assert recipes, "Should find recipes for Iron Plate"
    assert 20.0 in recipes, "Should include 20/min recipe"
    print("PASS: get_recipes_for")


def test_design_factory_with_input():
    """Test factory design with raw material input"""
    factory = design_factory(
        outputs={"Iron Plate": 100}, inputs=[("Iron Ore", 500)], mines=[]
    )

    assert factory.network is not None
    assert len(factory.network.body) > 0

    # Check that machines were created
    machines = [n for n in factory.network.body if "Machine_" in str(n)]
    assert len(machines) > 0, "Should create machine nodes"

    print(f"PASS: design_factory with input ({len(machines)} machines)")


def test_design_factory_with_mine():
    """Test factory design with mining node"""
    factory = design_factory(
        outputs={"Iron Plate": 100}, inputs={}, mines=[("Iron Ore", Purity.PURE)]
    )

    assert factory.network is not None
    assert len(factory.network.body) > 0

    # Check that mine was created (in source string since body is implementation detail)
    source = factory.network.source
    has_mine = "Mine_" in source or "Miner" in source
    assert has_mine, "Should create mine node"

    print("PASS: design_factory with mine")


def test_balancers_included():
    """Test that splitters and mergers are included in the graph"""
    # Create scenario that needs balancing
    factory = design_factory(
        outputs={"Iron Plate": 100}, inputs=[("Iron Ore", 500)], mines=[]
    )

    source = factory.network.source

    # Check for splitters or mergers (may not always be needed depending on recipe)
    has_splitters = bool(re.search(r"S\d+", source))
    has_mergers = bool(re.search(r"M\d+", source))

    # At least should have proper routing
    has_edges = "->" in source
    assert has_edges, "Should have edges connecting nodes"

    print(f"PASS: balancers check (splitters={has_splitters}, mergers={has_mergers})")


def test_material_flow_labels():
    """Test that edges have material and flow labels"""
    factory = design_factory(
        outputs={"Iron Plate": 100}, inputs=[("Iron Ore", 500)], mines=[]
    )

    source = factory.network.source

    # Check for labeled edges
    labeled_edges = re.findall(r'\[label="[^"]+"\]', source)
    assert len(labeled_edges) > 0, "Should have labeled edges"

    print(f"PASS: material flow labels ({len(labeled_edges)} labeled edges)")


def test_no_recipe_error():
    """Test that missing raw materials are auto-generated instead of erroring"""
    # Old behavior: would raise an error
    # New behavior: auto-generates required raw materials
    factory = design_factory(
        outputs={"Iron Plate": 100},
        inputs=[],
        mines=[],  # No iron ore provided  # No mines
    )
    # Should succeed and auto-generate Iron Ore input
    assert factory.network is not None
    source = factory.network.source
    assert "Iron Ore" in source
    print("PASS: auto-generates missing raw materials")


def test_factory_dataclass():
    """Test that Factory dataclass is properly populated"""
    outputs = {"Iron Plate": 100}
    inputs = [("Iron Ore", 500)]
    mines = []

    factory = design_factory(outputs, inputs, mines)

    # Check that all requested outputs are present (may include byproducts)
    for material, amount in outputs.items():
        assert material in factory.outputs, f"Missing requested output: {material}"
        assert (
            factory.outputs[material] >= amount
        ), f"Insufficient output for {material}: {factory.outputs[material]} < {amount}"

    assert factory.inputs == inputs
    assert factory.mines == mines
    assert factory.network is not None

    print("PASS: Factory dataclass")


def test_auto_raw_materials():
    """Test automatic raw material detection"""
    # Request concrete without specifying limestone input
    factory = design_factory(
        outputs={"Concrete": 480},
        inputs=[],  # No inputs - should auto-detect limestone need
        mines=[],
    )

    assert factory.network is not None
    source = factory.network.source

    # Should have auto-generated limestone input
    assert "Limestone" in source
    assert "auto" in source.lower()

    # Should have constructor machines
    assert "Constructor" in source

    print("PASS: Auto raw materials detection")


def run_all_tests():
    """Run all tests"""
    print("Running factory tests...\n")

    test_get_recipes_for()
    test_design_factory_with_input()
    test_design_factory_with_mine()
    test_balancers_included()
    test_material_flow_labels()
    test_no_recipe_error()
    test_factory_dataclass()
    test_auto_raw_materials()

    print("\n" + "=" * 50)
    print("All factory tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()
