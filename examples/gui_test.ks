:: Simple GUI Test
import gui;
import os;

let window = gui.create_window("Simple Test", 400, 300);
gui.configure(window, background="#f0f0f0");

:: Add some buttons
let btn1 = gui.create_button(window, "Click Me", lambda: {
    gui.message_box("Test", "Button 1 works!", "info");
});
gui.pack(btn1, pady=5);

let btn2 = gui.create_button(window, "Another Button", lambda: {
    gui.message_box("Test", "Button 2 works!", "info");
});
gui.pack(btn2, pady=5);

let btn3 = gui.create_button(window, "Third Button", lambda: {
    gui.message_box("Test", "Button 3 works!", "info");
});
gui.pack(btn3, pady=5);

:: Add a menu
let menubar = gui.create_menu(window);
window.config(menu=menubar);

let file_menu = gui.create_menu(menubar);
gui.menu_add_cascade(menubar, "File", file_menu);
gui.menu_add_command(file_menu, "About", lambda: {
    gui.message_box("About", "Simple test works!", "info");
});
gui.menu_add_separator(file_menu);
gui.menu_add_command(file_menu, "Exit", lambda: {
    gui.destroy(window);
});

let help_menu = gui.create_menu(menubar);
gui.menu_add_cascade(menubar, "Help", help_menu);
gui.menu_add_command(help_menu, "Info", lambda: {
    gui.message_box("Info", "This is a test GUI!", "info");
});
gui.menu_add_command(help_menu, "Warning", lambda: {
    gui.message_box("Warning", "This is a warning!", "warning");
});
gui.menu_add_command(help_menu, "Error", lambda: {
    gui.message_box("Error", "This is an error!", "error");
});

gui.mainloop(window);
