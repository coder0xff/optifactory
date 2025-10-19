"""Plan Satisfactory systems."""

# pylint: disable=logging-fstring-interpolation,import-outside-toplevel,bare-except,broad-exception-caught

import logging
import sys
import tkinter as tk
from tkinter import ttk

from ttkwidgets import CheckboxTreeview

from economy_editor import EconomyEditor
from factory import design_factory
from graphviz_viewer import GraphvizViewer
from parsing_utils import parse_material_rate
from recipes import get_all_recipes_by_machine, get_recipes_for
from slider_spinbox import SliderSpinbox

_LOGGER = logging.getLogger("satisgraphery")
_LOGGER.setLevel(logging.DEBUG)


class StatusBarLogHandler(logging.Handler):
    """Custom log handler that updates the status bar"""

    def __init__(self, root, status_label):
        super().__init__()
        self.root = root
        self.status_label = status_label
        self.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        self.setFormatter(formatter)

    def emit(self, record):
        """Emit a log record to the status bar"""
        try:
            msg = self.format(record)
            # Update status bar in main thread
            self.root.after(10, lambda: self.status_label.config(text=msg))
        except Exception:
            print(f"Error updating status bar: {record}", file=sys.stderr)


class MainWindow(tk.Tk):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.title("Satisgraphery - Factory Planner")
        
        # Economy state
        from economy import get_default_economy
        self.economy = get_default_economy()
        self.pinned_items = set()
        
        self._setup_ui()

    def _setup_ui(self):
        """Setup the main window UI components"""
        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create Factory tab
        factory_frame = ttk.Frame(self.notebook)
        self.notebook.add(factory_frame, text="Factory")
        factory_frame.columnconfigure(1, weight=1)
        factory_frame.rowconfigure(1, weight=1)
        
        # Create Economy tab
        economy_frame = ttk.Frame(self.notebook)
        self.notebook.add(economy_frame, text="Economy")
        
        # Setup Factory tab
        self._setup_factory_tab(factory_frame)
        
        # Setup Economy tab
        self._setup_economy_tab(economy_frame)
        
        # Status label (below tabs)
        self.status_label = ttk.Label(
            main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_label.grid(
            row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0)
        )
        
        # Setup custom log handler for status bar
        status_handler = StatusBarLogHandler(self, self.status_label)
        _LOGGER.addHandler(status_handler)
        
        # Generate initial factory
        self._generate_factory()

    def _setup_factory_tab(self, parent_frame):
        """Setup the factory configuration tab"""

        # Left panel for controls
        control_frame = ttk.LabelFrame(
            parent_frame, text="Factory Configuration", padding="10"
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

        # Create frame for checkbox tree and scrollbar
        tree_frame = ttk.Frame(control_frame)
        tree_frame.grid(row=9, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        tree_frame.columnconfigure(0, weight=1)

        self.recipe_tree = CheckboxTreeview(tree_frame, height=10)
        self.recipe_tree.grid(row=0, column=0, sticky=(tk.W, tk.E))

        tree_scrollbar = ttk.Scrollbar(
            tree_frame, orient=tk.VERTICAL, command=self.recipe_tree.yview
        )
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.recipe_tree.configure(yscrollcommand=tree_scrollbar.set)

        # Populate recipe tree
        self._populate_recipe_tree()

        # Bind recipe tree state changes to update power warning
        self.recipe_tree.bind("<ButtonRelease-1>", lambda e: self._update_power_warning())

        # Optimization weights section
        ttk.Label(
            control_frame, text="Optimize For:", font=("TkDefaultFont", 9, "bold")
        ).grid(row=10, column=0, sticky=tk.W, pady=(10, 5))

        self.input_costs_weight = SliderSpinbox(
            control_frame,
            from_=0.0,
            to=1.0,
            increment=0.01,
            initial_value=1.0,
            label="Input Costs:",
        )
        self.input_costs_weight.grid(row=11, column=0, sticky=(tk.W, tk.E), pady=2)

        self.machine_counts_weight = SliderSpinbox(
            control_frame,
            from_=0.0,
            to=1.0,
            increment=0.01,
            initial_value=0.0,
            label="Machine Counts:",
        )
        self.machine_counts_weight.grid(row=12, column=0, sticky=(tk.W, tk.E), pady=2)

        self.power_consumption_weight = SliderSpinbox(
            control_frame,
            from_=0.0,
            to=1.0,
            increment=0.01,
            initial_value=1.0,
            label="Power Usage:",
        )
        self.power_consumption_weight.grid(row=13, column=0, sticky=(tk.W, tk.E), pady=2)

        # Design power checkbox
        self.design_power_var = tk.BooleanVar(value=False)
        self.design_power_check = ttk.Checkbutton(
            control_frame,
            text="Include power in design",
            variable=self.design_power_var,
            command=self._update_power_warning,
        )
        self.design_power_check.grid(row=14, column=0, sticky=tk.W, pady=(10, 0))

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
        self.generate_btn.grid(row=16, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

        # Export button
        self.export_btn = ttk.Button(
            control_frame,
            text="Copy Graphviz to Clipboard",
            command=self._copy_graphviz,
        )
        self.export_btn.grid(row=17, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

        # Create the graph viewer component (includes scrollbars)
        self.viewer = GraphvizViewer(parent_frame)
        self.viewer.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Initialize power warning state
        self._update_power_warning()

    def _setup_economy_tab(self, parent_frame):
        """Setup the economy settings tab"""
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.rowconfigure(0, weight=1)
        
        # Create economy editor component
        self.economy_editor = EconomyEditor(
            parent_frame,
            self.economy,
            self.pinned_items,
            on_change=self._on_economy_change
        )
        self.economy_editor.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def _on_economy_change(self):
        """Handle economy changes"""
        # Future: could update status bar or trigger other actions here
        return

    def _populate_recipe_tree(self):
        """Populate the recipe tree with machines and recipes, all checked by default"""
        for machine_name, recipes in get_all_recipes_by_machine().items():
            # Add machine as parent node
            machine_id = self.recipe_tree.insert("", "end", text=machine_name)

            any_checked = False
            any_unchecked = False
            # Add recipes as children
            for recipe_name, recipe in recipes.items():
                recipe_id = self.recipe_tree.insert(machine_id, "end", text=recipe_name)
                if "MWm" not in recipe.outputs and machine_name != "Packager":
                    # Check no-power recipe by default
                    self.recipe_tree.change_state(recipe_id, "checked")
                    any_checked = True
                else:
                    self.recipe_tree.change_state(recipe_id, "unchecked")
                    any_unchecked = True

            if any_checked and any_unchecked:
                self.recipe_tree.change_state(machine_id, "mixed")
            elif any_checked:
                self.recipe_tree.change_state(machine_id, "checked")
            else:
                self.recipe_tree.change_state(machine_id, "unchecked")

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
                self.power_warning_label.grid(row=15, column=0, sticky=tk.W, pady=(2, 5))
            else:
                # Hide warning
                self.power_warning_label.grid_remove()
        else:
            # Hide warning when design_power is disabled
            self.power_warning_label.grid_remove()

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
            self.status_label.config(text="Generating factory...")
            self.generate_btn.config(state="disabled")
            self.update()

            # Parse outputs
            outputs_text = self.outputs_text.get("1.0", tk.END)
            outputs_list = self._parse_config_text(outputs_text)
            if not outputs_list:
                self.status_label.config(text="Error: No outputs specified")
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
            _LOGGER.info(f"Generating factory for outputs: {outputs}")
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

            self.status_label.config(text="Factory generated successfully")
            _LOGGER.info("Factory generated successfully")

        except ValueError as e:
            self.status_label.config(text=f"Error: {str(e)}")
            _LOGGER.error(f"Configuration error: {str(e)}")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            _LOGGER.error(f"Factory generation failed: {str(e)}")
            import traceback

            traceback.print_exc()
        finally:
            self.generate_btn.config(state="normal")

    def _copy_graphviz(self):
        """Copy graphviz source to clipboard"""
        try:
            if self.viewer.dot is None:
                self.status_label.config(text="No graph to export")
                return

            graphviz_source = self.viewer.dot.source
            self.clipboard_clear()
            self.clipboard_append(graphviz_source)
            self.status_label.config(text="Graphviz source copied to clipboard")
            _LOGGER.info("Graphviz source copied to clipboard")
        except Exception as e:
            self.status_label.config(text=f"Error copying to clipboard: {str(e)}")
            _LOGGER.error(f"Clipboard copy failed: {str(e)}")


def main():
    """Main function"""
    # Add explicit console log handler for debug output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(
        "%(levelname)s:%(name)s [%(thread)d] (%(filename)s:%(lineno)d) : %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    _LOGGER.addHandler(console_handler)

    _LOGGER.debug("Main thread started.")

    # Set DPI awareness for Windows
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_PER_MONITOR_DPI_AWARE
    except:
        pass  # Ignore if not on Windows or if call fails

    # Create and run main window
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
