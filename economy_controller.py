"""Controller for economy editor logic - no GUI dependencies"""

import logging
from dataclasses import dataclass, field
from typing import Set, Dict, List, Optional

_LOGGER = logging.getLogger("satisgraphery")


@dataclass
class EconomyItem:
    """Represents a single item in the economy table"""
    item_id: str  # "item:{name}"
    display_name: str
    value: float
    is_pinned: bool
    is_visible: bool


@dataclass
class EconomyTableStructure:
    """Complete table structure with IDs and states"""
    items: List[EconomyItem] = field(default_factory=list)
    sort_column: Optional[str] = None  # 'item', 'value', 'locked'
    sort_ascending: bool = True


class EconomyController:
    """Stateful controller for economy editing - single source of truth"""
    
    def __init__(self):
        """Initialize controller with default economy.

        Precondition:
            none

        Postcondition:
            self.economy is initialized with default economy dict
            self.pinned_items is initialized as empty set
            self._filter_text is empty string
            self._sort_column is 'item'
            self._sort_ascending is True
        """
        from economy import get_default_economy
        self.economy = dict(get_default_economy())
        self.pinned_items: Set[str] = set()
        
        # UI state
        self._filter_text = ""
        self._sort_column: Optional[str] = 'item'
        self._sort_ascending = True
    
    # ========== State Getters ==========
    
    def get_filter_text(self) -> str:
        """Get current filter text.

        Precondition:
            none

        Postcondition:
            returns current filter text string

        Returns:
            current filter text
        """
        return self._filter_text
    
    def get_sort_state(self) -> tuple[Optional[str], bool]:
        """Get current sort state.

        Precondition:
            none

        Postcondition:
            returns (sort_column, sort_ascending) tuple
            sort_column may be None, 'item', 'value', or 'locked'

        Returns:
            tuple of (sort_column, sort_ascending)
        """
        return self._sort_column, self._sort_ascending
    
    def get_header_texts(self) -> dict[str, str]:
        """Get header display texts with sort indicators.

        Precondition:
            self._sort_column is None, 'item', 'value', or 'locked'
            self._sort_ascending is a boolean

        Postcondition:
            returns dict mapping column names to display text
            sorted column has arrow indicator (▲ or ▼)
            unsorted columns have no indicator

        Returns:
            dict mapping column name ('item', 'value', 'locked') to display text
        """
        base_names = {
            'item': 'Item',
            'value': 'Value',
            'locked': 'Locked'
        }
        
        result = {}
        for col, base_text in base_names.items():
            text = base_text
            if self._sort_column == col:
                arrow = ' ▲' if self._sort_ascending else ' ▼'
                text += arrow
            result[col] = text
        
        return result
    
    # ========== State Setters ==========
    
    def set_filter_text(self, text: str):
        """Set filter text.

        Precondition:
            text is a string

        Postcondition:
            self._filter_text is updated to text

        Args:
            text: new filter text
        """
        self._filter_text = text
    
    def set_sort(self, column: Optional[str]):
        """Set sort column, toggling direction if same column.

        Precondition:
            column is None, 'item', 'value', or 'locked'

        Postcondition:
            if column == current column: direction is toggled
            if column != current column: column is set, direction is ascending
            self._sort_column and self._sort_ascending are updated

        Args:
            column: 'item', 'value', 'locked', or None
        """
        if self._sort_column == column:
            # Toggle direction
            self._sort_ascending = not self._sort_ascending
        else:
            # New column, default to ascending
            self._sort_column = column
            self._sort_ascending = True
    
    def set_item_value(self, item_name: str, value: float):
        """Set value for an item.

        Precondition:
            item_name is a string
            value is a float

        Postcondition:
            if item_name in economy: self.economy[item_name] is set to value
            if item_name not in economy: no change

        Args:
            item_name: name of the item
            value: new value
        """
        if item_name in self.economy:
            self.economy[item_name] = value
    
    def set_item_pinned(self, item_name: str, is_pinned: bool):
        """Set pinned state for an item.

        Precondition:
            item_name is a string
            is_pinned is a boolean

        Postcondition:
            if is_pinned: item_name is added to self.pinned_items
            if not is_pinned: item_name is removed from self.pinned_items

        Args:
            item_name: name of the item
            is_pinned: True to pin, False to unpin
        """
        if is_pinned:
            self.pinned_items.add(item_name)
        else:
            self.pinned_items.discard(item_name)
    
    # ========== Table Structure ==========
    
    @staticmethod
    def _make_item_id(item_name: str) -> str:
        """Generate stable ID for economy item.

        Precondition:
            item_name is a non-empty string

        Postcondition:
            returns string in format "item:{item_name}"

        Args:
            item_name: name of the item

        Returns:
            stable ID string
        """
        return f"item:{item_name}"
    
    def _filter_economy_items(self, filter_text: str) -> list[str]:
        """Filter economy items by text match.

        Precondition:
            filter_text is a lowercase string (may be empty)
            self.economy contains item names

        Postcondition:
            returns list of item names matching filter
            empty filter returns all items
            matching is case-insensitive

        Args:
            filter_text: lowercase filter text

        Returns:
            list of matching item names
        """
        return [
            item_name for item_name in self.economy.keys()
            if not filter_text or filter_text in item_name.lower()
        ]
    
    def _sort_economy_items(self, items: list[str]) -> None:
        """Sort economy items in-place based on current sort column.

        Precondition:
            items is a list of item names from self.economy
            self._sort_column is None, 'item', 'value', or 'locked'
            self._sort_ascending is a boolean

        Postcondition:
            items list is sorted in-place according to sort column and direction

        Args:
            items: list of item names to sort
        """
        if self._sort_column == 'item':
            items.sort(key=lambda x: x.lower(), reverse=not self._sort_ascending)
        elif self._sort_column == 'value':
            items.sort(key=lambda x: self.economy[x], reverse=not self._sort_ascending)
        else:
            assert self._sort_column == 'locked'
            items.sort(key=lambda x: (x in self.pinned_items, x.lower()), reverse=not self._sort_ascending)
    
    def _build_economy_item(self, item_name: str) -> EconomyItem:
        """Build an EconomyItem structure from an item name.

        Precondition:
            item_name is in self.economy
            item_name is a valid string

        Postcondition:
            returns EconomyItem with all fields populated
            is_visible is always True (pre-filtered)

        Args:
            item_name: name of the item

        Returns:
            EconomyItem structure
        """
        return EconomyItem(
            item_id=self._make_item_id(item_name),
            display_name=item_name,
            value=self.economy[item_name],
            is_pinned=item_name in self.pinned_items,
            is_visible=True  # Already filtered
        )
    
    def get_economy_table_structure(self) -> EconomyTableStructure:
        """Get complete table structure with IDs, values, and visibility.

        Precondition:
            self.economy is initialized
            self._filter_text is a string
            self._sort_column is None, 'item', 'value', or 'locked'
            self._sort_ascending is a boolean

        Postcondition:
            returns EconomyTableStructure with filtered, sorted items
            each item has ID, display name, value, and pinned state
            structure includes current sort state

        Returns:
            EconomyTableStructure ready for rendering
        """
        filter_text = self._filter_text.lower()
        
        # Filter and sort
        filtered_items = self._filter_economy_items(filter_text)
        self._sort_economy_items(filtered_items)
        
        # Build item structures
        items = [self._build_economy_item(item_name) for item_name in filtered_items]
        
        return EconomyTableStructure(
            items=items,
            sort_column=self._sort_column,
            sort_ascending=self._sort_ascending
        )
    
    # ========== Actions ==========
    
    def reset_to_default(self):
        """Reset economy to default values.

        Precondition:
            none

        Postcondition:
            self.economy is cleared and reloaded with default values
            self.pinned_items is cleared
            info message is logged

        """
        from economy import get_default_economy
        
        self.economy.clear()
        self.economy.update(dict(get_default_economy()))
        self.pinned_items.clear()
        
        _LOGGER.info("Economy reset to default")
    
    def recompute_values(self):
        """Recompute economy values using gradient descent with pinned values.

        Precondition:
            self.economy contains valid item values
            self.pinned_items contains item names to pin

        Postcondition:
            self.economy is updated with newly computed values
            pinned items retain their original values
            info message is logged

        Raises:
            Exception: if recomputation fails
        """
        from economy import compute_item_values
        
        # Build pinned_values dict from pinned items
        pinned_values = {item: self.economy[item] for item in self.pinned_items}
        
        # Recompute
        new_economy = compute_item_values(pinned_values=pinned_values)
        self.economy.clear()
        self.economy.update(new_economy)
        
        _LOGGER.info("Economy values recomputed successfully")
    
    def load_from_csv(self, filepath: str):
        """Load economy from CSV file.

        Precondition:
            filepath is a valid path to a CSV file
            CSV file contains economy data in correct format

        Postcondition:
            self.economy is cleared and loaded with data from file
            self.pinned_items is cleared and loaded with pinned items from file
            info message is logged with filename

        Args:
            filepath: path to CSV file
            
        Raises:
            Exception: if load fails
        """
        from economy import load_economy_from_csv
        import os
        
        loaded_economy, loaded_pinned = load_economy_from_csv(filepath)
        self.economy.clear()
        self.economy.update(loaded_economy)
        self.pinned_items.clear()
        self.pinned_items.update(loaded_pinned)
        
        filename = os.path.basename(filepath)
        _LOGGER.info("Economy loaded from %s", filename)
    
    def save_to_csv(self, filepath: str):
        """Save economy to CSV file.

        Precondition:
            filepath is a valid writable path
            self.economy contains valid item values
            self.pinned_items contains item names

        Postcondition:
            economy data is written to CSV file
            info message is logged with filename

        Args:
            filepath: path to CSV file
            
        Raises:
            Exception: if save fails
        """
        from economy import save_economy_to_csv
        import os
        
        save_economy_to_csv(filepath, self.economy, self.pinned_items)
        
        filename = os.path.basename(filepath)
        _LOGGER.info("Economy saved to %s", filename)

