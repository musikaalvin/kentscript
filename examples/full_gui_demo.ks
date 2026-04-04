:: KentScript Studio ✨ - Beautiful GUI Application
:: A modern, feature-rich IDE built with KentScript

import gui;
import os;
import time;
import math;
import random;

let current_file = "";
let is_modified = false;
let current_directory = ".";
let font_size = 14;

:: 🌈 Modern Dark Color Scheme
let bg_color = "#1e1e2e";
let fg_color = "#cdd6f4";
let accent_color = "#89b4fa";
let success_color = "#a6e3a1";
let warning_color = "#f9e2af";
let error_color = "#f38ba8";
let sidebar_bg = "#181825";
let toolbar_bg = "#313244";
let editor_bg = "#11111b";

let window = gui.create_window("KentScript Studio ✨", 1000, 700);
gui.geometry(window, "1000x700");
gui.configure(window, background=bg_color);

let main_container = gui.create_frame(window);
gui.pack(main_container, fill="both", expand=true);

:: ═══════════════════════════════════════════════════════════════════
:: 🎨 Menu Bar
:: ═══════════════════════════════════════════════════════════════════
let menubar = gui.create_menu(window);
window.config(menu=menubar);

let file_menu = gui.create_menu(menubar);
gui.menu_add_cascade(menubar, "📁 File", file_menu);

gui.menu_add_command(file_menu, "🆕 New", lambda: { new_file(); }, "Ctrl+N");
gui.menu_add_command(file_menu, "📂 Open", lambda: { open_file(); }, "Ctrl+O");
gui.menu_add_command(file_menu, "💾 Save", lambda: { save_file(); }, "Ctrl+S");
gui.menu_add_command(file_menu, "💾 Save As...", lambda: { save_file_as(); }, "Ctrl+Shift+S");
gui.menu_add_separator(file_menu);
gui.menu_add_command(file_menu, "❌ Exit", lambda: { exit_app(); }, "Alt+F4");

let edit_menu = gui.create_menu(menubar);
gui.menu_add_cascade(menubar, "✏️ Edit", edit_menu);

gui.menu_add_command(edit_menu, "✂️ Cut", lambda: { gui.event_generate(editor, "<<Cut>>"); }, "Ctrl+X");
gui.menu_add_command(edit_menu, "📋 Copy", lambda: { gui.event_generate(editor, "<<Copy>>"); }, "Ctrl+C");
gui.menu_add_command(edit_menu, "📝 Paste", lambda: { gui.event_generate(editor, "<<Paste>>"); }, "Ctrl+V");
gui.menu_add_separator(edit_menu);
gui.menu_add_command(edit_menu, "🔲 Select All", lambda: { gui.event_generate(editor, "<<SelectAll>>"); }, "Ctrl+A");

let view_menu = gui.create_menu(menubar);
gui.menu_add_cascade(menubar, "👁️ View", view_menu);

gui.menu_add_command(view_menu, "🔍 Zoom In", lambda: { zoom_in(); }, "Ctrl++");
gui.menu_add_command(view_menu, "🔍 Zoom Out", lambda: { zoom_out(); }, "Ctrl+-");
gui.menu_add_command(view_menu, "🔄 Reset Zoom", lambda: { reset_zoom(); }, "Ctrl+0");

let help_menu = gui.create_menu(menubar);
gui.menu_add_cascade(menubar, "❓ Help", help_menu);

gui.menu_add_command(help_menu, "ℹ️ About", lambda: { show_about(); });
gui.menu_add_command(help_menu, "📚 Documentation", lambda: { show_documentation(); });

:: ═══════════════════════════════════════════════════════════════════
:: 🛠️ Toolbar
:: ═══════════════════════════════════════════════════════════════════
let toolbar = gui.create_frame(main_container);
gui.configure(toolbar, background=toolbar_bg);
gui.pack(toolbar, fill="x", padx=0, pady=0);

let toolbar_inner = gui.create_frame(toolbar);
gui.configure(toolbar_inner, background=toolbar_bg);
gui.pack(toolbar_inner, fill="x", padx=10, pady=8);

let new_btn = gui.create_button(toolbar_inner, "🆕 New", lambda: { new_file(); });
gui.configure(new_btn, background=toolbar_bg, foreground=fg_color, relief="flat");
gui.pack(new_btn, side="left", padx=3);

