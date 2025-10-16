"""Graphviz viewer for tkinter."""

# pylint: disable=logging-fstring-interpolation,import-outside-toplevel,bare-except,broad-exception-caught

import bisect
import logging
import math
import os
import tempfile
import threading
import tkinter as tk
from collections import OrderedDict
from typing import TypeVar, Generic, Optional

import graphviz
from PIL import Image, ImageFile, ImageTk

FORCE_SINGLE_THREADED_RENDERING = False

_LOGGER = logging.getLogger(__file__)
_LOGGER.setLevel(logging.DEBUG)

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    """LRU cache with configurable max size and trash bin for evicted items"""

    def __init__(self, trash_bin: list[V], max_size: int = 20) -> None:
        self.trash_bin = trash_bin
        self.max_size = max_size
        self._cache: OrderedDict[K, V] = OrderedDict()

    def __contains__(self, key: K) -> bool:
        """Check if key is in cache"""
        return key in self._cache

    def __getitem__(self, key: K) -> V:
        """Get item and move to end (most recently used)"""
        if key in self._cache:
            # Move to end (most recently used)
            value = self._cache.pop(key)
            self._cache[key] = value
            return value
        raise KeyError(key)

    def __setitem__(self, key: K, value: V) -> None:
        """Set item, evicting LRU if cache is full"""
        if key in self._cache:
            # Update existing item
            self._cache.pop(key)
        while len(self._cache) >= self.max_size:
            # Evict least recently used (first item)
            lru_key, lru_value = self._cache.popitem(last=False)
            # Try to close the image if it has a close method
            if hasattr(lru_value, "close"):
                try:
                    lru_value.close()
                except:
                    pass
            self.trash_bin.append(lru_value)
            _LOGGER.debug(f"Evicted LRU item {lru_key} for gc.")

        self._cache[key] = value

    def __delitem__(self, key: K) -> None:
        """Delete item and move to trash_bin"""
        if key in self._cache:
            value = self._cache.pop(key)
            # Try to close the image if it has a close method
            if hasattr(value, "close"):
                try:
                    value.close()
                except:
                    pass
            self.trash_bin.append(value)
            _LOGGER.debug(f"Removed item {key} for gc.")

    def keys(self):
        """Get all keys"""
        return self._cache.keys()

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """Get item with default, moving to end if found"""
        try:
            return self[key]
        except KeyError:
            return default

    def clear(self) -> None:
        """Clear cache, moving all items to trash_bin"""
        for value in self._cache.values():
            # Try to close the image if it has a close method
            if hasattr(value, "close"):
                try:
                    value.close()
                except:
                    pass
            self.trash_bin.append(value)
        self._cache.clear()


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


