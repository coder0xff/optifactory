import tkinter as tk


class Popover:
    """popup window that can be positioned and shown/hidden at caller's discretion
    
    Provides the visual popup window without mouse event handling logic.
    Useful for cases where the caller wants to manage when/where to show the popup.
    """

    def __init__(self, parent, *, bg='#FFFFEA', pad=(5, 3, 5, 3), wraplength=250):
        """Initialize the popover
        
        Args:
            parent: parent widget (used for screen dimensions and creating toplevel)
            bg: background color
            pad: padding tuple (left, top, right, bottom)
            wraplength: maximum width before text wraps
        """
        self.parent = parent
        self.bg = bg
        self.pad = pad
        self.wraplength = wraplength
        self.tw = None

    def show(self, text, x=None, y=None, tip_delta=(10, 5)):
        """Show the popover with the given text
        
        Args:
            text: text to display
            x: x position (screen coordinates). If None, uses mouse x position
            y: y position (screen coordinates). If None, uses mouse y position
            tip_delta: offset from x, y position (default: 10 pixels right, 5 pixels down)
        """
        # Hide any existing popover first
        self.hide()

        bg = self.bg
        pad = self.pad

        # creates a toplevel window
        self.tw = tk.Toplevel(self.parent)

        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)

        win = tk.Frame(self.tw,
                       background=bg,
                       borderwidth=0)
        label = tk.Label(win,
                          text=text,
                          justify=tk.LEFT,
                          background=bg,
                          relief=tk.SOLID,
                          borderwidth=0,
                          wraplength=self.wraplength)

        label.grid(padx=(pad[0], pad[2]),
                   pady=(pad[1], pad[3]),
                   sticky=tk.NSEW)
        win.grid()

        # Calculate position
        pos_x, pos_y = self._calculate_position(label, x, y, tip_delta)
        self.tw.wm_geometry("+%d+%d" % (pos_x, pos_y))

    def hide(self):
        """Hide and destroy the popover window"""
        tw = self.tw
        if tw:
            tw.destroy()
        self.tw = None

    def _calculate_position(self, label, x, y, tip_delta):
        """Calculate the position for the popover, keeping it on screen
        
        Args:
            label: the label widget (to get dimensions)
            x: desired x position (None for mouse position)
            y: desired y position (None for mouse position)
            tip_delta: offset from x, y
            
        Returns:
            tuple of (x, y) screen coordinates
        """
        w = self.parent
        pad = self.pad

        s_width, s_height = w.winfo_screenwidth(), w.winfo_screenheight()

        width, height = (pad[0] + label.winfo_reqwidth() + pad[2],
                         pad[1] + label.winfo_reqheight() + pad[3])

        # Use provided coordinates or fall back to mouse position
        if x is None or y is None:
            mouse_x, mouse_y = w.winfo_pointerxy()
            if x is None:
                x = mouse_x
            if y is None:
                y = mouse_y

        x1, y1 = x + tip_delta[0], y + tip_delta[1]
        x2, y2 = x1 + width, y1 + height

        x_delta = x2 - s_width
        if x_delta < 0:
            x_delta = 0
        y_delta = y2 - s_height
        if y_delta < 0:
            y_delta = 0

        offscreen = (x_delta, y_delta) != (0, 0)

        if offscreen:
            if x_delta:
                x1 = x - tip_delta[0] - width

            if y_delta:
                y1 = y - tip_delta[1] - height

        offscreen_again = y1 < 0  # out on the top

        if offscreen_again:
            # No further checks will be done.

            # TIP:
            # A further mod might automagically augment the
            # wraplength when the tooltip is too high to be
            # kept inside the screen.
            y1 = 0

        return x1, y1


