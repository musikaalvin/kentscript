import gui;

:: Create window
let win = gui.create_window("My KentScript App", 400, 300);

:: Create label
let label = gui.create_label(win, "Hello KentScript!");
gui.pack(label);

:: Counter
let count = 0;

:: Button click handler
func on_click() {
    count = count + 1;
    gui.set_text(label, "Clicked: " + str(count));
}

:: Create button
let btn = gui.create_button(win, "Click Me!", on_click);
gui.pack(btn, pady=10);

:: Create entry
let entry = gui.create_entry(win);
gui.pack(entry, padx=20, pady=10);

:: Get text button
func on_get_text() {
    let text = gui.get_text(entry);
    gui.set_text(label, "You typed: " + text);
}

let get_btn = gui.create_button(win, "Get Text", on_get_text);
gui.pack(get_btn);

:: Message box button
func on_message() {
    gui.message_box("Info", "This is KentScript!", "info");
}

let msg_btn = gui.create_button(win, "Show Message", on_message);
gui.pack(msg_btn, pady=10);

:: Start the app
gui.mainloop(win);