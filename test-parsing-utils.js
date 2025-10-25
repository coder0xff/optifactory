import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { parse_material_rate } from './parsing-utils.js';

describe('Parsing Utils', () => {
    it('parse_material_rate parses valid input', () => {
        const [material, rate] = parse_material_rate('Iron Ore:120');
        assert.strictEqual(material, 'Iron Ore');
        assert.strictEqual(rate, 120);
    });

    it('parse_material_rate trims whitespace', () => {
        const [material, rate] = parse_material_rate('  Copper Ore  :  60  ');
        assert.strictEqual(material, 'Copper Ore');
        assert.strictEqual(rate, 60);
    });

    it('parse_material_rate handles decimal rates', () => {
        const [material, rate] = parse_material_rate('Iron Plate:37.5');
        assert.strictEqual(material, 'Iron Plate');
        assert.strictEqual(rate, 37.5);
    });

    it('parse_material_rate handles negative rates', () => {
        const [material, rate] = parse_material_rate('Coal:-30');
        assert.strictEqual(material, 'Coal');
        assert.strictEqual(rate, -30);
    });

    it('parse_material_rate throws on missing colon', () => {
        assert.throws(
            () => parse_material_rate('Iron Ore 120'),
            /Invalid format/
        );
    });

    it('parse_material_rate throws on invalid rate', () => {
        assert.throws(
            () => parse_material_rate('Iron Ore:abc'),
            /Invalid rate/
        );
    });

    it('parse_material_rate throws on empty rate', () => {
        assert.throws(
            () => parse_material_rate('Iron Ore:'),
            /Invalid rate/
        );
    });

    // Tests ported from test_parsing_utils.py

    it('test_parse_material_rate_basic: should parse basic Material:Rate strings', () => {
        const [material, rate] = parse_material_rate("Iron Ore:120");
        assert.strictEqual(material, "Iron Ore");
        assert.strictEqual(rate, 120);
    });

    it('test_parse_material_rate_with_spaces: should handle extra whitespace', () => {
        const [material, rate] = parse_material_rate("  Copper Ingot  :  60.5  ");
        assert.strictEqual(material, "Copper Ingot");
        assert.strictEqual(rate, 60.5);
    });

    it('test_parse_material_rate_float: should handle floating point rates', () => {
        const [material, rate] = parse_material_rate("Water:37.5");
        assert.strictEqual(material, "Water");
        assert.strictEqual(rate, 37.5);
    });

    it('test_parse_material_rate_no_colon: should raise error without colon', () => {
        assert.throws(
            () => parse_material_rate("Iron Ore 120"),
            /Invalid format/
        );
    });

    it('test_parse_material_rate_invalid_rate: should raise error for non-numeric rate', () => {
        assert.throws(
            () => parse_material_rate("Iron Ore:abc"),
            /Invalid rate/
        );
    });

    it('test_parse_material_rate_multiple_colons: should raise error when rate part contains colon', () => {
        assert.throws(
            () => parse_material_rate("Iron:Ore:120"),
            /Invalid rate/
        );
    });

    it('test_parse_material_rate_complex_material_name: should handle complex material names', () => {
        const [material, rate] = parse_material_rate("Alternate Wet Concrete:240");
        assert.strictEqual(material, "Alternate Wet Concrete");
        assert.strictEqual(rate, 240);
    });

    it('test_parse_material_rate_zero: should handle zero rate', () => {
        const [material, rate] = parse_material_rate("Coal:0");
        assert.strictEqual(material, "Coal");
        assert.strictEqual(rate, 0);
    });

    it('test_parse_material_rate_negative: should handle negative rates (consumption)', () => {
        const [material, rate] = parse_material_rate("Power:-100");
        assert.strictEqual(material, "Power");
        assert.strictEqual(rate, -100);
    });
});
