:: KentScript GUI - Complete Tkinter Wrapper Demo

import gui;

:: Access raw tkinter via gui.tk
let tk = gui.tk;
let ttk = gui.ttk;

:: Create window 
let win = gui.create_window("KentScript GUI Demo", 500, 400);
gui.title(win, "KentScript GUI Demo");

:: Main frame
let main = gui.create_frame(win);
gui.pack(main, fill="both", expand=true, padx=10, pady=10);

:: Title
gui.create_label(main, "=== KentScript GUI + Tkinter ===").pack(pady=10);

:: Canvas using tkinter directly
let canvas = tk.Canvas(main, width=400, height=150, bg="white");
gui.pack(canvas, pady=10);
tk.Canvas.create_line(canvas, 10, 10, 100, 100, fill="red", width=2);
tk.Canvas.create_oval(canvas, 150, 50, 250, 150, fill="blue");
tk.Canvas.create_rectangle(canvas, 300, 50, 400, 150, fill="green");

:: Entry with StringVar
let text_var = tk.StringVar();
text_var.set("Type here...");

let entry_frame = gui.create_frame(main);
gui.pack(entry_frame, fill="x", pady=5);
gui.create_label(entry_frame, "Entry:").pack(side="left");
let entry = tk.Entry(entry_frame, textvariable=text_var, width=25);
entry.pack(side="left", padx=5);

:: Counter with IntVar
let counter = tk.IntVar();
counter.set(0);

let counter_frame = gui.create_frame(main);
gui.pack(counter_frame, pady=10);

let count_label = gui.create_label(counter_frame, textvariable=counter);
gui.pack(count_label, side="left", padx=10);

let inc_btn = tk.Button(counter_frame, text="+", command=lambda: counter.set(counter.get() + 1));
inc_btn.pack(side="left", padx=2);

let dec_btn = tk.Button(counter_frame, text="-", command=lambda: counter.set(counter.get() - 1));
dec_btn.pack(side="left", padx=2);

let reset_btn = tk.Button(counter_frame, text="Reset", command=lambda: counter.set(0));
reset_btn.pack(side="left", padx=10);

:: Listbox
let list_frame = gui.create_frame(main);
gui.pack(list_frame, fill="both", expand=true, pady=5);
gui.create_label(list_frame, "Fruits:").pack(anchor="w");

let listbox = tk.Listbox(list_frame);
listbox.pack(side="left", fill="both", expand=true);

for fruit in ["Apple", "Banana", "Orange", "Mango"] {
    listbox.insert("end", fruit);
}

:: Buttons
let btn_frame = gui.create_frame(main);
gui.pack(btn_frame, pady=10);

let msg_btn = tk.Button(btn_frame, text="Message", command=lambda: gui.message_box("Hi", "Hello!", "info"));
msg_btn.pack(side="left", padx=5);

let color_btn = tk.Button(btn_frame, text="Color", command=lambda: gui.colorchooser("Pick"));
color_btn.pack(side="left", padx=5);

let exit_btn = tk.Button(btn_frame, text="Exit", bg="red", fg="white", command=lambda: gui.destroy(win));
exit_btn.pack(side="left", padx=10);

gui.mainloop(win);
