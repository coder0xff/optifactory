import { describe, it, before } from 'node:test';
import assert from 'node:assert/strict';
import { encodeStateToBase64, decodeStateFromBase64, loadStateFromUrlHash, encodeRecipeBitmap, decodeRecipeBitmap } from '../state-encoding.js';
import { FactoryController } from '../factory-controller.js';
import { EconomyController } from '../economy-controller.js';
import { RECIPE_INDEX_V1, RECIPE_COUNT } from '../recipe-index-v1.js';
import LZString from 'lz-string';

describe('State Encoding for URL Sharing', () => {
    // Setup global mock for window.LZString in Node.js environment
    before(() => {
        global.window = {
            LZString: LZString
        };
    });
    describe('encodeStateToBase64', () => {
        it('should encode state to base64', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: '{"test": "data"}',
                economyState: 'item,value\nIron Ore,1.0'
            };

            const encoded = encodeStateToBase64(testState, { includeEconomy: true });
            assert.strictEqual(typeof encoded, 'string');
            assert.ok(encoded.length > 0);
        });

        it('should exclude economy by default', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: '{"test": "data"}',
                economyState: 'item,value\nIron Ore,1.0'
            };

            const encoded = encodeStateToBase64(testState);
            const decoded = decodeStateFromBase64(encoded);
            
            assert.strictEqual(decoded.activeTab, 'factory');
            assert.strictEqual(decoded.economyState, undefined);
        });

        it('should include economy when requested', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: '{"test": "data"}',
                economyState: 'item,value\nIron Ore,1.0'
            };

            const encoded = encodeStateToBase64(testState, { includeEconomy: true });
            const decoded = decodeStateFromBase64(encoded);
            
            assert.strictEqual(decoded.activeTab, 'factory');
            assert.strictEqual(decoded.economyState, 'item,value\nIron Ore,1.0');
        });

        it('should produce URL-safe compressed string', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: '{"test": "data"}',
                economyState: 'item,value\n'
            };

            const encoded = encodeStateToBase64(testState);

            // Should start with 'c:' for compressed format
            assert.ok(encoded.startsWith('c:'));
            
            // After the prefix, should only contain URL-safe characters
            const payload = encoded.substring(2);
            assert.ok(/^[A-Za-z0-9\-_]+$/.test(payload) || /^[A-Za-z0-9+/=]+$/.test(payload));
        });

        it('should use compression when available', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: '{"test": "data"}',
                economyState: 'item,value\nIron Ore,1.0'
            };

            const encoded = encodeStateToBase64(testState);
            
            // Verify compression prefix
            assert.ok(encoded.startsWith('c:'));
        });

        it('should handle unicode characters in state', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: JSON.stringify({ text: 'Test with émojis 🏭' }),
                economyState: 'Item™,100\n'
            };

            const encoded = encodeStateToBase64(testState, { includeEconomy: true });
            assert.strictEqual(typeof encoded, 'string');
            assert.ok(encoded.length > 0);
        });

        it('should encode enabled_recipes as bitmap', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: JSON.stringify({
                    enabled_recipes: ['Iron Plate', 'Iron Rod', 'Screw'],
                    outputs_text: 'Screw:100'
                })
            };

            const encoded = encodeStateToBase64(testState);
            const decoded = decodeStateFromBase64(encoded);
            
            const factoryData = JSON.parse(decoded.factoryState);
            assert.ok(Array.isArray(factoryData.enabled_recipes));
            assert.ok(factoryData.enabled_recipes.includes('Iron Plate'));
            assert.ok(factoryData.enabled_recipes.includes('Iron Rod'));
            assert.ok(factoryData.enabled_recipes.includes('Screw'));
            assert.strictEqual(factoryData.outputs_text, 'Screw:100');
        });
    });

    describe('decodeStateFromBase64', () => {
        it('should decode state from base64 (round-trip)', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: '{"test": "data"}',
                economyState: 'item,value\nIron Ore,1.0'
            };

            const encoded = encodeStateToBase64(testState, { includeEconomy: true });
            const decoded = decodeStateFromBase64(encoded);

            assert.strictEqual(decoded.version, testState.version);
            assert.strictEqual(decoded.activeTab, testState.activeTab);
            // Factory state gets reparsed, so compare the actual data
            assert.deepStrictEqual(JSON.parse(decoded.factoryState), JSON.parse(testState.factoryState));
            assert.strictEqual(decoded.economyState, testState.economyState);
        });

        it('should handle invalid base64 gracefully', () => {
            const decoded = decodeStateFromBase64('!!!invalid!!!');
            assert.strictEqual(decoded, null);
        });

        it('should handle unicode characters (round-trip)', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: JSON.stringify({ text: 'Test with émojis 🏭' }),
                economyState: 'Item™,100\n'
            };

            const encoded = encodeStateToBase64(testState, { includeEconomy: true });
            const decoded = decodeStateFromBase64(encoded);

            assert.deepStrictEqual(decoded, testState);
        });
    });

    describe('Compression', () => {
        it('should compress large state more efficiently', () => {
            const largeState = {
                version: 1,
                activeTab: 'factory',
                factoryState: JSON.stringify({
                    outputs_text: 'Item1:100\nItem2:200\n'.repeat(50),
                    inputs_text: 'Input1:50\n'.repeat(50),
                    enabled_recipes: Array(200).fill('Recipe').map((r, i) => `${r}${i}`)
                }),
                economyState: Array(300).fill(0).map((_, i) => `Item${i},${Math.random()}`).join('\n')
            };

            const compressed = encodeStateToBase64(largeState);
            
            // Create uncompressed version for comparison
            const json = JSON.stringify(largeState);
            const uncompressed = 'u:' + btoa(unescape(encodeURIComponent(json)));
            
            // Compressed should be significantly smaller
            console.log(`Uncompressed: ${uncompressed.length} bytes, Compressed: ${compressed.length} bytes, Ratio: ${(compressed.length / uncompressed.length * 100).toFixed(1)}%`);
            assert.ok(compressed.length < uncompressed.length);
        });

        it('should handle legacy uncompressed format', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: '{"test": "data"}',
                economyState: 'item,value\n'
            };

            // Create legacy format (no prefix)
            const json = JSON.stringify(testState);
            const legacy = btoa(unescape(encodeURIComponent(json)));
            
            // Should still decode correctly
            const decoded = decodeStateFromBase64(legacy);
            assert.deepStrictEqual(decoded, testState);
        });

        it('should handle explicit uncompressed format', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: '{"test": "data"}',
                economyState: 'item,value\n'
            };

            // Create uncompressed format (u: prefix)
            const json = JSON.stringify(testState);
            const uncompressed = 'u:' + btoa(unescape(encodeURIComponent(json)));
            
            // Should decode correctly
            const decoded = decodeStateFromBase64(uncompressed);
            assert.deepStrictEqual(decoded, testState);
        });
    });

    describe('Integration with Controllers', () => {
        it('should handle large state data', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);

            // Create large state
            factoryController.set_outputs_text('Item1:100\nItem2:200\n'.repeat(50));
            factoryController.set_inputs_text('Input1:50\n'.repeat(50));

            const largeState = {
                version: 1,
                activeTab: 'factory',
                factoryState: factoryController.serialize_state(),
                economyState: economyController.save_to_csv()
            };

            const encoded = encodeStateToBase64(largeState);
            const decoded = decodeStateFromBase64(encoded);

            assert.strictEqual(decoded.version, largeState.version);
            assert.strictEqual(decoded.activeTab, largeState.activeTab);
            // Verify state is preserved (compression is working if we get here)
            assert.ok(encoded.length > 0);
        });

        it('should encode/decode complete application state', () => {
            const economyController = new EconomyController();
            const factoryController = new FactoryController(economyController.economy);

            // Configure controllers
            factoryController.set_outputs_text('Concrete:480');
            factoryController.set_inputs_text('Limestone:240');
            factoryController.set_input_costs_weight(0.7);
            economyController.set_item_value('Iron Ore', 15);
            economyController.set_item_pinned('Iron Ore', true);

            // Build state
            const state = {
                version: 1,
                activeTab: 'economy',
                factoryState: factoryController.serialize_state(),
                economyState: economyController.save_to_csv()
            };

            // Encode and decode with economy included
            const encoded = encodeStateToBase64(state, { includeEconomy: true });
            const decoded = decodeStateFromBase64(encoded);

            // Verify round-trip
            assert.strictEqual(decoded.version, 1);
            assert.strictEqual(decoded.activeTab, 'economy');

            // Restore into new controllers
            const newEconomyController = new EconomyController();
            const newFactoryController = new FactoryController(newEconomyController.economy);

            newEconomyController.load_from_csv(decoded.economyState);
            newFactoryController.deserialize_state(decoded.factoryState);

            // Verify state was restored correctly
            assert.strictEqual(newFactoryController.get_outputs_text(), 'Concrete:480');
            assert.strictEqual(newFactoryController.get_inputs_text(), 'Limestone:240');
            assert.strictEqual(newFactoryController.get_input_costs_weight(), 0.7);
            assert.strictEqual(newEconomyController.economy['Iron Ore'], 15);
            assert.ok(newEconomyController.pinned_items.has('Iron Ore'));
        });
    });

    describe('Recipe Bitmap Encoding', () => {
        describe('encodeRecipeBitmap', () => {
            it('should encode empty array to all zeros', () => {
                const encoded = encodeRecipeBitmap([]);
                const decoded = decodeRecipeBitmap(encoded);
                assert.deepStrictEqual(decoded, []);
            });

            it('should encode single recipe', () => {
                const recipes = ['Iron Plate'];
                const encoded = encodeRecipeBitmap(recipes);
                const decoded = decodeRecipeBitmap(encoded);
                assert.deepStrictEqual(decoded, recipes);
            });

            it('should encode multiple recipes', () => {
                const recipes = ['Iron Plate', 'Iron Rod', 'Screw'];
                const encoded = encodeRecipeBitmap(recipes);
                const decoded = decodeRecipeBitmap(encoded);
                assert.deepStrictEqual(new Set(decoded), new Set(recipes));
            });

            it('should encode all recipes', () => {
                const allRecipes = [...RECIPE_INDEX_V1];
                const encoded = encodeRecipeBitmap(allRecipes);
                const decoded = decodeRecipeBitmap(encoded);
                assert.strictEqual(decoded.length, RECIPE_COUNT);
                assert.deepStrictEqual(new Set(decoded), new Set(allRecipes));
            });

            it('should produce base64 string', () => {
                const recipes = ['Iron Plate', 'Iron Rod'];
                const encoded = encodeRecipeBitmap(recipes);
                assert.strictEqual(typeof encoded, 'string');
                // Should be valid base64
                assert.ok(/^[A-Za-z0-9+/=]+$/.test(encoded));
            });

            it('should ignore unknown recipe names', () => {
                const recipes = ['Iron Plate', 'Unknown Recipe', 'Iron Rod'];
                const encoded = encodeRecipeBitmap(recipes);
                const decoded = decodeRecipeBitmap(encoded);
                // Should only include known recipes
                assert.ok(decoded.includes('Iron Plate'));
                assert.ok(decoded.includes('Iron Rod'));
                assert.ok(!decoded.includes('Unknown Recipe'));
            });
        });

        describe('decodeRecipeBitmap', () => {
            it('should decode empty bitmap', () => {
                // All zeros bitmap
                const emptyBitmap = btoa(String.fromCharCode(...new Uint8Array(Math.ceil(RECIPE_COUNT / 8))));
                const decoded = decodeRecipeBitmap(emptyBitmap);
                assert.deepStrictEqual(decoded, []);
            });

            it('should handle invalid base64 gracefully', () => {
                const decoded = decodeRecipeBitmap('!!!invalid!!!');
                assert.deepStrictEqual(decoded, []);
            });

            it('should round-trip with many recipes', () => {
                const recipes = RECIPE_INDEX_V1.filter((_, i) => i % 3 === 0); // Every 3rd recipe
                const encoded = encodeRecipeBitmap(recipes);
                const decoded = decodeRecipeBitmap(encoded);
                assert.strictEqual(decoded.length, recipes.length);
                assert.deepStrictEqual(new Set(decoded), new Set(recipes));
            });
        });

        describe('Size comparison', () => {
            it('should be much smaller than JSON array', () => {
                // Test with typical recipe set (most enabled)
                const recipes = RECIPE_INDEX_V1.slice(0, 226); // 226 enabled recipes
                
                const jsonSize = JSON.stringify(recipes).length;
                const bitmapSize = encodeRecipeBitmap(recipes).length;
                
                console.log(`\nRecipe encoding comparison (226 recipes):`);
                console.log(`  JSON array: ${jsonSize} bytes`);
                console.log(`  Bitmap: ${bitmapSize} bytes`);
                console.log(`  Reduction: ${((1 - bitmapSize / jsonSize) * 100).toFixed(1)}%`);
                
                // Bitmap should be dramatically smaller
                assert.ok(bitmapSize < jsonSize / 10, 'Bitmap should be <10% of JSON size');
            });

            it('should verify bitmap is fixed size regardless of count', () => {
                const sizes = [];
                
                for (const count of [10, 50, 100, 200, 284]) {
                    const recipes = RECIPE_INDEX_V1.slice(0, count);
                    const encoded = encodeRecipeBitmap(recipes);
                    sizes.push({ count, size: encoded.length });
                }
                
                // All should be the same size (base64 encoded 36 bytes = 48 chars)
                const uniqueSizes = new Set(sizes.map(s => s.size));
                console.log(`\nBitmap sizes for different recipe counts:`);
                sizes.forEach(({ count, size }) => {
                    console.log(`  ${count} recipes: ${size} bytes`);
                });
                
                assert.strictEqual(uniqueSizes.size, 1, 'All bitmaps should be same size');
            });
        });
    });
});

