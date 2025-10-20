// Placeholder EconomyController
class EconomyController {
    constructor() {
        // mock economy data
        this.economy = {
            'Iron Ore': 1.0,
            'Copper Ore': 1.0,
            'Limestone': 1.0,
            'Coal': 1.5,
            'Caterium Ore': 2.0,
            'Iron Ingot': 2.0,
            'Copper Ingot': 2.0,
            'Steel Ingot': 4.0,
            'Concrete': 3.0,
            'Iron Plate': 4.0,
            'Iron Rod': 3.5,
            'Wire': 3.5,
            'Cable': 5.0,
            'Screw': 2.5,
            'Reinforced Iron Plate': 8.0,
            'Rotor': 10.0,
            'Modular Frame': 15.0,
            'Steel Beam': 6.0,
            'Steel Pipe': 7.0,
            'Encased Industrial Beam': 12.0
        };
        this.pinned_items = new Set();
        this._filter_text = '';
        this._sort_column = 'item';
        this._sort_ascending = true;
    }

    get_filter_text() {
        return this._filter_text;
    }

    set_filter_text(text) {
        this._filter_text = text;
    }

    get_header_texts() {
        const base_names = {
            'item': 'Item',
            'value': 'Value',
            'locked': 'Locked'
        };
        
        const result = {};
        for (const [col, base_text] of Object.entries(base_names)) {
            let text = base_text;
            if (this._sort_column === col) {
                const arrow = this._sort_ascending ? ' ▲' : ' ▼';
                text += arrow;
            }
            result[col] = text;
        }
        return result;
    }

    set_sort(column) {
        if (this._sort_column === column) {
            this._sort_ascending = !this._sort_ascending;
        } else {
            this._sort_column = column;
            this._sort_ascending = true;
        }
    }

    set_item_value(item_name, value) {
        if (item_name in this.economy) {
            this.economy[item_name] = value;
        }
    }

    set_item_pinned(item_name, is_pinned) {
        if (is_pinned) {
            this.pinned_items.add(item_name);
        } else {
            this.pinned_items.delete(item_name);
        }
    }

    get_economy_table_structure() {
        const filter_text = this._filter_text.toLowerCase();
        
        // filter
        let items = Object.keys(this.economy).filter(item_name => 
            !filter_text || item_name.toLowerCase().includes(filter_text)
        );
        
        // sort
        if (this._sort_column === 'item') {
            items.sort((a, b) => {
                const cmp = a.toLowerCase().localeCompare(b.toLowerCase());
                return this._sort_ascending ? cmp : -cmp;
            });
        } else if (this._sort_column === 'value') {
            items.sort((a, b) => {
                const cmp = this.economy[a] - this.economy[b];
                return this._sort_ascending ? cmp : -cmp;
            });
        } else if (this._sort_column === 'locked') {
            items.sort((a, b) => {
                const a_pinned = this.pinned_items.has(a) ? 1 : 0;
                const b_pinned = this.pinned_items.has(b) ? 1 : 0;
                const cmp = a_pinned - b_pinned || a.toLowerCase().localeCompare(b.toLowerCase());
                return this._sort_ascending ? cmp : -cmp;
            });
        }
        
        // build item structures
        const item_structures = items.map(item_name => ({
            item_id: `item:${item_name}`,
            display_name: item_name,
            value: this.economy[item_name],
            is_pinned: this.pinned_items.has(item_name),
            is_visible: true
        }));
        
        return {
            items: item_structures,
            sort_column: this._sort_column,
            sort_ascending: this._sort_ascending
        };
    }

    reset_to_default() {
        console.log('Reset to default - not implemented');
        // Placeholder: would reload default economy
    }

    recompute_values() {
        console.log('Recompute values - not implemented');
        // Placeholder: would run optimization algorithm
    }

    load_from_csv_data(csv_content) {
        console.log('Load from CSV data - not implemented');
        // Placeholder: would parse CSV string and update economy
        alert('CSV import not implemented in placeholder');
    }

    get_csv_export_data() {
        console.log('Get CSV export data - not implemented');
        // Placeholder: would generate CSV string from economy
        alert('CSV export not implemented in placeholder');
        return 'item,value,locked\n';  // empty CSV header
    }
}

