import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { Digraph, Subgraph } from '../graphviz-builder.js';

describe('GraphvizBuilder', () => {
    // ====================================================================
    // Basic structure tests
    // ====================================================================

    it('Empty graph creates valid DOT', () => {
        const g = new Digraph();
        const source = g.source;
        assert.ok(source.includes('digraph G {'));
        assert.ok(source.includes('}'));
    });

    it('Graph with custom name', () => {
        const g = new Digraph('MyGraph');
        const source = g.source;
        assert.ok(source.includes('digraph MyGraph {'));
    });

    it('Graph attributes are included', () => {
        const g = new Digraph();
        g.attr({ rankdir: 'LR' });
        const source = g.source;
        assert.ok(source.includes('rankdir=LR'));
    });

    it('Multiple graph attributes', () => {
        const g = new Digraph();
        g.attr({ rankdir: 'LR', bgcolor: 'white' });
        const source = g.source;
        assert.ok(source.includes('rankdir=LR'));
        assert.ok(source.includes('bgcolor=white'));
    });

    // ====================================================================
    // Node tests
    // ====================================================================

    it('Simple node with no attributes', () => {
        const g = new Digraph();
        g.node('A', 'Node A');
        const source = g.source;
        assert.ok(source.includes('A [label="Node A"]'));
    });

    it('Node with empty label', () => {
        const g = new Digraph();
        g.node('A', '');
        const source = g.source;
        assert.ok(source.includes('A'));
        assert.ok(source.includes('label=""'));
    });

    it('Node with no label parameter', () => {
        const g = new Digraph();
        g.node('A');
        const source = g.source;
        assert.ok(source.includes('A'));
        assert.ok(!source.includes('label='));
    });

    it('Node with shape attribute', () => {
        const g = new Digraph();
        g.node('A', 'Node A', { shape: 'box' });
        const source = g.source;
        assert.ok(source.includes('shape=box'));
    });

    it('Node with multiple attributes', () => {
        const g = new Digraph();
        g.node('A', 'Input', { shape: 'box', style: 'filled', fillcolor: 'lightgreen' });
        const source = g.source;
        assert.ok(source.includes('label="Input"'));
        assert.ok(source.includes('shape=box'));
        assert.ok(source.includes('style=filled'));
        assert.ok(source.includes('fillcolor=lightgreen'));
    });

    it('Multiple nodes', () => {
        const g = new Digraph();
        g.node('A', 'Node A');
        g.node('B', 'Node B');
        g.node('C', 'Node C');
        const source = g.source;
        assert.ok(source.includes('A [label="Node A"]'));
        assert.ok(source.includes('B [label="Node B"]'));
        assert.ok(source.includes('C [label="Node C"]'));
    });

    it('Node called once appears exactly once in output', () => {
        const g = new Digraph();
        g.node('A', 'Node A');
        const source = g.source;
        
        // Count occurrences of the node definition
        const nodeDefPattern = /A \[label="Node A"\]/g;
        const matches = source.match(nodeDefPattern);
        assert.strictEqual(matches?.length, 1, 'Node should appear exactly once');
    });

    it('Node with attributes called once appears exactly once', () => {
        const g = new Digraph();
        g.node('Test_Node', '', { shape: 'diamond', style: 'filled', fillcolor: 'lightyellow' });
        const source = g.source;
        
        // Count how many times this exact node ID appears as a definition (without quotes since no spaces)
        const nodeDefPattern = /Test_Node \[/g;
        const matches = source.match(nodeDefPattern);
        assert.strictEqual(matches?.length, 1, `Node definition should appear exactly once, found: ${matches?.length || 0}`);
    });

    it('Node with newline in label', () => {
        const g = new Digraph();
        g.node('A', 'Line 1\nLine 2');
        const source = g.source;
        assert.ok(source.includes('label="Line 1\\nLine 2"'));
    });

    // ====================================================================
    // Edge tests
    // ====================================================================

    it('Simple edge with no attributes', () => {
        const g = new Digraph();
        g.node('A', 'Node A');
        g.node('B', 'Node B');
        g.edge('A', 'B');
        const source = g.source;
        assert.ok(source.includes('A -> B'));
    });

    it('Edge with label', () => {
        const g = new Digraph();
        g.edge('A', 'B', { label: '100' });
        const source = g.source;
        assert.ok(source.includes('A -> B [label="100"]'));
    });

    it('Edge with multiple attributes', () => {
        const g = new Digraph();
        g.edge('A', 'B', { label: 'Iron', color: 'red', style: 'bold' });
        const source = g.source;
        assert.ok(source.includes('A -> B'));
        assert.ok(source.includes('label="Iron"'));
        assert.ok(source.includes('color="red"'));
        assert.ok(source.includes('style="bold"'));
    });

    it('Multiple edges', () => {
        const g = new Digraph();
        g.edge('A', 'B', { label: '10' });
        g.edge('B', 'C', { label: '20' });
        g.edge('C', 'A', { label: '30' });
        const source = g.source;
        assert.ok(source.includes('A -> B [label="10"]'));
        assert.ok(source.includes('B -> C [label="20"]'));
        assert.ok(source.includes('C -> A [label="30"]'));
    });

    it('Edge with numeric label zero', () => {
        const g = new Digraph();
        g.edge('A', 'B', { label: 0 });
        const source = g.source;
        assert.ok(source.includes('label=0'));
    });

    // ====================================================================
    // Complete graph tests
    // ====================================================================

    it('Complete graph with nodes, edges, and attributes', () => {
        const g = new Digraph('Factory');
        g.attr({ rankdir: 'LR' });
        g.node('Input', 'Iron Ore', { shape: 'box', fillcolor: 'orange' });
        g.node('Machine', 'Smelter', { shape: 'box', fillcolor: 'lightblue' });
        g.node('Output', 'Iron Ingot', { shape: 'box', fillcolor: 'lightgreen' });
        g.edge('Input', 'Machine', { label: '30' });
        g.edge('Machine', 'Output', { label: '30' });
        
        const source = g.source;
        assert.ok(source.includes('digraph Factory'));
        assert.ok(source.includes('rankdir=LR'));
        assert.ok(source.includes('Input'));
        assert.ok(source.includes('Machine'));
        assert.ok(source.includes('Output'));
        assert.ok(source.includes('Input -> Machine'));
        assert.ok(source.includes('Machine -> Output'));
    });

    it('Graph matches balancer use case', () => {
        const g = new Digraph();
        g.attr({ rankdir: 'LR' });
        g.node('I0', 'Input 0', { shape: 'box', style: 'filled', fillcolor: 'lightgreen' });
        g.node('O0', 'Output 0', { shape: 'box', style: 'filled', fillcolor: 'lightblue' });
        g.node('S0', '', { shape: 'diamond', style: 'filled', fillcolor: 'lightyellow' });
        g.edge('I0', 'S0', { label: '100' });
        g.edge('S0', 'O0', { label: '50' });
        
        const source = g.source;
        assert.ok(source.includes('rankdir=LR'));
        assert.ok(source.includes('shape=box'));
        assert.ok(source.includes('shape=diamond'));
        assert.ok(source.includes('fillcolor=lightgreen'));
        assert.ok(source.includes('I0 -> S0'));
    });

    it('Source property returns string', () => {
        const g = new Digraph();
        g.node('A', 'Node A');
        const source = g.source;
        assert.ok(typeof source === 'string');
        assert.ok(source.length > 0);
    });

    it('Source property can be called multiple times', () => {
        const g = new Digraph();
        g.node('A', 'Node A');
        const source1 = g.source;
        const source2 = g.source;
        assert.ok(source1 === source2);
    });

    it('Edge with penwidth attribute', () => {
        const g = new Digraph();
        g.edge('A', 'B', { penwidth: '2' });
        const source = g.source;
        assert.ok(source.includes('penwidth="2"'));
    });

    it('Edge with color containing colon (stripe colors)', () => {
        const g = new Digraph();
        g.edge('A', 'B', { color: 'black:white:black' });
        const source = g.source;
        assert.ok(source.includes('color="black:white:black"'));
    });

    it('Edge with newline in label', () => {
        const g = new Digraph();
        g.edge('A', 'B', { label: 'Iron Ore\n100' });
        const source = g.source;
        assert.ok(source.includes('label="Iron Ore\\n100"'));
    });

    // ====================================================================
    // Subgraph tests
    // ====================================================================

    it('Simple subgraph with callback', () => {
        const g = new Digraph();
        g.subgraph('cluster_0', (sub) => {
            sub.node('A', 'Node A');
        });
        const source = g.source;
        assert.ok(source.includes('subgraph cluster_0'));
        assert.ok(source.includes('A [label="Node A"]'));
    });

    it('Subgraph without callback (imperative)', () => {
        const g = new Digraph();
        const sub = g.subgraph('cluster_0');
        sub.node('A', 'Node A');
        const source = g.source;
        assert.ok(source.includes('subgraph cluster_0'));
        assert.ok(source.includes('A [label="Node A"]'));
    });

    it('Subgraph with label attribute', () => {
        const g = new Digraph();
        g.subgraph('cluster_0', (sub) => {
            sub.attr({ label: 'My Cluster' });
            sub.node('A', 'Node A');
        });
        const source = g.source;
        assert.ok(source.includes('label="My Cluster"'));
    });

    it('Subgraph with single attr call', () => {
        const g = new Digraph();
        const sub = g.subgraph('cluster_0');
        sub.attr('rank', 'same');
        sub.node('A', 'Node A');
        const source = g.source;
        assert.ok(source.includes('rank="same"'));
    });

    it('Subgraph with style and fillcolor', () => {
        const g = new Digraph();
        g.subgraph('cluster_0', (sub) => {
            sub.attr({ style: 'filled', fillcolor: 'lightblue' });
            sub.node('A', 'Node A');
        });
        const source = g.source;
        assert.ok(source.includes('style="filled"'));
        assert.ok(source.includes('fillcolor="lightblue"'));
    });

    it('Subgraph with empty label', () => {
        const g = new Digraph();
        g.subgraph('cluster_outputs', (sub) => {
            sub.attr({ label: '', style: 'invis' });
        });
        const source = g.source;
        assert.ok(source.includes('label=""'));
        assert.ok(source.includes('style="invis"'));
    });

    it('Nested subgraphs', () => {
        const g = new Digraph();
        g.subgraph('cluster_outer', (outer) => {
            outer.attr({ label: 'Outer' });
            outer.node('A', 'Node A');
            outer.subgraph('cluster_inner', (inner) => {
                inner.attr({ label: 'Inner' });
                inner.node('B', 'Node B');
            });
        });
        const source = g.source;
        assert.ok(source.includes('subgraph cluster_outer'));
        assert.ok(source.includes('subgraph cluster_inner'));
        assert.ok(source.includes('label="Outer"'));
        assert.ok(source.includes('label="Inner"'));
    });

    it('Subgraph with edges', () => {
        const g = new Digraph();
        const sub = g.subgraph('cluster_0');
        sub.node('A', 'Node A');
        sub.node('B', 'Node B');
        sub.edge('A', 'B', { label: '10' });
        const source = g.source;
        assert.ok(source.includes('A -> B [label="10"]'));
    });

    it('Multiple subgraphs', () => {
        const g = new Digraph();
        g.subgraph('cluster_0', (sub) => {
            sub.attr({ label: 'First' });
            sub.node('A', 'Node A');
        });
        g.subgraph('cluster_1', (sub) => {
            sub.attr({ label: 'Second' });
            sub.node('B', 'Node B');
        });
        const source = g.source;
        assert.ok(source.includes('cluster_0'));
        assert.ok(source.includes('cluster_1'));
        assert.ok(source.includes('label="First"'));
        assert.ok(source.includes('label="Second"'));
    });

    it('Factory-style graph with clusters', () => {
        const g = new Digraph('Factory');
        g.attr({ rankdir: 'LR' });
        
        // Inputs subgraph
        g.subgraph('inputs', (inputs) => {
            inputs.attr('rank', 'same');
            inputs.node('Input_0', 'Iron Ore\n120/min', { 
                shape: 'box', 
                style: 'filled', 
                fillcolor: 'orange' 
            });
        });
        
        // Machine cluster
        g.subgraph('cluster_0', (cluster) => {
            cluster.attr({ 
                label: 'Smelter - Iron Ingot\nIron Ore:30\n→ Iron Ingot:30',
                style: 'filled',
                fillcolor: 'lightblue'
            });
            cluster.node('Machine_0', '', { shape: 'box', style: 'filled', fillcolor: 'white' });
        });
        
        // Edge with color and penwidth
        g.edge('Input_0', 'Machine_0', { 
            label: 'Iron Ore\n30', 
            color: 'black:white:black',
            penwidth: '2'
        });
        
        const source = g.source;
        assert.ok(source.includes('digraph Factory'));
        assert.ok(source.includes('rankdir=LR'));
        assert.ok(source.includes('subgraph inputs'));
        assert.ok(source.includes('subgraph cluster_0'));
        assert.ok(source.includes('rank="same"'));
        assert.ok(source.includes('label="Smelter'));
        assert.ok(source.includes('penwidth="2"'));
        assert.ok(source.includes('color="black:white:black"'));
    });

    it('Node IDs with spaces are properly quoted', () => {
        const g = new Digraph();
        g.node('Iron Ore', 'Raw Material', { shape: 'box' });
        g.node('Iron Plate', 'Product', { shape: 'box' });
        g.edge('Iron Ore', 'Iron Plate', { label: '30' });
        
        const source = g.source;
        assert.ok(source.includes('"Iron Ore"'));
        assert.ok(source.includes('"Iron Plate"'));
        assert.ok(source.includes('"Iron Ore" -> "Iron Plate"'));
    });

    it('Special characters are properly escaped', () => {
        const g = new Digraph();
        g.node('A', 'Test\nNewline\tTab\\Backslash"Quote');
        const source = g.source;
        assert.ok(source.includes('\\n'));
        assert.ok(source.includes('\\t'));
        assert.ok(source.includes('\\\\'));
        assert.ok(source.includes('\\"'));
    });
});