let open_tool_btn = gui.create_button(toolbar_inner, "📂 Open", lambda: { open_file(); });
gui.configure(open_tool_btn, background=toolbar_bg, foreground=fg_color, relief="flat");
gui.pack(open_tool_btn, side="left", padx=3);

let save_tool_btn = gui.create_button(toolbar_inner, "💾 Save", lambda: { save_file(); });
gui.configure(save_tool_btn, background=toolbar_bg, foreground=fg_color, relief="flat");
gui.pack(save_tool_btn, side="left", padx=3);

let sep1 = gui.create_frame(toolbar_inner);
gui.configure(sep1, width=2, background=accent_color);
gui.pack(sep1, side="left", padx=15, fill="y", ipady=15);

let color_btn = gui.create_button(toolbar_inner, "🎨 Theme", lambda: { pick_color(); });
gui.configure(color_btn, background=toolbar_bg, foreground=fg_color, relief="flat");
gui.pack(color_btn, side="left", padx=3);

let sep2 = gui.create_frame(toolbar_inner);
gui.configure(sep2, width=2, background=accent_color);
gui.pack(sep2, side="left", padx=15, fill="y", ipady=15);

let zoom_in_btn = gui.create_button(toolbar_inner, "🔍+", lambda: { zoom_in(); });
gui.configure(zoom_in_btn, background=toolbar_bg, foreground=fg_color, relief="flat");
gui.pack(zoom_in_btn, side="left", padx=3);

let zoom_out_btn = gui.create_button(toolbar_inner, "🔍-", lambda: { zoom_out(); });
gui.configure(zoom_out_btn, background=toolbar_bg, foreground=fg_color, relief="flat");
gui.pack(zoom_out_btn, side="left", padx=3);

:: Title in toolbar
let title_label = gui.create_label(toolbar_inner, "📝 KentScript Studio ✨");
gui.configure(title_label, background=toolbar_bg, foreground=accent_color, font=("Courier", 12, "bold"));
gui.pack(title_label, side="right", padx=10);

:: ═══════════════════════════════════════════════════════════════════
:: 📐 Main Content Area
:: ═══════════════════════════════════════════════════════════════════
let content_paned = gui.create_panedwindow(main_container, orient="horizontal", background=bg_color);
gui.pack(content_paned, fill="both", expand=true, padx=0, pady=0);

:: ═══════════════════════════════════════════════════════════════════
:: 📂 Sidebar
:: ═══════════════════════════════════════════════════════════════════
let sidebar = gui.create_frame(content_paned);
gui.configure(sidebar, background=sidebar_bg);
gui.pack(sidebar, fill="both", expand=false);

let sidebar_header = gui.create_frame(sidebar);
gui.configure(sidebar_header, background=sidebar_bg);
gui.pack(sidebar_header, fill="x", padx=10, pady=10);

let sidebar_icon = gui.create_label(sidebar_header, "📂 Files");
gui.configure(sidebar_icon, background=sidebar_bg, foreground=accent_color, font=("Courier", 11, "bold"));
gui.pack(sidebar_icon, side="left");

let sidebar_count = gui.create_label(sidebar_header, "📊");
gui.configure(sidebar_count, background=sidebar_bg, foreground=fg_color);
gui.pack(sidebar_count, side="right");

let file_list = gui.create_listbox(sidebar, background=sidebar_bg, foreground=fg_color, font=("Courier", 10), relief="flat", selectbackground=accent_color, selectforeground=bg_color);
gui.pack(file_list, fill="both", expand=true, padx=8, pady=5);

let file_scroll = gui.create_scrollbar(sidebar, orient="vertical", command=lambda: gui.yview(file_list));
gui.pack(file_scroll, side="right", fill="y");
gui.configure(file_list, yscrollcommand=lambda a: gui.set_scrollbar(file_scroll, a));

let sidebar_buttons = gui.create_frame(sidebar);
gui.configure(sidebar_buttons, background=sidebar_bg);
gui.pack(sidebar_buttons, fill="x", padx=8, pady=8);

let refresh_btn = gui.create_button(sidebar_buttons, "🔄 Refresh", lambda: { refresh_files(); });
gui.configure(refresh_btn, background=toolbar_bg, foreground=fg_color, relief="flat");
gui.pack(refresh_btn, side="left", padx=3, fill="x", expand=true);

