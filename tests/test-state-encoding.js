import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { encodeStateToBase64, decodeStateFromBase64, loadStateFromUrlHash } from '../state-encoding.js';
import { FactoryController } from '../factory-controller.js';
import { EconomyController } from '../economy-controller.js';

describe('State Encoding for URL Sharing', () => {
    describe('encodeStateToBase64', () => {
        it('should encode state to base64', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: '{"test": "data"}',
                economyState: 'item,value\nIron Ore,1.0'
            };

            const encoded = encodeStateToBase64(testState);
            assert.strictEqual(typeof encoded, 'string');
            assert.ok(encoded.length > 0);
        });

        it('should produce URL-safe base64', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: '{"test": "data"}',
                economyState: 'item,value\n'
            };

            const encoded = encodeStateToBase64(testState);

            // Base64 should only contain alphanumeric, +, /, and =
            assert.ok(/^[A-Za-z0-9+/=]+$/.test(encoded));
        });

        it('should handle unicode characters in state', () => {
            const testState = {
                version: 1,
                activeTab: 'factory',
                factoryState: JSON.stringify({ text: 'Test with émojis 🏭' }),
                economyState: 'Item™,100\n'
            };

            const encoded = encodeStateToBase64(testState);
            assert.strictEqual(typeof encoded, 'string');
            assert.ok(encoded.length > 0);
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

            const encoded = encodeStateToBase64(testState);
            const decoded = decodeStateFromBase64(encoded);

            assert.strictEqual(decoded.version, testState.version);
            assert.strictEqual(decoded.activeTab, testState.activeTab);
            assert.strictEqual(decoded.factoryState, testState.factoryState);
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

            const encoded = encodeStateToBase64(testState);
            const decoded = decodeStateFromBase64(encoded);

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
            // Verify it's actually large
            assert.ok(encoded.length > 1000);
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

            // Encode and decode
            const encoded = encodeStateToBase64(state);
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
});

