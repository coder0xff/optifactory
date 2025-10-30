import assert from 'node:assert/strict';

/**
 * Assert two floating point values are almost equal (within tolerance)
 * @param {number} actual - actual value
 * @param {number} expected - expected value
 * @param {number} tolerance - allowed difference
 * @param {string} [message] - optional message
 */
export function assertAlmostEqual(actual, expected, tolerance, message) {
    const diff = Math.abs(actual - expected);
    assert.ok(diff <= tolerance, 
        message || `Expected ${actual} ≈ ${expected} (within ${tolerance}), diff was ${diff}`);
}