let open_sel_btn = gui.create_button(sidebar_buttons, "📖 Open", lambda: { open_selected(); });
gui.configure(open_sel_btn, background=accent_color, foreground=bg_color, relief="flat");
gui.pack(open_sel_btn, side="left", padx=3, fill="x", expand=true);

:: ═══════════════════════════════════════════════════════════════════
:: ✏️ Editor Area
:: ═══════════════════════════════════════════════════════════════════
let editor_frame = gui.create_frame(content_paned);
gui.configure(editor_frame, background=bg_color);
gui.pack(editor_frame, fill="both", expand=true);

let editor_header = gui.create_frame(editor_frame);
gui.configure(editor_header, background=bg_color);
gui.pack(editor_header, fill="x", padx=10, pady=5);

let editor_title = gui.create_label(editor_header, "✏️ Editor");
gui.configure(editor_title, background=bg_color, foreground=accent_color, font=("Courier", 11, "bold"));
gui.pack(editor_title, side="left");

let line_col_label = gui.create_label(editor_header, "📊 Lines: 0  Col: 0");
gui.configure(line_col_label, background=bg_color, foreground=fg_color, font=("Courier", 9));
gui.pack(line_col_label, side="right");

let editor = gui.create_text(editor_frame, font=("Courier", font_size), wrap="none", background=editor_bg, foreground=fg_color, insertbackground=fg_color, relief="flat");
gui.pack(editor, side="left", fill="both", expand=true, padx=8, pady=5);

let editor_scroll_y = gui.create_scrollbar(editor_frame, orient="vertical", command=lambda: gui.yview(editor));
gui.pack(editor_scroll_y, side="right", fill="y");
gui.configure(editor, yscrollcommand=lambda a: gui.set_scrollbar(editor_scroll_y, a));

let editor_scroll_x = gui.create_scrollbar(editor, orient="horizontal", command=lambda: gui.xview(editor));
gui.configure(editor, xscrollcommand=lambda a: gui.set_scrollbar(editor_scroll_x, a));

:: ═══════════════════════════════════════════════════════════════════
:: 📊 Status Bar
:: ═══════════════════════════════════════════════════════════════════
let status_bar = gui.create_frame(window);
gui.configure(status_bar, background=toolbar_bg);
gui.pack(status_bar, fill="x", side="bottom");

let status_text = gui.create_label(status_bar, "🟢 Ready");
gui.configure(status_text, background=toolbar_bg, foreground=success_color, font=("Courier", 10), anchor="w");
gui.pack(status_text, side="left", padx=10, pady=5);

let status_file = gui.create_label(status_bar, "📝 Untitled");
gui.configure(status_file, background=toolbar_bg, foreground=fg_color, font=("Courier", 10), anchor="e");
gui.pack(status_file, side="right", padx=10, pady=5);

:: ═══════════════════════════════════════════════════════════════════
:: 🔧 Functions
:: ═══════════════════════════════════════════════════════════════════

func new_file() {
    gui.delete(editor, "1.0", "end");
    current_file = "";
    is_modified = false;
    update_status("🆕 New file created", "success");
    update_title();
}

func open_file() {
    let path = gui.filedialog("open", "Open File");
    if path != "" {
        let content = file.read(path);
        gui.delete(editor, "1.0", "end");
        gui.insert(editor, "1.0", content);
        current_file = path;
        is_modified = false;
        update_status("📂 Opened: " + path, "success");
        update_title();
    }
}

func save_file() {
    if current_file == "" {
        save_file_as();
    } else {
        let content = gui.get_text(editor);
        file.write(current_file, content);
        is_modified = false;
        update_status("💾 Saved: " + current_file, "success");
        update_title();
    }
}

func save_file_as() {
    let path = gui.filedialog("save", "Save File");
    if path != "" {
        let content = gui.get_text(editor);
        file.write(path, content);
        current_file = path;
        is_modified = false;
        update_status("💾 Saved: " + path, "success");
        update_title();
    }
}

func exit_app() {
    gui.destroy(window);
}

