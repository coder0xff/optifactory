"""Plan Satisfactory systems."""

# pylint: disable=logging-fstring-interpolation,import-outside-toplevel,bare-except,broad-exception-caught

import logging
import sys
import tkinter as tk
from tkinter import ttk

from economy_editor import EconomyEditor
from factory_editor import FactoryEditor

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
        factory_frame.columnconfigure(0, weight=1)
        factory_frame.rowconfigure(0, weight=1)
        
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
        
        # Generate initial factory after everything is set up
        self.factory_editor._generate_factory()

    def _setup_factory_tab(self, parent_frame):
        """Setup the factory configuration tab"""
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.rowconfigure(0, weight=1)
        
        # Create factory editor component
        self.factory_editor = FactoryEditor(
            parent_frame,
            self.economy,
            on_status_change=self._update_status
        )
        self.factory_editor.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def _update_status(self, text):
        """Update status bar with text"""
        self.status_label.config(text=text)

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
