"""Combined slider and spinbox widget for numeric input."""

import tkinter as tk
from tkinter import ttk


class SliderSpinbox(ttk.Frame):
    """Combined slider and spinbox widget with bidirectional sync."""

    def __init__(
        self,
        parent,
        from_=0.0,
        to=10.0,
        increment=0.1,
        initial_value=1.0,
        label="",
        **kwargs
    ):
        """Initialize the slider-spinbox combo.

        Args:
            parent: parent widget
            from_: minimum value
            to: maximum value
            increment: step size for both slider and spinbox
            initial_value: starting value
            label: label text (empty = no label)
            **kwargs: additional frame options
        """
        super().__init__(parent, **kwargs)

        self.from_ = from_
        self.to = to
        self.increment = increment
        self._var = tk.DoubleVar(value=initial_value)

        # Label (optional)
        if label:
            self.label = ttk.Label(self, text=label, width=15, anchor=tk.W)
            self.label.grid(row=0, column=0, padx=(0, 5))
            slider_col = 1
            spinbox_col = 2
        else:
            self.label = None
            slider_col = 0
            spinbox_col = 1

        # Slider
        self.slider = ttk.Scale(
            self,
            from_=from_,
            to=to,
            orient=tk.HORIZONTAL,
            variable=self._var,
            command=self._on_slider_change,
            length=150,
        )
        self.slider.grid(row=0, column=slider_col, padx=(0, 5), sticky=(tk.W, tk.E))

        # Spinbox
        self.spinbox = ttk.Spinbox(
            self,
            from_=from_,
            to=to,
            increment=increment,
            textvariable=self._var,
            width=8,
            command=self._on_spinbox_change,
        )
        self.spinbox.grid(row=0, column=spinbox_col)
        self.spinbox.bind("<Return>", lambda e: self._on_spinbox_change())
        self.spinbox.bind("<FocusOut>", lambda e: self._on_spinbox_change())

        # Configure column weights
        self.columnconfigure(slider_col, weight=1)

    def _on_slider_change(self, value):
        """slider value changed - snap to increment"""
        snapped = round(float(value) / self.increment) * self.increment
        snapped = max(self.from_, min(self.to, snapped))
        self._var.set(snapped)

    def _on_spinbox_change(self):
        """spinbox value changed - validate and clamp"""
        try:
            value = float(self._var.get())
            value = max(self.from_, min(self.to, value))
            self._var.set(value)
        except (ValueError, tk.TclError):
            # Invalid input - reset to current value
            self._var.set(self._var.get())

    def get(self) -> float:
        """Get current value."""
        return self._var.get()

    def set(self, value: float):
        """Set value."""
        value = max(self.from_, min(self.to, value))
        self._var.set(value)

