/**
 * EconomyView - Reusable Vue component for economy editing
 * Requires: EconomyController
 */
const EconomyViewComponent = {
    template: `
        <div class="economy-editor">
            <div class="controls">
                <label>Filter:</label>
                <input 
                    type="text" 
                    v-model="filterText" 
                    @input="onFilterChanged"
                    placeholder="Type to filter items..."
                >
                <button @click="resetEconomy">Reset to Default</button>
                <button @click="rebalanceValues">Rebalance Values</button>
                <button @click="loadCSV">Load CSV</button>
                <button @click="saveCSV">Save CSV</button>
                <input 
                    ref="fileInput" 
                    type="file" 
                    accept=".csv" 
                    style="display: none" 
                    @change="handleFileSelected"
                >
            </div>

            <div class="table-container">
                <div class="table-scroll">
                    <table>
                        <thead>
                            <tr>
                                <th class="col-item" @click="onHeaderClick('item')">
                                    {{ headerTexts.item }}
                                </th>
                                <th class="col-value" @click="onHeaderClick('value')">
                                    {{ headerTexts.value }}
                                </th>
                                <th class="col-locked" @click="onHeaderClick('locked')">
                                    {{ headerTexts.locked }}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-if="tableItems.length === 0">
                                <td colspan="3" class="no-results">No items match the filter</td>
                            </tr>
                            <tr v-for="item in tableItems" :key="item.item_id">
                                <td class="col-item">{{ item.display_name }}</td>
                                <td class="col-value">
                                    <input 
                                        type="number" 
                                        :value="item.value"
                                        @input="onValueChanged(item.display_name, $event)"
                                        step="0.01"
                                        min="0"
                                    >
                                </td>
                                <td class="col-locked">
                                    <input 
                                        type="checkbox" 
                                        :checked="item.is_pinned"
                                        @change="onPinnedToggle(item.display_name, $event)"
                                    >
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `,
    props: {
        controller: {
            type: Object,
            required: true
        }
    },
    emits: ['statusChange', 'stateChange'],
    data() {
        return {
            filterText: '',
            headerTexts: {},
            tableItems: []
        };
    },
    mounted() {
        this.refreshView();
    },
    methods: {
        setStatus(text, level = 'info') {
            this.$emit('status-change', { text, level });
        },
        refreshView() {
            this.headerTexts = this.controller.get_header_texts();
            const structure = this.controller.get_economy_table_structure();
            this.tableItems = structure.items;
        },
        onFilterChanged() {
            this.controller.set_filter_text(this.filterText);
            this.refreshView();
            this.$emit('state-change');
        },
        onHeaderClick(column) {
            this.controller.set_sort(column);
            this.refreshView();
            this.$emit('state-change');
        },
        onValueChanged(itemName, event) {
            const value = parseFloat(event.target.value);
            if (!isNaN(value) && value >= 0) {
                this.controller.set_item_value(itemName, value);
                this.$emit('state-change');
            }
        },
        onPinnedToggle(itemName, event) {
            this.controller.set_item_pinned(itemName, event.target.checked);
            this.$emit('state-change');
        },
        resetEconomy() {
            this.controller.reset_to_default();
            this.refreshView();
            this.setStatus('Economy reset to default', 'info');
            this.$emit('state-change');
        },
        rebalanceValues() {
            this.controller.recompute_values();
            this.refreshView();
            this.setStatus('Economy values recomputed', 'info');
            this.$emit('state-change');
        },
        loadCSV() {
            // Trigger file input click (view responsibility)
            this.$refs.fileInput.click();
        },
        handleFileSelected(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const csvContent = e.target.result;
                    // Controller handles parsing, view handles file I/O
                    this.controller.load_from_csv(csvContent);
                    this.refreshView();
                    this.setStatus(`Loaded economy from ${file.name}`, 'info');
                    this.$emit('state-change');
                } catch (error) {
                    this.setStatus(`Failed to load CSV: ${error.message}`, 'error');
                }
            };
            reader.onerror = () => {
                this.setStatus('Failed to read file', 'error');
            };
            reader.readAsText(file);
            
            // Reset input so same file can be selected again
            event.target.value = '';
        },
        saveCSV() {
            try {
                // Controller generates data, view handles file download
                const csvData = this.controller.save_to_csv();
                
                // Create blob and download (view responsibility)
                const blob = new Blob([csvData], { type: 'text/csv' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'economy.csv';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                this.setStatus('Economy exported to economy.csv', 'info');
            } catch (error) {
                this.setStatus(`Failed to export CSV: ${error.message}`, 'error');
            }
        }
    }
};

export { EconomyViewComponent };
