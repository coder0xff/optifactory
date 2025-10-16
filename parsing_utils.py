"""Utility functions for parsing material and rate specifications."""


def parse_material_rate(text: str) -> tuple[str, float]:
    """Parse a 'Material:Rate' string into a (material, rate) tuple.

    Args:
        text: String in format "Material:Rate" (e.g., "Iron Ore:120")

    Returns:
        Tuple of (material_name, rate)

    Raises:
        ValueError: If format is invalid or rate is not a number
    """
    if ":" not in text:
        raise ValueError(f"Invalid format: '{text}'. Expected 'Material:Rate'")

    material, rate_str = text.split(":", 1)
    material = material.strip()
    rate_str = rate_str.strip()

    try:
        rate = float(rate_str)
    except ValueError as exc:
        raise ValueError(
            f"Invalid rate '{rate_str}' for {material}. Must be a number."
        ) from exc

    return material, rate
