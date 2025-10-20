"""Economy editor component for modifying item values and pinning"""

import logging
import tkinter as tk
from tkinter import ttk, filedialog
from _tkinter import TclError

from economy_controller import EconomyController

_LOGGER = logging.getLogger("satisgraphery")


class EconomyEditor(ttk.Frame):
    """scrollable economy editor with filter, editable values, and pinning"""
    
    def __init__(self, parent, controller, on_change=None):
        """Initialize the economy editor
        
        Args:
            parent: parent widget
            controller: EconomyController instance
            on_change: optional callback when economy changes
        """
        super().__init__(parent)
        
        # Initialize controller
        self.controller = controller
        self.on_change = on_change
        
        self._setup_ui()
    
    def _bind_mousewheel(self, widget):
        """Bind mouse wheel events to widget for scrolling"""
        def on_mousewheel(event):
            # Windows and MacOS
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def on_mousewheel_linux(event):
            # Linux
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
        
        # Bind for Windows and MacOS
        widget.bind("<MouseWheel>", on_mousewheel)
        # Bind for Linux
        widget.bind("<Button-4>", on_mousewheel_linux)
        widget.bind("<Button-5>", on_mousewheel_linux)
    
    def _setup_ui(self):
        """Setup the UI components"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Top controls frame
        controls_frame = ttk.Frame(self, padding="10")
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Filter box
        ttk.Label(controls_frame, text="Filter:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.filter_var = tk.StringVar(value=self.controller.get_filter_text())
        self.filter_var.trace_add('write', self._on_filter_changed)
        filter_entry = ttk.Entry(controls_frame, textvariable=self.filter_var, width=30)
        filter_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Buttons
        ttk.Button(controls_frame, text="Reset to Default", command=self._reset_economy).grid(
            row=0, column=2, padx=2
        )
        ttk.Button(controls_frame, text="Rebalance Values", command=self._recompute_economy).grid(
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
        self.canvas = tk.Canvas(table_frame, highlightthickness=0, bg="#FFFFFF")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.canvas.yview)
        
        # Frame inside canvas to hold the grid
        self.grid_frame = tk.Frame(self.canvas, bg="#FFFFFF")
        
        # Configure grid columns to expand
        self.grid_frame.columnconfigure(0, weight=2)  # Item column wider
        self.grid_frame.columnconfigure(1, weight=1)  # Value column
        self.grid_frame.columnconfigure(2, weight=1)  # Locked column
        
        # Configure canvas
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Create window in canvas
        canvas_frame = self.canvas.create_window((0, 0), window=self.grid_frame, anchor='nw')
        
        # Update scroll region when frame changes size
        def on_frame_configure(_event):
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        
        def on_canvas_configure(_event):
            self.canvas.itemconfig(canvas_frame, width=self.canvas.winfo_width())
        
        self.grid_frame.bind('<Configure>', on_frame_configure)
        self.canvas.bind('<Configure>', on_canvas_configure)
        
        # Bind mouse wheel scrolling
        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.grid_frame)
        
        # Headers (clickable for sorting)
        header_bg = "#D3D3D3"  # light gray
        header_item = tk.Label(self.grid_frame, text="Item", font=("TkDefaultFont", 9, "bold"), 
                               cursor="hand2", bg=header_bg, relief=tk.FLAT, anchor=tk.W, padx=5, pady=8)
        header_item.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=1, pady=(1, 2))
        header_item.bind("<Button-1>", lambda e: self._on_header_click('item'))
        self._bind_mousewheel(header_item)
        
        header_value = tk.Label(self.grid_frame, text="Value", font=("TkDefaultFont", 9, "bold"), 
                                cursor="hand2", bg=header_bg, relief=tk.FLAT, anchor=tk.W, padx=5, pady=8)
        header_value.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=1, pady=(1, 2))
        header_value.bind("<Button-1>", lambda e: self._on_header_click('value'))
        self._bind_mousewheel(header_value)
        
        header_locked = tk.Label(self.grid_frame, text="Locked", font=("TkDefaultFont", 9, "bold"), 
                                 cursor="hand2", bg=header_bg, relief=tk.FLAT, anchor=tk.W, padx=5, pady=8)
        header_locked.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=1, pady=(1, 2))
        header_locked.bind("<Button-1>", lambda e: self._on_header_click('locked'))
        self._bind_mousewheel(header_locked)
        
        # Store header references for updating sort indicators
        self.headers = {
            'item': header_item,
            'value': header_value,
            'locked': header_locked
        }
        
        # Store references to widgets
        self.widgets = {}
        
        # Populate the table
        self._populate_table()
    
    def _on_filter_changed(self, *args):
        """Handle filter text change"""
        self.controller.set_filter_text(self.filter_var.get())
        self._populate_table()
    
    def _on_header_click(self, column):
        """Handle header click for sorting"""
        self.controller.set_sort(column)
        self._update_header_labels()
        self._populate_table()
    
    def _update_header_labels(self):
        """Update header labels with sort indicators"""
        header_texts = self.controller.get_header_texts()
        for col, header in self.headers.items():
            header.config(text=header_texts[col])
    
    def _populate_table(self):
        """Populate table from controller structure"""
        # Clear existing widgets (except headers)
        for child in list(self.grid_frame.winfo_children()):
            if child not in self.headers.values():
                child.destroy()
        
        self.widgets.clear()
        
        # Get structure from controller
        table_structure = self.controller.get_economy_table_structure()
        
        # Add rows with alternating background colors
        row_bg_even = "#FFFFFF"  # white
        row_bg_odd = "#F5F5F5"   # very light gray
        
        for idx, economy_item in enumerate(table_structure.items, start=1):
            row_bg = row_bg_even if idx % 2 == 0 else row_bg_odd
            
            # Item name label
            label = tk.Label(self.grid_frame, text=economy_item.display_name, bg=row_bg, 
                           anchor=tk.W, padx=5, pady=5)
            label.grid(row=idx, column=0, sticky=(tk.W, tk.E), padx=1, pady=1)
            self._bind_mousewheel(label)
            
            # Value spinbox - wrap in frame for background
            value_frame = tk.Frame(self.grid_frame, bg=row_bg)
            value_frame.grid(row=idx, column=1, sticky=(tk.W, tk.E), padx=1, pady=1)
            
            value_var = tk.DoubleVar(value=economy_item.value)
            entry = ttk.Spinbox(
                value_frame, 
                textvariable=value_var, 
                width=15,
                from_=0.0,
                to=1000000.0,
                increment=1.0
            )
            entry.pack(padx=5, pady=5)
            self._bind_mousewheel(entry)
            self._bind_mousewheel(value_frame)
            
            # Bind Enter to move to next row's spinbox, Escape to canvas
            def make_enter_handler(current_idx, items_list):
                def on_enter(_event):
                    if current_idx < len(items_list) - 1:
                        next_item = items_list[current_idx + 1].display_name
                        if next_item in self.widgets:
                            next_entry = self.widgets[next_item]['entry']
                            next_entry.focus_set()
                            next_entry.select_range(0, tk.END)
                            # Scroll to ensure the widget is visible
                            next_entry.update_idletasks()
                            bbox = self.canvas.bbox('all')
                            if bbox:
                                y_pos = next_entry.winfo_y()
                                height = next_entry.winfo_height()
                                canvas_height = self.canvas.winfo_height()
                                total_height = bbox[3] - bbox[1]
                                
                                # Get current scroll position
                                current_view = self.canvas.yview()
                                visible_top = current_view[0] * total_height
                                visible_bottom = current_view[1] * total_height
                                
                                # Only scroll if widget is not fully visible
                                if y_pos < visible_top:
                                    # Widget is above visible area, scroll up
                                    self.canvas.yview_moveto(y_pos / total_height)
                                elif y_pos + height > visible_bottom:
                                    # Widget is below visible area, scroll down
                                    target_y = (y_pos + height - canvas_height)
                                    self.canvas.yview_moveto(target_y / total_height)
                    else:
                        self.canvas.focus_set()
                    return 'break'
                return on_enter
            
            def on_escape(_event):
                self.canvas.focus_set()
                return 'break'
            
            entry.bind('<Return>', make_enter_handler(idx - 1, table_structure.items))
            entry.bind('<Escape>', on_escape)
            
            # Restore valid value on focus out
            def make_focusout_handler(name, var):
                def on_focus_out(_event):
                    try:
                        value_str = var.get()
                        float(value_str)  # validate
                    except (ValueError, TclError):
                        # restore original value from controller
                        var.set(self.controller.economy[name])
                return on_focus_out
            
            entry.bind('<FocusOut>', make_focusout_handler(economy_item.display_name, value_var))
            
            # Bind value changes
            def make_value_callback(name, var):
                def on_value_change(*_args):
                    try:
                        value_str = var.get()
                        if value_str == "":
                            return  # empty value, don't assign
                        new_value = float(value_str)
                        self.controller.set_item_value(name, new_value)
                        if self.on_change:
                            self.on_change()
                    except (ValueError, TclError):
                        pass  # Invalid input, ignore
                return on_value_change
            
            value_var.trace_add('write', make_value_callback(economy_item.display_name, value_var))
            
            # Pinned checkbox - wrap in frame for background
            checkbox_frame = tk.Frame(self.grid_frame, bg=row_bg)
            checkbox_frame.grid(row=idx, column=2, sticky=(tk.W, tk.E), padx=1, pady=1)
            
            pinned_var = tk.BooleanVar(value=economy_item.is_pinned)
            checkbox = ttk.Checkbutton(
                checkbox_frame,
                variable=pinned_var,
                command=lambda name=economy_item.display_name, var=pinned_var: self._on_pinned_toggle(name, var)
            )
            checkbox.pack(padx=5, pady=5)
            self._bind_mousewheel(checkbox)
            self._bind_mousewheel(checkbox_frame)
            
            # Store widget references
            self.widgets[economy_item.display_name] = {
                'label': label,
                'entry': entry,
                'checkbox': checkbox,
                'value_var': value_var,
                'pinned_var': pinned_var
            }
    
    def _on_pinned_toggle(self, item_name, pinned_var):
        """Handle pinned checkbox toggle"""
        self.controller.set_item_pinned(item_name, pinned_var.get())
        
        if self.on_change:
            self.on_change()
    
    def _reset_economy(self):
        """Reset economy to default values"""
        self.controller.reset_to_default()
        self._populate_table()
        
        if self.on_change:
            self.on_change()
    
    def _recompute_economy(self):
        """Recompute economy values"""
        try:
            self.controller.recompute_values()
            self._populate_table()
            
            if self.on_change:
                self.on_change()
        except Exception as e:
            _LOGGER.error("Economy recomputation failed: %s", str(e))
            import traceback
            traceback.print_exc()
            raise
    
    def _load_economy(self):
        """Load economy from CSV file"""
        filepath = filedialog.askopenfilename(
            title="Load Economy",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            self.controller.load_from_csv(filepath)
            self._populate_table()
            
            if self.on_change:
                self.on_change()
        except Exception as e:
            _LOGGER.error("Economy load failed: %s", str(e))
            raise
    
    def _save_economy(self):
        """Save economy to CSV file"""
        filepath = filedialog.asksaveasfilename(
            title="Save Economy",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            self.controller.save_to_csv(filepath)
        except Exception as e:
            _LOGGER.error("Economy save failed: %s", str(e))
            raise
    
    def refresh(self):
        """Refresh the table display"""
        self._populate_table()