// Placeholder FactoryController
class FactoryController {
    constructor(economy) {
        this.economy = economy;
        this._outputs_text = 'Concrete:480';
        this._inputs_text = '# Leave empty to auto-detect\n# Or specify like:\n# Limestone:480\n# Limestone:480\n# Limestone:480';
        this._recipe_search_text = '';
        this.enabled_recipes = this._get_default_enabled_recipes();
        this._input_costs_weight = 1.0;
        this._machine_counts_weight = 0.0;
        this._power_consumption_weight = 1.0;
        this._design_power = false;
        this._current_factory = null;
    }

    _get_default_enabled_recipes() {
        // mock default recipes - in real implementation would come from recipes module
        return new Set([
            'Iron Ingot',
            'Copper Ingot',
            'Steel Ingot',
            'Caterium Ingot',
            'Concrete',
            'Iron Plate',
            'Iron Rod',
            'Wire',
            'Cable',
            'Screw',
            'Reinforced Iron Plate',
            'Rotor',
            'Modular Frame',
            'Steel Beam',
            'Steel Pipe',
            'Encased Industrial Beam'
        ]);
    }

    get_outputs_text() { return this._outputs_text; }
    get_inputs_text() { return this._inputs_text; }
    get_recipe_search_text() { return this._recipe_search_text; }
    get_input_costs_weight() { return this._input_costs_weight; }
    get_machine_counts_weight() { return this._machine_counts_weight; }
    get_power_consumption_weight() { return this._power_consumption_weight; }
    get_design_power() { return this._design_power; }

    set_outputs_text(text) { this._outputs_text = text; }
    set_inputs_text(text) { this._inputs_text = text; }
    set_recipe_search_text(text) { this._recipe_search_text = text; }
    set_input_costs_weight(value) { this._input_costs_weight = value; }
    set_machine_counts_weight(value) { this._machine_counts_weight = value; }
    set_power_consumption_weight(value) { this._power_consumption_weight = value; }
    set_design_power(value) { this._design_power = value; }

    set_recipe_enabled(recipe_name, enabled) {
        if (enabled) {
            this.enabled_recipes.add(recipe_name);
        } else {
            this.enabled_recipes.delete(recipe_name);
        }
    }

    on_recipe_toggled(recipe_tree_id, is_checked) {
        const parsed = this._parse_recipe_id(recipe_tree_id);
        if (parsed) {
            const [_, recipe_name] = parsed;
            this.set_recipe_enabled(recipe_name, is_checked);
        }
    }

    _parse_recipe_id(tree_id) {
        if (tree_id.startsWith('recipe:')) {
            const parts = tree_id.substring(7).split(':', 2);
            if (parts.length === 2) {
                return parts;
            }
        }
        return null;
    }

    get_recipe_tree_structure() {
        const search_text = this._recipe_search_text.toLowerCase();
        
        // mock recipe tree structure
        const mock_machines = {
            'Smelter': ['Iron Ingot', 'Copper Ingot', 'Steel Ingot', 'Caterium Ingot'],
            'Constructor': ['Iron Plate', 'Iron Rod', 'Wire', 'Cable', 'Concrete', 'Screw', 'Steel Beam', 'Steel Pipe'],
            'Assembler': ['Reinforced Iron Plate', 'Rotor', 'Modular Frame', 'Encased Industrial Beam'],
            'Manufacturer': ['Heavy Modular Frame', 'Computer', 'Motor'],
            'Coal Generator': ['Coal Power'],
            'Fuel Generator': ['Fuel Power']
        };

        const machines = [];
        for (const [machine_name, recipes] of Object.entries(mock_machines)) {
            const recipe_nodes = recipes.map(recipe_name => {
                const is_visible = !search_text || 
                    recipe_name.toLowerCase().includes(search_text) ||
                    machine_name.toLowerCase().includes(search_text);
                
                return {
                    tree_id: `recipe:${machine_name}:${recipe_name}`,
                    display_name: recipe_name,
                    is_enabled: this.enabled_recipes.has(recipe_name),
                    is_visible: is_visible
                };
            });

            const visible_recipes = recipe_nodes.filter(r => r.is_visible);
            if (visible_recipes.length === 0) {
                continue;
            }

            const enabled_count = visible_recipes.filter(r => r.is_enabled).length;
            let check_state = 'unchecked';
            if (enabled_count === visible_recipes.length) {
                check_state = 'checked';
            } else if (enabled_count > 0) {
                check_state = 'tristate';
            }

            machines.push({
                tree_id: `machine:${machine_name}`,
                display_name: machine_name,
                recipes: recipe_nodes,
                check_state: check_state,
                is_visible: true
            });
        }

        return machines;
    }

