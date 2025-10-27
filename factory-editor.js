/**
 * FactoryView - Reusable Vue component for factory design
 * Requires: FactoryController, GraphvizViewerComponent
 */
import { GraphvizViewerComponent } from './graphviz-viewer.js';

const FactoryViewComponent = {
    template: `
        <div class="factory-editor">
            <div class="control-panel">
                <!-- Outputs Section -->
                <div class="section">
                    <div class="section-title">Desired Outputs:</div>
                    <div class="section-hint">Format: Material:Rate</div>
                    <div class="section-hint">Example: Concrete:480</div>
                    <textarea v-model="outputsText" @input="onOutputsChanged"></textarea>
                </div>

                <!-- Inputs Section -->
                <div class="section">
                    <div class="section-title">Available Inputs (optional):</div>
                    <div class="section-hint">One per line for separate conveyors</div>
                    <div class="section-hint">Example: Limestone:480</div>
                    <textarea v-model="inputsText" @input="onInputsChanged"></textarea>
                </div>

                <!-- Recipe Filter Section -->
                <div class="section">
                    <div class="section-title">Recipe Filter:</div>
                    <input 
                        type="text" 
                        v-model="recipeSearchText" 
                        @input="onSearchChanged"
                        placeholder="Search recipes..."
                    >
                    <div class="tree-container">
                        <template v-for="machine in treeStructure" :key="machine.tree_id">
                            <div v-if="machine.is_visible">
                                <div class="tree-node tree-machine" @click="toggleMachine(machine.tree_id)">
                                    <span class="tree-expand">{{ machine.expanded ? '▼' : '▶' }}</span>
                                    <input 
                                        type="checkbox" 
                                        class="tree-checkbox"
                                        :checked="machine.check_state === 'checked'"
                                        :indeterminate.prop="machine.check_state === 'tristate'"
                                        @click.stop
                                        @change="toggleMachineCheck(machine)"
                                    >
                                    <span>{{ machine.display_name }}</span>
                                </div>
                                <template v-if="machine.expanded">
                                    <template v-for="recipe in machine.recipes" :key="recipe ? recipe.tree_id : Math.random()">
                                        <div 
                                            v-if="recipe && recipe.is_visible"
                                            class="tree-node tree-recipe"
                                            :title="getRecipeTooltip(recipe.tree_id)"
                                        >
                                            <input 
                                                type="checkbox" 
                                                class="tree-checkbox"
                                                :checked="recipe.is_enabled"
                                                @change="toggleRecipe(recipe.tree_id)"
                                            >
                                            <span>{{ recipe.display_name }}</span>
                                        </div>
                                    </template>
                                </template>
                            </div>
                        </template>
                    </div>
                </div>

                <!-- Optimization Weights Section -->
                <div class="section">
                    <div class="section-title">Optimize For:</div>
                    
                    <div class="slider-container tooltip">
                        <div class="slider-header">
                            <span class="slider-label">Input Costs:</span>
                            <span class="slider-value">{{ inputCostsWeight.toFixed(2) }}</span>
                        </div>
                        <input 
                            type="range" 
                            min="0" 
                            max="1" 
                            step="0.01" 
                            v-model.number="inputCostsWeight"
                            @input="onWeightChanged"
                        >
                        <span class="tooltip-text">prioritize minimizing raw material usage from inputs</span>
                    </div>

                    <div class="slider-container tooltip">
                        <div class="slider-header">
                            <span class="slider-label">Machine Counts:</span>
                            <span class="slider-value">{{ machineCountsWeight.toFixed(2) }}</span>
                        </div>
                        <input 
                            type="range" 
                            min="0" 
                            max="1" 
                            step="0.01" 
                            v-model.number="machineCountsWeight"
                            @input="onWeightChanged"
                        >
                        <span class="tooltip-text">prioritize fewer machines</span>
                    </div>

                    <div class="slider-container tooltip">
                        <div class="slider-header">
                            <span class="slider-label">Power Usage:</span>
                            <span class="slider-value">{{ powerConsumptionWeight.toFixed(2) }}</span>
                        </div>
                        <input 
                            type="range" 
                            min="0" 
                            max="1" 
                            step="0.01" 
                            v-model.number="powerConsumptionWeight"
                            @input="onWeightChanged"
                        >
                        <span class="tooltip-text">prioritize minimizing power consumption</span>
                    </div>
                </div>

                <!-- Design Power Section -->
                <div class="section">
                    <div class="checkbox-container">
                        <input 
                            type="checkbox" 
                            id="design-power"
                            v-model="designPower"
                            @change="onDesignPowerChanged"
                        >
                        <label for="design-power">Include power in design</label>
                    </div>
                    <div class="checkbox-container">
                        <input 
                            type="checkbox" 
                            id="disable-balancers"
                            v-model="disableBalancers"
                            @change="onDisableBalancersChanged"
                        >
                        <label for="disable-balancers">Disable balancers (use simple hubs)</label>
                    </div>
                    <div v-if="showPowerWarning" class="warning">
                        Warning: No power-generating recipes are enabled
                    </div>
                    <div v-if="showConverterWarning" class="warning">
                        Warning: Disable converter recipes if factory design is too slow
                    </div>
                </div>

                <!-- Action Buttons -->
                <button @click="generateFactory" :disabled="isGenerating">
                    {{ isGenerating ? 'Generating...' : 'Generate Factory' }}
                </button>
                <button class="button-secondary" @click="copyGraphviz">
                    Copy Graphviz to Clipboard
                </button>
                
                <!-- Save/Load Buttons -->
                <div class="button-group">
                    <button class="button-secondary" @click="saveState">
                        Save Design
                    </button>
                    <button class="button-secondary" @click="triggerLoadState">
                        Load Design
                    </button>
                    <input 
                        type="file" 
                        ref="fileInput" 
                        @change="loadState" 
                        accept=".json"
                        style="display: none;"
                    >
                </div>
            </div>

            <div class="viewer-panel">
                <graphviz-viewer
                    :dot-source="dotSource"
                    :placeholder="placeholder || 'Graph visualization will appear here'"
                    @status-change="handleStatusChange"
                ></graphviz-viewer>
            </div>
        </div>
    `,
    components: {
        'graphviz-viewer': GraphvizViewerComponent
    },
    props: {
        controller: {
            type: Object,
            required: true
        },
        placeholder: {
            type: String,
            default: ''
        }
    },
    emits: ['statusChange', 'stateChange'],
    data() {
        return {
            outputsText: '',
            inputsText: '',
            recipeSearchText: '',
            treeStructure: [],
            inputCostsWeight: 1.0,
            machineCountsWeight: 0.0,
            powerConsumptionWeight: 1.0,
            designPower: false,
            disableBalancers: false,
            showPowerWarning: false,
            showConverterWarning: false,
            isGenerating: false
        };
    },
    computed: {
        dotSource() {
            return this.controller.get_graphviz_source();
        }
    },
    mounted() {
        this.outputsText = this.controller.get_outputs_text();
        this.inputsText = this.controller.get_inputs_text();
        this.recipeSearchText = this.controller.get_recipe_search_text();
        this.inputCostsWeight = this.controller.get_input_costs_weight();
        this.machineCountsWeight = this.controller.get_machine_counts_weight();
        this.powerConsumptionWeight = this.controller.get_power_consumption_weight();
        this.designPower = this.controller.get_design_power();
        this.disableBalancers = this.controller.get_disable_balancers();
        this.refreshTreeView();
        this.updatePowerWarning();
        this.updateConverterWarning();
    },
    methods: {
        setStatus(text, level = 'info') {
            this.$emit('statusChange', { text, level });
        },
        handleStatusChange(event) {
            this.$emit('statusChange', event);
        },
        refreshTreeView() {
            const structure = this.controller.get_recipe_tree_structure();
            const oldExpanded = new Map();
            for (const machine of this.treeStructure) {
                oldExpanded.set(machine.tree_id, machine.expanded);
            }
            
            // Structure has a .machines property
            for (const machine of structure.machines) {
                machine.expanded = oldExpanded.get(machine.tree_id) || false;
            }
            
            this.treeStructure = structure.machines;
        },
        onOutputsChanged() {
            this.controller.set_outputs_text(this.outputsText);
            this.$emit('stateChange');
        },
        onInputsChanged() {
            this.controller.set_inputs_text(this.inputsText);
            this.$emit('stateChange');
        },
        onSearchChanged() {
            this.controller.set_recipe_search_text(this.recipeSearchText);
            this.refreshTreeView();
            this.$emit('stateChange');
        },
        onWeightChanged() {
            this.controller.set_input_costs_weight(this.inputCostsWeight);
            this.controller.set_machine_counts_weight(this.machineCountsWeight);
            this.controller.set_power_consumption_weight(this.powerConsumptionWeight);
            this.$emit('stateChange');
        },
        onDesignPowerChanged() {
            this.controller.set_design_power(this.designPower);
            this.updatePowerWarning();
            this.$emit('stateChange');
        },
        onDisableBalancersChanged() {
            this.controller.set_disable_balancers(this.disableBalancers);
            this.$emit('stateChange');
        },
        toggleMachine(machineId) {
            const machine = this.treeStructure.find(m => m.tree_id === machineId);
            if (machine) {
                machine.expanded = !machine.expanded;
            }
        },
        toggleMachineCheck(machine) {
            const newState = machine.check_state !== 'checked';
            this.controller.on_machine_toggled(machine.tree_id, newState);
            this.refreshTreeView();
            this.updatePowerWarning();
            this.updateConverterWarning();
            this.$emit('stateChange');
        },
        toggleRecipe(recipeId) {
            const machine = this.treeStructure.find(m => 
                m.recipes.some(r => r.tree_id === recipeId)
            );
            if (machine) {
                const recipe = machine.recipes.find(r => r.tree_id === recipeId);
                this.controller.on_recipe_toggled(recipeId, !recipe.is_enabled);
                this.refreshTreeView();
                this.updatePowerWarning();
                this.updateConverterWarning();
                this.$emit('stateChange');
            }
        },
        getRecipeTooltip(treeId) {
            return this.controller.get_tooltip_for_tree_id(treeId);
        },
        updatePowerWarning() {
            this.showPowerWarning = this.controller.should_show_power_warning();
        },
        updateConverterWarning() {
            this.showConverterWarning = this.controller.should_show_converter_warning();
        },
        async generateFactory() {
            this.isGenerating = true;
            this.setStatus('Generating factory...', 'info');
            
            try {
                // Progress callback to update status
                const onProgress = (message) => {
                    this.setStatus(message, 'info');
                };
                
                // generate_factory_from_state is async, updates controller state,
                // and Vue reactivity will automatically update the viewer
                await this.controller.generate_factory_from_state(onProgress);
                
                this.setStatus('Factory generated successfully', 'info');
                this.$emit('stateChange');
            } catch (error) {
                this.setStatus('Factory generation failed: ' + error.message, 'error');
                console.error('Factory generation error:', error);
            } finally {
                this.isGenerating = false;
            }
        },
        copyGraphviz() {
            const source = this.controller.copy_graphviz_source();
            if (source) {
                navigator.clipboard.writeText(source).then(() => {
                    this.setStatus('Graphviz source copied to clipboard', 'info');
                }).catch(err => {
                    this.setStatus('Failed to copy to clipboard: ' + err.message, 'error');
                });
            } else {
                this.setStatus('No graph to export', 'warning');
            }
        },
        saveState() {
            try {
                const stateJson = this.controller.serialize_state();
                
                // Create a blob and download it
                const blob = new Blob([stateJson], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                
                // Generate filename with timestamp
                const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
                a.download = `optifactory-design-${timestamp}.json`;
                
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                this.setStatus('Design saved successfully', 'info');
            } catch (error) {
                this.setStatus('Failed to save design: ' + error.message, 'error');
                console.error('Save state error:', error);
            }
        },
        triggerLoadState() {
            // Trigger the hidden file input
            this.$refs.fileInput.click();
        },
        async loadState(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            try {
                const text = await file.text();
                this.controller.deserialize_state(text);
                
                // Update UI from controller state
                this.outputsText = this.controller.get_outputs_text();
                this.inputsText = this.controller.get_inputs_text();
                this.recipeSearchText = this.controller.get_recipe_search_text();
                this.inputCostsWeight = this.controller.get_input_costs_weight();
                this.machineCountsWeight = this.controller.get_machine_counts_weight();
                this.powerConsumptionWeight = this.controller.get_power_consumption_weight();
                this.designPower = this.controller.get_design_power();
                this.disableBalancers = this.controller.get_disable_balancers();
                
                // Refresh tree view and warnings
                this.refreshTreeView();
                this.updatePowerWarning();
                this.updateConverterWarning();
                
                this.setStatus('Design loaded successfully', 'info');
                this.$emit('stateChange');
            } catch (error) {
                this.setStatus('Failed to load design: ' + error.message, 'error');
                console.error('Load state error:', error);
            } finally {
                // Reset file input so the same file can be loaded again
                event.target.value = '';
            }
        }
    }
};

export { FactoryViewComponent };
