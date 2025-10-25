import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { Factory, design_factory } from './factory.js';
import { Purity, get_recipes_for } from './recipes.js';

describe('Factory', () => {
    it('Factory class can be instantiated', () => {
        const factory = new Factory(null, [], {}, []);
        assert.ok(factory != null);
    });

    it('Factory class has correct properties', () => {
        const network = { test: 'network' };
        const inputs = [['Iron Ore', 100]];
        const outputs = { 'Iron Plate': 50 };
        const mines = [['Iron Ore', Purity.NORMAL]];
        
        const factory = new Factory(network, inputs, outputs, mines);
        
        assert.strictEqual(factory.network, network);
        assert.strictEqual(factory.inputs, inputs);
        assert.strictEqual(factory.outputs, outputs);
        assert.strictEqual(factory.mines, mines);
    });

    it('get_recipes_for works for Iron Plate', () => {
        const recipes = get_recipes_for("Iron Plate");
        assert.ok(recipes != null);
        assert.ok(20.0 in recipes);
    });

    it('design_factory with raw material input', async () => {
        const factory = await design_factory(
            { 'Iron Plate': 100 },
            [['Iron Ore', 500]],
            []
        );

        assert.ok(factory.network != null);
        assert.ok(factory.network.source.length > 0);
        
        // Check that machines were created
        const source = factory.network.source;
        assert.ok(source.includes('Machine_') || source.includes('Smelter'));
    });

    it('design_factory with mining node', async () => {
        const factory = await design_factory(
            { 'Iron Plate': 100 },
            [],
            [['Iron Ore', Purity.PURE]]
        );

        assert.ok(factory.network != null);
        assert.ok(factory.network.source.length > 0);

        // Check that mine was created
        const source = factory.network.source;
        const hasMine = source.includes('Mine_') || source.includes('Miner');
        assert.ok(hasMine);
    });

    it('auto-generates missing raw materials', async () => {
        const factory = await design_factory(
            { 'Iron Plate': 100 },
            [],
            []  // No inputs or mines
        );

        assert.ok(factory.network != null);
        const source = factory.network.source;
        assert.ok(source.includes('Iron Ore'));
        assert.ok(source.toLowerCase().includes('auto'));
    });

    it('Factory dataclass properly populated', async () => {
        const outputs = { 'Iron Plate': 100 };
        const inputs = [['Iron Ore', 500]];
        const mines = [];

        const factory = await design_factory(outputs, inputs, mines);

        // Check that all requested outputs are present
        for (const [material, amount] of Object.entries(outputs)) {
            assert.ok(material in factory.outputs, `Missing requested output: ${material}`);
            assert.ok(
                factory.outputs[material] >= amount,
                `Insufficient output for ${material}: ${factory.outputs[material]} < ${amount}`
            );
        }

        assert.strictEqual(factory.inputs, inputs);
        assert.strictEqual(factory.mines, mines);
        assert.ok(factory.network != null);
    });

    it('automatic raw material detection', async () => {
        const factory = await design_factory(
            { 'Concrete': 480 },
            [],  // No inputs - should auto-detect limestone need
            []
        );

        assert.ok(factory.network != null);
        const source = factory.network.source;

        // Should have auto-generated limestone input
        assert.ok(source.includes('Limestone'));
        assert.ok(source.toLowerCase().includes('auto'));

        // Should have constructor machines
        assert.ok(source.includes('Constructor'));
    });

    it('complex production chain', async () => {
        const factory = await design_factory(
            { 'Iron Plate': 200, 'Copper Ingot': 100 },
            [],
            [['Iron Ore', Purity.NORMAL], ['Copper Ore', Purity.NORMAL]]
        );

        assert.ok(factory.network != null);
        const source = factory.network.source;

        // Should have mine nodes
        assert.ok(source.includes('Mine') || source.includes('Miner'));

        // Should have multiple machines
        assert.ok(source.includes('Smelter') || source.includes('Machine'));
    });

    it('simple single machine case', async () => {
        const factory = await design_factory(
            { 'Iron Plate': 30 },
            [['Iron Ore', 30]],
            []
        );

        assert.ok(factory.network != null);
        assert.ok(factory.network.source.length > 0);
    });

    it('byproduct handling', async () => {
        const factory = await design_factory(
            { 'Fuel': 100 },
            [],
            []
        );

        assert.ok(factory.network != null);
        const source = factory.network.source;
        
        // Should create a valid graph with the primary output
        assert.ok(source.includes('Fuel'));
    });

    it('intermediate and final output', async () => {
        const factory = await design_factory(
            { 'Iron Ingot': 50, 'Iron Plate': 30 },
            [],
            [['Iron Ore', Purity.NORMAL]]
        );

        assert.ok(factory.network != null);
        const source = factory.network.source;
        
        // Both should be in the output
        assert.ok(source.includes('Iron Ingot'));
        assert.ok(source.includes('Iron Plate'));
    });

    it('Computer factory graph properties', async () => {
        const factory = await design_factory(
            { 'Computer': 1 },
            [],
            []
        );

        assert.ok(factory.network != null);
        assert.ok(factory.network.nodes != null);
        
        const nodes = factory.network.nodes;
        const circularShapes = ['circle', 'oval', 'ellipse', 'doublecircle', 'point'];
        
        // Check all nodes
        for (const node of nodes) {
            // Check node is not circular (shape must be set and not circular, since default is oval)
            assert.ok(node.shape, `Node ${node.id} must have shape set (default is oval which is circular)`);
            const isCircular = circularShapes.includes(node.shape.toLowerCase());
            assert.ok(!isCircular, `Node ${node.id} should not have circular shape, got ${node.shape}`)
            
            // Check node has a border (peripheries != 0 and style != invisible)
            if (node.peripheries !== undefined) {
                assert.ok(node.peripheries !== 0 && node.peripheries !== '0', 
                    `Node ${node.id} should have a border (peripheries=${node.peripheries})`);
            }
            if (node.style) {
                const hasNoBorder = node.style === 'invis' || node.style === 'invisible' || 
                                   node.style.includes('invis');
                assert.ok(!hasNoBorder, `Node ${node.id} should have a border (style=${node.style})`);
            }
            
            // Check diamond nodes have empty label
            if (node.shape && node.shape.toLowerCase() === 'diamond') {
                const hasEmptyLabel = !node.label || node.label === '' || node.label === '""';
                assert.ok(hasEmptyLabel, 
                    `Node ${node.id} with diamond shape should have empty label, got "${node.label}"`);
            }
        }
    });
});
