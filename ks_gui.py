"""
KentScript GUI Module - Enhanced Tkinter-based GUI Framework
==========================================================
A comprehensive GUI toolkit for KentScript providing:
- Window management with full protocol support
- Complete widget set (all Tkinter widgets)
- Keyboard shortcuts and accelerators
- Full event handling system
- Clipboard operations
- Canvas with all item types
- Complete text widget with tags and undo
- All dialogs

Usage in KentScript:
    import gui;
    let win = gui.create_window("My App", 400, 300);
    let lbl = gui.create_label(win, "Hello!");
    gui.pack(lbl);
    gui.mainloop(win);
"""

import sys
import os

_tkinter = None
_windows = []
_ks_interpreter_holder = [None]


def _lazy_import_tkinter():
    """Lazily import tkinter - returns None if not available"""
    global _tkinter
    if _tkinter is None:
        try:
            import tkinter as tk_module

            _tkinter = tk_module
        except ImportError:
            _tkinter = False
    return _tkinter if _tkinter is not False else None


# ============================================================================
# FALLBACK MODE - When tkinter is not available
# ============================================================================


def _create_fallback_gui():
    """Create fallback GUI functions that print helpful messages"""

    def create_window(title="KentScript GUI", width=400, height=300):
        print(f"[GUI] Would create window '{title}' ({width}x{height})")
        return {"__ks_gui_dummy__": True, "type": "window", "title": title}

    def create_label(parent, text=""):
        return {"__ks_gui_dummy__": True, "type": "label", "text": text}

    def create_button(parent, text="", command=None):
        return {"__ks_gui_dummy__": True, "type": "button", "text": text}

    def create_entry(parent, width=30):
        return {"__ks_gui_dummy__": True, "type": "entry", "text": ""}

    def create_text(parent, width=40, height=10):
        return {"__ks_gui_dummy__": True, "type": "text", "content": ""}

    def create_listbox(parent):
        return {"__ks_gui_dummy__": True, "type": "listbox"}

    def create_frame(parent):
        return {"__ks_gui_dummy__": True, "type": "frame"}

    def create_canvas(parent, width=200, height=200):
        return {"__ks_gui_dummy__": True, "type": "canvas"}

    def create_menu(parent):
        return {"__ks_gui_dummy__": True, "type": "menu"}

    def create_checkbutton(parent, text="", command=None):
        return {"__ks_gui_dummy__": True, "type": "checkbutton", "text": text}

    def create_radiobutton(parent, text="", value="", command=None):
        return {
            "__ks_gui_dummy__": True,
            "type": "radiobutton",
            "text": text,
            "value": value,
        }

    def create_scale(parent, from_=0, to=100, orient="horizontal"):
        return {"__ks_gui_dummy__": True, "type": "scale"}

    def create_spinbox(parent, from_=0, to=100):
        return {"__ks_gui_dummy__": True, "type": "spinbox"}

    def create_scrollbar(parent, orient="vertical", command=None):
        return {"__ks_gui_dummy__": True, "type": "scrollbar"}

    def create_progressbar(parent, mode="determinate"):
        return {"__ks_gui_dummy__": True, "type": "progressbar"}

    def create_notebook(parent):
        return {"__ks_gui_dummy__": True, "type": "notebook"}

    def create_panedwindow(parent, orient="horizontal"):
        return {"__ks_gui_dummy__": True, "type": "panedwindow"}

    def create_label_frame(parent, text=""):
        return {"__ks_gui_dummy__": True, "type": "labelframe", "text": text}

    def create_combobox(parent, values=None):
        return {"__ks_gui_dummy__": True, "type": "combobox"}

    def create_treeview(parent, columns=None):
        return {"__ks_gui_dummy__": True, "type": "treeview"}

    def create_separator(parent):
        return {"__ks_gui_dummy__": True, "type": "separator"}

    def create_sizegrip(parent):
        return {"__ks_gui_dummy__": True, "type": "sizegrip"}

    def create_image(parent, path):
        return {"__ks_gui_dummy__": True, "type": "image", "path": path}

    def create_timer(parent, interval, command):
        return {"__ks_gui_dummy__": True, "type": "timer"}

    def create_textbox(parent, width=40, height=10):
        return {"__ks_gui_dummy__": True, "type": "text", "content": ""}

    def create_texttag(parent):
        return {"__ks_gui_dummy__": True, "type": "texttag"}

    def create_windowwidget(parent, widget, **kwargs):
        return {"__ks_gui_dummy__": True, "type": "window"}

    # Layout managers
    def pack(widget, **kwargs):
        return None

    def grid(widget, **kwargs):
        return None

    def place(widget, **kwargs):
        return None

    def mainloop(window):
        return None

    def update():
        return None

    def update_idletasks():
        return None

    def after(ms, func=None):
        return None

    def after_cancel(id):
        return None

    def after_idle(func):
        return None

    # Widget operations
    def get_text(widget):
        if widget and isinstance(widget, dict):
            return widget.get("text", "") or widget.get("content", "")
        return ""

    def set_text(widget, text):
        if widget and isinstance(widget, dict):
            widget["text"] = text
        return None

    def get_value(widget):
        if widget and isinstance(widget, dict):
            return widget.get("value", "")
        return ""

    def set_value(widget, value):
        if widget and isinstance(widget, dict):
            widget["value"] = value
        return None

    def configure(widget, **kwargs):
        return None

    def config(widget, **kwargs):
        return None

    def bind(widget, event, handler):
        return None

    def bind_all(widget, event, handler):
        return None

    def unbind(widget, event):
        return None

    def unbind_all(event):
        return None

    def focus(widget=None):
        return None

    def focus_force():
        return None

    def focus_get():
        return None

    def focus_set(widget):
        return None

    def grab_set(widget):
        return None

    def grab_release(widget):
        return None

    def grab_set_global(widget):
        return None

    def tkraise(widget):
        return None

    def lower(widget):
        return None

    def lift(widget):
        return None

    # Shortcuts
    def add_shortcut(widget, key, handler):
        return None

    def remove_shortcut(widget, key):
        return None

    def bind_shortcut(widget, shortcut, handler):
        """Bind a keyboard shortcut - supports formats like 'Ctrl+C', 'Alt+F4', 'Return'"""
        return None

    # Clipboard
    def clipboard_get():
        return ""

    def clipboard_set(text):
        return None

    def clipboard_append(text):
        return None

    def clipboard_clear():
        return None

    # Dialogs
    def message_box(title, message, type="info"):
        print(f"[GUI] MessageBox [{type}] {title}: {message}")
        if type in ("yesno", "okcancel"):
            return True
        return None

    def filedialog(mode="open", title="Select File", **kwargs):
        return ""

    def colorchooser(title="Select Color"):
        return "#000000"

    def simpledialog(title="Input", prompt="Enter value:", initialvalue=""):
        return ""

    def fontchooser(title="Select Font"):
        return ("Arial", 10)

    # Canvas
    def canvas_create_line(canvas, x1, y1, x2, y2, **kwargs):
        return None

    def canvas_create_oval(canvas, x1, y1, x2, y2, **kwargs):
        return None

    def canvas_create_rectangle(canvas, x1, y1, x2, y2, **kwargs):
        return None

    def canvas_create_polygon(canvas, points, **kwargs):
        return None

    def canvas_create_text(canvas, x, y, text="", **kwargs):
        return None

    def canvas_create_image(canvas, x, y, image, **kwargs):
        return None

    def canvas_create_arc(canvas, x1, y1, x2, y2, **kwargs):
        return None

    def canvas_create_bitmap(canvas, x, y, bitmap="", **kwargs):
        return None

    def canvas_create_window(canvas, x, y, window, **kwargs):
        return None

    def canvas_create_oval(canvas, x1, y1, x2, y2, **kwargs):
        return None

    def canvas_delete(canvas, item):
        return None

    def canvas_move(canvas, item, dx, dy):
        return None

    def canvas_coords(canvas, item, *coords):
        return []

    def canvas_bind(canvas, item, event, handler):
        return None

    def canvas_itemconfig(canvas, item, **kwargs):
        return None

    def canvas_itemcget(canvas, item, option):
        return None

    def canvas_tags(canvas, item, *tags):
        return None

    def canvas_addtag(canvas, tag, method, *args):
        return None

    def canvas_dtag(canvas, item, tag):
        return None

    def canvas_find(canvas, withtag=None):
        return []

    def canvas_bbox(canvas, item=None):
        return None

    def canvas_confine(canvas, area):
        return None

    def canvas_curselection(canvas):
        return None

    def canvas_scan_dragto(canvas, x, y):
        return None

    def canvas_scan_mark(canvas, x, y):
        return None

    def canvas_select_from(canvas, item, index):
        return None

    def canvas_select_clear(canvas):
        return None

    def canvas_select_item(canvas):
        return None

    # Menu
    def menu_add_command(menu, label, command=None, accelerator=""):
        return None

    def menu_add_separator(menu):
        return None

    def menu_add_cascade(menu, label, menu_handle):
        return None

    def menu_add_checkbutton(menu, label, command=None):
        return None

    def menu_add_radiobutton(menu, label, command=None, value=""):
        return None

    def menu_delete(menu, start, end=None):
        return None

    def menu_entryconfig(menu, index, **kwargs):
        return None

    def menu_entrycget(menu, index, option):
        return None

    def menu_insert(menu, index, itemtype, **kwargs):
        return None

    # Text widget
    def text_index(widget, index):
        return "1.0"

    def text_get(widget, start="1.0", end="end"):
        return ""

    def text_insert(widget, index, text):
        return None

    def text_delete(widget, start="1.0", end="end"):
        return None

    def text_see(widget, index):
        return None

    def text_search(widget, pattern, start="1.0", stop="end"):
        return ""

    def text_tag_add(widget, tagName, start, end):
        return None

    def text_tag_remove(widget, tagName, start="1.0", end="end"):
        return None

    def text_tag_config(widget, tagName, **kwargs):
        return None

    def text_tag_names(widget, index=None):
        return []

    def text_tag_delete(widget, *tagNames):
        return None

    def text_tag_lower(widget, tagName, belowThis=None):
        return None

    def text_tag_raise(widget, tagName, aboveThis=None):
        return None

    def text_tag_ranges(widget, tagName):
        return []

    def text_dump(widget, index, **kwargs):
        return {}

    def text_edit_undo(widget):
        return None

    def text_edit_redo(widget):
        return None

    def text_edit_separator(widget):
        return None

    def text_edit_reset(widget):
        return None

    def text_mark_gravity(widget, markName, direction=None):
        return None

    def text_mark_set(widget, markName, index):
        return None

    def text_mark_unset(widget, *markNames):
        return None

    def text_mark_next(widget, index):
        return None

    def text_mark_previous(widget, index):
        return None

    def text_window_create(widget, index, window, **kwargs):
        return None

    def text_window_cget(widget, index, option):
        return None

    def text_window_config(widget, index, **kwargs):
        return None

    def text_image_create(widget, index, image, **kwargs):
        return None

    def text_image_cget(widget, index, option):
        return None

    def text_compare(widget, index1, op, index2):
        return None

    def text_count(widget, index1, index2, *options):
        return 0

    def text_debug(widget, boolean=None):
        return None

    def text_dlineinfo(widget, index):
        return None

    # Notebook
    def notebook_add(notebook, child, text=""):
        return None

    def notebook_forget(notebook, child):
        return None

    def notebook_select(notebook, child=None):
        return None

    def notebook_tab(notebook, child, option=None):
        return None

    def notebook_tabs(notebook):
        return []

    def notebook_hide(notebook, child):
        return None

    def notebook_insert(notebook, index, child, **kwargs):
        return None

    def notebook_enable_traversal(notebook):
        return None

    def notebook_validate(notebook, key, new_tab):
        return None

    # Treeview
    def treeview_insert(parent, iid, text="", values=None, **kwargs):
        return None

    def treeview_delete(tree, *items):
        return None

    def treeview_get_children(tree, item=None):
        return []

    def treeview_item(tree, item, option=None, **kwargs):
        return None

    def treeview_selection(tree, items=None):
        return []

    def treeview_see(tree, item):
        return None

    def treeview_tag_bind(tree, tag, event=None, callback=None):
        return None

    def treeview_tag_config(tree, tag, **kwargs):
        return None

    def treeview_columns(tree, columns=None):
        return []

    def treeview_column(tree, col, option=None, **kwargs):
        return None

    def treeview_heading(tree, col, option=None, **kwargs):
        return None

    def treeview_move(tree, item, parent, index):
        return None

    def treeview_next_sibling(tree, item):
        return None

    def treeview_prev_sibling(tree, item):
        return None

    def treeview_root(tree):
        return []

    def treeview_set_children(tree, parent, *items):
        return None

    # PanedWindow
    def panedwindow_add(paned, child, **kwargs):
        return None

    def panedwindow_forget(paned, child):
        return None

    def panedwindow_pane(paned, child, option=None, **kwargs):
        return None

    def panedwindow_sashpos(paned, index, pos=None):
        return None

    def panedwindow_add_with_drag(paned, child, **kwargs):
        return None

    def panedwindow_remove(paned, child):
        return None

    def panedwindow_get_children(paned):
        return []

    # Listbox
    def listbox_insert(listbox, index, *items):
        return None

    def listbox_delete(listbox, first, last=None):
        return None

    def listbox_get(listbox, first, last=None):
        return []

    def listbox_curselection(listbox):
        return []

    def listbox_size(listbox):
        return 0

    def listbox_activate(listbox, index):
        return None

    def listbox_cget(listbox, index, option):
        return None

    def listbox_config(listbox, **kwargs):
        return None

    def listbox_itemconfigure(listbox, index, **kwargs):
        return None

    def listbox_nearest(listbox, y):
        return 0

    def listbox_see(listbox, index):
        return None

    def listbox_selection_anchor(listbox, index):
        return None

    def listbox_selection_clear(listbox, first, last=None):
        return None

    def listbox_selection_includes(listbox, index):
        return False

    def listbox_selection_set(listbox, first, last=None):
        return None

    # Scrollbar
    def scrollbar_set(scrollbar, first, last):
        return None

    def scrollbar_get(scrollbar):
        return (0.0, 1.0)

    def scrollbar_set_command(scrollbar, command):
        return None

    # Progressbar
    def progressbar_start(widget):
        return None

    def progressbar_stop(widget):
        return None

    def progressbar_step(widget, amount=None):
        return None

    def progressbar_config(widget, **kwargs):
        return None

    # Spinbox
    def spinbox_config(widget, **kwargs):
        return None

    def spinbox_get(widget):
        return ""

    def spinbox_set(widget, value):
        return None

    # Entry
    def entry_config(widget, **kwargs):
        return None

    def entry_get(widget):
        return ""

    def entry_set(widget, value):
        return None

    def entry_validate(widget):
        return True

    def entry_selection_from(widget, start):
        return None

    def entry_selection_to(widget, end):
        return None

    def entry_selection_present(widget):
        return False

    def entry_selection_clear(widget):
        return None

    def entry_selection_get(widget):
        return ""

    def entry_index(widget, index):
        return 0

    def entry_icursor(widget, index=None):
        return None

    def entry_xview(widget, index=None):
        return None

    def entry_xview_moveto(widget, fraction):
        return None

    def entry_xview_scroll(widget, number, what):
        return None

    # Widget info
    def destroy(window):
        return None

    def withdraw(window):
        return None

    def deiconify(window):
        return None

    def iconify(window):
        return None

    def geometry(window, geometry=None):
        return ""

    def maxsize(window, width=None, height=None):
        return (0, 0)

    def minsize(window, width=None, height=None):
        return (0, 0)

    def resizable(window, width=True, height=True):
        return None

    def title(window, title=None):
        return ""

    def protocol(window, name, func=None):
        return None

    def attributes(window, **kwargs):
        return None

    def state(window, state=None):
        return "normal"

    def transient(window, parent=None):
        return None

    def winfo_children(window):
        return []

    def winfo_parent(window):
        return ""

    def winfo_width(window):
        return 0

    def winfo_height(window):
        return 0

    def winfo_x(window):
        return 0

    def winfo_y(window):
        return 0

    def winfo_rootx(window):
        return 0

    def winfo_rooty(window):
        return 0

    def winfo_reqwidth(window):
        return 0

    def winfo_reqheight(window):
        return 0

    def winfo_cells(window):
        return 0

    def winfo_colormapfull(window):
        return False

    def winfo_depth(window):
        return 0

    def winfo_exists(window):
        return False

    def winfo_fpixels(window, number):
        return 0.0

    def winfo_geometry(window):
        return ""

    def winfo_screenwidth(window):
        return 0

    def winfo_screenheight(window):
        return 0

    def winfo_screenmmwidth(window):
        return 0

    def winfo_screenmmheight(window):
        return 0

    def winfo_screenvdepth(window):
        return 0

    def winfo_screenvrootx(window):
        return 0

    def winfo_screenvrooty(window):
        return 0

    def winfo_visual(window):
        return ""

    def winfo_visualid(window):
        return 0

    # Timer
    def timer_start(timer_id):
        return None

    def timer_stop(timer_id):
        return None

    # Variables
    def create_string_var(value=""):
        return {"value": value}

    def create_int_var(value=0):
        return {"value": value}

    def create_bool_var(value=False):
        return {"value": value}

    def create_double_var(value=0.0):
        return {"value": value}

    # Animation
    def animate(widget, duration, properties, callback=None):
        return None

    # Modern styling
    def ttk_style():
        return True

    def set_style(widget, style_name):
        return None

    # New widget stubs (fallback mode)
    def create_toast(parent, message, duration=3000, **kwargs):
        print(f"[GUI] Toast: {message}")
        return None

    def create_status_bar(parent, text="", **kwargs):
        return {"__ks_gui_dummy__": True, "type": "status_bar"}

    def set_status_text(widget, text):
        return None

    def create_date_picker(parent, **kwargs):
        return {"__ks_gui_dummy__": True, "type": "date_picker"}

    def get_date(widget):
        return "2026-01-01"

    def create_context_menu(parent, items=None, **kwargs):
        return {"__ks_gui_dummy__": True, "type": "context_menu"}

    def show_context_menu(menu, event):
        return None

    def create_markdown_viewer(parent, width=60, height=20, **kwargs):
        return {"__ks_gui_dummy__": True, "type": "markdown_viewer"}

    def render_markdown(widget, md_text):
        return None

    def set_theme(widget, theme_name):
        return None

    def set_theme_recursive(widget, theme_name):
        return None

    # Generic widget ops (fallback no-ops)
    def insert(widget, index, text):
        return None

    def delete(widget, start, end=None):
        return None

    def curselection(widget):
        return ()

    def set_scrollbar(scrollbar, value):
        return None

    def xview(widget, *args):
        return None

    def yview(widget, *args):
        return None

    # Module exports
    return _create_fallback_exports(locals())


