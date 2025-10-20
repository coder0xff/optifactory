"""Factory editor component for designing and visualizing factories"""

import logging
import tkinter as tk
from tkinter import ttk

from ttkwidgets import CheckboxTreeview

from factory import design_factory
from graphviz_viewer import GraphvizViewer
from parsing_utils import parse_material_rate
from recipes import get_all_recipes_by_machine, get_recipes_for
from slider_spinbox import SliderSpinbox
from tooltip import Tooltip, TooltipZone

_LOGGER = logging.getLogger("satisgraphery")


class FactoryEditor(ttk.Frame):
    """factory configuration and visualization component"""
    
    def __init__(self, parent, economy, on_status_change=None):
        """Initialize the factory editor
        
        Args:
            parent: parent widget
            economy: dict of item names to values (reference that may be updated)
            on_status_change: optional callback for status updates, called with status text
        """
        super().__init__(parent)
        
        self.economy = economy
        self.on_status_change = on_status_change
        
        # Initialize tooltip tracking
        self.current_tooltip_item = None
        
        # Initialize enabled recipes with default set
        self.enabled_recipes = set()
        for machine_name, recipes in get_all_recipes_by_machine().items():
            for recipe_name, recipe in recipes.items():
                if "MWm" not in recipe.outputs and machine_name != "Packager":
                    self.enabled_recipes.add(recipe_name)
        
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
        
        self.outputs_text = tk.Text(control_frame, width=30, height=8, wrap=tk.WORD)
        self.outputs_text.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.outputs_text.insert("1.0", "Concrete:480")
        
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
        
        self.inputs_text = tk.Text(control_frame, width=30, height=8, wrap=tk.WORD)
        self.inputs_text.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        default_input_text = (
            "# Leave empty to auto-detect\n"
            "# Or specify like:\n"
            "# Limestone:480\n"
            "# Limestone:480\n"
            "# Limestone:480"
        )
        self.inputs_text.insert("1.0", default_input_text)
        
        # Recipe filter section
        ttk.Label(
            control_frame, text="Recipe Filter:", font=("TkDefaultFont", 9, "bold")
        ).grid(row=8, column=0, sticky=tk.W, pady=(10, 5))
        
        # Search box for filtering recipes
        search_frame = ttk.Frame(control_frame)
        search_frame.grid(row=9, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        search_frame.columnconfigure(0, weight=1)
        
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, sticky=tk.W)
        self.recipe_search_var = tk.StringVar()
        self.recipe_search_var.trace_add("write", lambda *args: self._refresh_recipe_tree())
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
            initial_value=1.0,
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
            initial_value=0.0,
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
            initial_value=1.0,
            label="Power Usage:",
        )
        self.power_consumption_weight.grid(row=14, column=0, sticky=(tk.W, tk.E), pady=2)
        Tooltip(
            self.power_consumption_weight,
            text="Drag the slider to the right to prioritize minimizing power consumption",
            waittime=500
        )
        
        # Design power checkbox
        self.design_power_var = tk.BooleanVar(value=False)
        self.design_power_check = ttk.Checkbutton(
            control_frame,
            text="Include power in design",
            variable=self.design_power_var,
            command=self._update_power_warning,
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
    
    def _populate_recipe_tree(self):
        """Populate the recipe tree with machines and recipes, all with correct enabled state"""
        # Store metadata for each tree item for filtering
        self.recipe_metadata = {}
        
        for machine_name, recipes in get_all_recipes_by_machine().items():
            # Add machine as parent node
            machine_id = self.recipe_tree.insert("", "end", text=machine_name)
            self.recipe_metadata[machine_id] = {
                "type": "machine",
                "name": machine_name.lower(),
                "children": []
            }
            
            any_checked = False
            any_unchecked = False
            # Add recipes as children
            for recipe_name, recipe in recipes.items():
                recipe_id = self.recipe_tree.insert(machine_id, "end", text=recipe_name)
                
                # Store searchable content for this recipe
                input_names = [name.lower() for name in recipe.inputs.keys()]
                output_names = [name.lower() for name in recipe.outputs.keys()]
                self.recipe_metadata[recipe_id] = {
                    "type": "recipe",
                    "name": recipe_name.lower(),
                    "inputs": input_names,
                    "outputs": output_names,
                    "parent": machine_id
                }
                self.recipe_metadata[machine_id]["children"].append(recipe_id)
                
                # Use saved enabled state
                is_enabled = recipe_name in self.enabled_recipes
                
                if is_enabled:
                    self.recipe_tree.change_state(recipe_id, "checked")
                    any_checked = True
                else:
                    self.recipe_tree.change_state(recipe_id, "unchecked")
                    any_unchecked = True
            
            if any_checked and any_unchecked:
                self.recipe_tree.change_state(machine_id, "tristate")
            elif any_checked:
                self.recipe_tree.change_state(machine_id, "checked")
            else:
                self.recipe_tree.change_state(machine_id, "unchecked")
    
    def _refresh_recipe_tree(self):
        """Refresh the recipe tree based on current search text"""
        # Don't update enabled_recipes here - just refresh the display
        # The enabled state is independent of visibility
        search_text = self.recipe_search_var.get().lower()
        
        # Process all machines (use metadata to get all, not just visible ones)
        for machine_id in self.recipe_metadata.keys():
            if self.recipe_metadata[machine_id]["type"] != "machine":
                continue
                
            metadata = self.recipe_metadata[machine_id]
            visible_children = []
            
            # Check each recipe child
            for recipe_id in metadata["children"]:
                recipe_meta = self.recipe_metadata[recipe_id]
                
                # Check if search text matches recipe name, inputs, or outputs
                if not search_text:
                    # Empty search - show everything
                    matches = True
                else:
                    matches = (
                        search_text in recipe_meta["name"]
                        or any(search_text in inp for inp in recipe_meta["inputs"])
                        or any(search_text in out for out in recipe_meta["outputs"])
                    )
                
                if matches:
                    visible_children.append(recipe_id)
                    # Reattach recipe to tree (move works even if already attached)
                    self.recipe_tree.move(recipe_id, machine_id, "end")
                else:
                    # Detach recipe from tree (hides it but preserves state)
                    try:
                        self.recipe_tree.detach(recipe_id)
                    except tk.TclError:
                        pass  # Already detached
            
            # Show/hide machine based on whether it has visible children
            if visible_children:
                # Reattach machine to tree (move works even if already attached)
                self.recipe_tree.move(machine_id, "", "end")
            else:
                # Detach machine from tree
                try:
                    self.recipe_tree.detach(machine_id)
                except tk.TclError:
                    pass  # Already detached
        
        # Update parent states after all children have been attached/detached
        for machine_id in self.recipe_metadata.keys():
            if self.recipe_metadata[machine_id]["type"] != "machine":
                continue
            
            # Get visible children for this machine
            visible_children = []
            for recipe_id in self.recipe_metadata[machine_id]["children"]:
                # Check if recipe is attached (visible)
                try:
                    parent = self.recipe_tree.parent(recipe_id)
                    if parent:  # Has a parent, so it's attached
                        visible_children.append(recipe_id)
                except tk.TclError:
                    pass
            
            if visible_children:
                # Update parent check state based on visible children
                # Count checked children by checking each one individually
                visible_checked_count = 0
                for recipe_id in visible_children:
                    if self.recipe_tree.tag_has("checked", recipe_id):
                        visible_checked_count += 1
                
                # Set the appropriate state based on how many visible children are checked
                if visible_checked_count == 0:
                    self.recipe_tree.change_state(machine_id, "unchecked")
                elif visible_checked_count == len(visible_children):
                    self.recipe_tree.change_state(machine_id, "checked")
                else:
                    self.recipe_tree.change_state(machine_id, "tristate")
    
    def _on_recipe_tree_change(self):
        """Handle recipe tree checkbox changes"""
        # Get currently visible recipes
        visible_recipes = set()
        for machine_id in self.recipe_tree.get_children(""):
            for recipe_id in self.recipe_tree.get_children(machine_id):
                recipe_name = self.recipe_tree.item(recipe_id, "text")
                visible_recipes.add(recipe_name)
        
        # Get which visible recipes are checked
        visible_checked = self._get_selected_recipes()
        
        # Update enabled_recipes: remove all visible recipes, then add back the checked ones
        # This preserves the state of non-visible recipes
        self.enabled_recipes = (self.enabled_recipes - visible_recipes) | visible_checked
        
        # Update power warning
        self._update_power_warning()
    
    def _get_selected_recipes(self):
        """Get set of selected recipe names from the checkbox tree"""
        # get_checked() returns leaf nodes only (recipes, not machines)
        checked_items = self.recipe_tree.get_checked()
        selected_recipes = {
            self.recipe_tree.item(item_id, "text") for item_id in checked_items
        }
        return selected_recipes
    
    def _update_power_warning(self):
        """show/hide warning if design_power is enabled but no power recipes are enabled"""
        design_power = self.design_power_var.get()
        
        if design_power:
            # Check if any power-generating recipes are enabled
            enablement_set = self._get_selected_recipes()
            power_recipes = get_recipes_for("MWm", enablement_set)
            
            if not power_recipes:
                # Show warning
                self.power_warning_label.grid(row=16, column=0, sticky=tk.W, pady=(2, 5))
            else:
                # Hide warning
                self.power_warning_label.grid_remove()
        else:
            # Hide warning when design_power is disabled
            self.power_warning_label.grid_remove()
    
    def _on_tree_motion(self, event):
        """handle mouse motion over recipe tree to show tooltips"""
        # Identify which item is under the cursor
        item_id = self.recipe_tree.identify_row(event.y)
        
        # If we're on the same item, no need to update
        if item_id == self.current_tooltip_item:
            return
        
        # Moving to different item - exit current tooltip
        if self.current_tooltip_item is not None:
            self.recipe_tooltip_zone.exit()
        
        self.current_tooltip_item = item_id
        
        # If no item or empty, don't show tooltip
        if not item_id:
            return
        
        # Check if this is a recipe (not a machine)
        metadata = self.recipe_metadata.get(item_id)
        if not metadata or metadata["type"] != "recipe":
            return
        
        # Get the recipe name and look up the actual recipe data
        recipe_name = self.recipe_tree.item(item_id, "text")
        
        # Get recipe from all recipes
        all_recipes = get_all_recipes_by_machine()
        recipe = None
        for machine_recipes in all_recipes.values():
            if recipe_name in machine_recipes:
                recipe = machine_recipes[recipe_name]
                break
        
        if not recipe:
            return
        
        # Format tooltip text and enter the zone
        tooltip_text = self._format_recipe_tooltip(recipe)
        self.recipe_tooltip_zone.enter(tooltip_text)
    
    def _on_tree_leave(self, _event):
        """handle mouse leaving recipe tree to hide tooltip"""
        self.current_tooltip_item = None
        self.recipe_tooltip_zone.exit()
    
    def _on_tree_button_press(self, _event):
        """handle button press in recipe tree to dismiss tooltip"""
        self.current_tooltip_item = None
        self.recipe_tooltip_zone.exit()
    
    def _format_recipe_tooltip(self, recipe):
        """format recipe inputs/outputs for tooltip display"""
        lines = []
        
        if recipe.inputs:
            lines.append("Inputs:")
            for material, rate in recipe.inputs.items():
                lines.append(f"  - {material}: {rate}/min")
        
        if recipe.outputs:
            if lines:  # Add spacing if we had inputs
                lines.append("")
            lines.append("Outputs:")
            for material, rate in recipe.outputs.items():
                lines.append(f"  - {material}: {rate}/min")
        
        return "\n".join(lines)
    
    def _parse_config_text(self, text):
        """Parse configuration text into list of (material, rate) tuples.
        
        Format: Material:Rate, one per line
        Lines starting with # are comments and ignored
        Empty lines are ignored
        """
        items = []
        for line in text.strip().split("\n"):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            
            # Parse Material:Rate
            material, rate = parse_material_rate(line)
            items.append((material, rate))
        
        return items
    
    def _generate_factory(self):
        """Generate factory based on current inputs"""
        try:
            if self.on_status_change:
                self.on_status_change("Generating factory...")
            
            self.generate_btn.config(state="disabled")
            self.update()
            
            # Parse outputs
            outputs_text = self.outputs_text.get("1.0", tk.END)
            outputs_list = self._parse_config_text(outputs_text)
            if not outputs_list:
                if self.on_status_change:
                    self.on_status_change("Error: No outputs specified")
                self.generate_btn.config(state="normal")
                return
            
            outputs = dict(outputs_list)
            
            # Parse inputs
            inputs_text = self.inputs_text.get("1.0", tk.END)
            inputs = self._parse_config_text(inputs_text)
            
            # Get selected recipes
            enablement_set = self._get_selected_recipes()
            
            # Get optimization weights
            input_costs_weight = self.input_costs_weight.get()
            machine_counts_weight = self.machine_counts_weight.get()
            power_consumption_weight = self.power_consumption_weight.get()
            
            # Get power design setting
            design_power = self.design_power_var.get()
            
            # Generate factory
            _LOGGER.info("Generating factory for outputs: %s", outputs)
            factory = design_factory(
                outputs=outputs,
                inputs=inputs,
                mines=[],
                enablement_set=enablement_set,
                economy=self.economy,
                input_costs_weight=input_costs_weight,
                machine_counts_weight=machine_counts_weight,
                power_consumption_weight=power_consumption_weight,
                design_power=design_power,
            )
            
            # Update viewer with new diagram (dot setter handles all cleanup)
            self.viewer.dot = factory.network
            
            if self.on_status_change:
                self.on_status_change("Factory generated successfully")
            _LOGGER.info("Factory generated successfully")
        
        except ValueError as e:
            if self.on_status_change:
                self.on_status_change(f"Error: {str(e)}")
            _LOGGER.error("Configuration error: %s", str(e))
        except Exception as e:
            if self.on_status_change:
                self.on_status_change(f"Error: {str(e)}")
            _LOGGER.error("Factory generation failed: %s", str(e))
            import traceback
            traceback.print_exc()
        finally:
            self.generate_btn.config(state="normal")
    
    def _copy_graphviz(self):
        """Copy graphviz source to clipboard"""
        try:
            if self.viewer.dot is None:
                if self.on_status_change:
                    self.on_status_change("No graph to export")
                return
            
            graphviz_source = self.viewer.dot.source
            self.clipboard_clear()
            self.clipboard_append(graphviz_source)
            if self.on_status_change:
                self.on_status_change("Graphviz source copied to clipboard")
            _LOGGER.info("Graphviz source copied to clipboard")
        except Exception as e:
            if self.on_status_change:
                self.on_status_change(f"Error copying to clipboard: {str(e)}")
            _LOGGER.error("Clipboard copy failed: %s", str(e))

