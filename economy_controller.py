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
        """Initialize controller with default economy"""
        from economy import get_default_economy
        self.economy = dict(get_default_economy())
        self.pinned_items: Set[str] = set()
        
        # UI state
        self._filter_text = ""
        self._sort_column: Optional[str] = 'item'
        self._sort_ascending = True
    
    # ========== State Getters ==========
    
    def get_filter_text(self) -> str:
        """Get filter text"""
        return self._filter_text
    
    def get_sort_state(self) -> tuple[Optional[str], bool]:
        """Get current sort state
        
        Returns:
            Tuple of (sort_column, sort_ascending)
        """
        return self._sort_column, self._sort_ascending
    
    def get_header_texts(self) -> dict[str, str]:
        """Get header display texts with sort indicators
        
        Returns:
            Dict mapping column name to display text
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
        """Set filter text"""
        self._filter_text = text
    
    def set_sort(self, column: Optional[str]):
        """Set sort column, toggling direction if same column
        
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
        """Set value for an item
        
        Args:
            item_name: Name of the item
            value: New value
        """
        if item_name in self.economy:
            self.economy[item_name] = value
    
    def set_item_pinned(self, item_name: str, is_pinned: bool):
        """Set pinned state for an item
        
        Args:
            item_name: Name of the item
            is_pinned: True to pin, False to unpin
        """
        if is_pinned:
            self.pinned_items.add(item_name)
        else:
            self.pinned_items.discard(item_name)
    
    # ========== Table Structure ==========
    
    @staticmethod
    def _make_item_id(item_name: str) -> str:
        """Generate stable ID for economy item"""
        return f"item:{item_name}"
    
    def get_economy_table_structure(self) -> EconomyTableStructure:
        """Get complete table structure with IDs, values, and visibility
        
        Returns:
            EconomyTableStructure ready for rendering
        """
        filter_text = self._filter_text.lower()
        
        # Filter items
        filtered_items = [
            item_name for item_name in self.economy.keys()
            if not filter_text or filter_text in item_name.lower()
        ]
        
        # Sort items
        if self._sort_column == 'item':
            filtered_items.sort(key=lambda x: x.lower(), reverse=not self._sort_ascending)
        elif self._sort_column == 'value':
            filtered_items.sort(key=lambda x: self.economy[x], reverse=not self._sort_ascending)
        else:
            assert self._sort_column == 'locked'
            filtered_items.sort(key=lambda x: (x in self.pinned_items, x.lower()), reverse=not self._sort_ascending)
        
        # Build item structures
        items = []
        for item_name in filtered_items:
            item = EconomyItem(
                item_id=self._make_item_id(item_name),
                display_name=item_name,
                value=self.economy[item_name],
                is_pinned=item_name in self.pinned_items,
                is_visible=True  # Already filtered
            )
            items.append(item)
        
        return EconomyTableStructure(
            items=items,
            sort_column=self._sort_column,
            sort_ascending=self._sort_ascending
        )
    
    # ========== Actions ==========
    
    def reset_to_default(self):
        """Reset economy to default values"""
        from economy import get_default_economy
        
        self.economy.clear()
        self.economy.update(dict(get_default_economy()))
        self.pinned_items.clear()
        
        _LOGGER.info("Economy reset to default")
    
    def recompute_values(self):
        """Recompute economy values using gradient descent with pinned values
        
        Raises:
            Exception: If recomputation fails
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
        """Load economy from CSV file
        
        Args:
            filepath: Path to CSV file
            
        Raises:
            Exception: If load fails
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
        """Save economy to CSV file
        
        Args:
            filepath: Path to CSV file
            
        Raises:
            Exception: If save fails
        """
        from economy import save_economy_to_csv
        import os
        
        save_economy_to_csv(filepath, self.economy, self.pinned_items)
        
        filename = os.path.basename(filepath)
        _LOGGER.info("Economy saved to %s", filename)

