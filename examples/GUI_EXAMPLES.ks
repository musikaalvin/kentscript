:: ============ KentScript GUI Examples ============

:: Example 1: Simple Hello Window
import gui;

let window = gui.create_window("Hello World", 300, 200);

let label = gui.create_label(window, "Welcome to KentScript GUI!");
gui.pack(label);

let button = gui.create_button(window, "Click Me!", lambda: 
    gui.message_box("Success!", "Button clicked!", "info"));
gui.pack(button);

gui.mainloop(window);


:: ============ Example 2: Counter App ============
import gui;

let window = gui.create_window("Counter", 300, 200);
let counter = [0];  :: Mutable counter in list

let title = gui.create_label(window, "Counter Application");
gui.pack(title);

let count_label = gui.create_label(window, "Count: 0");
gui.pack(count_label);

let increment_btn = gui.create_button(window, "Increment", lambda: {
    counter[0] = counter[0] + 1;
    gui.set_text(count_label, "Count: " + str(counter[0]));
});
gui.pack(increment_btn);

let decrement_btn = gui.create_button(window, "Decrement", lambda: {
    counter[0] = counter[0] - 1;
    gui.set_text(count_label, "Count: " + str(counter[0]));
});
gui.pack(decrement_btn);

gui.mainloop(window);


:: ============ Example 3: Text Input ============
import gui;

let window = gui.create_window("Input", 400, 250);

let label = gui.create_label(window, "Enter your name:");
gui.pack(label);

let entry = gui.create_entry(window);
gui.pack(entry);

let submit_btn = gui.create_button(window, "Submit", lambda: {
    let name = gui.get_text(entry);
    gui.message_box("Greeting", "Hello, " + name + "!", "info");
});
gui.pack(submit_btn);

gui.mainloop(window);


:: ============ Example 4: Multi-line Text ============
import gui;

let window = gui.create_window("Text Editor", 500, 400);

let label = gui.create_label(window, "Simple Text Editor");
gui.pack(label);

let text_area = gui.create_text(window, 50, 15);
gui.pack(text_area);

let save_btn = gui.create_button(window, "Save", lambda: {
    let content = gui.get_text(text_area);
    gui.message_box("Saved", "Content saved! " + str(content.len()) + " chars", "info");
});
gui.pack(save_btn);

gui.mainloop(window);


:: ============ Example 5: Todo List ============
import gui;

class TodoApp {
    func __init__() {
        self.window = gui.create_window("Todo List", 400, 500);
        self.todos = [];
        self.setup();
    }
    
    func setup() {
        let title = gui.create_label(self.window, "My Todo List");
        gui.pack(title);
        
        let frame = gui.create_frame(self.window);
        gui.pack(frame);
        
        self.entry = gui.create_entry(frame);
        gui.pack(self.entry, {"side": "left"});
        
        let add_btn = gui.create_button(frame, "Add", lambda: self.add_todo());
        gui.pack(add_btn, {"side": "left"});
        
        self.display = gui.create_text(self.window, 40, 15);
        gui.pack(self.display);
    }
    
    func add_todo() {
        let task = gui.get_text(self.entry);
        if task {
            self.todos.append(task);
            gui.set_text(self.entry, "");
            self.refresh();
        }
    }
    
    func refresh() {
        let text = "";
        for i in range(0, self.todos.len()) {
            text = text + str(i + 1) + ". " + self.todos[i] + "\n";
        }
        gui.set_text(self.display, text);
    }
    
    func run() {
        gui.mainloop(self.window);
    }
}

let app = TodoApp();
app.run();
