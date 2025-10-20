"""Factory editor component for designing and visualizing factories"""

import logging
import tkinter as tk
from tkinter import ttk

from ttkwidgets import CheckboxTreeview

from factory_controller import FactoryController
from graphviz_viewer import GraphvizViewer
from slider_spinbox import SliderSpinbox
from tooltip import Tooltip, TooltipZone

_LOGGER = logging.getLogger("satisgraphery")


class FactoryEditor(ttk.Frame):
    """factory configuration and visualization component"""
    
    def __init__(self, parent, controller, on_status_change=None):
        """Initialize the factory editor
        
        Args:
            parent: parent widget
            controller: FactoryController instance
            on_status_change: optional callback for status updates, called with status text
        """
        super().__init__(parent)
        
        # Initialize controller (MVC pattern) - single source of truth
        self.controller = controller
        
        self.on_status_change = on_status_change
        
        # Initialize tooltip tracking (view-only state)
        self.current_tooltip_item = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI components"""
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Left panel for controls
        control_frame = ttk.LabelFrame(
            self, text="Factory Configuration", padding="10"
        )
        control_frame.grid(
            row=0, column=0, rowspan=2, sticky=(tk.N, tk.S, tk.W), padx=(0, 10)
        )
        control_frame.columnconfigure(0, weight=1)
        
        # Outputs section
        ttk.Label(
            control_frame, text="Desired Outputs:", font=("TkDefaultFont", 9, "bold")
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Label(
            control_frame, text="Format: Material:Rate", font=("TkDefaultFont", 8)
        ).grid(row=1, column=0, sticky=tk.W)
        ttk.Label(
            control_frame, text="Example: Concrete:480", font=("TkDefaultFont", 8)
        ).grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        self.outputs_text = tk.Text(control_frame, width=30, height=8, wrap=tk.WORD, undo=True)
        self.outputs_text.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.outputs_text.insert("1.0", self.controller.get_outputs_text())
        # Bind to update controller on change
        self.outputs_text.bind("<<Modified>>", self._on_outputs_modified)
        
        # Inputs section
        ttk.Label(
            control_frame,
            text="Available Inputs (optional):",
            font=("TkDefaultFont", 9, "bold"),
        ).grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        ttk.Label(
            control_frame,
            text="One per line for separate conveyors",
            font=("TkDefaultFont", 8),
        ).grid(row=5, column=0, sticky=tk.W)
        ttk.Label(
            control_frame, text="Example: Limestone:480", font=("TkDefaultFont", 8)
        ).grid(row=6, column=0, sticky=tk.W, pady=(0, 5))
        
        self.inputs_text = tk.Text(control_frame, width=30, height=8, wrap=tk.WORD, undo=True)
        self.inputs_text.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.inputs_text.insert("1.0", self.controller.get_inputs_text())
        # Bind to update controller on change
        self.inputs_text.bind("<<Modified>>", self._on_inputs_modified)
        
        # Recipe filter section
        ttk.Label(
            control_frame, text="Recipe Filter:", font=("TkDefaultFont", 9, "bold")
        ).grid(row=8, column=0, sticky=tk.W, pady=(10, 5))
        
        # Search box for filtering recipes
        search_frame = ttk.Frame(control_frame)
        search_frame.grid(row=9, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        search_frame.columnconfigure(1, weight=1)
        
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, sticky=tk.W)
        self.recipe_search_var = tk.StringVar(value=self.controller.get_recipe_search_text())
        self.recipe_search_var.trace_add("write", self._on_search_changed)
        self.recipe_search_entry = ttk.Entry(search_frame, textvariable=self.recipe_search_var)
        self.recipe_search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # Create frame for checkbox tree and scrollbar
        tree_frame = ttk.Frame(control_frame)
        tree_frame.grid(row=10, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        tree_frame.columnconfigure(0, weight=1)
        
        self.recipe_tree = CheckboxTreeview(tree_frame, height=10, show='tree')
        self.recipe_tree.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        tree_scrollbar = ttk.Scrollbar(
            tree_frame, orient=tk.VERTICAL, command=self.recipe_tree.yview
        )
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.recipe_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # Setup tooltips for recipe tree items
        self.recipe_tooltip_zone = TooltipZone(self.recipe_tree, waittime=500)
        self.recipe_tree.bind("<Motion>", self._on_tree_motion)
        self.recipe_tree.bind("<Leave>", self._on_tree_leave)
        self.recipe_tree.bind("<Button-1>", self._on_tree_button_press, add=True)
        
        # Populate recipe tree
        self._populate_recipe_tree()
        
        # Bind recipe tree state changes to update enabled set and power warning
        self.recipe_tree.bind("<ButtonRelease-1>", lambda e: self._on_recipe_tree_change())
        
        # Optimization weights section
        ttk.Label(
            control_frame, text="Optimize For:", font=("TkDefaultFont", 9, "bold")
        ).grid(row=11, column=0, sticky=tk.W, pady=(10, 5))
        
        self.input_costs_weight = SliderSpinbox(
            control_frame,
            from_=0.0,
            to=1.0,
            increment=0.01,
            initial_value=self.controller.get_input_costs_weight(),
            label="Input Costs:",
        )
        self.input_costs_weight.grid(row=12, column=0, sticky=(tk.W, tk.E), pady=2)
        Tooltip(
            self.input_costs_weight,
            text="Drag the slider to the right to prioritize minimizing raw material usage from inputs",
            waittime=500
        )
        
        self.machine_counts_weight = SliderSpinbox(
            control_frame,
            from_=0.0,
            to=1.0,
            increment=0.01,
            initial_value=self.controller.get_machine_counts_weight(),
            label="Machine Counts:",
        )
        self.machine_counts_weight.grid(row=13, column=0, sticky=(tk.W, tk.E), pady=2)
        Tooltip(
            self.machine_counts_weight,
            text="Drag the slider to the right to prioritize fewer machines",
            waittime=500
        )
        
        self.power_consumption_weight = SliderSpinbox(
            control_frame,
            from_=0.0,
            to=1.0,
            increment=0.01,
            initial_value=self.controller.get_power_consumption_weight(),
            label="Power Usage:",
        )
        self.power_consumption_weight.grid(row=14, column=0, sticky=(tk.W, tk.E), pady=2)
        Tooltip(
            self.power_consumption_weight,
            text="Drag the slider to the right to prioritize minimizing power consumption",
            waittime=500
        )
        
        # Design power checkbox
        self.design_power_var = tk.BooleanVar(value=self.controller.get_design_power())
        self.design_power_check = ttk.Checkbutton(
            control_frame,
            text="Include power in design",
            variable=self.design_power_var,
            command=self._on_design_power_changed,
        )
        self.design_power_check.grid(row=15, column=0, sticky=tk.W, pady=(10, 0))
        
        # Warning label for power design without power recipes
        self.power_warning_label = ttk.Label(
            control_frame,
            text="Warning: No power-generating recipes are enabled",
            foreground="red",
            font=("TkDefaultFont", 8),
        )
        # Will be shown/hidden by _update_power_warning()
        
        # Generate button
        self.generate_btn = ttk.Button(
            control_frame, text="Generate Factory", command=self._generate_factory
        )
        self.generate_btn.grid(row=17, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Export button
        self.export_btn = ttk.Button(
            control_frame,
            text="Copy Graphviz to Clipboard",
            command=self._copy_graphviz,
        )
        self.export_btn.grid(row=18, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Create the graph viewer component (includes scrollbars)
        self.viewer = GraphvizViewer(self)
        self.viewer.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Initialize power warning state
        self._update_power_warning()
    
    def _on_outputs_modified(self, event):
        """Handle outputs text modification"""
        # Clear modified flag to prevent repeated events
        self.outputs_text.edit_modified(False)
        # Update controller state
        text = self.outputs_text.get("1.0", tk.END)
        self.controller.set_outputs_text(text)
    
    def _on_inputs_modified(self, event):
        """Handle inputs text modification"""
        # Clear modified flag to prevent repeated events
        self.inputs_text.edit_modified(False)
        # Update controller state
        text = self.inputs_text.get("1.0", tk.END)
        self.controller.set_inputs_text(text)
    
    def _on_search_changed(self, *args):
        """Handle search text change"""
        # Update controller state
        self.controller.set_recipe_search_text(self.recipe_search_var.get())
        # Refresh view based on new filter
        self._refresh_recipe_tree()
    
    def _on_design_power_changed(self):
        """Handle design power checkbox change"""
        # Update controller state
        self.controller.set_design_power(self.design_power_var.get())
        # Update UI based on new state
        self._update_power_warning()
    
    def _populate_recipe_tree(self):
        """Initial tree build using controller-provided structure"""
        # Clear tree
        for item in self.recipe_tree.get_children():
            self.recipe_tree.delete(item)
        
        # Get complete structure from controller
        tree_structure = self.controller.get_recipe_tree_structure()
        
        for machine_node in tree_structure.machines:
            if not machine_node.is_visible:
                continue
            
            # Create machine with controller's ID
            self.recipe_tree.insert("", "end",
                                   iid=machine_node.tree_id,
                                   text=machine_node.display_name)
            
            for recipe_node in machine_node.recipes:
                if not recipe_node.is_visible:
                    continue
                
                # Create recipe with controller's ID
                self.recipe_tree.insert(machine_node.tree_id, "end",
                                       iid=recipe_node.tree_id,
                                       text=recipe_node.display_name)
                
                # Set state from controller
                state = "checked" if recipe_node.is_enabled else "unchecked"
                self.recipe_tree.change_state(recipe_node.tree_id, state)
            
            # Set machine state from controller
            self.recipe_tree.change_state(machine_node.tree_id, machine_node.check_state)
    
    def _refresh_recipe_tree(self):
        """Smart refresh - preserves expansion and scroll automatically via attach/detach"""
        # Get fresh structure from controller
        tree_structure = self.controller.get_recipe_tree_structure()
        
        for machine_node in tree_structure.machines:
            machine_id = machine_node.tree_id
            
            if machine_node.is_visible:
                # Ensure machine exists and is attached
                try:
                    self.recipe_tree.move(machine_id, "", "end")
                except tk.TclError:
                    # Doesn't exist, create it
                    self.recipe_tree.insert("", "end",
                                           iid=machine_id,
                                           text=machine_node.display_name)
            else:
                # Hide machine
                try:
                    self.recipe_tree.detach(machine_id)
                except tk.TclError:
                    pass
            
            # Update recipes
            for recipe_node in machine_node.recipes:
                recipe_id = recipe_node.tree_id
                
                if recipe_node.is_visible:
                    # Ensure recipe exists and is attached
                    try:
                        self.recipe_tree.move(recipe_id, machine_id, "end")
                    except tk.TclError:
                        # Create it
                        self.recipe_tree.insert(machine_id, "end",
                                               iid=recipe_id,
                                               text=recipe_node.display_name)
                    
                    # Update check state
                    state = "checked" if recipe_node.is_enabled else "unchecked"
                    self.recipe_tree.change_state(recipe_id, state)
                else:
                    # Hide recipe
                    try:
                        self.recipe_tree.detach(recipe_id)
                    except tk.TclError:
                        pass
            
            # Update machine check state
            try:
                self.recipe_tree.change_state(machine_id, machine_node.check_state)
            except tk.TclError:
                pass
    
    def _on_recipe_tree_change(self):
        """Handle checkbox change - route IDs to controller"""
        checked_ids = self.recipe_tree.get_checked()
        
        # Get all visible recipe IDs (controller's IDs)
        all_recipe_ids = []
        for machine_id in self.recipe_tree.get_children(""):
            for recipe_id in self.recipe_tree.get_children(machine_id):
                if recipe_id.startswith("recipe:"):
                    all_recipe_ids.append(recipe_id)
        
        # Notify controller about each recipe's state
        for recipe_id in all_recipe_ids:
            self.controller.on_recipe_toggled(recipe_id, recipe_id in checked_ids)
        
        # Update power warning
        self._update_power_warning()
    
    
    def _update_power_warning(self):
        """show/hide warning based on controller state"""
        # Ask controller if warning should be shown
        if self.controller.should_show_power_warning():
            # Show warning
            self.power_warning_label.grid(row=16, column=0, sticky=tk.W, pady=(2, 5))
        else:
            # Hide warning
            self.power_warning_label.grid_remove()
    
    def _on_tree_motion(self, event):
        """handle mouse motion over recipe tree to show tooltips"""
        # Identify which item is under the cursor
        tree_id = self.recipe_tree.identify_row(event.y)
        
        # If we're on the same item, no need to update
        if tree_id == self.current_tooltip_item:
            return
        
        # Moving to different item - exit current tooltip
        if self.current_tooltip_item is not None:
            self.recipe_tooltip_zone.exit()
        
        self.current_tooltip_item = tree_id
        
        # If no item or empty, don't show tooltip
        if not tree_id:
            return
        
        # Ask controller for tooltip using its own ID
        tooltip_text = self.controller.get_tooltip_for_tree_id(tree_id)
        
        if tooltip_text:
            self.recipe_tooltip_zone.enter(tooltip_text)
    
    def _on_tree_leave(self, _event):
        """handle mouse leaving recipe tree to hide tooltip"""
        self.current_tooltip_item = None
        self.recipe_tooltip_zone.exit()
    
    def _on_tree_button_press(self, _event):
        """handle button press in recipe tree to dismiss tooltip"""
        self.current_tooltip_item = None
        self.recipe_tooltip_zone.exit()
    
    def _generate_factory(self):
        """Generate factory using controller"""
        try:
            self.generate_btn.config(state="disabled")
            self.update()
            
            # Sync UI state to controller before generating
            self._sync_ui_to_controller()
            
            # Generate factory from controller's current state
            graphviz_diagram = self.controller.generate_factory_from_state()
            
            # Update viewer with graphviz diagram
            self.viewer.dot = graphviz_diagram
        
        except ValueError as e:
            _LOGGER.error("Configuration error: %s", str(e))
        except Exception as e:
            _LOGGER.error("Factory generation failed: %s", str(e))
            import traceback
            traceback.print_exc()
        finally:
            self.generate_btn.config(state="normal")
    
    def _sync_ui_to_controller(self):
        """Sync all UI widget state to controller before operations"""
        # Sync text fields (may not have triggered <<Modified>> yet)
        self.controller.set_outputs_text(self.outputs_text.get("1.0", tk.END))
        self.controller.set_inputs_text(self.inputs_text.get("1.0", tk.END))
        
        # Sync recipe selection from tree checkboxes
        checked_ids = self.recipe_tree.get_checked()
        all_recipe_ids = []
        for machine_id in self.recipe_tree.get_children(""):
            for recipe_id in self.recipe_tree.get_children(machine_id):
                if recipe_id.startswith("recipe:"):
                    all_recipe_ids.append(recipe_id)
        
        # Update controller with current tree state
        for recipe_id in all_recipe_ids:
            self.controller.on_recipe_toggled(recipe_id, recipe_id in checked_ids)
        
        # Sync optimization weights
        self.controller.set_input_costs_weight(self.input_costs_weight.get())
        self.controller.set_machine_counts_weight(self.machine_counts_weight.get())
        self.controller.set_power_consumption_weight(self.power_consumption_weight.get())
        
        # Sync design power
        self.controller.set_design_power(self.design_power_var.get())
    
    def _copy_graphviz(self):
        """Copy graphviz source to clipboard"""
        try:
            graphviz_source = self.controller.copy_graphviz_source()
            
            if graphviz_source is None:
                return
            
            self.clipboard_clear()
            self.clipboard_append(graphviz_source)
        except Exception as e:
            _LOGGER.error("Clipboard copy failed: %s", str(e))