class TooltipZone:
    """manages delayed tooltip display with timing logic
    
    Encapsulates a Popover and handles scheduling/unscheduling the tooltip
    display after a configurable wait time. Provides enter/exit/move methods
    for controlling when tooltips appear.
    """

    def __init__(self, widget, *, bg='#FFFFEA', pad=(5, 3, 5, 3), 
                 waittime=400, wraplength=250):
        """Initialize the tooltip zone
        
        Args:
            widget: widget for after() calls and creating popover
            bg: background color for popover
            pad: padding tuple for popover (left, top, right, bottom)
            waittime: delay in milliseconds before showing tooltip
            wraplength: maximum width before text wraps
        """
        self.widget = widget
        self.waittime = waittime
        self.popover = Popover(widget, bg=bg, pad=pad, wraplength=wraplength)
        self.scheduled_id = None
        self.pending_text = None

    def enter(self, text):
        """schedule showing the tooltip after waittime
        
        Args:
            text: text to display in tooltip
        """
        self.pending_text = text
        self._schedule()

    def exit(self):
        """cancel pending tooltip and hide if visible"""
        self._unschedule()
        self.popover.hide()
        self.pending_text = None

    def move(self, text):
        """reschedule tooltip with new text (restarts timer)
        
        Args:
            text: text to display in tooltip
        """
        self.pending_text = text
        self._schedule()

    def _schedule(self):
        """start timer to show tooltip"""
        self._unschedule()
        self.scheduled_id = self.widget.after(self.waittime, self._show)

    def _unschedule(self):
        """cancel pending timer"""
        if self.scheduled_id:
            self.widget.after_cancel(self.scheduled_id)
            self.scheduled_id = None

    def _show(self):
        """show the popover with pending text"""
        self.scheduled_id = None
        if self.pending_text:
            self.popover.show(self.pending_text)


class Tooltip:
    """automatic tooltip for a widget on mouse hover
    
    see:

    http://stackoverflow.com/questions/3221956/
           what-is-the-simplest-way-to-make-tooltips-
           in-tkinter/36221216#36221216

    http://www.daniweb.com/programming/software-development/
           code/484591/a-tooltip-class-for-tkinter

    - Originally written by vegaseat on 2014.09.09.

    - Modified to include a delay time by Victor Zaccardo on 2016.03.25.

    - Modified
        - to correct extreme right and extreme bottom behavior,
        - to stay inside the screen whenever the tooltip might go out on
          the top but still the screen is higher than the tooltip,
        - to use the more flexible mouse positioning,
        - to add customizable background color, padding, waittime and
          wraplength on creation
      by Alberto Vassena on 2016.11.05.

      Tested on Ubuntu 16.04/16.10, running Python 3.5.2

    TODO: themes styles support
    """

    def __init__(self, widget,
                 *,
                 bg='#FFFFEA',
                 pad=(5, 3, 5, 3),
                 text='widget info',
                 waittime=400,
                 wraplength=250):

        self.widget = widget
        self.text = text
        self.entered_widgets = set()  # track which widgets mouse is currently over
        
        # Bind events to parent widget
        self.widget.bind("<Enter>", self.onEnter)
        self.widget.bind("<Leave>", self.onLeave)
        self.widget.bind("<ButtonPress>", self.onButtonPress)
        
        # Bind events to all child widgets
        self._bind_to_children(widget)
        
        self.zone = TooltipZone(widget, bg=bg, pad=pad, waittime=waittime, 
                                wraplength=wraplength)
    
    def _bind_to_children(self, widget):
        """recursively bind events to widget and all its children"""
        for child in widget.winfo_children():
            child.bind("<Enter>", self.onEnter)
            child.bind("<Leave>", self.onLeave)
            child.bind("<ButtonPress>", self.onButtonPress)
            self._bind_to_children(child)

    def onEnter(self, event=None):
        widget = event.widget if event else self.widget
        self.entered_widgets.add(widget)
        self.zone.enter(self.text)

    def onLeave(self, event=None):
        widget = event.widget if event else self.widget
        self.entered_widgets.discard(widget)
        
        # Only exit if we've left all widgets
        if not self.entered_widgets:
            self.zone.exit()
    
    def onButtonPress(self, _event=None):
        self.entered_widgets.clear()
        self.zone.exit()


