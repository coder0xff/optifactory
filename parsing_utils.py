"""Utility functions for parsing material and rate specifications."""


def _validate_has_colon(text: str) -> None:
    """Validate that text contains a colon separator.
    
    Precondition:
        text is a non-None string
    
    Postcondition:
        raises ValueError if ':' not in text, otherwise returns None
    
    Args:
        text: string to validate
        
    Raises:
        ValueError: if text does not contain a colon
    """
    if ":" not in text:
        raise ValueError(f"Invalid format: '{text}'. Expected 'Material:Rate'")


def _split_material_rate_string(text: str) -> tuple[str, str]:
    """Split text on colon and trim whitespace from both parts.
    
    Precondition:
        text contains at least one colon character
    
    Postcondition:
        returns (material_name, rate_string) where both are stripped of whitespace
    
    Args:
        text: string in format "Material:Rate"
        
    Returns:
        tuple of (material_name, rate_string) with whitespace removed
    """
    material, rate_str = text.split(":", 1)
    return material.strip(), rate_str.strip()


def _parse_rate_value(rate_str: str, material: str) -> float:
    """Convert rate string to float.
    
    Precondition:
        rate_str is a non-None string
        material is a non-None string (used for error messages)
    
    Postcondition:
        returns float value of rate_str
    
    Args:
        rate_str: string representation of a number
        material: material name (for error messages)
        
    Returns:
        float value of rate_str
        
    Raises:
        ValueError: if rate_str cannot be converted to float
    """
    try:
        return float(rate_str)
    except ValueError as exc:
        raise ValueError(
            f"Invalid rate '{rate_str}' for {material}. Must be a number."
        ) from exc


def parse_material_rate(text: str) -> tuple[str, float]:
    """Parse a 'Material:Rate' string into a (material, rate) tuple.
    
    Precondition:
        text is a non-None string in format "Material:Rate"
    
    Postcondition:
        returns (material_name, rate) where material_name is trimmed and rate is a float

    Args:
        text: String in format "Material:Rate" (e.g., "Iron Ore:120")

    Returns:
        Tuple of (material_name, rate)

    Raises:
        ValueError: If format is invalid or rate is not a number
    """
    _validate_has_colon(text)
    material, rate_str = _split_material_rate_string(text)
    rate = _parse_rate_value(rate_str, material)
    return material, rate