    should_show_power_warning() {
        if (!this._design_power) {
            return false;
        }
        // check if any power recipe is enabled
        return !this.enabled_recipes.has('Coal Power') && !this.enabled_recipes.has('Fuel Power');
    }

    get_tooltip_for_tree_id(tree_id) {
        const parsed = this._parse_recipe_id(tree_id);
        if (parsed) {
            const [machine_name, recipe_name] = parsed;
            // mock tooltip data
            const tooltips = {
                'Iron Ingot': 'Inputs:\n  - Iron Ore: 30/min\n\nOutputs:\n  - Iron Ingot: 30/min',
                'Copper Ingot': 'Inputs:\n  - Copper Ore: 30/min\n\nOutputs:\n  - Copper Ingot: 30/min',
                'Concrete': 'Inputs:\n  - Limestone: 45/min\n\nOutputs:\n  - Concrete: 15/min',
                'Iron Plate': 'Inputs:\n  - Iron Ingot: 30/min\n\nOutputs:\n  - Iron Plate: 20/min',
                'Iron Rod': 'Inputs:\n  - Iron Ingot: 15/min\n\nOutputs:\n  - Iron Rod: 15/min',
                'Wire': 'Inputs:\n  - Copper Ingot: 15/min\n\nOutputs:\n  - Wire: 30/min',
                'Cable': 'Inputs:\n  - Wire: 60/min\n\nOutputs:\n  - Cable: 30/min',
                'Reinforced Iron Plate': 'Inputs:\n  - Iron Plate: 30/min\n  - Screw: 60/min\n\nOutputs:\n  - Reinforced Iron Plate: 5/min'
            };
            return tooltips[recipe_name] || `Recipe: ${recipe_name}\nMachine: ${machine_name}\n(Tooltip details not implemented in placeholder)`;
        }
        return null;
    }

    generate_factory_from_state() {
        console.log('Generating factory...');
        console.log('Outputs:', this._outputs_text);
        console.log('Inputs:', this._inputs_text);
        console.log('Enabled recipes:', Array.from(this.enabled_recipes));
        console.log('Weights:', {
            input_costs: this._input_costs_weight,
            machine_counts: this._machine_counts_weight,
            power: this._power_consumption_weight
        });
        
        // mock graphviz output based on outputs
        const lines = this._outputs_text.trim().split('\n').filter(line => {
            const trimmed = line.trim();
            return trimmed && !trimmed.startsWith('#');
        });
        
        let graphviz = 'digraph Factory {\n';
        graphviz += '  rankdir=LR;\n';
        graphviz += '  node [shape=box, style=filled];\n\n';
        
        // parse first output for demo
        if (lines.length > 0) {
            const parts = lines[0].split(':');
            if (parts.length === 2) {
                const material = parts[0].trim();
                const rate = parts[1].trim();
                
                graphviz += `  "Input:\\nLimestone" [fillcolor=lightblue];\n`;
                graphviz += `  "Constructor\\n(x2)" [fillcolor=lightgreen];\n`;
                graphviz += `  "Output:\\n${material}:${rate}" [fillcolor=lightyellow];\n\n`;
                graphviz += `  "Input:\\nLimestone" -> "Constructor\\n(x2)";\n`;
                graphviz += `  "Constructor\\n(x2)" -> "Output:\\n${material}:${rate}";\n`;
            }
        }
        
        graphviz += '}';
        
        return { source: graphviz };
    }

    copy_graphviz_source() {
        if (this._current_factory && this._current_factory.source) {
            console.log('Copying graphviz source to clipboard');
            return this._current_factory.source;
        }
        console.log('No graph to export');
        return null;
    }
}

export { EconomyController, FactoryController };
