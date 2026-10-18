"""Centralized, leak-safe, DPI-aware mouse-wheel scrolling manager for CustomTkinter.

Provides reliable mouse-wheel scrolling across all application views and modals:
- Directs wheel scrolling to the scrollable container beneath the mouse pointer.
- Fully DPI-aware coordinate mapping on Windows across any display scale factor (100%, 125%, 150%, 175%, 200%).
- Robust multi-strategy resolution: leaf widget ancestry, card containers, pointer coordinates, and active view/modal context.
- Natural desktop scroll increment (40px per 120-delta notch) for smooth, visible content movement.
- Suppresses redundant per-frame global bindings to avoid callback accumulation.
- Supports vertical scrolling and Shift + wheel horizontal scrolling.
- Automatically respects nested scroll containers (inner container scrolls first).
- Protects interactive controls (CTkTextbox, CTkOptionMenu, CTkSlider) from being hijacked.
- Prevents scrolling of hidden/unmapped tabs or screens whose content fully fits.
- Safe lifecycle management with zero memory leaks and zero stale callbacks.
"""
import sys
import tkinter as tk
from typing import Optional, List
import customtkinter as ctk


class ScrollManager:
    """Centralized mouse-wheel controller for CustomTkinter scrollable containers."""

    _installed: bool = False
    _shift_pressed: bool = False
    _orig_init = None
    _root_window: Optional[tk.Misc] = None

    @classmethod
    def install(cls, root: Optional[tk.Misc] = None) -> None:
        """Install centralized mouse-wheel handler and patch CTkScrollableFrame.
        
        Args:
            root: Root or toplevel window to bind global listeners to.
        """
        if root is not None:
            cls._root_window = root

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
        """Locate the innermost active CTkScrollableFrame related to the target widget.
        
        Climbs up the hierarchy from leaf widgets to ensure nested containers take precedence.
        Also inspects widget attributes, canvas parents, and child containers.
        """
        if widget is None or cls.is_ignored_widget(widget):
            return None

        curr = widget
        while curr is not None:
            name = type(curr).__name__

            # Direct match
            if isinstance(curr, ctk.CTkScrollableFrame) or name == "CTkScrollableFrame":
                if cls.is_widget_visible(curr):
                    return curr

            # Underlying Canvas of a CTkScrollableFrame
            if isinstance(curr, (tk.Canvas, ctk.windows.widgets.core_rendering.ctk_canvas.CTkCanvas)) or name in ("Canvas", "CTkCanvas"):
                master = getattr(curr, "master", None)
                if isinstance(master, ctk.CTkScrollableFrame) or type(master).__name__ == "CTkScrollableFrame":
                    if cls.is_widget_visible(master):
                        return master
                for child in getattr(curr, "children", {}).values():
                    if isinstance(child, ctk.CTkScrollableFrame) or type(child).__name__ == "CTkScrollableFrame":
                        if cls.is_widget_visible(child):
                            return child

            # Outer _parent_frame of a CTkScrollableFrame or card container
            for child in getattr(curr, "children", {}).values():
                if isinstance(child, ctk.CTkScrollableFrame) or type(child).__name__ == "CTkScrollableFrame":
                    if cls.is_widget_visible(child):
                        return child
                # Check canvas child of parent frame
                if isinstance(child, tk.Canvas) or type(child).__name__ in ("Canvas", "CTkCanvas"):
                    for sub in getattr(child, "children", {}).values():
                        if isinstance(sub, ctk.CTkScrollableFrame) or type(sub).__name__ == "CTkScrollableFrame":
                            if cls.is_widget_visible(sub):
                                return sub

            # Common view attributes referencing scrollable containers
            for attr in ("rows_frame", "form_scroll", "scroll_frame", "scroll_container", "tqm_scroll"):
                candidate = getattr(curr, attr, None)
                if candidate is not None and (isinstance(candidate, ctk.CTkScrollableFrame) or type(candidate).__name__ == "CTkScrollableFrame"):
                    if cls.is_widget_visible(candidate):
                        return candidate

            curr = getattr(curr, "master", None)

        return None

    @classmethod
    def _find_all_visible_scrollables(cls, root: tk.Misc) -> List[ctk.CTkScrollableFrame]:
        """Find all viewable CTkScrollableFrames within a container hierarchy."""
        results = []
        if root is None or not hasattr(root, "winfo_exists") or not root.winfo_exists():
            return results

        if (isinstance(root, ctk.CTkScrollableFrame) or type(root).__name__ == "CTkScrollableFrame") and cls.is_widget_visible(root):
            results.append(root)

        for child in getattr(root, "children", {}).values():
            results.extend(cls._find_all_visible_scrollables(child))
        return results

    @classmethod
    def resolve_scroll_target(cls, event) -> Optional[ctk.CTkScrollableFrame]:
        """Resolve the target CTkScrollableFrame dynamically and DPI-agnostically."""
        # Strategy 1: Check event.widget directly
        ev_widget = getattr(event, "widget", None)
        if ev_widget is not None:
            sf = cls.find_scrollable_container(ev_widget)
            if sf is not None:
                return sf

        # Strategy 2: Pointer coordinate resolution with DPI awareness
        root = cls._root_window
        if root is None and ev_widget is not None and hasattr(ev_widget, "winfo_toplevel"):
            root = ev_widget.winfo_toplevel()

        if root is not None and hasattr(root, "winfo_exists") and root.winfo_exists():
            scaling = 1.0
            if hasattr(root, "_get_window_scaling"):
                try:
                    scaling = float(root._get_window_scaling())
                except Exception:
                    scaling = 1.0

            x_root = getattr(event, "x_root", None)
            y_root = getattr(event, "y_root", None)

            candidates = []
            if x_root is not None and y_root is not None:
                # Raw coordinates
                try:
                    w1 = root.winfo_containing(x_root, y_root)
                    if w1 is not None:
                        candidates.append(w1)
                except Exception:
                    pass

                # Scaled coordinates (when Windows delivers physical screen coordinates under high DPI)
                if scaling != 1.0 and scaling > 0:
                    try:
                        w2 = root.winfo_containing(int(x_root / scaling), int(y_root / scaling))
                        if w2 is not None and w2 not in candidates:
                            candidates.append(w2)
                    except Exception:
                        pass

            # winfo_pointerxy fallback
            try:
                px, py = root.winfo_pointerxy()
                w3 = root.winfo_containing(px, py)
                if w3 is not None and w3 not in candidates:
                    candidates.append(w3)
                if scaling != 1.0 and scaling > 0:
                    w4 = root.winfo_containing(int(px / scaling), int(py / scaling))
                    if w4 is not None and w4 not in candidates:
                        candidates.append(w4)
            except Exception:
                pass

            for c in candidates:
                sf = cls.find_scrollable_container(c)
                if sf is not None:
                    return sf

            # Strategy 3: Check active modal dialogs (CTkToplevel)
            try:
                for child in root.winfo_children():
                    if isinstance(child, (ctk.CTkToplevel, tk.Toplevel)) and cls.is_widget_visible(child):
                        modal_sfs = cls._find_all_visible_scrollables(child)
                        if modal_sfs:
                            return modal_sfs[0]
            except Exception:
                pass

            # Strategy 4: Active view frame or root container contextual fallback
            container = getattr(root, "current_view_frame", None) or root
            if container is not None and cls.is_widget_visible(container):
                view_sfs = cls._find_all_visible_scrollables(container)
                if len(view_sfs) == 1:
                    return view_sfs[0]
                elif len(view_sfs) > 1:
                    # Multi-container views (e.g. Dashboard): pick container closest to pointer
                    best_sf = view_sfs[0]
                    if x_root is not None and y_root is not None:
                        for sf in view_sfs:
                            try:
                                sx = sf.winfo_rootx()
                                sy = sf.winfo_rooty()
                                sw = sf.winfo_width()
                                sh = sf.winfo_height()
                                # Test raw or scaled containment
                                if (sx <= x_root <= sx + sw and sy <= y_root <= sy + sh) or \
                                   (sx <= int(x_root / scaling) <= sx + sw and sy <= int(y_root / scaling) <= sy + sh):
                                    return sf
                            except Exception:
                                pass
                    return best_sf

        return None

    @classmethod
    def handle_mousewheel(cls, event) -> None:
        """Route mouse wheel event dynamically to the scrollable container under pointer."""
        sf = cls.resolve_scroll_target(event)
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

            # Responsive desktop scroll increment (40px per 120-delta notch = 1 full row / 3 text lines)
            step_pixels = 40
            units = -int((delta / 120.0) * step_pixels)
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
