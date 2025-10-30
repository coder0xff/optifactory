import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { design_balancer } from '../balancer.js';

/**
 * Count splitters and mergers in a graph
 * @param {string} graph_source - string representation of the graph
 * @returns {Array} [splitters, mergers]
 */
function count_devices(graph_source) {
    const splitter_matches = graph_source.match(/S\d+/g);
    const merger_matches = graph_source.match(/M\d+/g);
    const splitters = splitter_matches ? new Set(splitter_matches).size : 0;
    const mergers = merger_matches ? new Set(merger_matches).size : 0;
    return [splitters, mergers];
}

describe('Balancer', () => {
    // ====================================================================
    // Tests ported from test_balancer.py
    // ====================================================================

    it('test_basic_split: basic 3-way split', () => {
        const g = design_balancer([100], [40, 30, 30]);
        const [s, m] = count_devices(g.source);
        if (s !== 1 || m !== 0) {
            throw new Error(`Expected 1S + 0M, got ${s}S + ${m}M`);
        }
    });

    it('test_basic_merge: basic 3-way merge', () => {
        const g = design_balancer([50, 30, 20], [100]);
        const [s, m] = count_devices(g.source);
        if (s !== 0 || m !== 1) {
            throw new Error(`Expected 0S + 1M, got ${s}S + ${m}M`);
        }
    });

    it('test_split_and_merge: combined split and merge', () => {
        const g = design_balancer([120, 60], [90, 90]);
        const [s, m] = count_devices(g.source);
        if (s !== 1 || m !== 1) {
            throw new Error(`Expected 1S + 1M, got ${s}S + ${m}M`);
        }
    });

    it('test_perfect_3way_split: perfect 3-way split with equal outputs', () => {
        const g = design_balancer([90], [30, 30, 30]);
        const [s, m] = count_devices(g.source);
        if (s !== 1 || m !== 0) {
            throw new Error(`Expected 1S + 0M, got ${s}S + ${m}M`);
        }
        
        // Verify it's actually a 3-way split (one splitter connected to all 3 outputs)
        if (!g.source.includes("S0 -> O0")) throw new Error("Missing S0 -> O0");
        if (!g.source.includes("S0 -> O1")) throw new Error("Missing S0 -> O1");
        if (!g.source.includes("S0 -> O2")) throw new Error("Missing S0 -> O2");
    });

    it('test_large_example: [480]*3 -> [45]*32', () => {
        const inputs = Array(3).fill(480);
        const outputs = Array(32).fill(45);
        const g = design_balancer(inputs, outputs);
        const [s, m] = count_devices(g.source);
        
        // With 3 inputs going to 32 outputs, each input feeds ~10-11 outputs
        // Optimal splits: for 11 outputs we need ceil((11-1)/2) = 5 splitters per input
        // So roughly 15 splitters total (actual may vary based on exact distribution)
        // The algorithm achieves 16 which is near optimal
        if (s !== 16 || m !== 2) {
            throw new Error(`Expected 16S + 2M, got ${s}S + ${m}M`);
        }
    });

    it('test_optimal_split_counts: split counts are optimal for various output counts', () => {
        for (let n = 2; n < 12; n++) {
            const g = design_balancer([n * 30], Array(n).fill(30));
            const [s, m] = count_devices(g.source);
            const optimal = Math.ceil((n - 1) / 2);
            
            if (s !== optimal || m !== 0) {
                throw new Error(`N=${n}: Expected ${optimal}S + 0M, got ${s}S + ${m}M`);
            }
        }
    });

    it('test_optimal_merge_counts: merge counts are optimal for various input counts', () => {
        for (let n = 2; n < 12; n++) {
            const g = design_balancer(Array(n).fill(30), [n * 30]);
            const [s, m] = count_devices(g.source);
            const optimal = Math.ceil((n - 1) / 2);
            
            if (s !== 0 || m !== optimal) {
                throw new Error(`N=${n}: Expected 0S + ${optimal}M, got ${s}S + ${m}M`);
            }
        }
    });

    it('test_feasibility_check: mismatched flows are rejected', () => {
        try {
            design_balancer([100], [90]);
            throw new Error('Should have raised error for mismatched flows');
        } catch (e) {
            if (!e.message.includes('must equal')) {
                throw new Error('Wrong error message: ' + e.message);
            }
        }
    });

    it('test_direct_connection: direct connection when possible', () => {
        const g = design_balancer([100], [100]);
        const [s, m] = count_devices(g.source);
        if (s !== 0 || m !== 0) {
            throw new Error(`Expected 0S + 0M for direct connection, got ${s}S + ${m}M`);
        }
        if (!g.source.includes("I0 -> O0")) {
            throw new Error("Missing direct I0 -> O0 connection");
        }
    });

    it('test_graph_structure: graph has proper structure with colored nodes', () => {
        const g = design_balancer([120, 60], [90, 90]);
        const source = g.source;
        
        if (!source.includes("fillcolor=lightgreen")) {
            throw new Error("Missing green input nodes");
        }
        if (!source.includes("fillcolor=lightblue")) {
            throw new Error("Missing blue output nodes");
        }
        if (!source.includes("fillcolor=lightyellow")) {
            throw new Error("Missing yellow splitter nodes");
        }
        if (!source.includes("fillcolor=lightcoral")) {
            throw new Error("Missing coral merger nodes");
        }
        if (!source.includes("rankdir=LR")) {
            throw new Error("Missing LR layout");
        }
    });

    it('test_complex_routing: complex routing scenario', () => {
        // 2 inputs to 5 outputs requires splits and merges
        const g = design_balancer([150, 150], [60, 60, 60, 60, 60]);
        const [s, m] = count_devices(g.source);
        
        // Each input feeds 2.5 outputs
        // Input 0 -> 3 outputs needs 1 splitter
        // Input 1 -> 3 outputs needs 1 splitter
        // Some outputs need mergers
        // Total should be around 2 splitters + some mergers
        if (s + m > 5) {
            throw new Error(`Expected <= 5 total devices, got ${s}S + ${m}M = ${s+m}`);
        }
    });

    it('test_two_way_split: simple 2-way split to cover edge cases', () => {
        const g = design_balancer([100], [50, 50]);
        const [s, m] = count_devices(g.source);
        if (s !== 1 || m !== 0) {
            throw new Error(`Expected 1S + 0M, got ${s}S + ${m}M`);
        }
        if (!g.source.includes("I0 -> S0")) {
            throw new Error("Missing I0 -> S0 connection");
        }
        if (!g.source.includes("S0 -> O0")) {
            throw new Error("Missing S0 -> O0 connection");
        }
        if (!g.source.includes("S0 -> O1")) {
            throw new Error("Missing S0 -> O1 connection");
        }
    });

    it('test_single_source_output: single source to single output', () => {
        const g = design_balancer([80], [80]);
        const [s, m] = count_devices(g.source);
        if (!g.source.includes("I0 -> O0")) {
            throw new Error("Missing direct I0 -> O0 connection");
        }
    });
});
