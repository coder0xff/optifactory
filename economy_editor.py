"""Economy editor component for modifying item values and pinning"""

import logging
import os
import tkinter as tk
from tkinter import ttk, filedialog

_LOGGER = logging.getLogger("satisgraphery")


class EconomyEditor(ttk.Frame):
    """scrollable economy editor with filter, editable values, and pinning"""
    
    def __init__(self, parent, economy, pinned_items, on_change=None):
        """Initialize the economy editor
        
        Args:
            parent: parent widget
            economy: dict of item names to values
            pinned_items: set of pinned item names
            on_change: optional callback when economy changes
        """
        super().__init__(parent)
        
        self.economy = economy
        self.pinned_items = pinned_items
        self.on_change = on_change
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Top controls frame
        controls_frame = ttk.Frame(self, padding="10")
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Filter box
        ttk.Label(controls_frame, text="Filter:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add('write', lambda *args: self._populate_table())
        filter_entry = ttk.Entry(controls_frame, textvariable=self.filter_var, width=30)
        filter_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Buttons
        ttk.Button(controls_frame, text="Reset to Default", command=self._reset_economy).grid(
            row=0, column=2, padx=2
        )
        ttk.Button(controls_frame, text="Recompute Values", command=self._recompute_economy).grid(
            row=0, column=3, padx=2
        )
        ttk.Button(controls_frame, text="Load CSV", command=self._load_economy).grid(
            row=0, column=4, padx=2
        )
        ttk.Button(controls_frame, text="Save CSV", command=self._save_economy).grid(
            row=0, column=5, padx=2
        )
        
        controls_frame.columnconfigure(1, weight=1)
        
        # Scrollable table frame
        table_frame = ttk.Frame(self)
        table_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Create canvas with scrollbar for scrollable content
        canvas = tk.Canvas(table_frame, highlightthickness=0)
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=canvas.yview)
        
        # Frame inside canvas to hold the grid
        self.grid_frame = ttk.Frame(canvas)
        
        # Configure canvas
        canvas.configure(yscrollcommand=vsb.set)
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Create window in canvas
        canvas_frame = canvas.create_window((0, 0), window=self.grid_frame, anchor='nw')
        
        # Update scroll region when frame changes size
        def on_frame_configure(_event):
            canvas.configure(scrollregion=canvas.bbox('all'))
        
        def on_canvas_configure(_event):
            canvas.itemconfig(canvas_frame, width=canvas.winfo_width())
        
        self.grid_frame.bind('<Configure>', on_frame_configure)
        canvas.bind('<Configure>', on_canvas_configure)
        
        # Headers
        ttk.Label(self.grid_frame, text="Item", font=("TkDefaultFont", 9, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        ttk.Label(self.grid_frame, text="Value", font=("TkDefaultFont", 9, "bold")).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=5
        )
        ttk.Label(self.grid_frame, text="Pinned", font=("TkDefaultFont", 9, "bold")).grid(
            row=0, column=2, sticky=tk.W, padx=5, pady=5
        )
        
        # Store references to widgets
        self.widgets = {}
        
        # Populate the table
        self._populate_table()
    
    def _populate_table(self):
        """Populate the table with current values"""
        # Clear existing widgets (except headers)
        for widget_dict in self.widgets.values():
            widget_dict['label'].destroy()
            widget_dict['entry'].destroy()
            widget_dict['checkbox'].destroy()
        
        self.widgets.clear()
        
        # Filter items
        filter_text = self.filter_var.get().lower()
        filtered_items = [
            item_name for item_name in sorted(self.economy.keys())
            if not filter_text or filter_text in item_name.lower()
        ]
        
        # Add rows
        for idx, item_name in enumerate(filtered_items, start=1):
            value = self.economy[item_name]
            
            # Item name label
            label = ttk.Label(self.grid_frame, text=item_name)
            label.grid(row=idx, column=0, sticky=tk.W, padx=5, pady=2)
            
            # Value entry
            value_var = tk.StringVar(value=f"{value:.6f}")
            entry = ttk.Entry(self.grid_frame, textvariable=value_var, width=15)
            entry.grid(row=idx, column=1, sticky=tk.W, padx=5, pady=2)
            
            # Bind value changes
            def make_value_callback(name, var):
                def on_value_change(*_args):
                    try:
                        new_value = float(var.get())
                        self.economy[name] = new_value
                        if self.on_change:
                            self.on_change()
                    except ValueError:
                        pass  # Invalid input, ignore
                return on_value_change
            
            value_var.trace_add('write', make_value_callback(item_name, value_var))
            
            # Pinned checkbox
            pinned_var = tk.BooleanVar(value=item_name in self.pinned_items)
            checkbox = ttk.Checkbutton(
                self.grid_frame,
                variable=pinned_var,
                command=lambda name=item_name, var=pinned_var: self._on_pinned_toggle(name, var)
            )
            checkbox.grid(row=idx, column=2, sticky=tk.W, padx=5, pady=2)
            
            # Store widget references
            self.widgets[item_name] = {
                'label': label,
                'entry': entry,
                'checkbox': checkbox,
                'value_var': value_var,
                'pinned_var': pinned_var
            }
    
    def _on_pinned_toggle(self, item_name, pinned_var):
        """Handle pinned checkbox toggle"""
        if pinned_var.get():
            self.pinned_items.add(item_name)
        else:
            self.pinned_items.discard(item_name)
        
        if self.on_change:
            self.on_change()
    
    def _reset_economy(self):
        """Reset economy to default values"""
        from economy import get_default_economy
        
        self.economy.clear()
        self.economy.update(get_default_economy())
        self.pinned_items.clear()
        self._populate_table()
        
        if self.on_change:
            self.on_change()
        
        _LOGGER.info("Economy reset to default")
    
    def _recompute_economy(self):
        """Recompute economy values using gradient descent with pinned values"""
        try:
            from economy import compute_item_values
            
            # Build pinned_values dict from pinned items
            pinned_values = {item: self.economy[item] for item in self.pinned_items}
            
            # Recompute
            new_economy = compute_item_values(pinned_values=pinned_values)
            self.economy.clear()
            self.economy.update(new_economy)
            
            self._populate_table()
            
            if self.on_change:
                self.on_change()
            
            _LOGGER.info("Economy values recomputed successfully")
        except Exception as e:
            _LOGGER.error("Economy recomputation failed: %s", str(e))
            import traceback
            traceback.print_exc()
            raise
    
    def _load_economy(self):
        """Load economy from CSV file"""
        from economy import load_economy_from_csv
        
        filepath = filedialog.askopenfilename(
            title="Load Economy",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            loaded_economy, loaded_pinned = load_economy_from_csv(filepath)
            self.economy.clear()
            self.economy.update(loaded_economy)
            self.pinned_items.clear()
            self.pinned_items.update(loaded_pinned)
            
            self._populate_table()
            
            if self.on_change:
                self.on_change()
            
            filename = os.path.basename(filepath)
            _LOGGER.info("Economy loaded from %s", filename)
        except Exception as e:
            _LOGGER.error("Economy load failed: %s", str(e))
            raise
    
    def _save_economy(self):
        """Save economy to CSV file"""
        from economy import save_economy_to_csv
        
        filepath = filedialog.asksaveasfilename(
            title="Save Economy",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            save_economy_to_csv(filepath, self.economy, self.pinned_items)
            filename = os.path.basename(filepath)
            _LOGGER.info("Economy saved to %s", filename)
        except Exception as e:
            _LOGGER.error("Economy save failed: %s", str(e))
            raise
    
    def refresh(self):
        """Refresh the table display"""
        self._populate_table()

