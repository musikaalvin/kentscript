let loop = get_event_loop();

:: Enqueue I/O operation (doesn't block)
loop.enqueue_macrotask(file_read_operation);

:: GUI event handling (non-blocking)
loop.enqueue_gui_event("click", button_handler);

:: Schedule with timeout
loop.set_timeout(callback, 1000);

:: Run event loop
loop.run();