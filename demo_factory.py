"""Demonstration of the factory design system with balancers."""

from factory import design_factory, Purity

# Example 1: Simple Iron Plate production with Iron Ore input
print("=" * 60)
print("Example 1: Iron Plate Factory with Iron Ore input")
print("=" * 60)

factory1 = design_factory(
    outputs={"Iron Plate": 100},
    inputs={"Iron Ore": 500},
    mines=[]
)

print(f"Machines needed: {len([n for n in factory1.network.body if 'Machine_' in str(n)])}")
print("Rendering factory_iron_plates.png...")
factory1.network.render("factory_iron_plates", format="png", cleanup=True)
print("Done!\n")

# Example 2: Iron Plate production with a Pure Iron Ore mine
print("=" * 60)
print("Example 2: Iron Plate Factory with Pure Iron Ore Mine")
print("=" * 60)

factory2 = design_factory(
    outputs={"Iron Plate": 100},
    inputs={},
    mines=[("Iron Ore", Purity.PURE)]
)

print(f"Machines needed: {len([n for n in factory2.network.body if 'Machine_' in str(n)])}")
print("Rendering factory_with_mine.png...")
factory2.network.render("factory_with_mine", format="png", cleanup=True)
print("Done!\n")

print("=" * 60)
print("Factory designs complete!")
print("The graphs include:")
print("  - Input/Mine nodes (green/brown)")
print("  - Machine nodes (blue) showing recipes")
print("  - Splitters (yellow diamonds) for distributing materials")
print("  - Mergers (coral diamonds) for combining materials")
print("  - Output nodes (coral)")
print("  - Edges labeled with material names and flow rates")
print("=" * 60)

