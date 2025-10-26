/**
 * State encoding/decoding utilities for URL sharing
 */

/**
 * Encode state to base64 for URL sharing.
 * @param {Object} state - state object to encode
 * @returns {string} base64-encoded state
 */
export function encodeStateToBase64(state) {
    const json = JSON.stringify(state);
    return btoa(unescape(encodeURIComponent(json)));
}

/**
 * Decode state from base64 URL hash.
 * @param {string} base64String - base64-encoded state
 * @returns {Object|null} decoded state object or null if invalid
 */
export function decodeStateFromBase64(base64String) {
    try {
        const json = decodeURIComponent(escape(atob(base64String)));
        return JSON.parse(json);
    } catch (error) {
        console.error('Failed to decode state from URL:', error);
        return null;
    }
}

/**
 * Load state from URL hash if present.
 * @returns {Object|null} state object or null if no hash state
 */
export function loadStateFromUrlHash() {
    const hash = window.location.hash;
    if (hash.startsWith('#share=')) {
        const base64State = hash.substring(7); // Remove '#share='
        return decodeStateFromBase64(base64State);
    }
    return null;
}

