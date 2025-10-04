"""Plan Satisfactory systems."""

# pylint: disable=logging-fstring-interpolation,import-outside-toplevel,bare-except,broad-exception-caught

import bisect
import logging
import os
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageFile, ImageTk
import graphviz


_LOGGER = logging.getLogger("satisgraphery")
_LOGGER.setLevel(logging.DEBUG)

FORCE_SINGLE_THREADED = False


def get_system_dpi_scale():
    """Get the system DPI scaling factor"""
    try:
        import ctypes

        # Get the DPI awareness context
        user32 = ctypes.windll.user32
        shcore = ctypes.windll.shcore

        # Get the DPI of the primary monitor
        hdc = user32.GetDC(0)
        dpi_x = ctypes.c_uint()
        dpi_y = ctypes.c_uint()

        # Try to get DPI using GetDpiForMonitor (Windows 8.1+)
        try:
            shcore.GetDpiForMonitor(0, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
            dpi = dpi_x.value
        except:
            # Fallback to GetDeviceCaps
            dpi = user32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX

        user32.ReleaseDC(0, hdc)

        # Calculate scaling factor (96 is the standard DPI)
        scale = dpi / 96.0
        if scale == 0:
            return 1.0
        return scale
    except:
        # Fallback to 1.0 if detection fails
        return 1.0


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


class GraphvizViewer:
    """Canvas-based viewer component for displaying rendered graphs"""

    def __init__(self, parent_widget, diagram=None):
        self.parent = parent_widget

        # Zoom and pan variables
        self.zoom_exponent = 0
        self.pan_x = 0
        self.pan_y = 0
        self.last_pan_x = 0
        self.last_pan_y = 0
        self.is_panning = False

        self.cache_lock = threading.Lock()
        self.image_cache: dict[float, ImageFile.ImageFile] = dict()
        self.photo_cache: dict[float, ImageTk.PhotoImage] = dict()
        self.trash_bin = list[ImageTk.PhotoImage]()

        self.system_dpi_scale = get_system_dpi_scale()
        self.base_dpi = int(96 * self.system_dpi_scale)
        _LOGGER.debug(
            f"System DPI scale: {self.system_dpi_scale:.2f}x, using base DPI: {self.base_dpi}"
        )

        self.dot = diagram or graphviz.Digraph()

        # After event ID for updating the UI image
        self.after_event_id = None
        self._setup_canvas()
        self._render_callback(self.zoom_exponent, self._render(self.zoom_exponent))

    def _setup_canvas(self):
        """Setup the canvas widget and its event bindings"""
        # Canvas for displaying the graph
        self.canvas = tk.Canvas(self.parent, bg="white", relief=tk.SUNKEN, bd=2)

        # Bind mouse events for pan and zoom
        self.canvas.bind("<Button-1>", self._handle_start_pan)
        self.canvas.bind("<B1-Motion>", self._handle_pan)
        self.canvas.bind("<ButtonRelease-1>", self._handle_end_pan)
        self.canvas.bind("<MouseWheel>", self._handle_zoom_event)
        self.canvas.bind("<Button-4>", self._handle_zoom_event)  # Linux scroll up
        self.canvas.bind("<Button-5>", self._handle_zoom_event)  # Linux scroll down

    def grid(self, **kwargs):
        """Grid the canvas widget"""
        self.canvas.grid(**kwargs)

    def _schedule_render(self, zoom_exponent):
        """Schedule a render operation"""
        if FORCE_SINGLE_THREADED:
            self._render_callback(
                zoom_exponent, self.renderer.render_graph(zoom_exponent)
            )
        else:
            threading.Thread(
                target=self._render,
                args=(zoom_exponent, self._render_callback),
                daemon=True,
            ).start()

    def _render_callback(self, zoom_exponent, image, error=None):
        """Callback for when rendering is complete"""
        if error:
            _LOGGER.error(f"Render error: {error}")
            self._schedule_update_ui_image()
            return

        if image:
            with self.cache_lock:
                self.image_cache[zoom_exponent] = image
                # Move old photo cache to trash bin
                if zoom_exponent in self.photo_cache:
                    self.trash_bin.append(self.photo_cache[zoom_exponent])
                    del self.photo_cache[zoom_exponent]

            _LOGGER.debug(f"Render completed at zoom {zoom_exponent}")
            self._schedule_update_ui_image()

    def _graphviz_with_dpi(self, dot, dpi):
        """Insert the DPI attribute into the graph"""
        # Check if the DPI attribute already exists
        dot = dot.copy()
        dot.attr("graph", dpi=str(dpi))
        return dot

    def _render(self, zoom_exponent, callback=None):
        """Render graph at specified zoom level, optionally calling callback with result"""
        zoom_factor = self._zoom_exponent_to_zoom_factor(zoom_exponent)

        _LOGGER.debug(f"Starting render at {zoom_factor:.2f}x zoom")

        try:
            scaled = self._graphviz_with_dpi(self.dot, self._zoom_exponent_to_dpi(zoom_exponent))

            # Render to PNG format with calculated DPI
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file = os.path.join(temp_dir, "graph")
                _LOGGER.debug(f"About to render graph to {temp_file}.png")
                scaled.render(temp_file, format="png", cleanup=True, engine="dot")
                _LOGGER.debug(f"Graph rendered to {temp_file}.png")
                temp_path = temp_file + ".png"

                # Load the high-resolution image
                if os.path.exists(temp_path):
                    _LOGGER.debug(f"Loading image from {temp_path}")
                    image = Image.open(temp_path)
                    image.load()
                    _LOGGER.debug(
                        f"Image loaded with size: {image.width}x{image.height}"
                    )

                    if callback:
                        callback(zoom_exponent, image)
                    return image

        except Exception as e:
            _LOGGER.error(f"Render failed at {zoom_factor:.2f}x zoom: {str(e)}")
            if callback:
                callback(zoom_exponent, None, str(e))
            return None

    @staticmethod
    def _zoom_exponent_to_zoom_factor(zoom_exponent):
        return 1.1**zoom_exponent

    def _zoom_exponent_to_dpi(self, zoom_exponent):
        return int(self.base_dpi * self._zoom_exponent_to_zoom_factor(zoom_exponent))

    def _handle_start_pan(self, event):
        """Start panning when mouse button is pressed"""
        self.is_panning = True
        self.last_pan_x = event.x
        self.last_pan_y = event.y

    def _handle_pan(self, event):
        """Pan the canvas while mouse is dragged"""
        if self.is_panning:
            dx = event.x - self.last_pan_x
            dy = event.y - self.last_pan_y

            self.pan_x += dx
            self.pan_y += dy

            self.last_pan_x = event.x
            self.last_pan_y = event.y

            self._update_ui_image()

    def _handle_end_pan(self, _event):
        """End panning when mouse button is released"""
        self.is_panning = False

    def _handle_zoom_event(self, event):
        """Zoom in/out with mouse wheel - immediate feedback + background rendering"""
        # Determine zoom direction
        if event.delta > 0 or event.num == 4:  # Zoom in
            zoom_delta = 1
        else:  # Zoom out
            zoom_delta = -1

        old_zoom_exponent = self.zoom_exponent
        # Calculate new zoom factor
        self.zoom_exponent += zoom_delta

        # Limit zoom range
        self.zoom_exponent = int(max(-7, min(20.0, self.zoom_exponent)))

        if old_zoom_exponent != self.zoom_exponent:
            self._update_ui_image()

    def _schedule_update_ui_image(self):
        """Schedule the update of the UI image"""
        if self.after_event_id:
            _LOGGER.debug(f"Cancelling after event {self.after_event_id}")
            self.parent.after_cancel(self.after_event_id)
            _LOGGER.debug(f"After event {self.after_event_id} cancelled")
        _LOGGER.debug(f"Scheduling after event {self.after_event_id}")
        self.after_event_id = self.parent.after(10, self._update_ui_image)
        _LOGGER.debug(f"After event {self.after_event_id} scheduled")

    def _get_photo_image(self, zoom_exponent):
        zoom_factor = self._zoom_exponent_to_zoom_factor(zoom_exponent)
        with self.cache_lock:
            self.trash_bin.clear()

            if zoom_exponent in self.photo_cache:
                _LOGGER.debug(f"Cache hit for PhotoImage {zoom_factor:.2f}x")
                return self.photo_cache[zoom_exponent]

            if zoom_exponent in self.image_cache:
                _LOGGER.debug(
                    f"Cache miss for PhotoImage {zoom_factor:.2f}x,"
                    f" cache hit for Image {zoom_exponent:.2f}x"
                )
                _LOGGER.debug(
                    f"About to create PhotoImage from Image {zoom_factor:.2f}x"
                )
                self.photo_cache[zoom_exponent] = ImageTk.PhotoImage(
                    self.image_cache[zoom_exponent]
                )
                _LOGGER.debug("PhotoImage created and cached")
                return self.photo_cache[zoom_exponent]

        if FORCE_SINGLE_THREADED:
            _LOGGER.debug(
                f"Cache miss for PhotoImage {zoom_factor:.2f}x, forcing single threaded render"
            )
            image = self.renderer.render_graph(zoom_exponent)
            if image:
                _LOGGER.debug(
                    f"About to create PhotoImage from Image {zoom_factor:.2f}x"
                )
                photo = self.photo_cache[zoom_exponent] = ImageTk.PhotoImage(image)
                _LOGGER.debug("PhotoImage created and cached")
                return photo
            return None

        _LOGGER.debug(
            f"Cache miss for PhotoImage {zoom_factor:.2f}x, starting background render"
        )
        self._schedule_render(zoom_exponent)
        _LOGGER.debug("Background render started")

        # Find the closest zoom factor in the cache, favoring higher zoom factors.
        with self.cache_lock:
            sorted_keys = sorted(self.image_cache.keys())
            closest_index = min(
                bisect.bisect_right(sorted_keys, zoom_exponent), len(sorted_keys) - 1
            )
            closest_zoom_exponent = sorted_keys[closest_index]
            closest_image = self.image_cache[closest_zoom_exponent]

        _LOGGER.debug(
            f"Temporarily using {zoom_factor:.2f}x as fallback during background render"
        )
        # Rescale the closest image to the current zoom factor while waiting for the background
        # render to complete.
        rescale = self._zoom_exponent_to_zoom_factor(
            zoom_exponent
        ) / self._zoom_exponent_to_zoom_factor(closest_zoom_exponent)
        # Dont put the rescale in the cache, because its temporary.
        image = closest_image.resize(
            (int(closest_image.width * rescale), int(closest_image.height * rescale)),
            Image.Resampling.LANCZOS,
        )

        with self.cache_lock:
            # Never replace the image in the cache, as that would overwrite the background render.
            if zoom_exponent not in self.image_cache:
                self.image_cache[zoom_exponent] = image
            else:
                image = self.image_cache[zoom_exponent]
            _LOGGER.debug(f"About to create PhotoImage from Image {zoom_factor:.2f}x")
            photo = self.photo_cache[zoom_exponent] = ImageTk.PhotoImage(image)
            _LOGGER.debug("PhotoImage created and cached")
            return photo

    def _update_ui_image(self):
        """Update UI with new high-quality image (called from main thread)"""
        _LOGGER.debug("Updating UI image")

        if self.after_event_id:
            _LOGGER.debug(f"Cancelling after event {self.after_event_id}")
            self.parent.after_cancel(self.after_event_id)
            _LOGGER.debug(f"After event {self.after_event_id} cancelled")
            self.after_event_id = None

        _LOGGER.debug("Updating UI image")
        self.canvas.delete("all")
        self.canvas.create_image(
            self.pan_x,
            self.pan_y,
            anchor=tk.NW,
            image=self._get_photo_image(self.zoom_exponent),
        )
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        _LOGGER.info(
            f"Zoom: {self._zoom_exponent_to_zoom_factor(self.zoom_exponent):.1f}x"
        )


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
