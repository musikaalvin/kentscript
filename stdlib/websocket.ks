:: websocket - WebSocket Client & Server
::
:: Usage:
::   import websocket;
::
::   :: Client
::   let ws = websocket.connect("ws://localhost:8080");
::   ws.send("hello");
::   let msg = ws.recv();
::   ws.close();
::
::   :: Server
::   let server = websocket.server("0.0.0.0", 8080);
::   server.on_message(func(client, msg) {
::       print("Received: " + msg);
::       client.send("Echo: " + msg);
::   });
::   server.start();

class WebSocketClient {
    func __init__(self) {
        self._ws = none;
    }

    func connect(self, url, headers) {
        if headers != none {
            self._ws = system_websocket_connect(url, headers);
        } else {
            self._ws = system_websocket_connect(url);
        }
        return self;
    }

    func send(self, data) {
        system_websocket_send(self._ws, data);
    }

    func recv(self) {
        return system_websocket_recv(self._ws);
    }

    func close(self, code, reason) {
        if code == none { code = 1000; }
        if reason == none { reason = ""; }
        system_websocket_close(self._ws, code, reason);
    }

    func ping(self) {
        self.send("\x09");
    }
}

class WebSocketServer {
    func __init__(self, host, port) {
        self.host = host;
        self.port = port;
        self._server = none;
        self._on_message = none;
        self._on_connect = none;
        self._on_disconnect = none;
        self.clients = {};
    }

    func on_message(self, handler) {
        self._on_message = handler;
    }

    func on_connect(self, handler) {
        self._on_connect = handler;
    }

    func on_disconnect(self, handler) {
        self._on_disconnect = handler;
    }

    func _handle(self, client, path) {
        let client_id = str(id(client));
        self.clients[client_id] = client;

        if self._on_connect != none {
            self._on_connect(client, path);
        }

        while true {
            let msg = system_websocket_recv(client);
            if msg == none { break; }

            if self._on_message != none {
                self._on_message(client, msg);
            }
        }

        if self._on_disconnect != none {
            self._on_disconnect(client);
        }

        del self.clients[client_id];
    }

    func broadcast(self, message) {
        for client_id in self.clients {
            let client = self.clients[client_id];
            system_websocket_send(client, message);
        }
    }

    func start(self) {
        print("WebSocket server listening on ws://" + self.host + ":" + str(self.port));
        self._server = system_websocket_server_create(self.host, self.port);
        let handler = func(client, path) { self._handle(client, path); };
        system_websocket_server_start(self._server, handler);
    }

    func stop(self) {
        if self._server != none {
            system_websocket_server_stop(self._server);
        }
    }
}

func connect(url, headers) {
    let client = WebSocketClient();
    return client.connect(url, headers);
}

func server(host, port) {
    if host == none { host = "0.0.0.0"; }
    if port == none { port = 8080; }
    return WebSocketServer(host, port);
}

export { WebSocketClient, WebSocketServer, connect, server };
