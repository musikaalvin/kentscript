:: Simple GUI app
import gui;

let window = gui.create_window("My App", 400, 300);

let label = gui.create_label(window, "Enter your name:");
gui.pack(label);

let entry = gui.create_entry(window);
gui.pack(entry);

let button = gui.create_button(window, "Submit", lambda: {
    let name = gui.get_text(entry);
    gui.message_box("Hello", "Welcome, " + name + "!", "info");
});
gui.pack(button);

gui.mainloop(window);