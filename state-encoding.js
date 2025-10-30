/**
 * State encoding/decoding utilities for URL sharing
 * Uses LZ-string compression to reduce URL size
 * Uses bitmap encoding for enabled recipes
 */

import { RECIPE_TO_INDEX_V1, RECIPE_INDEX_V1, RECIPE_COUNT } from './recipe-index-v1.js';

// Use lz-string for compression (loaded from CDN in index.html)
// Falls back to uncompressed base64 if lz-string is not available

/**
 * Mapping from format version to recipe index version.
 * This determines which recipe-index-vX.js file to use for bitmap encoding/decoding.
 * 
 * When game recipes change:
 *   1. Generate new recipe index: node scripts/generate-recipe-index.js 2
 *   2. Import it at the top of this file
 *   3. Add a new format version here (e.g., 3: 2)
 *   4. Update getRecipeIndexForFormat() to handle the new version
 *   5. Update encodeStateToBase64() to use the new format version
 * 
 * Trade-off: Format versions are coupled to recipe index versions to save bytes.
 * We can't update one independently, but URLs stay compact.
 */
const RECIPE_INDEX_FOR_FORMAT = {
    1: null,  // Format v1 uses JSON array (no recipe index needed)
    2: 1,     // Format v2 uses recipe-index-v1.js
};

/**
 * Get the appropriate recipe index constants for a given format version.
 * @param {number} formatVersion - the format version
 * @returns {Object} object with RECIPE_TO_INDEX, RECIPE_INDEX, and RECIPE_COUNT
 */
function getRecipeIndexForFormat(formatVersion) {
    const recipeIndexVersion = RECIPE_INDEX_FOR_FORMAT[formatVersion];
    
    if (recipeIndexVersion === null) {
        return null; // No recipe index needed
    }
    
    // Currently only v1 exists, but structured to add more versions easily
    if (recipeIndexVersion === 1) {
        return {
            RECIPE_TO_INDEX: RECIPE_TO_INDEX_V1,
            RECIPE_INDEX: RECIPE_INDEX_V1,
            RECIPE_COUNT: RECIPE_COUNT
        };
    }
    
    throw new Error(`Unknown recipe index version: ${recipeIndexVersion}`);
}

/**
 * Encode an array of recipe names as a bitmap.
 * @param {Array<string>} recipeNames - array of enabled recipe names
 * @returns {string} base64-encoded bitmap
 */
export function encodeRecipeBitmap(recipeNames) {
    // Create a bitmap with one bit per recipe
    const byteCount = Math.ceil(RECIPE_COUNT / 8);
    const bitmap = new Uint8Array(byteCount);
    
    // Set bits for enabled recipes
    for (const recipeName of recipeNames) {
        const index = RECIPE_TO_INDEX_V1.get(recipeName);
        if (index !== undefined) {
            const byteIndex = Math.floor(index / 8);
            const bitIndex = index % 8;
            bitmap[byteIndex] |= (1 << bitIndex);
        }
    }
    
    // Convert to base64
    const binaryString = String.fromCharCode(...bitmap);
    return btoa(binaryString);
}

/**
 * Decode a bitmap back to an array of recipe names using a specific recipe index.
 * @param {string} base64Bitmap - base64-encoded bitmap
 * @param {Object} recipeIndex - recipe index object with RECIPE_INDEX and RECIPE_COUNT
 * @returns {Array<string>} array of enabled recipe names
 */
function decodeRecipeBitmapWithIndex(base64Bitmap, recipeIndex) {
    try {
        // Decode from base64
        const binaryString = atob(base64Bitmap);
        const bitmap = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bitmap[i] = binaryString.charCodeAt(i);
        }
        
        // Extract enabled recipe names
        const enabledRecipes = [];
        for (let i = 0; i < recipeIndex.RECIPE_COUNT; i++) {
            const byteIndex = Math.floor(i / 8);
            const bitIndex = i % 8;
            if (bitmap[byteIndex] & (1 << bitIndex)) {
                enabledRecipes.push(recipeIndex.RECIPE_INDEX[i]);
            }
        }
        
        return enabledRecipes;
    } catch (error) {
        console.error('Failed to decode recipe bitmap:', error);
        return [];
    }
}

/**
 * Decode a bitmap back to an array of recipe names (uses current v1 recipe index).
 * @param {string} base64Bitmap - base64-encoded bitmap
 * @returns {Array<string>} array of enabled recipe names
 */
