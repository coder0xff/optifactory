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
     *
     * Precondition:
     *     none
     *
     * Postcondition:
     *     this.economy is initialized with default economy dict
     *     this.pinned_items is initialized as empty set
     *     this._filter_text is empty string
     *     this._sort_column is 'item'
     *     this._sort_ascending is true
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
     *
     * Precondition:
     *     none
     *
     * Postcondition:
     *     returns current filter text string
     *
     * Returns:
     *     current filter text
     */
    get_filter_text() {
        return this._filter_text;
    }
    
    /**
     * Get current sort state.
     *
     * Precondition:
     *     none
     *
     * Postcondition:
     *     returns [sort_column, sort_ascending] array
     *     sort_column may be null, 'item', 'value', or 'locked'
     *
     * Returns:
     *     array of [sort_column, sort_ascending]
     */
    get_sort_state() {
        return [this._sort_column, this._sort_ascending];
    }
    
    /**
     * Get header display texts with sort indicators.
     *
     * Precondition:
     *     this._sort_column is null, 'item', 'value', or 'locked'
     *     this._sort_ascending is a boolean
     *
     * Postcondition:
     *     returns object mapping column names to display text
     *     sorted column has arrow indicator (▲ or ▼)
     *     unsorted columns have no indicator
     *
     * Returns:
     *     object mapping column name ('item', 'value', 'locked') to display text
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
     *
     * Precondition:
     *     text is a string
     *
     * Postcondition:
     *     this._filter_text is updated to text
     *
     * Args:
     *     text: new filter text
     */
    set_filter_text(text) {
        this._filter_text = text;
    }
    
    /**
     * Set sort column, toggling direction if same column.
     *
     * Precondition:
     *     column is null, 'item', 'value', or 'locked'
     *
     * Postcondition:
     *     if column == current column: direction is toggled
     *     if column != current column: column is set, direction is ascending
     *     this._sort_column and this._sort_ascending are updated
     *
     * Args:
     *     column: 'item', 'value', 'locked', or null
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
     *
     * Precondition:
     *     item_name is a string
     *     value is a number
     *
     * Postcondition:
     *     if item_name in economy: this.economy[item_name] is set to value
     *     if item_name not in economy: no change
     *
     * Args:
     *     item_name: name of the item
     *     value: new value
     */
    set_item_value(item_name, value) {
        if (item_name in this.economy) {
            this.economy[item_name] = value;
        }
    }
    
    /**
     * Set pinned state for an item.
     *
     * Precondition:
     *     item_name is a string
     *     is_pinned is a boolean
     *
     * Postcondition:
     *     if is_pinned: item_name is added to this.pinned_items
     *     if not is_pinned: item_name is removed from this.pinned_items
     *
     * Args:
     *     item_name: name of the item
     *     is_pinned: true to pin, false to unpin
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
     *
     * Precondition:
     *     item_name is a non-empty string
     *
     * Postcondition:
     *     returns string in format "item:{item_name}"
     *
     * Args:
     *     item_name: name of the item
     *
     * Returns:
     *     stable ID string
     */
    static _make_item_id(item_name) {
        return `item:${item_name}`;
    }
    
    /**
     * Filter economy items by text match.
     *
     * Precondition:
     *     filter_text is a lowercase string (may be empty)
     *     this.economy contains item names
     *
     * Postcondition:
     *     returns array of item names matching filter
     *     empty filter returns all items
     *     matching is case-insensitive
     *
     * Args:
     *     filter_text: lowercase filter text
     *
     * Returns:
     *     array of matching item names
     */
    _filter_economy_items(filter_text) {
        return Object.keys(this.economy).filter(item_name =>
            !filter_text || item_name.toLowerCase().includes(filter_text)
        );
    }
    
    /**
     * Sort economy items in-place based on current sort column.
     *
     * Precondition:
     *     items is an array of item names from this.economy
     *     this._sort_column is null, 'item', 'value', or 'locked'
     *     this._sort_ascending is a boolean
     *
     * Postcondition:
     *     items array is sorted in-place according to sort column and direction
     *
     * Args:
     *     items: array of item names to sort
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
     *
     * Precondition:
     *     item_name is in this.economy
     *     item_name is a valid string
     *
     * Postcondition:
     *     returns EconomyItem with all fields populated
     *     is_visible is always true (pre-filtered)
     *
     * Args:
     *     item_name: name of the item
     *
     * Returns:
     *     EconomyItem structure
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
     *
     * Precondition:
     *     this.economy is initialized
     *     this._filter_text is a string
     *     this._sort_column is null, 'item', 'value', or 'locked'
     *     this._sort_ascending is a boolean
     *
     * Postcondition:
     *     returns EconomyTableStructure with filtered, sorted items
     *     each item has ID, display name, value, and pinned state
     *     structure includes current sort state
     *
     * Returns:
     *     EconomyTableStructure ready for rendering
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
     *
     * Precondition:
     *     none
     *
     * Postcondition:
     *     this.economy is cleared and reloaded with default values
     *     this.pinned_items is cleared
     *     info message is logged
     */
    reset_to_default() {
        this.economy = Object.assign({}, get_default_economy());
        this.pinned_items.clear();
        
        console.log("Economy reset to default");
    }
    
    /**
     * Recompute economy values using gradient descent with pinned values.
     *
     * Precondition:
     *     this.economy contains valid item values
     *     this.pinned_items contains item names to pin
     *
     * Postcondition:
     *     this.economy is updated with newly computed values
     *     pinned items retain their original values
     *     info message is logged
     *
     * Throws:
     *     Exception: if recomputation fails
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
     *
     * Precondition:
     *     csv_string is a valid CSV string
     *     CSV string contains economy data in correct format
     *
     * Postcondition:
     *     this.economy is cleared and loaded with data from CSV
     *     this.pinned_items is cleared and loaded with pinned items from CSV
     *     info message is logged
     *
     * Args:
     *     csv_string: CSV string with economy data
     *     
     * Throws:
     *     Exception: if load fails
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
     *
     * Precondition:
     *     this.economy contains valid item values
     *     this.pinned_items contains item names
     *
     * Postcondition:
     *     returns CSV string with economy data
     *     info message is logged
     *
     * Returns:
     *     CSV string representation of economy
     *     
     * Throws:
     *     Exception: if save fails
     */
    save_to_csv() {
        const csv_string = economy_to_csv(this.economy, this.pinned_items);
        
        console.log("Economy saved to CSV");
        return csv_string;
    }
}

export { EconomyItem, EconomyTableStructure, EconomyController };

