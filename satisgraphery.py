"""Plan Satisfactory systems."""

# pylint: disable=logging-fstring-interpolation,import-outside-toplevel,bare-except,broad-exception-caught

import logging
import tkinter as tk
from tkinter import ttk
import sys

from graphviz_viewer import GraphvizViewer
from factory import design_factory

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


def build_graph():
    """Build a demo factory graph"""
    # Demo: Create a concrete factory with automatic raw material detection
    # Just specify we want 480 concrete - the system figures out we need limestone
    factory = design_factory(
        outputs={"Concrete": 480},
        inputs=[],  # No inputs specified - will auto-generate required materials
        mines=[]
    )
    return factory.network


class MainWindow(tk.Tk):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.title("Satisgraphery - Factory Planner")
        self._setup_ui()

    def _setup_ui(self):
        """Setup the main window UI components"""
        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # Left panel for controls
        control_frame = ttk.LabelFrame(main_frame, text="Factory Configuration", padding="10")
        control_frame.grid(row=0, column=0, rowspan=2, sticky=(tk.N, tk.S, tk.W), padx=(0, 10))

        # Outputs section
        ttk.Label(control_frame, text="Desired Outputs:", font=("TkDefaultFont", 9, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Label(control_frame, text="Format: Material:Rate", font=("TkDefaultFont", 8)).grid(
            row=1, column=0, sticky=tk.W)
        ttk.Label(control_frame, text="Example: Concrete:480", font=("TkDefaultFont", 8)).grid(
            row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        self.outputs_text = tk.Text(control_frame, width=30, height=8, wrap=tk.WORD)
        self.outputs_text.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.outputs_text.insert("1.0", "Concrete:480")
        
        # Inputs section
        ttk.Label(control_frame, text="Available Inputs (optional):", font=("TkDefaultFont", 9, "bold")).grid(
            row=4, column=0, sticky=tk.W, pady=(10, 5))
        ttk.Label(control_frame, text="One per line for separate conveyors", font=("TkDefaultFont", 8)).grid(
            row=5, column=0, sticky=tk.W)
        ttk.Label(control_frame, text="Example: Limestone:480", font=("TkDefaultFont", 8)).grid(
            row=6, column=0, sticky=tk.W, pady=(0, 5))
        
        self.inputs_text = tk.Text(control_frame, width=30, height=8, wrap=tk.WORD)
        self.inputs_text.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.inputs_text.insert("1.0", "# Leave empty to auto-detect\n# Or specify like:\n# Limestone:480\n# Limestone:480\n# Limestone:480")
        
        # Generate button
        self.generate_btn = ttk.Button(control_frame, text="Generate Factory", command=self._generate_factory)
        self.generate_btn.grid(row=8, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # Create a dedicated frame for the viewer and its scrollbars
        viewer_frame = ttk.Frame(main_frame)
        viewer_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        viewer_frame.columnconfigure(0, weight=1)
        viewer_frame.rowconfigure(0, weight=1)

        # Create the graph viewer component inside the viewer frame
        self.viewer = GraphvizViewer(viewer_frame, diagram=build_graph())
        self.viewer.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Scrollbars for canvas (inside viewer_frame)
        v_scrollbar = ttk.Scrollbar(
            viewer_frame, orient=tk.VERTICAL, command=self.viewer._canvas.yview
        )
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.viewer._canvas.configure(yscrollcommand=v_scrollbar.set)

        h_scrollbar = ttk.Scrollbar(
            viewer_frame, orient=tk.HORIZONTAL, command=self.viewer._canvas.xview
        )
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.viewer._canvas.configure(xscrollcommand=h_scrollbar.set)

        # Status label (spans both columns)
        self.status_label = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        # Setup custom log handler for status bar
        status_handler = StatusBarLogHandler(self, self.status_label)
        _LOGGER.addHandler(status_handler)

    def _parse_config_text(self, text):
        """Parse configuration text into list of (material, rate) tuples.
        
        Format: Material:Rate, one per line
        Lines starting with # are comments and ignored
        Empty lines are ignored
        """
        items = []
        for line in text.strip().split('\n'):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse Material:Rate
            if ':' not in line:
                raise ValueError(f"Invalid format: '{line}'. Expected 'Material:Rate'")
            
            material, rate_str = line.split(':', 1)
            material = material.strip()
            rate_str = rate_str.strip()
            
            try:
                rate = float(rate_str)
            except ValueError:
                raise ValueError(f"Invalid rate '{rate_str}' for {material}. Must be a number.")
            
            items.append((material, rate))
        
        return items

    def _generate_factory(self):
        """Generate factory based on current inputs"""
        try:
            self.status_label.config(text="Generating factory...")
            self.generate_btn.config(state='disabled')
            self.update()
            
            # Parse outputs
            outputs_text = self.outputs_text.get("1.0", tk.END)
            outputs_list = self._parse_config_text(outputs_text)
            if not outputs_list:
                self.status_label.config(text="Error: No outputs specified")
                self.generate_btn.config(state='normal')
                return
            
            outputs = {material: rate for material, rate in outputs_list}
            
            # Parse inputs
            inputs_text = self.inputs_text.get("1.0", tk.END)
            inputs = self._parse_config_text(inputs_text)
            
            # Generate factory
            _LOGGER.info(f"Generating factory for outputs: {outputs}")
            factory = design_factory(
                outputs=outputs,
                inputs=inputs,
                mines=[]
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
            self.generate_btn.config(state='normal')


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
