:: Simple KentScript GUI Demo
import gui;

let win = gui.create_window("KentScript GUI Demo", 350, 250);

let lbl = gui.create_label(win, "Hello from KentScript!");
gui.pack(lbl, pady=10);

let entry = gui.create_entry(win);
gui.pack(entry, padx=20, pady=5);

let result_lbl = gui.create_label(win, "Type something:");
gui.pack(result_lbl, pady=5);

func show_text() {
    let txt = gui.get_text(entry);
    gui.set_text(result_lbl, "You typed: " + txt);
}

let btn = gui.create_button(win, "Show Text", show_text);
gui.pack(btn, pady=10);

func do_msg() {
    gui.message_box("KentScript", "GUI works!", "info");
}

let btn2 = gui.create_button(win, "Message", do_msg);
gui.pack(btn2, pady=5);

gui.mainloop(win);
