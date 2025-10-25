/**
 * Documentation viewer component with interactive examples
 */

import { design_factory } from './factory.js';
import { get_default_economy } from './economy.js';
import { Purity } from './recipes.js';
import { DiagramViewerComponent } from './diagram-viewer-component.js';

const DocsViewerComponent = {
    components: {
        'diagram-viewer': DiagramViewerComponent
    },
    template: `
        <div class="docs-content">
            <div class="docs-container">
                <h1>Optifactory Documentation</h1>
                
                <div class="docs-intro">
                    <p><strong>Optifactory</strong> is a web-based factory planning tool for Satisfactory. Design mathematically optimal production chains in seconds and visualize factory networks with interactive diagrams.</p>
                </div>

                <!-- Table of Contents -->
                <div class="toc">
                    <h2>Table of Contents</h2>
                    <ul v-if="tocItems.length > 0">
                        <li v-for="item in tocItems" :key="item.id">
                            <a :href="'#' + item.id">{{ item.text }}</a>
                            <ul v-if="item.children.length > 0">
                                <li v-for="child in item.children" :key="child.id">
                                    <a :href="'#' + child.id">{{ child.text }}</a>
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>

                <!-- Introduction -->
                <section id="introduction">
                    <h2>1. Introduction</h2>
                    <h3>Key Features</h3>
                    <ul>
                        <li>Designs complete factory networks including material routing</li>
                        <li>Optimizes for input costs, machine counts, or power consumption</li>
                        <li>Interactive diagrams with zoom and pan</li>
                        <li>Runs entirely in browser (no server required)</li>
                    </ul>
                </section>

                <!-- Getting Started -->
                <section id="getting-started">
                    <h2>2. Quick Start</h2>
                    <p>Optifactory has three tabs:</p>
                    <ul>
                        <li><strong>Factory:</strong> Design production chains</li>
                        <li><strong>Economy:</strong> Adjust item values for optimization</li>
                        <li><strong>Documentation:</strong> View this documentation and interactive examples</li>
                    </ul>
                </section>

                <!-- Factory Tutorial -->
                <section id="factory-tutorial">
                    <h2>3. Factory Tab</h2>

                    <h3 id="defining-outputs">3.1 Outputs</h3>
                    <p>Enter the items you want to produce, one per line.</p>
                    <p><strong>Format:</strong> <code>Material:Rate</code></p>
                    
                    <div class="example-box">
                        <strong>Example:</strong> Produce 20 Plastic per minute from raw resources<br>
                        <strong>Outputs:</strong> <code>Plastic:20</code>
                    </div>
                    <diagram-viewer 
                        :dot-source="example1Dot"
                        :is-loading="isGeneratingExample1"
                        container-ref="example1-output"
                    />

                    <h3 id="adding-inputs">3.2 Inputs (Optional)</h3>
                    <p>Enter materials you want to supply from outside your factory, one per line. Each line represents a separate conveyor or pipe. Leave blank to let the optimizer determine what's needed.</p>
                    <p><strong>Format:</strong> <code>Material:Rate</code></p>
                    
                    <div class="example-box">
                        <strong>Example:</strong> Produce 20 Plastic per minute using supplied Polymer Resin<br>
                        <strong>Outputs:</strong> <code>Plastic:20</code><br>
                        <strong>Inputs:</strong> <code>Polymer Resin:60</code>
                    </div>
                    <diagram-viewer 
                        :dot-source="example2Dot"
                        :is-loading="isGeneratingExample2"
                        container-ref="example2-output"
                    />
                    <p>Notice how providing Polymer Resin as an input simplifies the factory - it no longer needs to produce it from Crude Oil.</p>
                    
                    <div class="example-box">
                        <strong>Multiple outputs and inputs:</strong> You can specify multiple materials, one per line<br>
                        <strong>Outputs:</strong><br>
                        <code>Cable:30</code><br>
                        <code>Wire:30</code><br>
                        <code>Copper Sheet:30</code><br>
                        <strong>Inputs:</strong><br>
                        <code>Water:20</code><br>
                        <code>MWm:100</code><br><br>
                        Note: MWm is megawatt-minutes (power). Since all rates are per minute, 100 MWm means 100 MW of power.
                    </div>
                    <diagram-viewer 
                        :dot-source="example3Dot"
                        :is-loading="isGeneratingExample3"
                        container-ref="example3-output"
                    />

                    <h3 id="selecting-recipes">3.3 Recipe Selection</h3>
                    <p>Use the search box to filter recipes by name. Click machine names to expand and see their recipes. Check or uncheck recipes to enable or disable them.</p>
                    <p><strong>Note:</strong> Power generation recipes (Biomass Burner, Coal Generator, Fuel Generator, etc.) and Packager recipes are disabled by default. Enable them manually if needed.</p>

                    <h3 id="optimization">3.4 Optimization</h3>
                    <p>Use the three sliders to control what the optimizer prioritizes:</p>
                    <ul>
                        <li><strong>Input Costs</strong> - Minimize raw material usage</li>
                        <li><strong>Machine Counts</strong> - Minimize number of machines</li>
                        <li><strong>Power Usage</strong> - Minimize power consumption</li>
                    </ul>
                    <p>Higher values = higher priority. Adjust the sliders to match your goals.</p>

                    <h3 id="power-generation">3.5 Power Generation</h3>
                    <p>Check "Include power in design" to have the optimizer include power generation recipes to meet your factory's power requirements.</p>

                    <h3 id="viewing-diagram">3.6 Viewing the Diagram</h3>
                    <p>Click "Generate Factory" to run the optimizer and display the factory diagram.</p>
                    <p>Once generated, you can:</p>
                    <ul>
                        <li><strong>Zoom:</strong> Mouse wheel</li>
                        <li><strong>Pan:</strong> Click and drag</li>
                        <li><strong>Reset zoom:</strong> Click "Fit" button</li>
                    </ul>
                </section>

                <!-- Economy Tutorial -->
                <section id="economy-tutorial">
                    <h2>4. Economy Tab</h2>
                    <p>The Economy tab computes relative values for all items based on recipe costs. These values guide the optimizer when minimizing input costs.</p>

                    <h3 id="filter">4.1 Filter</h3>
                    <p>Type in the filter box to narrow down the item list.</p>

                    <h3 id="editing-values">4.2 Editing Values</h3>
                    <p>Click in the Value column to edit an item's value. Higher values mean the optimizer will try harder to avoid using that material.</p>

                    <h3 id="pinning-values">4.3 Pinning Values</h3>
                    <p>Check the box in the Locked column to pin a value. Pinned values won't change when you click "Rebalance Values." Use this to prioritize or de-prioritize certain materials.</p>

                    <h3 id="buttons">4.4 Buttons</h3>
                    <ul>
                        <li><strong>Reset to Default</strong> - Recompute all values from recipes, clear all pins</li>
                        <li><strong>Rebalance Values</strong> - Recompute values while keeping pinned values fixed</li>
                        <li><strong>Load CSV</strong> - Load economy from a CSV file</li>
                        <li><strong>Save CSV</strong> - Download economy as a CSV file</li>
                    </ul>
                </section>

                <!-- Tips -->
                <section id="tips">
                    <h2>7. Tips</h2>
                    <ul>
                        <li>Start simple - try basic production chains before complex builds</li>
                        <li>Experiment with optimization weights to find designs you like</li>
                        <li>Disable recipes you haven't unlocked yet</li>
                        <li>Pin strategic resources in the Economy tab to guide optimization</li>
                        <li>Save your economy settings as CSV for different game stages</li>
                    </ul>
                </section>

                <!-- Limitations -->
                <section id="limitations">
                    <h2>8. Known Limitations</h2>
                    <p><strong>No Mine Configuration UI:</strong> The backend supports mines with different purities, but there's no UI to configure them. All examples use Normal purity nodes with Mk.3 miners.</p>
                    <p><strong>Default Recipe Exclusions:</strong> Power generation and Packager recipes are disabled by default. You must manually enable them if needed.</p>
                </section>
            </div>
        </div>
    `,
    data() {
        return {
            example1Dot: null,
            example2Dot: null,
            example3Dot: null,
            simpleExampleDot: null,
            balancerExampleDot: null,
            complexExampleDot: null,
            isGeneratingExample1: true,
            isGeneratingExample2: true,
            isGeneratingExample3: true,
            isGeneratingSimple: true,
            isGeneratingBalancer: true,
            isGeneratingComplex: true,
            economy: null,
            tocItems: []
        };
    },
    async created() {
        // Preload default economy for factory generation
        this.economy = await get_default_economy();
    },
    async mounted() {
        // Generate TOC from rendered content
        this.generateTableOfContents();
        
        // Generate examples automatically after component mounts
        // Do them sequentially to avoid overwhelming the system
        await this.generateExample1();
        await this.generateExample2();
        await this.generateExample3();
    },
    methods: {
        generateTableOfContents() {
            // Find all sections with IDs
            const sections = this.$el.querySelectorAll('section[id]');
            const toc = [];
            
            sections.forEach(section => {
                const id = section.id;
                const h2 = section.querySelector('h2');
                
                if (h2) {
                    const tocItem = {
                        id: id,
                        text: h2.textContent,
                        children: []
                    };
                    
                    // Find all h3 elements with IDs within this section
                    const h3Elements = section.querySelectorAll('h3[id]');
                    h3Elements.forEach(h3 => {
                        tocItem.children.push({
                            id: h3.id,
                            text: h3.textContent
                        });
                    });
                    
                    toc.push(tocItem);
                }
            });
            
            this.tocItems = toc;
        },
        
        async generateExample1() {
            this.isGeneratingExample1 = true;
            this.$emit('status-change', { text: 'Generating Plastic factory (no inputs)...', level: 'info' });
            
            try {
                const outputs = { 'Plastic': 20 };
                const inputs = [];
                const mines = [['Crude Oil', Purity.NORMAL]];
                
                const factory = await design_factory(
                    outputs,
                    inputs,
                    mines,
                    Set(["Plastic"]),
                    this.economy,
                    1.0,
                    0.0,
                    1.0
                );
                
                this.example1Dot = factory.network.source;
                this.$emit('status-change', { text: 'Plastic factory (no inputs) generated!', level: 'info' });
            } catch (error) {
                console.error('Error generating example 1:', error);
                this.$emit('status-change', { text: 'Error: ' + error.message, level: 'error' });
            } finally {
                this.isGeneratingExample1 = false;
            }
        },
        
        async generateExample2() {
            this.isGeneratingExample2 = true;
            this.$emit('status-change', { text: 'Generating Plastic factory (with Polymer Resin input)...', level: 'info' });
            
            try {
                const outputs = { 'Plastic': 20 };
                const inputs = [['Polymer Resin', 60]];
                const mines = [];
                
                const factory = await design_factory(
                    outputs,
                    inputs,
                    mines,
                    null,
                    this.economy,
                    1.0,
                    0.0,
                    1.0
                );
                
                this.example2Dot = factory.network.source;
                this.$emit('status-change', { text: 'Plastic factory (with input) generated!', level: 'info' });
            } catch (error) {
                console.error('Error generating example 2:', error);
                this.$emit('status-change', { text: 'Error: ' + error.message, level: 'error' });
            } finally {
                this.isGeneratingExample2 = false;
            }
        },
        
        async generateExample3() {
            this.isGeneratingExample3 = true;
            this.$emit('status-change', { text: 'Generating multi-output factory...', level: 'info' });
            
            try {
                const outputs = { 
                    'Cable': 30,
                    'Wire': 30,
                    'Copper Sheet': 30
                };
                const inputs = [
                    ['Water', 20],
                    ['MWm', 100]
                ];
                const mines = [];
                
                const factory = await design_factory(
                    outputs,
                    inputs,
                    mines,
                    null,
                    this.economy,
                    1.0,
                    0.0,
                    1.0
                );
                
                this.example3Dot = factory.network.source;
                this.$emit('status-change', { text: 'Multi-output factory generated!', level: 'info' });
            } catch (error) {
                console.error('Error generating example 3:', error);
                this.$emit('status-change', { text: 'Error: ' + error.message, level: 'error' });
            } finally {
                this.isGeneratingExample3 = false;
            }
        },
        
        async generateSimpleExample() {
            this.isGeneratingSimple = true;
            this.$emit('status-change', { text: 'Generating Iron Rod factory...', level: 'info' });
            
            try {
                // outputs is an object mapping item names to rates
                const outputs = { 'Iron Rod': 60 };
                // inputs is an array of [material, rate] tuples
                const inputs = [];
                // mines is an array of [resource, purity] tuples where purity is Purity.NORMAL, etc.
                const mines = [['Iron Ore', Purity.NORMAL]];
                
                const factory = await design_factory(
                    outputs,
                    inputs,
                    mines,
                    Set(["Residual Plastic"]),
                    this.economy,
                    1.0,   // inputCostsWeight
                    0.0,   // machineCountsWeight
                    1.0    // powerConsumptionWeight
                );
                
                // Factory.network is the Digraph object, get DOT source from it
                this.simpleExampleDot = factory.network.source;
                this.$emit('status-change', { text: 'Iron Rod factory generated!', level: 'info' });
            } catch (error) {
                console.error('Error generating simple example:', error);
                this.$emit('status-change', { text: 'Error: ' + error.message, level: 'error' });
            } finally {
                this.isGeneratingSimple = false;
            }
        },
        
        async generateBalancerExample() {
            this.isGeneratingBalancer = true;
            this.$emit('status-change', { text: 'Generating scaled production factory...', level: 'info' });
            
            try {
                // Produce Iron Rods at 240/min - requires multiple machines and demonstrates balancers
                const outputs = { 'Iron Rod': 240 };
                const inputs = [];
                const mines = [
                    ['Iron Ore', Purity.NORMAL],
                    ['Iron Ore', Purity.NORMAL],
                    ['Iron Ore', Purity.NORMAL]
                ];
                
                const factory = await design_factory(
                    outputs,
                    inputs,
                    mines,
                    Set([["Alternate: Pure Copper Ingot", "Copper Ingot", "Wire", "Copper Sheet", "Cable"]]),
                    this.economy,
                    1.0,
                    0.0,
                    1.0
                );
                
                this.balancerExampleDot = factory.network.source;
                this.$emit('status-change', { text: 'Scaled production factory generated!', level: 'info' });
            } catch (error) {
                console.error('Error generating scaling example:', error);
                this.$emit('status-change', { text: 'Error: ' + error.message, level: 'error' });
            } finally {
                this.isGeneratingBalancer = false;
            }
        },
        
        async generateComplexExample() {
            this.isGeneratingComplex = true;
            this.$emit('status-change', { text: 'Generating Reinforced Iron Plate factory...', level: 'info' });
            
            try {
                // outputs is an object mapping item names to rates
                const outputs = { 'Reinforced Iron Plate': 20 };
                // inputs is an array of [material, rate] tuples
                const inputs = [];
                // mines is an array of [resource, purity] tuples where purity is Purity.NORMAL, etc.
                const mines = [
                    ['Iron Ore', Purity.NORMAL],
                    ['Iron Ore', Purity.NORMAL],
                    ['Limestone', Purity.NORMAL]
                ];
                
                const factory = await design_factory(
                    outputs,
                    inputs,
                    mines,
                    null,
                    this.economy,
                    1.0,
                    0.0,
                    1.0
                );
                
                this.complexExampleDot = factory.network.source;
                this.$emit('status-change', { text: 'Reinforced Iron Plate factory generated!', level: 'info' });
            } catch (error) {
                console.error('Error generating complex example:', error);
                this.$emit('status-change', { text: 'Error: ' + error.message, level: 'error' });
            } finally {
                this.isGeneratingComplex = false;
            }
        }
    }
};

export { DocsViewerComponent };

