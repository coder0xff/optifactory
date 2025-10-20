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
    """Parse comma-separated Material:Rate pairs into a dictionary.

    Precondition:
        text is a string (may be empty or whitespace-only)

    Postcondition:
        returns dict mapping material names to rates
        empty/whitespace text returns empty dict
        duplicate materials will have last rate win

    Args:
        text: String like "Iron Plate:100, Concrete:480"

    Returns:
        dict of {material_name: rate}

    Raises:
        ValueError: if any item has invalid Material:Rate format
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

    Precondition:
        text is a string (may be empty or whitespace-only)

    Postcondition:
        returns list of (material_name, rate) tuples
        empty/whitespace text returns empty list
        preserves duplicates (unlike parse_material_list)
        order is preserved from input

    Args:
        text: String like "Iron Ore:200, Iron Ore:200"

    Returns:
        list of (material_name, rate) tuples

    Raises:
        ValueError: if any item has invalid Material:Rate format
    """
    if not text or not text.strip():
        return []

    result = []
    for item in [stripped for item in text.split(",") if (stripped := item.strip())]:
        material, rate = parse_material_rate(item)
        result.append((material, rate))

    return result


def _parse_resource_purity_pair(item: str) -> tuple[str, Purity]:
    """Parse a single Resource:Purity pair.

    Precondition:
        item is a non-empty, non-whitespace string

    Postcondition:
        returns (resource_name, Purity_enum)
        resource name is trimmed
        purity is converted to Purity enum

    Args:
        item: string like "Iron Ore:NORMAL"

    Returns:
        tuple of (resource_name, Purity)

    Raises:
        ValueError: if format is invalid or purity is not recognized
    """
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

    return resource, purity


def parse_mine_list(text):
    """Parse comma-separated Resource:Purity pairs.

    Precondition:
        text is a string (may be empty or whitespace-only)

    Postcondition:
        returns list of (resource_name, Purity) tuples
        empty/whitespace text returns empty list
        preserves duplicates and order
        purity strings are case-insensitive

    Args:
        text: String like "Iron Ore:NORMAL, Copper Ore:PURE"

    Returns:
        list of (resource_name, Purity) tuples

    Raises:
        ValueError: if any item has invalid format or purity
    """
    if not text or not text.strip():
        return []

    result = []
    for item in [stripped for item in text.split(",") if (stripped := item.strip())]:
        resource, purity = _parse_resource_purity_pair(item)
        result.append((resource, purity))

    return result


def _print_design_info(outputs: dict, inputs: list, mines: list) -> None:
    """Print information about the factory design to stderr.

    Precondition:
        outputs is a dict of material -> rate
        inputs is a list of (material, rate) tuples
        mines is a list of (resource, Purity) tuples

    Postcondition:
        design information is printed to stderr

    Args:
        outputs: dict of output materials and rates
        inputs: list of input tuples
        mines: list of mine tuples
    """
    print(f"Designing factory for outputs: {outputs}", file=sys.stderr)
    if inputs:
        print(f"With inputs: {inputs}", file=sys.stderr)
    if mines:
        print(f"With mines: {mines}", file=sys.stderr)


def _generate_factory_design(outputs: dict, inputs: list, mines: list) -> str:
    """Generate factory design and return graphviz source.

    Precondition:
        outputs is a non-empty dict of material -> rate
        inputs is a list of (material, rate) tuples
        mines is a list of (resource, Purity) tuples

    Postcondition:
        returns graphviz source string for factory design
        controllers are created and configured

    Args:
        outputs: dict of output materials and rates
        inputs: list of input tuples
        mines: list of mine tuples

    Returns:
        graphviz source string

    Raises:
        ValueError: if factory generation fails
    """
    # Format to text for controller
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

    # Generate and return graphviz source
    graphviz_diagram = factory_controller.generate_factory_from_state()
    return graphviz_diagram.source


def _output_graphviz(graphviz_source: str, output_file: str | None) -> None:
    """Write graphviz source to file or stdout.

    Precondition:
        graphviz_source is a non-empty string
        output_file is either None or a valid file path

    Postcondition:
        graphviz source is written to file or stdout
        success message is printed to stderr if file written

    Args:
        graphviz_source: graphviz source code to output
        output_file: optional file path to write to (None = stdout)
    """
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(graphviz_source)
        print(f"\nGraphviz written to {output_file}", file=sys.stderr)
    else:
        print("\n" + "=" * 60, file=sys.stderr)
        print(graphviz_source)


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the CLI argument parser.

    Precondition:
        none

    Postcondition:
        returns configured ArgumentParser with all CLI arguments defined

    Returns:
        ArgumentParser instance ready to parse command-line arguments
    """
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

    return parser


def main():
    """Main CLI function.

    Precondition:
        command-line arguments are available via sys.argv

    Postcondition:
        factory design is generated and output
        returns 0 on success, 1 on error
        graphviz output is written to file or stdout

    Returns:
        exit code (0=success, 1=error)
    """
    parser = _create_argument_parser()
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

        # Format and generate
        _print_design_info(outputs, inputs, mines)
        graphviz_source = _generate_factory_design(outputs, inputs, mines)
        _output_graphviz(graphviz_source, args.output_file)

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
