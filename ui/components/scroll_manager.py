"""Centralized, leak-safe mouse-wheel scrolling manager for CustomTkinter.

Provides reliable mouse-wheel scrolling across all application views and modals:
- Directs wheel scrolling to the widget directly under the mouse pointer.
- Suppresses redundant per-frame global bindings to avoid callback accumulation.
- Supports vertical scrolling and Shift + wheel horizontal scrolling.
- Automatically respects nested scroll containers (inner container scrolls first).
- Protects interactive controls (CTkTextbox, CTkOptionMenu, CTkSlider) from being hijacked.
- Prevents scrolling of hidden/unmapped tabs or screens whose content fully fits.
- Safe lifecycle management with zero memory leaks and zero stale callbacks.
"""
import sys
import tkinter as tk
from typing import Optional
import customtkinter as ctk


class ScrollManager:
    """Centralized mouse-wheel controller for CustomTkinter scrollable containers."""

    _installed: bool = False
    _shift_pressed: bool = False
    _orig_init = None

    @classmethod
    def install(cls, root: Optional[tk.Misc] = None) -> None:
        """Install centralized mouse-wheel handler and patch CTkScrollableFrame.
        
        Args:
            root: Root or toplevel window to bind global listeners to.
        """
        # Patch CTkScrollableFrame.__init__ to prevent redundant/leaking bind_all calls
        if cls._orig_init is None:
            cls._orig_init = ctk.CTkScrollableFrame.__init__

            def _patched_init(self, *args, **kwargs):
                # Suppress CTkScrollableFrame's internal bind_all during instantiation
                orig_bind_all = self.bind_all
                self.bind_all = lambda *a, **k: ""
                try:
                    cls._orig_init(self, *args, **kwargs)
                finally:
                    self.bind_all = orig_bind_all

            ctk.CTkScrollableFrame.__init__ = _patched_init

        # Neutralize CTkScrollableFrame._mouse_wheel_all to avoid duplicate/erroneous calls
        ctk.CTkScrollableFrame._mouse_wheel_all = cls._noop_mouse_wheel

        if root is not None and not getattr(root, "_scroll_manager_installed", False):
            root._scroll_manager_installed = True

            # Register single centralized listener on the application shell
            root.bind_all("<MouseWheel>", cls.handle_mousewheel, add=True)
            root.bind_all("<KeyPress-Shift_L>", cls._on_shift_press, add=True)
            root.bind_all("<KeyPress-Shift_R>", cls._on_shift_press, add=True)
            root.bind_all("<KeyRelease-Shift_L>", cls._on_shift_release, add=True)
            root.bind_all("<KeyRelease-Shift_R>", cls._on_shift_release, add=True)

            # Linux Button-4 (up) and Button-5 (down)
            if "linux" in sys.platform:
                root.bind_all("<Button-4>", cls.handle_mousewheel, add=True)
                root.bind_all("<Button-5>", cls.handle_mousewheel, add=True)

        cls._installed = True

    @classmethod
    def _noop_mouse_wheel(cls, self, event) -> None:
        """No-op replacement for native CTkScrollableFrame._mouse_wheel_all."""
        pass

    @classmethod
    def _on_shift_press(cls, event) -> None:
        """Track left/right shift key press for horizontal scrolling."""
        cls._shift_pressed = True

    @classmethod
    def _on_shift_release(cls, event) -> None:
        """Track left/right shift key release."""
        cls._shift_pressed = False

    @classmethod
    def is_widget_visible(cls, widget: tk.Misc) -> bool:
        """Check if widget is active and displayed (handles deiconified & test modes)."""
        if not hasattr(widget, "winfo_exists") or not widget.winfo_exists():
            return False

        try:
            toplevel = widget.winfo_toplevel()
            # If toplevel window is normal/deiconified, use native winfo_viewable
            if toplevel and toplevel.state() != "withdrawn":
                return bool(widget.winfo_viewable())

            # In withdrawn test mode, verify all ancestors are actively managed
            curr = widget
            while curr is not None and curr != toplevel:
                if curr.winfo_manager() == "":
                    return False
                curr = getattr(curr, "master", None)
            return True
        except Exception:
            return False

    @classmethod
    def is_ignored_widget(cls, widget: tk.Misc) -> bool:
        """Check if widget or its ancestor has its own expected mouse-wheel behavior."""
        curr = widget
        while curr is not None:
            name = type(curr).__name__
            # Text boxes, sliders, option menus, comboboxes manage their own wheel
            if isinstance(curr, (ctk.CTkTextbox, tk.Text, ctk.CTkSlider, ctk.CTkOptionMenu, ctk.CTkComboBox)):
                return True
            if name in ("CTkTextbox", "Text", "CTkSlider", "CTkOptionMenu", "CTkComboBox", "Combobox"):
                return True
            curr = getattr(curr, "master", None)
        return False

    @classmethod
    def find_scrollable_container(cls, widget: tk.Misc) -> Optional[ctk.CTkScrollableFrame]:
        """Locate the innermost active CTkScrollableFrame under the target widget.
        
        Walking up from the leaf widget guarantees that nested scrollable areas
        take precedence over outer parent containers.
        """
        if cls.is_ignored_widget(widget):
            return None

        curr = widget
        while curr is not None:
            name = type(curr).__name__

            if isinstance(curr, ctk.CTkScrollableFrame) or name == "CTkScrollableFrame":
                if cls.is_widget_visible(curr):
                    return curr

            # Check if curr is the underlying Canvas of a CTkScrollableFrame
            elif isinstance(curr, tk.Canvas):
                for child in curr.children.values():
                    if (isinstance(child, ctk.CTkScrollableFrame) or type(child).__name__ == "CTkScrollableFrame"):
                        if cls.is_widget_visible(child):
                            return child

            curr = getattr(curr, "master", None)
        return None

    @classmethod
    def handle_mousewheel(cls, event) -> None:
        """Route mouse wheel event dynamically to the scrollable container under pointer."""
        target_widget = None

        # 1. Determine widget directly under the pointer coordinates
        try:
            if hasattr(event, "x_root") and hasattr(event, "y_root"):
                w = getattr(event, "widget", None)
                if hasattr(w, "winfo_containing"):
                    target_widget = w.winfo_containing(event.x_root, event.y_root)
        except Exception:
            pass

        # 2. Fallback to event.widget for synthetic test events
        if target_widget is None and hasattr(event, "widget"):
            target_widget = event.widget

        if target_widget is None:
            return

        # 3. Locate innermost scrollable frame
        sf = cls.find_scrollable_container(target_widget)
        if sf is None:
            return

        try:
            canvas = getattr(sf, "_parent_canvas", None)
            if canvas is None or not canvas.winfo_exists():
                return

            # Determine scroll direction & delta
            delta = getattr(event, "delta", 0)
            if delta == 0:
                # Linux Button-4 is scroll up, Button-5 is scroll down
                num = getattr(event, "num", 0)
                if num == 4:
                    delta = 120
                elif num == 5:
                    delta = -120
                else:
                    return

            # Shift key detection (keyboard tracking or event state bitmask)
            is_shift = cls._shift_pressed or bool(getattr(event, "state", 0) & 0x0001)

            # Standard smooth scroll increment
            units = -int(delta / 6)
            if units == 0:
                units = -1 if delta > 0 else 1

            if is_shift:
                # Horizontal scrolling where applicable
                if canvas.xview() != (0.0, 1.0):
                    canvas.xview("scroll", units, "units")
            else:
                # Vertical scrolling (only if content exceeds visible area)
                if canvas.yview() != (0.0, 1.0):
                    canvas.yview("scroll", units, "units")
        except Exception:
            pass
