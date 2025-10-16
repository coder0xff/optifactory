#!/usr/bin/env python3
"""Command-line interface for factory design."""

import argparse
import io
import sys
import traceback

from factory import design_factory, Purity
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
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue

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
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
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

    try:
        # Parse arguments
        outputs = parse_material_list(args.outputs)
        inputs = parse_input_list(args.inputs)
        mines = parse_mine_list(args.mines)

        if not outputs:
            print("Error: No outputs specified", file=sys.stderr)
            return 1

        # Design factory
        print(f"Designing factory for outputs: {outputs}", file=sys.stderr)
        if inputs:
            print(f"With inputs: {inputs}", file=sys.stderr)
        if mines:
            print(f"With mines: {mines}", file=sys.stderr)

        factory = design_factory(outputs, inputs, mines)

        print(f"\nActual outputs produced: {factory.outputs}", file=sys.stderr)

        # Output graphviz
        graphviz_source = factory.network.source

        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(graphviz_source)
            print(f"\nGraphviz written to {args.output_file}", file=sys.stderr)
        else:
            print("\n" + "=" * 60, file=sys.stderr)
            # Use UTF-8 encoding for stdout on Windows
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
            print(graphviz_source)

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
