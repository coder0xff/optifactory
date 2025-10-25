/**
 * Utility functions for parsing material and rate specifications.
 */

/**
 * Validate that text contains a colon separator.
 * 
 * Precondition:
 *     text is a non-null string
 * 
 * Postcondition:
 *     throws Error if ':' not in text, otherwise returns undefined
 * 
 * @param {string} text - string to validate
 * @throws {Error} if text does not contain a colon
 */
function _validate_has_colon(text) {
    if (!text.includes(':')) {
        throw new Error(`Invalid format: '${text}'. Expected 'Material:Rate'`);
    }
}

/**
 * Split text on colon and trim whitespace from both parts.
 * 
 * Precondition:
 *     text contains at least one colon character
 * 
 * Postcondition:
 *     returns [material_name, rate_string] where both are stripped of whitespace
 * 
 * @param {string} text - string in format "Material:Rate"
 * @returns {[string, string]} [material_name, rate_string] with whitespace removed
 */
function _split_material_rate_string(text) {
    const colonIndex = text.indexOf(':');
    const material = text.substring(0, colonIndex);
    const rate_str = text.substring(colonIndex + 1);
    return [material.trim(), rate_str.trim()];
}

/**
 * Convert rate string to float.
 * 
 * Precondition:
 *     rate_str is a non-null string
 *     material is a non-null string (used for error messages)
 * 
 * Postcondition:
 *     returns float value of rate_str
 * 
 * @param {string} rate_str - string representation of a number
 * @param {string} material - material name (for error messages)
 * @returns {number} float value of rate_str
 * @throws {Error} if rate_str cannot be converted to float
 */
function _parse_rate_value(rate_str, material) {
    const rate = parseFloat(rate_str);
    if (isNaN(rate)) {
        throw new Error(
            `Invalid rate '${rate_str}' for ${material}. Must be a number.`
        );
    }
    return rate;
}

/**
 * Parse a 'Material:Rate' string into a [material, rate] tuple.
 * 
 * Precondition:
 *     text is a non-null string in format "Material:Rate"
 * 
 * Postcondition:
 *     returns [material_name, rate] where material_name is trimmed and rate is a float
 *
 * @param {string} text - string in format "Material:Rate" (e.g., "Iron Ore:120")
 * @returns {[string, number]} [material_name, rate]
 * @throws {Error} if format is invalid or rate is not a number
 */
export function parse_material_rate(text) {
    _validate_has_colon(text);
    const [material, rate_str] = _split_material_rate_string(text);
    const rate = _parse_rate_value(rate_str, material);
    return [material, rate];
}

