#!/usr/bin/env python3
"""Command-line interface for factory design."""

import argparse
import sys
import logging

from factory import Purity
from factory_controller import FactoryController
from economy_controller import EconomyController
from parsing_utils import parse_material_rate


def parse_material_list(text):
    """Parse comma-separated Material:Rate pairs.

    Args:
        text: String like "Iron Plate:100, Concrete:480"

    Returns:
        dict of {material: rate}
    """
    if not text or not text.strip():
        return {}

    result = {}
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue

        material, rate = parse_material_rate(item)
        result[material] = rate

    return result


def parse_input_list(text):
    """Parse comma-separated Material:Rate pairs into list of tuples.

    Args:
        text: String like "Iron Ore:200, Iron Ore:200"

    Returns:
        list of (material, rate) tuples
    """
    if not text or not text.strip():
        return []

    result = []
    for item in [stripped for item in text.split(",") if (stripped := item.strip())]:
        material, rate = parse_material_rate(item)
        result.append((material, rate))

    return result


def parse_mine_list(text):
    """Parse comma-separated Resource:Purity pairs.

    Args:
        text: String like "Iron Ore:NORMAL, Copper Ore:PURE"

    Returns:
        list of (resource, Purity) tuples
    """
    if not text or not text.strip():
        return []

    result = []
    for item in [stripped for item in text.split(",") if (stripped := item.strip())]:
        if ":" not in item:
            raise ValueError(f"Invalid format: '{item}'. Expected 'Resource:Purity'")

        resource, purity_str = item.split(":", 1)
        resource = resource.strip()
        purity_str = purity_str.strip().upper()

        try:
            purity = Purity[purity_str]
        except KeyError as exc:
            raise ValueError(
                f"Invalid purity '{purity_str}'. Must be IMPURE, NORMAL, or PURE."
            ) from exc

        result.append((resource, purity))

    return result


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Design Satisfactory factory networks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple concrete factory
  %(prog)s --outputs "Concrete:480"

  # Computer factory with specific inputs
  %(prog)s --outputs "Computer:1.0" --inputs "Crude Oil:150"

  # Multiple outputs
  %(prog)s --outputs "Iron Plate:100, Copper Wire:50"

  # With mining nodes
  %(prog)s --outputs "Iron Plate:100" --mines "Iron Ore:PURE, Iron Ore:NORMAL"
        """,
    )

    parser.add_argument(
        "--outputs",
        "-o",
        required=True,
        help='Desired outputs as "Material:Rate, Material:Rate, ..."',
    )

    parser.add_argument(
        "--inputs",
        "-i",
        default="",
        help='Available inputs as "Material:Rate, Material:Rate, ..." (optional)',
    )

    parser.add_argument(
        "--mines",
        "-m",
        default="",
        help='Mining nodes as "Resource:Purity, Resource:Purity, ..." (optional)',
    )

    parser.add_argument(
        "--output-file", "-f", help="Write graphviz output to file instead of stdout"
    )

    args = parser.parse_args()

    # Setup logging to capture controller messages
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    try:
        # Parse arguments
        outputs = parse_material_list(args.outputs)
        inputs = parse_input_list(args.inputs)
        mines = parse_mine_list(args.mines)

        if not outputs:
            print("Error: No outputs specified", file=sys.stderr)
            return 1

        # Format back to text for controller
        outputs_text = ", ".join(f"{name}:{rate}" for name, rate in outputs.items())
        inputs_text = ", ".join(f"{name}:{rate}" for name, rate in inputs)
        mines_text = ", ".join(f"{name}:{purity.name}" for name, purity in mines)

        # Create controllers
        economy_controller = EconomyController()
        factory_controller = FactoryController(economy_controller.economy)
        
        # Set factory state
        factory_controller.set_outputs_text(outputs_text)
        factory_controller.set_inputs_text(inputs_text)
        factory_controller.set_mines_text(mines_text)

        # Generate factory
        print(f"Designing factory for outputs: {outputs}", file=sys.stderr)
        if inputs:
            print(f"With inputs: {inputs}", file=sys.stderr)
        if mines:
            print(f"With mines: {mines}", file=sys.stderr)

        graphviz_diagram = factory_controller.generate_factory_from_state()
        graphviz_source = graphviz_diagram.source

        # Output graphviz
        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(graphviz_source)
            print(f"\nGraphviz written to {args.output_file}", file=sys.stderr)
        else:
            print("\n" + "=" * 60, file=sys.stderr)
            print(graphviz_source)

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