func pick_color() {
    let colors = ["#1e1e2e", "#282a36", "#2d2d3f", "#1a1a2e", "#0f0f1a", "#242436"];
    let idx = int(random.random() * len(colors));
    let color = colors[idx];
    gui.configure(editor, background=color);
    update_status("🎨 Theme applied: " + color, "info");
}

func zoom_in() {
    font_size = font_size + 2;
    gui.configure(editor, font=("Courier", font_size));
    update_status("🔍 Font size: " + str(font_size), "info");
}

func zoom_out() {
    if font_size > 8 {
        font_size = font_size - 2;
        gui.configure(editor, font=("Courier", font_size));
        update_status("🔍 Font size: " + str(font_size), "info");
    }
}

func reset_zoom() {
    font_size = 14;
    gui.configure(editor, font=("Courier", font_size));
    update_status("🔄 Font size reset to 14", "info");
}

func refresh_files() {
    gui.delete(file_list, "0", "end");
    let files = os.listdir(current_directory);
    let count = 0;
    for f in files {
        gui.insert(file_list, "end", f);
        count = count + 1;
    }
    gui.set_text(sidebar_count, "📊 " + str(count) + " files");
    update_status("🔄 Refreshed file list - " + str(count) + " files", "info");
}

func open_selected() {
    let selection = gui.curselection(file_list);
    if selection != () {
        let index = selection[0];
        let filename = gui.listbox_get(file_list, index);
        let filepath = current_directory + "/" + filename;
        if os.path.isfile(filepath) {
            let content = file.read(filepath);
            gui.delete(editor, "1.0", "end");
            gui.insert(editor, "1.0", content);
            current_file = filepath;
            is_modified = false;
            update_status("📖 Opened: " + filepath, "success");
            update_title();
        }
    } else {
        update_status("⚠️ No file selected", "warning");
    }
}

func show_about() {
    gui.message_box("About", "🌟 KentScript Studio ✨\n\nVersion 2.0\n\nA modern, feature-rich IDE\nbuilt with KentScript\n\nMade with ❤️", "info");
}

func show_documentation() {
    gui.message_box("Documentation", "📚 KentScript Studio Documentation\n\n📁 File Menu:\n  • New - Create new file\n  • Open - Open existing file\n  • Save - Save current file\n  • Save As - Save as new file\n\n✏️ Edit Menu:\n  • Cut/Copy/Paste - Standard editing\n  • Select All - Select all text\n\n👁️ View Menu:\n  • Zoom In/Out - Adjust font size\n  • Reset Zoom - Reset to default\n\n📂 Sidebar:\n  • Shows files in current directory\n  • Double-click or use Open to edit\n\n✏️ Editor:\n  • Full-featured code editor\n  • Line numbers in status bar", "info");
}

func update_status(message: str, msg_type: str) {
    let icon = "🟢";
    if msg_type == "warning" {
        icon = "⚠️";
    } else if msg_type == "error" {
        icon = "❌";
    } else if msg_type == "success" {
        icon = "✅";
    } else if msg_type == "info" {
        icon = "ℹ️";
    }
    let status_text_value = icon + " " + message;
    gui.set_text(status_text, status_text_value);
}

func update_title() {
    let title = "KentScript Studio ✨";
    let file_part = "";
    if current_file != "" && current_file != none {
        file_part = " - " + current_file;
    }
    if is_modified {
        file_part = file_part + " *";
    }
    gui.configure(window, title=title + file_part);
    
    let file_label = "📝 ";
    if current_file == "" || current_file == none {
        file_label = file_label + "Untitled";
    } else {
        file_label = file_label + current_file;
    }
    if is_modified {
        file_label = file_label + " [Modified]";
    }
    gui.set_text(status_file, file_label);
}

func update_line_col() {
    let cursor_pos = gui.text_index(editor, "insert");
    let parts = str(cursor_pos);
    gui.set_text(line_col_label, "📊 Lines: " + str(cursor_pos) + " Col: " + str(cursor_pos));
}

:: Bind cursor movement to update line/column
gui.bind(editor, "<KeyRelease>", lambda: { update_line_col(); });
gui.bind(editor, "<ButtonRelease-1>", lambda: { update_line_col(); });

:: Initialize
refresh_files();
update_status("🟢 Welcome to KentScript Studio!", "success");
update_title();

gui.mainloop(window);