def _create_fallback_exports(local_dict):
    """Create exports dict from fallback functions"""
    return local_dict


# ============================================================================
# REAL TKINTER MODE - Full GUI functionality
# ============================================================================


def _create_real_gui():
    """Create real tkinter GUI functions"""
    global _windows

    tk = _lazy_import_tkinter()
    if tk is None:
        return _create_fallback_gui()

    _timers = {}
    _timer_id = [0]
    _callbacks = {}
    _callback_id = [0]
    _widget_ids = {}
    _widget_id_counter = [0]
    _main_window = None
    _shortcut_handlers = {}  # Keyboard shortcut handlers

    # --- Helper functions ---
    def _get_interpreter():
        return _ks_interpreter_holder[0]

    def _set_interpreter(interp):
        _ks_interpreter_holder[0] = interp

    def _get_next_widget_id():
        wid = _widget_id_counter[0]
        _widget_id_counter[0] += 1
        return wid

    def assign_widget_id(widget, widget_type="widget"):
        wid = _get_next_widget_id()
        _widget_ids[wid] = {"widget": widget, "type": widget_type, "callbacks": {}}
        return wid

    def get_widget_by_id(wid):
        if wid in _widget_ids:
            return _widget_ids[wid]["widget"]
        return None

    def _wrap_callback(handler, *extra_args, **extra_kwargs):
        """Wrap a KentScript callback for safe execution"""

        def wrapper(*args, **kwargs):
            try:
                _ks_interp = _get_interpreter()
                merged_args = extra_args + args
                merged_kwargs = {**extra_kwargs, **kwargs}
                if hasattr(handler, "body") and _ks_interp is not None:
                    for stmt in handler.body:
                        _ks_interp.interpret([stmt])
                elif callable(handler):
                    handler(*merged_args, **merged_kwargs)
            except Exception as e:
                print(f"Callback error: {e}")

        return wrapper

    # --- Shortcut system ---
    def _parse_shortcut(shortcut):
        """Parse shortcut string like 'Ctrl+C', 'Alt+F4', 'Return' into Tk format"""
        tk_shortcut = shortcut
        tk_shortcut = tk_shortcut.replace("Ctrl", "Control")
        tk_shortcut = tk_shortcut.replace("Esc", "Escape")
        tk_shortcut = tk_shortcut.replace("Del", "Delete")
        tk_shortcut = tk_shortcut.replace("Ins", "Insert")
        return f"<{tk_shortcut}>"

    def add_shortcut(widget, key, handler):
        """Add a keyboard shortcut to a widget"""
        try:
            event_sequence = _parse_shortcut(key)
            wrapped = _wrap_callback(handler)
            widget.bind(event_sequence, wrapped)
            # Store for later unbinding
            if widget not in _shortcut_handlers:
                _shortcut_handlers[widget] = {}
            _shortcut_handlers[widget][key] = (event_sequence, wrapped)
            return True
        except Exception as e:
            print(f"add_shortcut error: {e}")
            return False

    def remove_shortcut(widget, key):
        """Remove a keyboard shortcut from a widget"""
        try:
            if widget in _shortcut_handlers and key in _shortcut_handlers[widget]:
                event_sequence, handler = _shortcut_handlers[widget][key]
                widget.unbind(event_sequence)
                del _shortcut_handlers[widget][key]
                return True
            return False
        except Exception as e:
            print(f"remove_shortcut error: {e}")
            return False

    def bind_shortcut(widget, shortcut, handler):
        """Bind a keyboard shortcut - alias for add_shortcut"""
        return add_shortcut(widget, shortcut, handler)

    # --- Window Management ---
    def create_window(title="KentScript GUI", width=400, height=300):
        try:
            root = tk.Tk()
            root.title(title)
            root.geometry(f"{width}x{height}")
            _windows.append(root)
            global _main_window
            _main_window = root
            return root
        except Exception as e:
            print(f"create_window error: {e}")
            return None

    # --- Basic Widgets ---
    def create_label(parent, text="", **kwargs):
        try:
            return tk.Label(parent, text=text, padx=5, pady=5, **kwargs)
        except Exception as e:
            print(f"create_label error: {e}")
            return None

    def create_button(parent, text="", command=None, **kwargs):
        try:
            btn = tk.Button(parent, text=text, padx=5, pady=2, **kwargs)
            btn_id = assign_widget_id(btn, "button")
            _widget_ids[btn_id]["callbacks"]["click"] = command
            wrapped = _wrap_callback(command)
            btn.config(command=wrapped)
            return btn
        except Exception as e:
            print(f"create_button error: {e}")
            return None

    def create_entry(parent, width=30, **kwargs):
        try:
            return tk.Entry(parent, width=width, **kwargs)
        except Exception as e:
            print(f"create_entry error: {e}")
            return None

    def create_text(parent, width=40, height=10, **kwargs):
        try:
            return tk.Text(parent, width=width, height=height, **kwargs)
        except Exception as e:
            print(f"create_text error: {e}")
            return None

    def create_textbox(parent, width=40, height=10, **kwargs):
        """Alias for create_text"""
        return create_text(parent, width, height, **kwargs)

    def create_listbox(parent, **kwargs):
        try:
            return tk.Listbox(parent, **kwargs)
        except Exception as e:
            print(f"create_listbox error: {e}")
            return None

    def create_frame(parent, **kwargs):
        try:
            return tk.Frame(parent, padx=5, pady=5, **kwargs)
        except Exception as e:
            print(f"create_frame error: {e}")
            return None

    def create_checkbutton(parent, text="", command=None, **kwargs):
        try:
            var = tk.BooleanVar(value=False)
            wrapped = _wrap_callback(command)
            cb = tk.Checkbutton(
                parent, text=text, variable=var, command=wrapped, **kwargs
            )
            cb._ks_var = var
            return cb
        except Exception as e:
            print(f"create_checkbutton error: {e}")
            return None

    def create_radiobutton(parent, text="", value="", command=None, **kwargs):
        try:
            var = kwargs.pop("variable", tk.StringVar(value=value))
            wrapped = _wrap_callback(command)
            return tk.Radiobutton(
                parent, text=text, value=value, variable=var, command=wrapped, **kwargs
            )
        except Exception as e:
            print(f"create_radiobutton error: {e}")
            return None

    def create_scale(parent, from_=0, to=100, orient="horizontal", **kwargs):
        try:
            orient_val = {"horizontal": tk.HORIZONTAL, "vertical": tk.VERTICAL}.get(
                orient, tk.HORIZONTAL
            )
            return tk.Scale(parent, from_=from_, to=to, orient=orient_val, **kwargs)
        except Exception as e:
            print(f"create_scale error: {e}")
            return None

    def create_spinbox(parent, from_=0, to=100, **kwargs):
        try:
            return tk.Spinbox(parent, from_=from_, to=to, **kwargs)
        except Exception as e:
            print(f"create_spinbox error: {e}")
            return None

    def create_scrollbar(parent, orient="vertical", command=None, **kwargs):
        try:
            orient_val = {"horizontal": tk.HORIZONTAL, "vertical": tk.VERTICAL}.get(
                orient, tk.VERTICAL
            )
            sb = tk.Scrollbar(parent, orient=orient_val, **kwargs)
            if command:
                sb.config(command=command)
            return sb
        except Exception as e:
            print(f"create_scrollbar error: {e}")
            return None

    def create_separator(parent, **kwargs):
        try:
            return tk.Separator(parent, **kwargs)
        except Exception as e:
            print(f"create_separator error: {e}")
            return None

    def create_sizegrip(parent, **kwargs):
        try:
            return tk.Sizegrip(parent, **kwargs)
        except Exception as e:
            print(f"create_sizegrip error: {e}")
            return None

    # --- Advanced Widgets ---
    def create_canvas(parent, width=200, height=200, **kwargs):
        try:
            return tk.Canvas(parent, width=width, height=height, **kwargs)
        except Exception as e:
            print(f"create_canvas error: {e}")
            return None

    def create_menu(parent, **kwargs):
        try:
            return tk.Menu(parent, **kwargs)
        except Exception as e:
            print(f"create_menu error: {e}")
            return None

    def create_notebook(parent, **kwargs):
        try:
            try:
                import tkinter.ttk as ttk

                return ttk.Notebook(parent, **kwargs)
            except:
                return tk.Canvas(parent, **kwargs)
        except Exception as e:
            print(f"create_notebook error: {e}")
            return None

    def create_panedwindow(parent, orient="horizontal", **kwargs):
        try:
            orient_val = {"horizontal": tk.HORIZONTAL, "vertical": tk.VERTICAL}.get(
                orient, tk.HORIZONTAL
            )
            return tk.PanedWindow(parent, orient=orient_val, **kwargs)
        except Exception as e:
            print(f"create_panedwindow error: {e}")
            return None

    def create_label_frame(parent, text="", **kwargs):
        try:
            return tk.LabelFrame(parent, text=text, **kwargs)
        except Exception as e:
            print(f"create_label_frame error: {e}")
            return None

    def create_combobox(parent, values=None, **kwargs):
        try:
            try:
                import tkinter.ttk as ttk

                cb = ttk.Combobox(parent, values=values or [], **kwargs)
                return cb
            except:
                return tk.OptionMenu(parent, tk.StringVar(), *(values or []))
        except Exception as e:
            print(f"create_combobox error: {e}")
            return None

    def create_treeview(parent, columns=None, **kwargs):
        try:
            try:
                import tkinter.ttk as ttk

                cols = columns or ()
                tv = ttk.Treeview(parent, columns=cols, show="tree headings", **kwargs)
                for col in cols:
                    tv.heading(col, text=col)
                    tv.column(col, width=100)
                return tv
            except:
                return None
        except Exception as e:
            print(f"create_treeview error: {e}")
            return None

    def create_progressbar(parent, mode="determinate", **kwargs):
        try:
            try:
                import tkinter.ttk as ttk

                return ttk.Progressbar(parent, mode=mode, **kwargs)
            except:
                return None
        except Exception as e:
            print(f"create_progressbar error: {e}")
            return None

    def create_image(parent, path, **kwargs):
        try:
            try:
                from PIL import Image, ImageTk

                img = Image.open(path)
                photo = ImageTk.PhotoImage(img)
                return photo
            except:
                try:
                    return tk.PhotoImage(file=path)
                except:
                    return None
        except Exception as e:
            print(f"create_image error: {e}")
            return None

    def create_timer(parent, interval, command):
        try:
            timer_id = _timer_id[0]
            _timer_id[0] += 1

            def wrapper():
                try:
                    _ks_interp = _get_interpreter()
                    if hasattr(command, "body") and _ks_interp is not None:
                        for stmt in command.body:
                            _ks_interp.interpret([stmt])
                    elif callable(command):
                        command()
                except Exception as e:
                    print(f"Timer error: {e}")
                _timers[timer_id] = parent.after(interval, wrapper)

            _timers[timer_id] = parent.after(interval, wrapper)
            return {"__ks_timer__": True, "id": timer_id}
        except Exception as e:
            print(f"create_timer error: {e}")
            return None

    # --- Layout Managers ---
    def pack(widget, **kwargs):
        try:
            if widget and hasattr(widget, "pack"):
                widget.pack(**kwargs)
        except Exception as e:
            print(f"pack error: {e}")

    def grid(widget, **kwargs):
        try:
            if widget and hasattr(widget, "grid"):
                widget.grid(**kwargs)
        except Exception as e:
            print(f"grid error: {e}")

    def place(widget, **kwargs):
        try:
            if widget and hasattr(widget, "place"):
                widget.place(**kwargs)
        except Exception as e:
            print(f"place error: {e}")

    # --- Main Loop ---
    def mainloop(window):
        try:
            if window:
                window.mainloop()
        except Exception as e:
            print(f"mainloop error: {e}")

    def update():
        """Process all pending events"""
        try:
            for w in _windows:
                w.update()
        except Exception as e:
            print(f"update error: {e}")

    def update_idletasks():
        """Process all pending idle tasks"""
        try:
            for w in _windows:
                w.update_idletasks()
        except Exception as e:
            print(f"update_idletasks error: {e}")

    def after(ms, func=None):
        """Schedule func to be called after ms milliseconds"""
        try:
            if _main_window:
                if func:
                    wrapped = _wrap_callback(func)
                    return _main_window.after(ms, wrapped)
                else:
                    return _main_window.after(ms)
            return None
        except Exception as e:
            print(f"after error: {e}")
            return None

    def after_cancel(id):
        """Cancel a scheduled callback"""
        try:
            if _main_window:
                _main_window.after_cancel(id)
        except Exception as e:
            print(f"after_cancel error: {e}")

    def after_idle(func):
        """Schedule func to be called when idle"""
        try:
            if _main_window:
                wrapped = _wrap_callback(func)
                return _main_window.after_idle(wrapped)
            return None
        except Exception as e:
            print(f"after_idle error: {e}")
            return None

    # --- Widget Operations ---
    def get_text(widget):
        try:
            if isinstance(widget, (tk.Entry, tk.Spinbox)):
                return widget.get()
            elif isinstance(widget, tk.Text):
                return widget.get("1.0", tk.END).strip()
            elif isinstance(widget, (tk.Label, tk.Button)):
                return widget.cget("text")
            elif hasattr(widget, "get"):
                return widget.get()
        except Exception as e:
            print(f"get_text error: {e}")
        return ""

    def set_text(widget, text):
        try:
            if isinstance(widget, (tk.Entry, tk.Spinbox)):
                widget.delete(0, tk.END)
                widget.insert(0, text)
            elif isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
                widget.insert("1.0", text)
            elif hasattr(widget, "config"):
                widget.config(text=text)
            elif hasattr(widget, "configure"):
                widget.configure(text=text)
        except Exception as e:
            print(f"set_text error: {e}")

    def get_value(widget):
        try:
            if hasattr(widget, "get"):
                return widget.get()
            elif hasattr(widget, "cget"):
                return widget.cget("text")
        except Exception as e:
            print(f"get_value error: {e}")
        return ""

    def set_value(widget, value):
        try:
            if hasattr(widget, "set"):
                widget.set(value)
            elif hasattr(widget, "delete") and hasattr(widget, "insert"):
                widget.delete(0, tk.END)
                widget.insert(0, value)
        except Exception as e:
            print(f"set_value error: {e}")

    def configure(widget, **kwargs):
        try:
            # `title` is a window *method*, not a config option — route it to widget.title()
            title = kwargs.pop("title", None)
            if title is not None and hasattr(widget, "title"):
                widget.title(title)
            if kwargs:
                if hasattr(widget, "config"):
                    widget.config(**kwargs)
                elif hasattr(widget, "configure"):
                    widget.configure(**kwargs)
        except Exception as e:
            print(f"configure error: {e}")

    def config(widget, **kwargs):
        """Alias for configure"""
        return configure(widget, **kwargs)

    def insert(widget, index, text):
        """Generic insert for any widget (Text index or Listbox index)."""
        try:
            if hasattr(widget, "insert"):
                widget.insert(index, text)
        except Exception as e:
            print(f"insert error: {e}")

    def delete(widget, start, end=None):
        """Generic delete for any widget (Text or Listbox range)."""
        try:
            if hasattr(widget, "delete"):
                if end is not None:
                    widget.delete(start, end)
                else:
                    widget.delete(start)
        except Exception as e:
            print(f"delete error: {e}")

    def curselection(widget):
        """Return the selected indices of a widget (e.g. Listbox)."""
        try:
            if hasattr(widget, "curselection"):
                return widget.curselection()
        except Exception as e:
            print(f"curselection error: {e}")
        return ()

    def set_scrollbar(scrollbar, value):
        """Set a scrollbar's position from a widget's scrollcommand value."""
        try:
            if isinstance(value, (tuple, list)):
                scrollbar.set(*value)
            else:
                scrollbar.set(value)
        except Exception as e:
            print(f"set_scrollbar error: {e}")

    def xview(widget, *args):
        """Scroll/query a widget's horizontal view."""
        try:
            if hasattr(widget, "xview"):
                return widget.xview(*args)
        except Exception as e:
            print(f"xview error: {e}")

    def yview(widget, *args):
        """Scroll/query a widget's vertical view."""
        try:
            if hasattr(widget, "yview"):
                return widget.yview(*args)
        except Exception as e:
            print(f"yview error: {e}")

    def bind(widget, event, handler):
        try:
            wrapped = _wrap_callback(handler)
            widget.bind(event, wrapped)
        except Exception as e:
            print(f"bind error: {e}")

    def bind_all(event, handler):
        try:
            wrapped = _wrap_callback(handler)
            widget.bind_all(event, wrapped)
        except Exception as e:
            print(f"bind_all error: {e}")

    def unbind(widget, event):
        try:
            widget.unbind(event)
        except Exception as e:
            print(f"unbind error: {e}")

    def unbind_all(event):
        try:
            widget.unbind_all(event)
        except Exception as e:
            print(f"unbind_all error: {e}")

    def focus(widget=None):
        try:
            if widget:
                widget.focus()
            return widget
        except Exception as e:
            print(f"focus error: {e}")

    def focus_force():
        try:
            return tk._default_root.focus_force() if tk._default_root else None
        except:
            return None

    def focus_get():
        try:
            return tk._default_root.focus_get() if tk._default_root else None
        except:
            return None

    def focus_set(widget):
        try:
            widget.focus_set()
        except Exception as e:
            print(f"focus_set error: {e}")

    def grab_set(widget):
        try:
            widget.grab_set()
        except Exception as e:
            print(f"grab_set error: {e}")

    def grab_release(widget):
        try:
            widget.grab_release()
        except Exception as e:
            print(f"grab_release error: {e}")

    def grab_set_global(widget):
        try:
            widget.grab_set_global()
        except Exception as e:
            print(f"grab_set_global error: {e}")

    def tkraise(widget):
        """Raise widget to top of stacking order"""
        try:
            widget.tkraise()
        except Exception as e:
            print(f"tkraise error: {e}")

    def lift(widget):
        """Alias for tkraise"""
        return tkraise(widget)

    def lower(widget):
        """Lower widget to bottom of stacking order"""
        try:
            widget.lower()
        except Exception as e:
            print(f"lower error: {e}")

    # --- Clipboard ---
    def clipboard_get():
        try:
            return widget.clipboard_get() if widget else ""
        except:
            return ""

    def clipboard_set(text):
        try:
            widget.clipboard_clear()
            widget.clipboard_append(text)
        except Exception as e:
            print(f"clipboard_set error: {e}")

    def clipboard_append(text):
        try:
            widget.clipboard_append(text)
        except Exception as e:
            print(f"clipboard_append error: {e}")

    def clipboard_clear():
        try:
            widget.clipboard_clear()
        except Exception as e:
            print(f"clipboard_clear error: {e}")

    # --- Dialogs ---
    def message_box(title, message, type="info"):
        try:
            from tkinter import messagebox

            mbox_map = {
                "info": messagebox.showinfo,
                "warning": messagebox.showwarning,
                "error": messagebox.showerror,
                "yesno": messagebox.askyesno,
                "okcancel": messagebox.askokcancel,
                "yesnocancel": messagebox.askyesnocancel,
                "retrycancel": messagebox.askretrycancel,
            }
            func = mbox_map.get(type, messagebox.showinfo)
            if type in ("yesno", "okcancel", "yesnocancel", "retrycancel"):
                return func(title, message)
            else:
                func(title, message)
        except Exception as e:
            print(f"message_box error: {e}")
        return None

    def filedialog(mode="open", title="Select File", **kwargs):
        try:
            from tkinter import filedialog

            fd_map = {
                "open": filedialog.askopenfilename,
                "save": filedialog.asksaveasfilename,
                "directory": filedialog.askdirectory,
                "openmultiple": filedialog.askopenfilenames,
            }
            func = fd_map.get(mode, filedialog.askopenfilename)
            return func(title=title, **kwargs) or ""
        except Exception as e:
            print(f"filedialog error: {e}")
        return ""

    def colorchooser(title="Select Color"):
        try:
            from tkinter import colorchooser

            result = colorchooser.askcolor(title=title)
            return result[1] if result else "#000000"
        except Exception as e:
            print(f"colorchooser error: {e}")
        return "#000000"

    def simpledialog(title="Input", prompt="Enter value:", initialvalue=""):
        try:
            from tkinter import simpledialog

            return (
                simpledialog.askstring(title, prompt, initialvalue=initialvalue) or ""
            )
        except Exception as e:
            print(f"simpledialog error: {e}")
        return ""

    def fontchooser(title="Select Font"):
        try:
            from tkinter import font as tkfont

            return tkfont.Chooser().show()
        except Exception as e:
            print(f"fontchooser error: {e}")
            return ("Arial", 10)

    # --- Canvas Operations ---
    def canvas_create_line(canvas, x1, y1, x2, y2, **kwargs):
        try:
            return canvas.create_line(x1, y1, x2, y2, **kwargs)
        except Exception as e:
            print(f"canvas_create_line error: {e}")

    def canvas_create_oval(canvas, x1, y1, x2, y2, **kwargs):
        try:
            return canvas.create_oval(x1, y1, x2, y2, **kwargs)
        except Exception as e:
            print(f"canvas_create_oval error: {e}")

    def canvas_create_rectangle(canvas, x1, y1, x2, y2, **kwargs):
        try:
            return canvas.create_rectangle(x1, y1, x2, y2, **kwargs)
        except Exception as e:
            print(f"canvas_create_rectangle error: {e}")

    def canvas_create_polygon(canvas, points, **kwargs):
        try:
            return canvas.create_polygon(points, **kwargs)
        except Exception as e:
            print(f"canvas_create_polygon error: {e}")

    def canvas_create_text(canvas, x, y, text="", **kwargs):
        try:
            return canvas.create_text(x, y, text=text, **kwargs)
        except Exception as e:
            print(f"canvas_create_text error: {e}")

    def canvas_create_image(canvas, x, y, image, **kwargs):
        try:
            return canvas.create_image(x, y, image=image, **kwargs)
        except Exception as e:
            print(f"canvas_create_image error: {e}")

    def canvas_create_arc(canvas, x1, y1, x2, y2, **kwargs):
        try:
            return canvas.create_arc(x1, y1, x2, y2, **kwargs)
        except Exception as e:
            print(f"canvas_create_arc error: {e}")

    def canvas_create_bitmap(canvas, x, y, bitmap="", **kwargs):
        try:
            return canvas.create_bitmap(x, y, bitmap=bitmap, **kwargs)
        except Exception as e:
            print(f"canvas_create_bitmap error: {e}")

    def canvas_create_window(canvas, x, y, window, **kwargs):
        try:
            return canvas.create_window(x, y, window=window, **kwargs)
        except Exception as e:
            print(f"canvas_create_window error: {e}")

    def canvas_delete(canvas, item):
        try:
            canvas.delete(item)
        except Exception as e:
            print(f"canvas_delete error: {e}")

    def canvas_move(canvas, item, dx, dy):
        try:
            canvas.move(item, dx, dy)
        except Exception as e:
            print(f"canvas_move error: {e}")

    def canvas_coords(canvas, item, *coords):
        try:
            if coords:
                return canvas.coords(item, *coords)
            return canvas.coords(item)
        except Exception as e:
            print(f"canvas_coords error: {e}")
            return []

    def canvas_bind(canvas, item, event, handler):
        try:
            wrapped = _wrap_callback(handler)
            canvas.tag_bind(item, event, wrapped)
        except Exception as e:
            print(f"canvas_bind error: {e}")

    def canvas_itemconfig(canvas, item, **kwargs):
        try:
            canvas.itemconfig(item, **kwargs)
        except Exception as e:
            print(f"canvas_itemconfig error: {e}")

    def canvas_itemcget(canvas, item, option):
        try:
            return canvas.itemcget(item, option)
        except Exception as e:
            print(f"canvas_itemcget error: {e}")

    def canvas_tags(canvas, item, *tags):
        try:
            if tags:
                canvas.itemconfig(item, tags=tags)
            return canvas.gettags(item)
        except Exception as e:
            print(f"canvas_tags error: {e}")

    def canvas_addtag(canvas, tag, method, *args):
        try:
            getattr(canvas, f"addtag_{method}")(tag, *args)
        except Exception as e:
            print(f"canvas_addtag error: {e}")

    def canvas_dtag(canvas, item, tag):
        try:
            canvas.dtag(item, tag)
        except Exception as e:
            print(f"canvas_dtag error: {e}")

    def canvas_find(canvas, withtag=None):
        try:
            if withtag:
                return canvas.find_withtag(withtag)
            return canvas.find_all()
        except Exception as e:
            print(f"canvas_find error: {e}")
            return []

    def canvas_bbox(canvas, item=None):
        try:
            if item:
                return canvas.bbox(item)
            return canvas.bbox("all")
        except Exception as e:
            print(f"canvas_bbox error: {e}")

    def canvas_scan_dragto(canvas, x, y):
        try:
            canvas.scan_dragto(x, y)
        except Exception as e:
            print(f"canvas_scan_dragto error: {e}")

    def canvas_scan_mark(canvas, x, y):
        try:
            canvas.scan_mark(x, y)
        except Exception as e:
            print(f"canvas_scan_mark error: {e}")

    # --- Menu Operations ---
    def menu_add_command(menu, label, command=None, accelerator=""):
        try:
            wrapped = _wrap_callback(command)
            menu.add_command(label=label, command=wrapped, accelerator=accelerator)
        except Exception as e:
            print(f"menu_add_command error: {e}")

    def menu_add_separator(menu):
        try:
            menu.add_separator()
        except Exception as e:
            print(f"menu_add_separator error: {e}")

    def menu_add_cascade(menu, label, menu_handle):
        try:
            menu.add_cascade(label=label, menu=menu_handle)
        except Exception as e:
            print(f"menu_add_cascade error: {e}")

    def menu_add_checkbutton(menu, label, command=None, **kwargs):
        try:
            var = kwargs.pop("variable", tk.BooleanVar(value=False))
            wrapped = _wrap_callback(command)
            menu.add_checkbutton(label=label, variable=var, command=wrapped, **kwargs)
        except Exception as e:
            print(f"menu_add_checkbutton error: {e}")

    def menu_add_radiobutton(menu, label, command=None, value="", **kwargs):
        try:
            var = kwargs.pop("variable", tk.StringVar(value=value))
            wrapped = _wrap_callback(command)
            menu.add_radiobutton(
                label=label, variable=var, value=value, command=wrapped, **kwargs
            )
        except Exception as e:
            print(f"menu_add_radiobutton error: {e}")

    def menu_delete(menu, start, end=None):
        try:
            if end:
                menu.delete(start, end)
            else:
                menu.delete(start)
        except Exception as e:
            print(f"menu_delete error: {e}")

    def menu_entryconfig(menu, index, **kwargs):
        try:
            menu.entryconfig(index, **kwargs)
        except Exception as e:
            print(f"menu_entryconfig error: {e}")

    def menu_entrycget(menu, index, option):
        try:
            return menu.entrycget(index, option)
        except Exception as e:
            print(f"menu_entrycget error: {e}")

    # --- Text Widget Operations ---
    def text_index(widget, index):
        try:
            return widget.index(index)
        except Exception as e:
            print(f"text_index error: {e}")
            return "1.0"

    def text_get(widget, start="1.0", end="end"):
        try:
            return widget.get(start, end)
        except Exception as e:
            print(f"text_get error: {e}")
            return ""

    def text_insert(widget, index, text):
        try:
            widget.insert(index, text)
        except Exception as e:
            print(f"text_insert error: {e}")

    def text_delete(widget, start="1.0", end="end"):
        try:
            widget.delete(start, end)
        except Exception as e:
            print(f"text_delete error: {e}")

    def text_see(widget, index):
        try:
            widget.see(index)
        except Exception as e:
            print(f"text_see error: {e}")

    def text_search(widget, pattern, start="1.0", stop="end"):
        try:
            return widget.search(pattern, start, stop)
        except Exception as e:
            print(f"text_search error: {e}")
            return ""

    def text_tag_add(widget, tagName, start, end):
        try:
            widget.tag_add(tagName, start, end)
        except Exception as e:
            print(f"text_tag_add error: {e}")

    def text_tag_remove(widget, tagName, start="1.0", end="end"):
        try:
            widget.tag_remove(tagName, start, end)
        except Exception as e:
            print(f"text_tag_remove error: {e}")

    def text_tag_config(widget, tagName, **kwargs):
        try:
            widget.tag_config(tagName, **kwargs)
        except Exception as e:
            print(f"text_tag_config error: {e}")

    def text_tag_names(widget, index=None):
        try:
            if index:
                return widget.tag_names(index)
            return widget.tag_names()
        except Exception as e:
            print(f"text_tag_names error: {e}")
            return []

    def text_tag_delete(widget, *tagNames):
        try:
            for tag in tagNames:
                widget.tag_delete(tag)
        except Exception as e:
            print(f"text_tag_delete error: {e}")

    def text_tag_lower(widget, tagName, belowThis=None):
        try:
            if belowThis:
                widget.tag_lower(tagName, belowThis)
            else:
                widget.tag_lower(tagName)
        except Exception as e:
            print(f"text_tag_lower error: {e}")

    def text_tag_raise(widget, tagName, aboveThis=None):
        try:
            if aboveThis:
                widget.tag_raise(tagName, aboveThis)
            else:
                widget.tag_raise(tagName)
        except Exception as e:
            print(f"text_tag_raise error: {e}")

    def text_tag_ranges(widget, tagName):
        try:
            return widget.tag_ranges(tagName)
        except Exception as e:
            print(f"text_tag_ranges error: {e}")
            return []

    def text_edit_undo(widget):
        try:
            widget.edit_undo()
        except Exception as e:
            print(f"text_edit_undo error: {e}")

    def text_edit_redo(widget):
        try:
            widget.edit_redo()
        except Exception as e:
            print(f"text_edit_redo error: {e}")

    def text_edit_separator(widget):
        try:
            widget.edit_separator()
        except Exception as e:
            print(f"text_edit_separator error: {e}")

    def text_edit_reset(widget):
        try:
            widget.edit_reset()
        except Exception as e:
            print(f"text_edit_reset error: {e}")

    def text_mark_gravity(widget, markName, direction=None):
        try:
            if direction:
                widget.mark_set(markName, direction)
            return widget.mark_gravity(markName)
        except Exception as e:
            print(f"text_mark_gravity error: {e}")

    def text_mark_set(widget, markName, index):
        try:
            widget.mark_set(markName, index)
        except Exception as e:
            print(f"text_mark_set error: {e}")

    def text_mark_unset(widget, *markNames):
        try:
            for mark in markNames:
                widget.mark_unset(mark)
        except Exception as e:
            print(f"text_mark_unset error: {e}")

    def text_compare(widget, index1, op, index2):
        try:
            return widget.compare(index1, op, index2)
        except Exception as e:
            print(f"text_compare error: {e}")

    def text_window_create(widget, index, window, **kwargs):
        try:
            widget.window_create(index, window=window, **kwargs)
        except Exception as e:
            print(f"text_window_create error: {e}")

    def text_image_create(widget, index, image, **kwargs):
        try:
            widget.image_create(index, image=image, **kwargs)
        except Exception as e:
            print(f"text_image_create error: {e}")

    # --- Notebook Operations ---
    def notebook_add(notebook, child, text=""):
        try:
            notebook.add(child, text=text)
        except Exception as e:
            print(f"notebook_add error: {e}")

    def notebook_forget(notebook, child):
        try:
            notebook.forget(child)
        except Exception as e:
            print(f"notebook_forget error: {e}")

    def notebook_select(notebook, child=None):
        try:
            if child:
                notebook.select(child)
            return notebook.select()
        except Exception as e:
            print(f"notebook_select error: {e}")

    def notebook_tab(notebook, child, option=None, **kwargs):
        try:
            if option:
                if kwargs:
                    notebook.tab(child, **{option: kwargs.get(option)})
                else:
                    return notebook.tab(child, option=option)
            elif kwargs:
                notebook.tab(child, **kwargs)
            return notebook.tab(child)
        except Exception as e:
            print(f"notebook_tab error: {e}")

    def notebook_tabs(notebook):
        try:
            return notebook.tabs()
        except Exception as e:
            print(f"notebook_tabs error: {e}")
            return []

    def notebook_hide(notebook, child):
        try:
            notebook.hide(child)
        except Exception as e:
            print(f"notebook_hide error: {e}")

    def notebook_insert(notebook, index, child, **kwargs):
        try:
            notebook.insert(index, child, **kwargs)
        except Exception as e:
            print(f"notebook_insert error: {e}")

    def notebook_enable_traversal(notebook):
        try:
            try:
                import tkinter.ttk as ttk

                if hasattr(ttk, "Style"):
                    pass
                notebook.enable_traversal()
            except:
                pass
        except Exception as e:
            print(f"notebook_enable_traversal error: {e}")

    # --- Treeview Operations ---
    def treeview_insert(parent, iid, text="", values=None, **kwargs):
        try:
            return parent.insert(iid, "end", text=text, values=values or [], **kwargs)
        except Exception as e:
            print(f"treeview_insert error: {e}")

    def treeview_delete(tree, *items):
        try:
            for item in items:
                tree.delete(item)
        except Exception as e:
            print(f"treeview_delete error: {e}")

    def treeview_get_children(tree, item=None):
        try:
            return tree.get_children(item)
        except Exception as e:
            print(f"treeview_get_children error: {e}")
            return []

    def treeview_item(tree, item, option=None, **kwargs):
        try:
            if option:
                return tree.item(item, option=option)
            elif kwargs:
                tree.item(item, **kwargs)
            return tree.item(item)
        except Exception as e:
            print(f"treeview_item error: {e}")

    def treeview_selection(tree, items=None):
        try:
            if items:
                tree.selection_set(items)
            return tree.selection()
        except Exception as e:
            print(f"treeview_selection error: {e}")
            return []

    def treeview_see(tree, item):
        try:
            tree.see(item)
        except Exception as e:
            print(f"treeview_see error: {e}")

    def treeview_tag_bind(tree, tag, event=None, callback=None):
        try:
            if event and callback:
                wrapped = _wrap_callback(callback)
                tree.tag_bind(tag, event, wrapped)
            elif event:
                tree.tag_unbind(tag, event)
        except Exception as e:
            print(f"treeview_tag_bind error: {e}")

    def treeview_tag_config(tree, tag, **kwargs):
        try:
            tree.tag_configure(tag, **kwargs)
        except Exception as e:
            print(f"treeview_tag_config error: {e}")

    def treeview_column(tree, col, option=None, **kwargs):
        try:
            if option:
                return tree.column(col, option=option)
            elif kwargs:
                tree.column(col, **kwargs)
            return tree.column(col)
        except Exception as e:
            print(f"treeview_column error: {e}")

    def treeview_heading(tree, col, option=None, **kwargs):
        try:
            if option:
                return tree.heading(col, option=option)
            elif kwargs:
                tree.heading(col, **kwargs)
            return tree.heading(col)
        except Exception as e:
            print(f"treeview_heading error: {e}")

    # --- PanedWindow Operations ---
    def panedwindow_add(paned, child, **kwargs):
        try:
            paned.add(child, **kwargs)
        except Exception as e:
            print(f"panedwindow_add error: {e}")

    def panedwindow_forget(paned, child):
        try:
            paned.forget(child)
        except Exception as e:
            print(f"panedwindow_forget error: {e}")

    def panedwindow_pane(paned, child, option=None, **kwargs):
        try:
            if option:
                return paned.pane(child, option=option)
            elif kwargs:
                paned.pane(child, **kwargs)
            return paned.pane(child)
        except Exception as e:
            print(f"panedwindow_pane error: {e}")

    def panedwindow_sashpos(paned, index, pos=None):
        try:
            if pos is not None:
                paned.sashpos(index, pos)
            return paned.sashpos(index)
        except Exception as e:
            print(f"panedwindow_sashpos error: {e}")

    # --- Listbox Operations ---
    def listbox_insert(listbox, index, *items):
        try:
            listbox.insert(index, *items)
        except Exception as e:
            print(f"listbox_insert error: {e}")

    def listbox_delete(listbox, first, last=None):
        try:
            if last:
                listbox.delete(first, last)
            else:
                listbox.delete(first)
        except Exception as e:
            print(f"listbox_delete error: {e}")

    def listbox_get(listbox, first, last=None):
        try:
            if last:
                return listbox.get(first, last)
            return listbox.get(first)
        except Exception as e:
            print(f"listbox_get error: {e}")

    def listbox_curselection(listbox):
        try:
            return listbox.curselection()
        except Exception as e:
            print(f"listbox_curselection error: {e}")
            return ()

    def listbox_size(listbox):
        try:
            return listbox.size()
        except Exception as e:
            print(f"listbox_size error: {e}")
            return 0

    def listbox_activate(listbox, index):
        try:
            listbox.activate(index)
        except Exception as e:
            print(f"listbox_activate error: {e}")

    def listbox_see(listbox, index):
        try:
            listbox.see(index)
        except Exception as e:
            print(f"listbox_see error: {e}")

    def listbox_selection_set(listbox, first, last=None):
        try:
            if last:
                listbox.selection_set(first, last)
            else:
                listbox.selection_set(first)
        except Exception as e:
            print(f"listbox_selection_set error: {e}")

    def listbox_selection_clear(listbox, first, last=None):
        try:
            if last:
                listbox.selection_clear(first, last)
            else:
                listbox.selection_clear(first)
        except Exception as e:
            print(f"listbox_selection_clear error: {e}")

    def listbox_selection_includes(listbox, index):
        try:
            return listbox.selection_includes(index)
        except Exception as e:
            print(f"listbox_selection_includes error: {e}")
            return False

    # --- Entry Operations ---
    def entry_config(widget, **kwargs):
        try:
            widget.config(**kwargs)
        except Exception as e:
            print(f"entry_config error: {e}")

    def entry_get(widget):
        try:
            return widget.get()
        except Exception as e:
            print(f"entry_get error: {e}")
            return ""

    def entry_set(widget, value):
        try:
            widget.delete(0, tk.END)
            widget.insert(0, value)
        except Exception as e:
            print(f"entry_set error: {e}")

    def entry_selection_get(widget):
        try:
            return widget.selection_get()
        except Exception as e:
            print(f"entry_selection_get error: {e}")
            return ""

    def entry_selection_clear(widget):
        try:
            widget.selection_clear()
        except Exception as e:
            print(f"entry_selection_clear error: {e}")

    def entry_icursor(widget, index=None):
        try:
            if index is not None:
                widget.icursor(index)
            return widget.icursor()
        except Exception as e:
            print(f"entry_icursor error: {e}")

    def entry_index(widget, index):
        try:
            return widget.index(index)
        except Exception as e:
            print(f"entry_index error: {e}")
            return 0

    # --- Scrollbar Operations ---
    def scrollbar_set(scrollbar, first, last):
        try:
            scrollbar.set(first, last)
        except Exception as e:
            print(f"scrollbar_set error: {e}")

    def scrollbar_get(scrollbar):
        try:
            return scrollbar.get()
        except Exception as e:
            print(f"scrollbar_get error: {e}")
            return (0.0, 1.0)

    # --- Progressbar Operations ---
    def progressbar_start(widget):
        try:
            widget.start()
        except Exception as e:
            print(f"progressbar_start error: {e}")

    def progressbar_stop(widget):
        try:
            widget.stop()
        except Exception as e:
            print(f"progressbar_stop error: {e}")

    def progressbar_step(widget, amount=None):
        try:
            if amount:
                widget.step(amount)
            else:
                widget.step()
        except Exception as e:
            print(f"progressbar_step error: {e}")

    def progressbar_config(widget, **kwargs):
        try:
            widget.config(**kwargs)
        except Exception as e:
            print(f"progressbar_config error: {e}")

    # --- Timer Operations ---
    def timer_start(timer_id):
        try:
            if isinstance(timer_id, dict) and "__ks_timer__" in timer_id:
                pass
        except Exception as e:
            print(f"timer_start error: {e}")

    def timer_stop(timer_id):
        try:
            if isinstance(timer_id, dict) and "__ks_timer__" in timer_id:
                tid = timer_id["id"]
                if tid in _timers:
                    widget = _windows[0] if _windows else None
                    if widget:
                        widget.after_cancel(_timers[tid])
                    del _timers[tid]
        except Exception as e:
            print(f"timer_stop error: {e}")

    # --- Window Operations ---
    def destroy(window):
        try:
            window.destroy()
        except Exception as e:
            print(f"destroy error: {e}")

    def withdraw(window):
        try:
            window.withdraw()
        except Exception as e:
            print(f"withdraw error: {e}")

    def deiconify(window):
        try:
            window.deiconify()
        except Exception as e:
            print(f"deiconify error: {e}")

    def iconify(window):
        try:
            window.iconify()
        except Exception as e:
            print(f"iconify error: {e}")

    def geometry(window, geometry=None):
        try:
            if geometry:
                window.geometry(geometry)
            return window.geometry()
        except Exception as e:
            print(f"geometry error: {e}")
            return ""

    def maxsize(window, width=None, height=None):
        try:
            if width and height:
                window.maxsize(width, height)
            return window.maxsize()
        except Exception as e:
            print(f"maxsize error: {e}")
            return (0, 0)

    def minsize(window, width=None, height=None):
        try:
            if width and height:
                window.minsize(width, height)
            return window.minsize()
        except Exception as e:
            print(f"minsize error: {e}")
            return (0, 0)

    def resizable(window, width=True, height=True):
        try:
            window.resizable(width, height)
        except Exception as e:
            print(f"resizable error: {e}")

    def title(window, title=None):
        try:
            if title:
                window.title(title)
            return window.title()
        except Exception as e:
            print(f"title error: {e}")
            return ""

    def protocol(window, name, func=None):
        try:
            if func:
                wrapped = _wrap_callback(func)
                window.protocol(name, wrapped)
            return window.protocol(name)
        except Exception as e:
            print(f"protocol error: {e}")

    def attributes(window, **kwargs):
        try:
            window.attributes(**kwargs)
        except Exception as e:
            print(f"attributes error: {e}")

    def state(window, state=None):
        try:
            if state:
                window.state(state)
            return window.state()
        except Exception as e:
            print(f"state error: {e}")
            return "normal"

    # --- Widget Info ---
    def winfo_children(window):
        try:
            return window.winfo_children()
        except Exception as e:
            print(f"winfo_children error: {e}")
            return []

    def winfo_parent(window):
        try:
            return window.winfo_parent()
        except Exception as e:
            print(f"winfo_parent error: {e}")
            return ""

    def winfo_width(window):
        try:
            return window.winfo_width()
        except Exception as e:
            print(f"winfo_width error: {e}")
            return 0

    def winfo_height(window):
        try:
            return window.winfo_height()
        except Exception as e:
            print(f"winfo_height error: {e}")
            return 0

    def winfo_x(window):
        try:
            return window.winfo_x()
        except Exception as e:
            print(f"winfo_x error: {e}")
            return 0

    def winfo_y(window):
        try:
            return window.winfo_y()
        except Exception as e:
            print(f"winfo_y error: {e}")
            return 0

    def winfo_rootx(window):
        try:
            return window.winfo_rootx()
        except Exception as e:
            print(f"winfo_rootx error: {e}")
            return 0

    def winfo_rooty(window):
        try:
            return window.winfo_rooty()
        except Exception as e:
            print(f"winfo_rooty error: {e}")
            return 0

    def winfo_geometry(window):
        try:
            return window.winfo_geometry()
        except Exception as e:
            print(f"winfo_geometry error: {e}")
            return ""

    def winfo_exists(window):
        try:
            return window.winfo_exists()
        except Exception as e:
            print(f"winfo_exists error: {e}")
            return False

    def winfo_screenwidth(window):
        try:
            return window.winfo_screenwidth()
        except Exception as e:
            print(f"winfo_screenwidth error: {e}")
            return 0

    def winfo_screenheight(window):
        try:
            return window.winfo_screenheight()
        except Exception as e:
            print(f"winfo_screenheight error: {e}")
            return 0

    # --- Variables ---
    def create_string_var(value=""):
        try:
            return tk.StringVar(value=value)
        except Exception as e:
            print(f"create_string_var error: {e}")

    def create_int_var(value=0):
        try:
            return tk.IntVar(value=value)
        except Exception as e:
            print(f"create_int_var error: {e}")

    def create_bool_var(value=False):
        try:
            return tk.BooleanVar(value=value)
        except Exception as e:
            print(f"create_bool_var error: {e}")

    def create_double_var(value=0.0):
        try:
            return tk.DoubleVar(value=value)
        except Exception as e:
            print(f"create_double_var error: {e}")

    # --- Modern Styling ---
    def ttk_style():
        try:
            import tkinter.ttk as ttk

            style = ttk.Style()
            style.theme_use("clam")
            style.configure("TFrame", background="#2b2b2b")
            style.configure("TLabel", background="#2b2b2b", foreground="#ffffff")
            style.configure("TButton", background="#0e639c", foreground="#ffffff")
            style.map("TButton", background=[("active", "#1177bb")])
            return True
        except Exception as e:
            print(f"ttk_style error: {e}")
            return False

    def set_style(widget, style_name):
        try:
            if hasattr(widget, "config"):
                widget.config(style=style_name)
            elif hasattr(widget, "configure"):
                widget.configure(style=style_name)
        except Exception as e:
            print(f"set_style error: {e}")

    # --- Toast Notification ---
    def create_toast(parent, message, duration=3000, **kwargs):
        try:
            tk = _tkinter
            toast = tk.Label(parent, text=message, bg="#333333", fg="#ffffff",
                             font=("Arial", 11), padx=16, pady=8, relief="flat",
                             **kwargs)
            toast.place(relx=0.5, rely=0.05, anchor="n")
            toast.after(duration, lambda: toast.destroy())
            return toast
        except Exception as e:
            print(f"create_toast error: {e}")
            return None

    # --- Status Bar ---
    def create_status_bar(parent, text="", **kwargs):
        try:
            tk = _tkinter
            frame = tk.Frame(parent, bg="#2b2b2b", relief="sunken", bd=1)
            label = tk.Label(frame, text=text, bg="#2b2b2b", fg="#cccccc",
                             font=("Arial", 10), anchor="w", padx=8, pady=4, **kwargs)
            label.pack(fill="x")
            frame._ks_label = label
            return frame
        except Exception as e:
            print(f"create_status_bar error: {e}")
            return None

    def set_status_text(widget, text):
        try:
            if hasattr(widget, "_ks_label"):
                widget._ks_label.config(text=text)
            elif hasattr(widget, "config"):
                widget.config(text=text)
        except Exception as e:
            print(f"set_status_text error: {e}")

    # --- Date Picker ---
    def create_date_picker(parent, **kwargs):
        try:
            tk = _tkinter
            frame = tk.Frame(parent, **kwargs)
            from datetime import datetime
            now = datetime.now()

            tk.Label(frame, text="Year").grid(row=0, column=0, padx=2)
            tk.Label(frame, text="Month").grid(row=0, column=1, padx=2)
            tk.Label(frame, text="Day").grid(row=0, column=2, padx=2)

            year_var = tk.IntVar(value=now.year)
            month_var = tk.IntVar(value=now.month)
            day_var = tk.IntVar(value=now.day)

            year_spin = tk.Spinbox(frame, from_=2000, to=2100, width=6, textvariable=year_var)
            year_spin.grid(row=1, column=0, padx=2)
            month_spin = tk.Spinbox(frame, from_=1, to=12, width=4, textvariable=month_var)
            month_spin.grid(row=1, column=1, padx=2)
            day_spin = tk.Spinbox(frame, from_=1, to=31, width=4, textvariable=day_var)
            day_spin.grid(row=1, column=2, padx=2)

            frame._year = year_var
            frame._month = month_var
            frame._day = day_var
            return frame
        except Exception as e:
            print(f"create_date_picker error: {e}")
            return None

    def get_date(widget):
        try:
            return f"{widget._year.get():04d}-{widget._month.get():02d}-{widget._day.get():02d}"
        except Exception:
            return ""

    # --- Context Menu ---
    def create_context_menu(parent, items=None, **kwargs):
        try:
            tk = _tkinter
            menu = tk.Menu(parent, tearoff=0, **kwargs)
            if items:
                for item in items:
                    if item == "-":
                        menu.add_separator()
                    elif isinstance(item, tuple):
                        menu.add_command(label=item[0], command=item[1] if len(item) > 1 else None)
                    else:
                        menu.add_command(label=item)
            return menu
        except Exception as e:
            print(f"create_context_menu error: {e}")
            return None

    def show_context_menu(menu, event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            print(f"show_context_menu error: {e}")

    # --- Markdown Viewer ---
    def create_markdown_viewer(parent, width=60, height=20, **kwargs):
        try:
            tk = _tkinter
            text = tk.Text(parent, width=width, height=height, wrap="word",
                           bg="#1e1e1e", fg="#d4d4d4", insertbackground="#ffffff",
                           font=("Consolas", 11), relief="flat", padx=12, pady=12,
                           **kwargs)
            text._ks_tags_set = False
            return text
        except Exception as e:
            print(f"create_markdown_viewer error: {e}")
            return None

    def render_markdown(widget, md_text):
        try:
            if not widget._ks_tags_set:
                widget.tag_config("h1", font=("Arial", 20, "bold"), foreground="#569cd6")
                widget.tag_config("h2", font=("Arial", 16, "bold"), foreground="#4ec9b0")
                widget.tag_config("h3", font=("Arial", 13, "bold"), foreground="#c586c0")
                widget.tag_config("bold", font=("Arial", 11, "bold"), foreground="#dcdcaa")
                widget.tag_config("code", font=("Consolas", 11), background="#2d2d2d", foreground="#ce9178")
                widget.tag_config("link", foreground="#569cd6", underline=True)
                widget._ks_tags_set = True

            widget.delete("1.0", "end")
            lines = md_text.split("\n")
            for line in lines:
                if line.startswith("### "):
                    widget.insert("end", line[4:] + "\n", "h3")
                elif line.startswith("## "):
                    widget.insert("end", line[3:] + "\n", "h2")
                elif line.startswith("# "):
                    widget.insert("end", line[2:] + "\n", "h1")
                elif line.startswith("    ") or line.startswith("\t"):
                    widget.insert("end", line + "\n", "code")
                elif line.startswith("- "):
                    widget.insert("end", "  • " + line[2:] + "\n")
                else:
                    widget.insert("end", line + "\n")
        except Exception as e:
            print(f"render_markdown error: {e}")

    # --- Theme Support ---
    _themes = {
        "dark": {
            "bg": "#1e1e1e", "fg": "#d4d4d4", "surface": "#252526",
            "accent": "#0e639c", "accent_fg": "#ffffff",
            "border": "#3c3c3c", "entry_bg": "#3c3c3c", "entry_fg": "#d4d4d4",
        },
        "light": {
            "bg": "#ffffff", "fg": "#1e1e1e", "surface": "#f3f3f3",
            "accent": "#0066bf", "accent_fg": "#ffffff",
            "border": "#d4d4d4", "entry_bg": "#ffffff", "entry_fg": "#1e1e1e",
        },
        "midnight": {
            "bg": "#0d1117", "fg": "#c9d1d9", "surface": "#161b22",
            "accent": "#58a6ff", "accent_fg": "#ffffff",
            "border": "#30363d", "entry_bg": "#0d1117", "entry_fg": "#c9d1d9",
        },
    }

    def set_theme(widget, theme_name):
        try:
            if theme_name not in _themes:
                print(f"Unknown theme: {theme_name}. Available: {', '.join(_themes.keys())}")
                return
            t = _themes[theme_name]
            wtype = str(type(widget).__name__)
            if hasattr(widget, "config"):
                if "Frame" in wtype:
                    widget.config(bg=t["bg"])
                elif "Label" in wtype:
                    widget.config(bg=t["bg"], fg=t["fg"])
                elif "Button" in wtype:
                    widget.config(bg=t["accent"], fg=t["accent_fg"],
                                  activebackground=t["accent"], activeforeground=t["accent_fg"])
                elif "Entry" in wtype or "Text" in wtype:
                    widget.config(bg=t["entry_bg"], fg=t["entry_fg"],
                                  insertbackground=t["fg"])
                elif "Listbox" in wtype:
                    widget.config(bg=t["surface"], fg=t["fg"],
                                  selectbackground=t["accent"], selectforeground=t["accent_fg"])
        except Exception as e:
            print(f"set_theme error: {e}")

    def set_theme_recursive(widget, theme_name):
        try:
            set_theme(widget, theme_name)
            if hasattr(widget, "winfo_children"):
                for child in widget.winfo_children():
                    set_theme_recursive(child, theme_name)
        except Exception as e:
            print(f"set_theme_recursive error: {e}")

    # --- Animation ---
    def animate(widget, duration, properties, callback=None):
        try:
            steps = 20
            delay = duration // steps

            def step(current):
                for prop, (start, end) in properties.items():
                    value = start + (end - start) * (current / steps)
                    if prop == "x":
                        widget.place_configure(x=int(value))
                    elif prop == "y":
                        widget.place_configure(y=int(value))
                if current < steps:
                    widget.after(delay, lambda: step(current + 1))
                elif callback:
                    _wrap_callback(callback)()

            step(0)
        except Exception as e:
            print(f"animate error: {e}")

    # --- Event generate ---
    def event_generate(widget, event, **kwargs):
        try:
            widget.event_generate(event, **kwargs)
        except Exception as e:
            print(f"event_generate error: {e}")

    # --- Callbacks ---
    def register_callback(callback):
        cb_id = _callback_id[0]
        _callback_id[0] += 1
        _callbacks[cb_id] = callback
        return f"_ks_cb_{cb_id}"

    def trigger_callback(cb_id):
        try:
            if cb_id in _callbacks:
                _wrap_callback(_callbacks[cb_id])()
        except Exception as e:
            print(f"trigger_callback error: {e}")

    def make_callback(func):
        return _wrap_callback(func)

    def set_interpreter(interpreter):
        _ks_interpreter_holder[0] = interpreter

    # --- Module Exports ---
    return {
        # Window
        "create_window": create_window,
        # Basic widgets
        "create_label": create_label,
        "create_button": create_button,
        "create_entry": create_entry,
        "create_text": create_text,
        "create_textbox": create_textbox,
        "create_listbox": create_listbox,
        "create_frame": create_frame,
        "create_checkbutton": create_checkbutton,
        "create_radiobutton": create_radiobutton,
        "create_scale": create_scale,
        "create_spinbox": create_spinbox,
        "create_scrollbar": create_scrollbar,
        "create_separator": create_separator,
        "create_sizegrip": create_sizegrip,
        # Advanced widgets
        "create_canvas": create_canvas,
        "create_menu": create_menu,
        "create_notebook": create_notebook,
        "create_panedwindow": create_panedwindow,
        "create_label_frame": create_label_frame,
        "create_combobox": create_combobox,
        "create_treeview": create_treeview,
        "create_progressbar": create_progressbar,
        # Media
        "create_image": create_image,
        # Timers/Animation
        "create_timer": create_timer,
        "animate": animate,
        # Layout
        "pack": pack,
        "grid": grid,
        "place": place,
        # Main loop
        "mainloop": mainloop,
        "update": update,
        "update_idletasks": update_idletasks,
        "after": after,
        "after_cancel": after_cancel,
        "after_idle": after_idle,
        # Widget ops
        "get_text": get_text,
        "set_text": set_text,
        "insert": insert,
        "delete": delete,
        "curselection": curselection,
        "set_scrollbar": set_scrollbar,
        "xview": xview,
        "yview": yview,
        "get_value": get_value,
        "set_value": set_value,
        "configure": configure,
        "config": config,
        "bind": bind,
        "bind_all": bind_all,
        "unbind": unbind,
        "unbind_all": unbind_all,
        "focus": focus,
        "focus_force": focus_force,
        "focus_get": focus_get,
        "focus_set": focus_set,
        "grab_set": grab_set,
        "grab_release": grab_release,
        "grab_set_global": grab_set_global,
        "tkraise": tkraise,
        "lift": lift,
        "lower": lower,
        # Keyboard shortcuts
        "add_shortcut": add_shortcut,
        "remove_shortcut": remove_shortcut,
        "bind_shortcut": bind_shortcut,
        # Clipboard
        "clipboard_get": clipboard_get,
        "clipboard_set": clipboard_set,
        "clipboard_append": clipboard_append,
        "clipboard_clear": clipboard_clear,
        # Dialogs
        "message_box": message_box,
        "filedialog": filedialog,
        "colorchooser": colorchooser,
        "simpledialog": simpledialog,
        "fontchooser": fontchooser,
        # Canvas
        "canvas_create_line": canvas_create_line,
        "canvas_create_oval": canvas_create_oval,
        "canvas_create_rectangle": canvas_create_rectangle,
        "canvas_create_polygon": canvas_create_polygon,
        "canvas_create_text": canvas_create_text,
        "canvas_create_image": canvas_create_image,
        "canvas_create_arc": canvas_create_arc,
        "canvas_create_bitmap": canvas_create_bitmap,
        "canvas_create_window": canvas_create_window,
        "canvas_delete": canvas_delete,
        "canvas_move": canvas_move,
        "canvas_coords": canvas_coords,
        "canvas_bind": canvas_bind,
        "canvas_itemconfig": canvas_itemconfig,
        "canvas_itemcget": canvas_itemcget,
        "canvas_tags": canvas_tags,
        "canvas_addtag": canvas_addtag,
        "canvas_dtag": canvas_dtag,
        "canvas_find": canvas_find,
        "canvas_bbox": canvas_bbox,
        "canvas_scan_dragto": canvas_scan_dragto,
        "canvas_scan_mark": canvas_scan_mark,
        # Menu
        "menu_add_command": menu_add_command,
        "menu_add_separator": menu_add_separator,
        "menu_add_cascade": menu_add_cascade,
        "menu_add_checkbutton": menu_add_checkbutton,
        "menu_add_radiobutton": menu_add_radiobutton,
        "menu_delete": menu_delete,
        "menu_entryconfig": menu_entryconfig,
        "menu_entrycget": menu_entrycget,
        # Text widget
        "text_index": text_index,
        "text_get": text_get,
        "text_insert": text_insert,
        "text_delete": text_delete,
        "text_see": text_see,
        "text_search": text_search,
        "text_tag_add": text_tag_add,
        "text_tag_remove": text_tag_remove,
        "text_tag_config": text_tag_config,
        "text_tag_names": text_tag_names,
        "text_tag_delete": text_tag_delete,
        "text_tag_lower": text_tag_lower,
        "text_tag_raise": text_tag_raise,
        "text_tag_ranges": text_tag_ranges,
        "text_edit_undo": text_edit_undo,
        "text_edit_redo": text_edit_redo,
        "text_edit_separator": text_edit_separator,
        "text_edit_reset": text_edit_reset,
        "text_mark_gravity": text_mark_gravity,
        "text_mark_set": text_mark_set,
        "text_mark_unset": text_mark_unset,
        "text_compare": text_compare,
        "text_window_create": text_window_create,
        "text_image_create": text_image_create,
        # Notebook
        "notebook_add": notebook_add,
        "notebook_forget": notebook_forget,
        "notebook_select": notebook_select,
        "notebook_tab": notebook_tab,
        "notebook_tabs": notebook_tabs,
        "notebook_hide": notebook_hide,
        "notebook_insert": notebook_insert,
        "notebook_enable_traversal": notebook_enable_traversal,
        # Treeview
        "treeview_insert": treeview_insert,
        "treeview_delete": treeview_delete,
        "treeview_get_children": treeview_get_children,
        "treeview_item": treeview_item,
        "treeview_selection": treeview_selection,
        "treeview_see": treeview_see,
        "treeview_tag_bind": treeview_tag_bind,
        "treeview_tag_config": treeview_tag_config,
        "treeview_column": treeview_column,
        "treeview_heading": treeview_heading,
        # PanedWindow
        "panedwindow_add": panedwindow_add,
        "panedwindow_forget": panedwindow_forget,
        "panedwindow_pane": panedwindow_pane,
        "panedwindow_sashpos": panedwindow_sashpos,
        # Listbox
        "listbox_insert": listbox_insert,
        "listbox_delete": listbox_delete,
        "listbox_get": listbox_get,
        "listbox_curselection": listbox_curselection,
        "listbox_size": listbox_size,
        "listbox_activate": listbox_activate,
        "listbox_see": listbox_see,
        "listbox_selection_set": listbox_selection_set,
        "listbox_selection_clear": listbox_selection_clear,
        "listbox_selection_includes": listbox_selection_includes,
        # Entry
        "entry_config": entry_config,
        "entry_get": entry_get,
        "entry_set": entry_set,
        "entry_selection_get": entry_selection_get,
        "entry_selection_clear": entry_selection_clear,
        "entry_icursor": entry_icursor,
        "entry_index": entry_index,
        # Scrollbar
        "scrollbar_set": scrollbar_set,
        "scrollbar_get": scrollbar_get,
        # Progressbar
        "progressbar_start": progressbar_start,
        "progressbar_stop": progressbar_stop,
        "progressbar_step": progressbar_step,
        "progressbar_config": progressbar_config,
        # Timer
        "timer_start": timer_start,
        "timer_stop": timer_stop,
        # Variables
        "create_string_var": create_string_var,
        "create_int_var": create_int_var,
        "create_bool_var": create_bool_var,
        "create_double_var": create_double_var,
        # Modern styling
        "ttk_style": ttk_style,
        "set_style": set_style,
        # Callbacks
        "register_callback": register_callback,
        "trigger_callback": trigger_callback,
        "make_callback": make_callback,
        "set_interpreter": set_interpreter,
        # Event system
        "event_generate": event_generate,
        # Window ops
        "destroy": destroy,
        "withdraw": withdraw,
        "deiconify": deiconify,
        "iconify": iconify,
        "geometry": geometry,
        "maxsize": maxsize,
        "minsize": minsize,
        "resizable": resizable,
        "title": title,
        "protocol": protocol,
        "attributes": attributes,
        "state": state,
        # Widget info
        "winfo_children": winfo_children,
        "winfo_parent": winfo_parent,
        "winfo_width": winfo_width,
        "winfo_height": winfo_height,
        "winfo_x": winfo_x,
        "winfo_y": winfo_y,
        "winfo_rootx": winfo_rootx,
        "winfo_rooty": winfo_rooty,
        "winfo_geometry": winfo_geometry,
        "winfo_exists": winfo_exists,
        "winfo_screenwidth": winfo_screenwidth,
        "winfo_screenheight": winfo_screenheight,
        # Direct tkinter access
        "tk": tk,
        "ttk": __import__("tkinter.ttk"),
        # New widgets
        "create_toast": create_toast,
        "create_status_bar": create_status_bar,
        "set_status_text": set_status_text,
        "create_date_picker": create_date_picker,
        "get_date": get_date,
        "create_context_menu": create_context_menu,
        "show_context_menu": show_context_menu,
        "create_markdown_viewer": create_markdown_viewer,
        "render_markdown": render_markdown,
        "set_theme": set_theme,
        "set_theme_recursive": set_theme_recursive,
    }


# Create the GUI module
_gui_module = None


def get_gui_module():
    """Get the GUI module - creates it on first call"""
    global _gui_module
    if _gui_module is None:
        _gui_module = _create_real_gui()
    return _gui_module


def create_gui_module():
    """Create and return GUI module dict"""
    return get_gui_module()