export function decodeRecipeBitmap(base64Bitmap) {
    return decodeRecipeBitmapWithIndex(base64Bitmap, {
        RECIPE_INDEX: RECIPE_INDEX_V1,
        RECIPE_COUNT: RECIPE_COUNT
    });
}

/**
 * Encode state with compression for URL sharing.
 * Uses bitmap encoding for enabled_recipes to reduce size.
 * @param {Object} state - state object to encode
 * @param {Object} options - encoding options
 * @param {boolean} options.includeEconomy - whether to include economy state (default: false)
 * @returns {string} compressed and encoded state
 */
export function encodeStateToBase64(state, options = {}) {
    const { includeEconomy = false } = options;
    
    // Clone state and optimize it for URL sharing
    const optimizedState = {
        version: 2, // Format version (v2 uses bitmap encoding)
        activeTab: state.activeTab
    };
    
    // Parse and optimize factory state
    if (state.factoryState) {
        try {
            const factoryData = JSON.parse(state.factoryState);
            
            // Convert enabled_recipes array to bitmap
            if (Array.isArray(factoryData.enabled_recipes)) {
                factoryData.enabled_recipes_bitmap = encodeRecipeBitmap(factoryData.enabled_recipes);
                delete factoryData.enabled_recipes;
            }
            
            optimizedState.factoryState = JSON.stringify(factoryData);
        } catch (error) {
            console.warn('Failed to optimize factory state, using original:', error);
            optimizedState.factoryState = state.factoryState;
        }
    }
    
    // Optionally include economy state
    if (includeEconomy && state.economyState) {
        optimizedState.economyState = state.economyState;
    }
    
    const json = JSON.stringify(optimizedState);
    
    // Try to use LZ-string compression if available
    if (typeof window !== 'undefined' && window.LZString) {
        try {
            return 'c:' + window.LZString.compressToEncodedURIComponent(json);
        } catch (error) {
            console.warn('Compression failed, falling back to uncompressed:', error);
        }
    }
    
    // Fallback to uncompressed base64
    return 'u:' + btoa(unescape(encodeURIComponent(json)));
}

/**
 * Decode state from compressed or base64 URL hash.
 * Handles both v1 (JSON array) and v2 (bitmap) formats.
 * Uses the recipe index version specified by RECIPE_INDEX_FOR_FORMAT mapping.
 * @param {string} encodedString - compressed or base64-encoded state
 * @returns {Object|null} decoded state object or null if invalid
 */
export function decodeStateFromBase64(encodedString) {
    try {
        let state;
        
        // Check for format prefix
        if (encodedString.startsWith('c:')) {
            // Compressed format
            const compressed = encodedString.substring(2);
            if (typeof window !== 'undefined' && window.LZString) {
                const json = window.LZString.decompressFromEncodedURIComponent(compressed);
                if (json) {
                    state = JSON.parse(json);
                }
            } else {
                throw new Error('LZ-string library not available for decompression');
            }
        } else if (encodedString.startsWith('u:')) {
            // Uncompressed base64 format
            const base64 = encodedString.substring(2);
            const json = decodeURIComponent(escape(atob(base64)));
            state = JSON.parse(json);
        } else {
            // Legacy format (no prefix) - assume uncompressed base64
            const json = decodeURIComponent(escape(atob(encodedString)));
            state = JSON.parse(json);
        }
        
        if (!state) {
            return null;
        }
        
        // Handle v2+ formats with bitmap encoding
        if (state.version >= 2 && state.factoryState) {
            const recipeIndex = getRecipeIndexForFormat(state.version);
            if (!recipeIndex) {
                throw new Error(`Format version ${state.version} does not support bitmap encoding`);
            }
            
            try {
                const factoryData = JSON.parse(state.factoryState);
                
                // Convert bitmap back to enabled_recipes array using the correct recipe index
                if (factoryData.enabled_recipes_bitmap) {
                    factoryData.enabled_recipes = decodeRecipeBitmapWithIndex(
                        factoryData.enabled_recipes_bitmap,
                        recipeIndex
                    );
                    delete factoryData.enabled_recipes_bitmap;
                    state.factoryState = JSON.stringify(factoryData);
                }
            } catch (error) {
                console.warn('Failed to decode factory state bitmap:', error);
            }
        }
        
        // Convert v2+ format to v1 format for compatibility with rest of application
        if (state.version >= 2) {
            state.version = 1;
        }
        
        return state;
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

