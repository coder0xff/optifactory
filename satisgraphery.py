"""Plan Satisfactory systems."""

# pylint: disable=logging-fstring-interpolation,import-outside-toplevel,bare-except,broad-exception-caught

import logging
import tkinter as tk
from tkinter import ttk
import sys

import graphviz

from graphviz_viewer import GraphvizViewer


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
    """Build the graph structure programmatically with optional DPI setting"""
    # Create a new Digraph
    dot = graphviz.Digraph(comment="Process Flow")

    # Set graph attributes
    dot.attr(rankdir="LR")
    dot.attr("node", shape="box", style="filled", fillcolor="lightblue")
    dot.attr("edge", color="gray")

    # Add nodes
    dot.node("A", "Start", fillcolor="lightgreen")
    dot.node("B", "Process 1", fillcolor="lightyellow")
    dot.node("C", "Decision", fillcolor="orange", shape="diamond")
    dot.node("D", "Process 2", fillcolor="lightyellow")
    dot.node("E", "End", fillcolor="lightcoral")

    # Add edges
    dot.edge("A", "B", label="begin")
    dot.edge("B", "C", label="check")
    dot.edge("C", "D", label="yes", color="green")
    dot.edge("C", "E", label="no", color="red")
    dot.edge("D", "E", label="complete")

    # Add subgraph
    with dot.subgraph(name="cluster_0") as c:
        c.attr(label="Main Process")
        c.node("B")
        c.node("C")
        c.node("D")

    return dot


class MainWindow(tk.Tk):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.title("Satisgraphery")
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


        # Create the graph viewer component
        self.viewer = GraphvizViewer(main_frame, diagram=build_graph())
        self.viewer.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # Scrollbars for canvas
        v_scrollbar = ttk.Scrollbar(
            main_frame, orient=tk.VERTICAL, command=self.viewer.canvas.yview
        )
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.viewer.canvas.configure(yscrollcommand=v_scrollbar.set)

        h_scrollbar = ttk.Scrollbar(
            main_frame, orient=tk.HORIZONTAL, command=self.viewer.canvas.xview
        )
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.viewer.canvas.configure(xscrollcommand=h_scrollbar.set)

        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        # Setup custom log handler for status bar
        status_handler = StatusBarLogHandler(self, self.status_label)
        _LOGGER.addHandler(status_handler)


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
