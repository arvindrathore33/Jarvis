from flask import Flask, request, make_response, render_template_string
import uuid

app = Flask(__name__)

# Mock data
sessions = {
    "admin_session_777": "admin",
    "user1_session_123": "guest"
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Old Social Media</title></head>
<body>
    <h1>Welcome to Old Social Media</h1>
    {% if username %}
        <p>Logged in as: <b>{{ username }}</b></p>
        {% if username == 'admin' %}
            <p style="color: green;">Flag: <b>picoCTF{s3ss1on_h1j4ck1ng_1s_fun_5a92bc}</b></p>
        {% else %}
            <p>Only admin can see the flag.</p>
        {% endif %}
        <a href="/logout">Logout</a>
    {% else %}
        <a href="/login">Login</a>
    {% endif %}
    <hr>
    <p>Check out our <a href="/sessions">public sessions list</a> (for debugging purposes, will be removed later!)</p>
</body>
</html>
"""

@app.route("/")
def index():
    session_id = request.cookies.get("session")
    username = sessions.get(session_id)
    return render_template_string(HTML_TEMPLATE, username=username)

@app.route("/login")
def login():
    resp = make_response("Logged in! <a href='/'>Go home</a>")
    new_session = str(uuid.uuid4())
    sessions[new_session] = "new_user"
    resp.set_cookie("session", new_session)
    return resp

@app.route("/logout")
def logout():
    resp = make_response("Logged out! <a href='/'>Go home</a>")
    resp.set_cookie("session", "", expires=0)
    return resp

@app.route("/sessions")
def list_sessions():
    return "<h3>Active Sessions</h3><ul>" + "".join([f"<li>User: {v} | Session ID: {k}</li>" for k, v in sessions.items()]) + "</ul>"

if __name__ == "__main__":
    app.run(port=5001)
