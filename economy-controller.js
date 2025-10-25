/**
 * Controller for economy editor logic - no GUI dependencies
 */

import {
    get_default_economy,
    compute_item_values,
    economy_from_csv,
    economy_to_csv
} from './economy.js';

/**
 * Represents a single item in the economy table
 */
class EconomyItem {
    /**
     * @param {string} item_id - "item:{name}"
     * @param {string} display_name
     * @param {number} value
     * @param {boolean} is_pinned
     * @param {boolean} is_visible
     */
    constructor(item_id, display_name, value, is_pinned, is_visible) {
        this.item_id = item_id;
        this.display_name = display_name;
        this.value = value;
        this.is_pinned = is_pinned;
        this.is_visible = is_visible;
    }
}

/**
 * Complete table structure with IDs and states
 */
class EconomyTableStructure {
    /**
     * @param {Array<EconomyItem>} items
     * @param {string|null} sort_column - 'item', 'value', 'locked'
     * @param {boolean} sort_ascending
     */
    constructor(items = [], sort_column = null, sort_ascending = true) {
        this.items = items;
        this.sort_column = sort_column;
        this.sort_ascending = sort_ascending;
    }
}

/**
 * Stateful controller for economy editing - single source of truth
 */
class EconomyController {
    /**
     * Initialize controller with default economy.
     */
    constructor() {
        this.economy = Object.assign({}, get_default_economy());
        this.pinned_items = new Set();
        
        // UI state
        this._filter_text = "";
        this._sort_column = 'item';
        this._sort_ascending = true;
    }
    
    // ========== State Getters ==========
    
    /**
     * Get current filter text.
     * @returns {string} current filter text
     */
    get_filter_text() {
        return this._filter_text;
    }
    
    /**
     * Get current sort state.
     * @returns {Array<*>} array of [sort_column, sort_ascending]
     */
    get_sort_state() {
        return [this._sort_column, this._sort_ascending];
    }
    
    /**
     * Get header display texts with sort indicators.
     * @returns {Object<string, string>} object mapping column name ('item', 'value', 'locked') to display text
     */
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
    
    // ========== State Setters ==========
    
    /**
     * Set filter text.
     * @param {string} text - new filter text
     */
    set_filter_text(text) {
        this._filter_text = text;
    }
    
    /**
     * Set sort column, toggling direction if same column.
     * @param {string|null} column - 'item', 'value', 'locked', or null
     */
    set_sort(column) {
        if (this._sort_column === column) {
            // Toggle direction
            this._sort_ascending = !this._sort_ascending;
        } else {
            // New column, default to ascending
            this._sort_column = column;
            this._sort_ascending = true;
        }
    }
    
    /**
     * Set value for an item.
     * @param {string} item_name - name of the item
     * @param {number} value - new value
     */
    set_item_value(item_name, value) {
        if (item_name in this.economy) {
            this.economy[item_name] = value;
        }
    }
    
    /**
     * Set pinned state for an item.
     * @param {string} item_name - name of the item
     * @param {boolean} is_pinned - true to pin, false to unpin
     */
    set_item_pinned(item_name, is_pinned) {
        if (is_pinned) {
            this.pinned_items.add(item_name);
        } else {
            this.pinned_items.delete(item_name);
        }
    }
    
    // ========== Table Structure ==========
    
    /**
     * Generate stable ID for economy item.
     * @param {string} item_name - name of the item
     * @returns {string} stable ID string
     */
    static _make_item_id(item_name) {
        return `item:${item_name}`;
    }
    
    /**
     * Filter economy items by text match.
     * @param {string} filter_text - lowercase filter text
     * @returns {Array<string>} array of matching item names
     */
    _filter_economy_items(filter_text) {
        return Object.keys(this.economy).filter(item_name =>
            !filter_text || item_name.toLowerCase().includes(filter_text)
        );
    }
    
    /**
     * Sort economy items in-place based on current sort column.
     * @param {Array<string>} items - array of item names to sort
     */
    _sort_economy_items(items) {
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
        } else {
            // 'locked' column
            items.sort((a, b) => {
                const a_pinned = this.pinned_items.has(a);
                const b_pinned = this.pinned_items.has(b);
                if (a_pinned !== b_pinned) {
                    const cmp = a_pinned ? 1 : -1;
                    return this._sort_ascending ? cmp : -cmp;
                }
                const cmp = a.toLowerCase().localeCompare(b.toLowerCase());
                return this._sort_ascending ? cmp : -cmp;
            });
        }
    }
    
    /**
     * Build an EconomyItem structure from an item name.
     * @param {string} item_name - name of the item
     * @returns {EconomyItem} EconomyItem structure
     */
    _build_economy_item(item_name) {
        return new EconomyItem(
            EconomyController._make_item_id(item_name),
            item_name,
            this.economy[item_name],
            this.pinned_items.has(item_name),
            true  // Already filtered
        );
    }
    
    /**
     * Get complete table structure with IDs, values, and visibility.
     * @returns {EconomyTableStructure} EconomyTableStructure ready for rendering
     */
    get_economy_table_structure() {
        const filter_text = this._filter_text.toLowerCase();
        
        // Filter and sort
        const filtered_items = this._filter_economy_items(filter_text);
        this._sort_economy_items(filtered_items);
        
        // Build item structures
        const items = filtered_items.map(item_name => this._build_economy_item(item_name));
        
        return new EconomyTableStructure(
            items,
            this._sort_column,
            this._sort_ascending
        );
    }
    
    // ========== Actions ==========
    
    /**
     * Reset economy to default values.
     */
    reset_to_default() {
        this.economy = Object.assign({}, get_default_economy());
        this.pinned_items.clear();
        
        console.log("Economy reset to default");
    }
    
    /**
     * Recompute economy values using gradient descent with pinned values.
     * @throws {Error} if recomputation fails
     */
    recompute_values() {
        // Build pinned_values object from pinned items
        const pinned_values = {};
        for (const item of this.pinned_items) {
            pinned_values[item] = this.economy[item];
        }
        
        // Recompute
        const new_economy = compute_item_values(null, pinned_values);
        this.economy = Object.assign({}, new_economy);
        
        console.log("Economy values recomputed successfully");
    }
    
    /**
     * Load economy from CSV string.
     * @param {string} csv_string - CSV string with economy data
     * @throws {Error} if load fails
     */
    load_from_csv(csv_string) {
        const [loaded_economy, loaded_pinned] = economy_from_csv(csv_string);
        this.economy = Object.assign({}, loaded_economy);
        this.pinned_items.clear();
        for (const item of loaded_pinned) {
            this.pinned_items.add(item);
        }
        
        console.log("Economy loaded from CSV");
    }
    
    /**
     * Save economy to CSV string.
     * @returns {string} CSV string representation of economy
     * @throws {Error} if save fails
     */
    save_to_csv() {
        const csv_string = economy_to_csv(this.economy, this.pinned_items);
        
        console.log("Economy saved to CSV");
        return csv_string;
    }
}

export { EconomyItem, EconomyTableStructure, EconomyController };

