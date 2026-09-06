import flask;
import sqlite3;

let app = flask.Flask(__name__);
let db = sqlite3.connect("data.db");

@app.route("/")
func home() -> str {
    let cursor = db.execute("SELECT * FROM users");
    return flask.jsonify(cursor.fetchall());
}

app.run(port=8080);