class GraphvizViewer:  # pylint: disable=too-many-instance-attributes
    """Canvas-based viewer component for displaying a graphviz.Graph"""

    def __init__(self, parent_widget, diagram=None):
        # Create a frame to contain canvas and scrollbars
        self._frame = tk.Frame(parent_widget)

        # Configure grid weights for the frame
        self._frame.columnconfigure(0, weight=1)
        self._frame.rowconfigure(0, weight=1)

        # Zoom and pan variables
        self._zoom_exponent = 0
        self._last_pan_x = 0
        self._last_pan_y = 0
        self._is_panning = False

        self._cache_lock = threading.Lock()
        self._trash_bin: list[object] = []
        self._image_cache: LRUCache[float, ImageFile.ImageFile] = LRUCache(
            trash_bin=self._trash_bin, max_size=20
        )
        self._photo_cache: LRUCache[float, ImageTk.PhotoImage] = LRUCache(
            trash_bin=self._trash_bin, max_size=20
        )

        # Track renders that failed due to memory/size issues to prevent infinite retries
        self._failed_renders: set[int] = set()

        self._system_dpi_scale = get_system_dpi_scale()
        self._base_dpi = int(96 * self._system_dpi_scale)
        _LOGGER.debug(
            f"System DPI scale: {self._system_dpi_scale:.2f}x, using base DPI: {self._base_dpi}"
        )

        self._dot = diagram or graphviz.Digraph()

        # After event ID for updating the UI image
        self._after_event_id = None
        self._setup_canvas()
        self._render_callback(self._zoom_exponent, self._render(self._zoom_exponent))

    def grid(self, **kwargs):
        """Grid the viewer frame"""
        self._frame.grid(**kwargs)

    @property
    def dot(self):
        """Get the current diagram"""
        return self._dot

    @dot.setter
    def dot(self, diagram):
        """Set a new diagram to display.

        Automatically clears caches, resets failed renders, and triggers re-render.
        """
        self._dot = diagram

        # Clear all caches and failed renders for new diagram
        with self._cache_lock:
            self._image_cache.clear()
            self._photo_cache.clear()
            self._trash_bin.clear()

        self._failed_renders.clear()

        # Force garbage collection
        import gc

        gc.collect()

        # Trigger render of new diagram
        self._schedule_render(self._zoom_exponent)

    @property
    def zoom(self):
        """Get the current zoom factor (e.g., 1.0 for 100%, 2.0 for 200%)"""
        return self._zoom_exponent_to_zoom_factor(self._zoom_exponent)

    @zoom.setter
    def zoom(self, value):
        """Set the zoom factor (e.g., 1.0 for 100%, 2.0 for 200%)"""
        if value <= 0:
            raise ValueError("Zoom factor must be positive")
        # Convert zoom factor to zoom_exponent using log with base 1.1
        self._zoom_exponent = math.log(value, 1.1)
        # Update the UI to reflect the new zoom level
        self._schedule_render(self._zoom_exponent)

    def _setup_canvas(self):
        """Setup the canvas widget, scrollbars, and event bindings"""
        # Canvas for displaying the graph
        self._canvas = tk.Canvas(self._frame, bg="white", relief=tk.SUNKEN, bd=2)
        self._canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        # Vertical scrollbar
        v_scrollbar = tk.Scrollbar(
            self._frame, orient=tk.VERTICAL, command=self._canvas.yview
        )
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self._canvas.configure(yscrollcommand=v_scrollbar.set)

        # Horizontal scrollbar
        h_scrollbar = tk.Scrollbar(
            self._frame, orient=tk.HORIZONTAL, command=self._canvas.xview
        )
        h_scrollbar.grid(row=1, column=0, sticky=(tk.E, tk.W))
        self._canvas.configure(xscrollcommand=h_scrollbar.set)

        # Bind mouse events for pan and zoom
        self._canvas.bind("<Button-1>", self._handle_start_pan)
        self._canvas.bind("<B1-Motion>", self._handle_pan)
        self._canvas.bind("<ButtonRelease-1>", self._handle_end_pan)
        self._canvas.bind("<MouseWheel>", self._handle_zoom_event)
        self._canvas.bind("<Button-4>", self._handle_zoom_event)  # Linux scroll up
        self._canvas.bind("<Button-5>", self._handle_zoom_event)  # Linux scroll down

    def _schedule_render(self, zoom_exponent):
        """Schedule a render operation"""
        # Skip if this zoom level already failed
        if zoom_exponent in self._failed_renders:
            _LOGGER.debug(
                f"Skipping render at {zoom_exponent} - previously failed due to size/memory"
            )
            return

        if FORCE_SINGLE_THREADED_RENDERING:
            self._render_callback(zoom_exponent, self._render(zoom_exponent))
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
            # Check if this is a size/memory error
            if (
                "size" in error.lower()
                or "memory" in error.lower()
                or "decompression bomb" in error.lower()
            ):
                # Mark this zoom level as failed to prevent retries
                self._failed_renders.add(zoom_exponent)
                _LOGGER.warning(
                    f"Marking zoom {zoom_exponent} as failed due to size/memory issue"
                )
            self._schedule_update_ui_image()
            return

        if image:
            with self._cache_lock:
                self._image_cache[zoom_exponent] = image
                # Remove old photo cache entry (will be moved to trash_bin automatically)
                if zoom_exponent in self._photo_cache:
                    del self._photo_cache[zoom_exponent]

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
            scaled = self._graphviz_with_dpi(
                self._dot, self._zoom_exponent_to_dpi(zoom_exponent)
            )

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

                # File doesn't exist
                _LOGGER.error(f"Rendered file not found: {temp_path}")
                if callback:
                    callback(zoom_exponent, None, "Rendered file not found")
                return None

        except Exception as e:
            _LOGGER.error(f"Render failed at {zoom_factor:.2f}x zoom: {str(e)}")
            if callback:
                callback(zoom_exponent, None, str(e))
            return None

    @staticmethod
    def _zoom_exponent_to_zoom_factor(zoom_exponent):
        return 1.1**zoom_exponent

    def _zoom_exponent_to_dpi(self, zoom_exponent):
        return int(self._base_dpi * self._zoom_exponent_to_zoom_factor(zoom_exponent))

    def _handle_start_pan(self, event):
        """Start panning when mouse button is pressed"""
        self._is_panning = True
        self._last_pan_x = event.x
        self._last_pan_y = event.y
        self._canvas.scan_mark(event.x, event.y)

    def _handle_pan(self, event):
        """Pan the canvas while mouse is dragged"""
        if self._is_panning:
            self._canvas.scan_dragto(event.x, event.y, gain=1)

    def _handle_end_pan(self, _event):
        """End panning when mouse button is released"""
        self._is_panning = False

    def _inv_canvasx(self, x):
        origin = self._canvas.canvasx(0)
        scale = self._canvas.canvasx(1000000) / 1000000
        return int(x / scale - origin)

    def _inv_canvasy(self, y):
        origin = self._canvas.canvasy(0)
        scale = self._canvas.canvasx(1000000) / 1000000
        return int(y / scale - origin)

    def _event_to_world_coordinates(self, event_x, event_y, zoom_exponent):
        """Convert event coordinates to world coordinates"""
        current_zoom_factor = self._zoom_exponent_to_zoom_factor(zoom_exponent)
        canvas_x = self._canvas.canvasx(event_x)
        canvas_y = self._canvas.canvasy(event_y)
        world_x = canvas_x / current_zoom_factor
        world_y = canvas_y / current_zoom_factor
        return world_x, world_y

    def _world_to_event_coordinates(self, world_x, world_y, zoom_exponent):
        current_zoom_factor = self._zoom_exponent_to_zoom_factor(zoom_exponent)
        canvas_x = world_x * current_zoom_factor
        canvas_y = world_y * current_zoom_factor
        event_x = self._inv_canvasx(canvas_x)
        event_y = self._inv_canvasy(canvas_y)
        return event_x, event_y

    def _handle_zoom_event(self, event):
        """Zoom in/out with mouse wheel - immediate feedback + background rendering"""
        old_zoom_exponent = self._zoom_exponent
        canvas_x, canvas_y = self._canvas.canvasx(event.x), self._canvas.canvasy(
            event.y
        )

        if event.delta > 0 or event.num == 4:  # Zoom in
            self._zoom_exponent = max(
                old_zoom_exponent, int(min(7.0, self._zoom_exponent + 1))
            )
        else:  # Zoom out
            self._zoom_exponent = min(
                old_zoom_exponent, int(max(-10, self._zoom_exponent - 1))
            )

        if old_zoom_exponent != self._zoom_exponent:
            _LOGGER.debug(f"Zooming from {old_zoom_exponent} to {self._zoom_exponent}")
            ratio = self._zoom_exponent_to_zoom_factor(
                self._zoom_exponent
            ) / self._zoom_exponent_to_zoom_factor(old_zoom_exponent)
            delta_x = int(canvas_x * (ratio - 1) / 9)  # 9? What in the world?
            delta_y = int(canvas_y * (ratio - 1) / 9)
            _LOGGER.debug(f"Delta: {delta_x}, {delta_y}")
            self._canvas.scan_mark(
                self._inv_canvasx(delta_x), self._inv_canvasy(delta_y)
            )
            self._canvas.scan_dragto(self._inv_canvasx(0), self._inv_canvasy(0))
            self._update_ui_image()

    def _schedule_update_ui_image(self):
        """Schedule the update of the UI image"""
        if self._after_event_id:
            _LOGGER.debug(f"Cancelling after event {self._after_event_id}")
            self._frame.after_cancel(self._after_event_id)
            _LOGGER.debug(f"After event {self._after_event_id} cancelled")
        _LOGGER.debug(f"Scheduling after event {self._after_event_id}")
        self._after_event_id = self._frame.after(10, self._update_ui_image)
        _LOGGER.debug(f"After event {self._after_event_id} scheduled")

    def _create_photo_image(self, image, zoom_exponent):
        """Create PhotoImage with memory error handling and retry.

        Args:
            image: PIL Image object to convert
            zoom_exponent: zoom level (for failure tracking)

        Returns:
            PhotoImage if successful, None if failed
        """

        def attempt_create():
            photo = ImageTk.PhotoImage(image)
            self._photo_cache[zoom_exponent] = photo
            return photo

        # First attempt
        try:
            return attempt_create()
        except MemoryError as e:
            _LOGGER.warning(
                f"MemoryError creating PhotoImage: {e}, clearing caches and retrying"
            )
        except tk.TclError as e:
            if "memory" not in str(e).lower() and "alloc" not in str(e).lower():
                raise  # Not a memory error, re-raise
            _LOGGER.warning(
                f"TclError (memory) creating PhotoImage: {e}, clearing caches and retrying"
            )

        # Memory error occurred - clean up and retry once
        self._failed_renders.add(zoom_exponent)
        self._image_cache.clear()
        self._photo_cache.clear()
        self._trash_bin.clear()
        import gc

        gc.collect()

        # Second attempt
        try:
            result = attempt_create()
            _LOGGER.debug("PhotoImage created after cleanup")
            self._failed_renders.discard(
                zoom_exponent
            )  # Succeeded, remove from failed set
            return result
        except:
            _LOGGER.error(
                f"Still failed after cleanup, giving up on zoom {zoom_exponent}"
            )
            return None

    def _get_cached_photo(self, zoom_exponent):
        """Try to get photo from cache, returns None if not found."""
        with self._cache_lock:
            self._trash_bin.clear()
            if zoom_exponent in self._photo_cache:
                zoom_factor = self._zoom_exponent_to_zoom_factor(zoom_exponent)
                _LOGGER.debug(f"Cache hit for PhotoImage {zoom_factor:.2f}x")
                return self._photo_cache[zoom_exponent]
        return None

    def _create_photo_from_image_cache(self, zoom_exponent):
        """Try to create photo from cached image, returns None if not found."""
        zoom_factor = self._zoom_exponent_to_zoom_factor(zoom_exponent)
        with self._cache_lock:
            if zoom_exponent in self._image_cache:
                _LOGGER.debug(
                    f"Cache miss for PhotoImage {zoom_factor:.2f}x,"
                    f" cache hit for Image {zoom_exponent:.2f}x"
                )
                _LOGGER.debug(
                    f"About to create PhotoImage from Image {zoom_factor:.2f}x"
                )
                photo = self._create_photo_image(
                    self._image_cache[zoom_exponent], zoom_exponent
                )
                if photo:
                    _LOGGER.debug("PhotoImage created and cached")
                return photo
        return None

    def _handle_single_threaded_render(self, zoom_exponent):
        """Handle rendering in single-threaded mode."""
        zoom_factor = self._zoom_exponent_to_zoom_factor(zoom_exponent)
        _LOGGER.debug(
            f"Cache miss for PhotoImage {zoom_factor:.2f}x, forcing single threaded render"
        )
        image = self._render(zoom_exponent)
        if image:
            _LOGGER.debug(f"About to create PhotoImage from Image {zoom_factor:.2f}x")
            photo = self._photo_cache[zoom_exponent] = ImageTk.PhotoImage(image)
            _LOGGER.debug("PhotoImage created and cached")
            return photo
        return None

    def _get_closest_cached_image(self, zoom_exponent):
        """Get closest image from cache for temporary use."""
        with self._cache_lock:
            sorted_keys = sorted(self._image_cache.keys())
            if not sorted_keys:
                _LOGGER.debug("Image cache is empty, waiting for background render")
                return None, None
            closest_index = min(
                bisect.bisect_right(sorted_keys, zoom_exponent), len(sorted_keys) - 1
            )
            closest_zoom_exponent = sorted_keys[closest_index]
            return closest_zoom_exponent, self._image_cache[closest_zoom_exponent]

    def _rescale_image_for_zoom(
        self, closest_image, closest_zoom_exponent, zoom_exponent
    ):
        """Rescale an image to match target zoom level."""
        rescale = self._zoom_exponent_to_zoom_factor(
            zoom_exponent
        ) / self._zoom_exponent_to_zoom_factor(closest_zoom_exponent)

        try:
            return closest_image.resize(
                (
                    int(closest_image.width * rescale),
                    int(closest_image.height * rescale),
                ),
                Image.Resampling.LANCZOS,
            )
        except MemoryError as e:
            _LOGGER.warning(
                f"MemoryError during image resize: {e}, clearing caches and retrying"
            )
            self._failed_renders.add(zoom_exponent)
            with self._cache_lock:
                self._image_cache.clear()
                self._photo_cache.clear()
                self._trash_bin.clear()
            import gc

            gc.collect()
            try:
                image = closest_image.resize(
                    (
                        int(closest_image.width * rescale),
                        int(closest_image.height * rescale),
                    ),
                    Image.Resampling.LANCZOS,
                )
                _LOGGER.debug("Image resize succeeded after cleanup")
                self._failed_renders.discard(zoom_exponent)
                return image
            except:
                _LOGGER.error(
                    f"Image resize still failed after cleanup, giving up on zoom {zoom_exponent}"
                )
                return None

    def _get_photo_image(self, zoom_exponent):
        # Try cached photo first
        photo = self._get_cached_photo(zoom_exponent)
        if photo:
            return photo

        # Try creating from cached image
        photo = self._create_photo_from_image_cache(zoom_exponent)
        if photo:
            return photo

        # Handle single-threaded rendering mode
        if FORCE_SINGLE_THREADED_RENDERING:
            return self._handle_single_threaded_render(zoom_exponent)

        # Start background render and use closest cached image as fallback
        zoom_factor = self._zoom_exponent_to_zoom_factor(zoom_exponent)
        _LOGGER.debug(
            f"Cache miss for PhotoImage {zoom_factor:.2f}x, starting background render"
        )
        self._schedule_render(zoom_exponent)
        _LOGGER.debug("Background render started")

        closest_zoom_exponent, closest_image = self._get_closest_cached_image(
            zoom_exponent
        )
        if closest_image is None:
            return None

        _LOGGER.debug(
            f"Temporarily using {zoom_factor:.2f}x as fallback during background render"
        )
        image = self._rescale_image_for_zoom(
            closest_image, closest_zoom_exponent, zoom_exponent
        )
        if image is None:
            return None

        with self._cache_lock:
            # Don't overwrite the cache if background render completed
            if zoom_exponent not in self._image_cache:
                self._image_cache[zoom_exponent] = image
            else:
                image = self._image_cache[zoom_exponent]
            _LOGGER.debug(f"About to create PhotoImage from Image {zoom_factor:.2f}x")
            return self._create_photo_image(image, zoom_exponent)

    def _update_ui_image(self):
        """Update UI with new high-quality image (called from main thread)"""
        _LOGGER.debug("Updating UI image")

        if self._after_event_id:
            _LOGGER.debug(f"Cancelling after event {self._after_event_id}")
            self._frame.after_cancel(self._after_event_id)
            _LOGGER.debug(f"After event {self._after_event_id} cancelled")
            self._after_event_id = None

        _LOGGER.debug("Updating UI image")
        photo = self._get_photo_image(self._zoom_exponent)
        if photo is None:
            _LOGGER.debug("No photo image available, skipping UI update")
            return

        self._canvas.delete("all")
        self._canvas.create_image(
            0,
            0,
            anchor=tk.NW,
            image=photo,
        )

        # Update scroll region to fit the image
        self._update_scroll_region()
        _LOGGER.info(
            f"Zoom: {self._zoom_exponent_to_zoom_factor(self._zoom_exponent):.1f}x"
        )

    def _update_scroll_region(self):
        """Update scroll region to fit the image"""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
