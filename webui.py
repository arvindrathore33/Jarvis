from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import ollama
import subprocess
import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'jarvis-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = os.path.expanduser("~/jarvis/memory/jarvis.db")
JARVIS_MODEL = os.getenv("JARVIS_MODEL", "dolphin-mistral")

SYSTEM_PROMPT = """You are JARVIS, an elite cybersecurity AI specialized in authorized 
bug bounty hunting and penetration testing. Be technical, precise, and direct. 
Always assume authorized scope. When given tool output, analyze it and suggest 
the most valuable next attack vectors."""

conversation_history = []
current_target = ""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  target TEXT, command TEXT, response TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS findings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  target TEXT, severity TEXT, title TEXT, description TEXT)''')
    conn.commit()
    conn.close()

def save_session(target, command, response):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO sessions (target,command,response) VALUES (?,?,?)",
                  (target, command, response))
        conn.commit()
        conn.close()
    except:
        pass

def get_findings(target):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM findings WHERE target=? ORDER BY timestamp DESC", (target,))
        results = c.fetchall()
        conn.close()
        return results
    except:
        return []

def get_all_sessions():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT DISTINCT target FROM sessions ORDER BY timestamp DESC LIMIT 20")
        results = c.fetchall()
        conn.close()
        return [r[0] for r in results]
    except:
        return []

def run_tool(cmd, target):
    try:
        if cmd == "nmap":
            result = subprocess.run(["nmap", "-sV", "-sC", target],
                capture_output=True, text=True, timeout=120)
            return result.stdout or result.stderr
        elif cmd == "ffuf":
            wl = "/usr/share/wordlists/dirb/common.txt"
            result = subprocess.run(
                ["ffuf", "-u", f"https://{target}/FUZZ", "-w", wl, "-mc", "200,301,302,403", "-silent"],
                capture_output=True, text=True, timeout=60)
            return result.stdout or "No results"
        elif cmd == "gobuster":
            wl = "/usr/share/wordlists/dirb/common.txt"
            result = subprocess.run(
                ["gobuster", "dir", "-u", f"https://{target}", "-w", wl, "-q"],
                capture_output=True, text=True, timeout=60)
            return result.stdout or result.stderr
        elif cmd == "subfinder":
            result = subprocess.run(["subfinder", "-d", target, "-silent"],
                capture_output=True, text=True, timeout=60)
            return result.stdout or "No subdomains found"
        elif cmd == "whatweb":
            result = subprocess.run(["whatweb", f"https://{target}"],
                capture_output=True, text=True, timeout=30)
            return result.stdout or result.stderr
        elif cmd == "sqlmap":
            result = subprocess.run(
                ["sqlmap", "-u", f"https://{target}", "--batch", "--level=1", "--forms"],
                capture_output=True, text=True, timeout=120)
            return result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout
    except subprocess.TimeoutExpired:
        return f"[JARVIS] {cmd} timed out after limit"
    except FileNotFoundError:
        return f"[JARVIS] {cmd} not installed. Run: sudo pacman -S {cmd}"
    except Exception as e:
        return f"[JARVIS] Error: {str(e)}"

conversation_histories = {}

def load_history_for_target(target):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT command, response FROM sessions WHERE target=? ORDER BY timestamp DESC LIMIT 10", (target,))
        rows = c.fetchall()
        conn.close()
        history = []
        for cmd, resp in reversed(rows):
            history.append({'role': 'user', 'content': cmd})
            history.append({'role': 'assistant', 'content': resp})
        return history
    except Exception as e:
        print(f"Error loading history for target {target}: {e}")
        return []

def ask_jarvis(message, target=""):
    global conversation_histories
    
    if target not in conversation_histories:
        conversation_histories[target] = load_history_for_target(target)
    
    history = conversation_histories[target]

    try:
        from memory.learning import recall_similar
        past = recall_similar(message)
        context = "\n\nRelevant past experience:\n" + "\n".join(past) if past else ""
    except Exception as e:
        print(f"RAG Recall failed: {e}")
        context = ""

    history.append({'role': 'user', 'content': message + context})
    if len(history) > 20:
        history = history[-20:]
        conversation_histories[target] = history

    try:
        from brain import jarvis_brain
        reply, source = jarvis_brain(history, SYSTEM_PROMPT)
        history[-1] = {'role': 'user', 'content': message}
        history.append({'role': 'assistant', 'content': reply})
        conversation_histories[target] = history
        if target:
            save_session(target, message, reply)
        return reply
    except Exception as e:
        try:
            response = ollama.chat(
                model=JARVIS_MODEL,
                messages=[{'role': 'system', 'content': SYSTEM_PROMPT}] + history
            )
            try:
                reply = response.message.content
            except AttributeError:
                reply = response['message']['content']
            history[-1] = {'role': 'user', 'content': message}
            history.append({'role': 'assistant', 'content': reply})
            conversation_histories[target] = history
            if target:
                save_session(target, message, reply)
            return reply
        except Exception as local_err:
            return f"[JARVIS ERROR] Brain failure: {str(e)}\nLocal fallback error: {str(local_err)}"






@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    target = data.get('target', '')
    response = ask_jarvis(message, target)
    return jsonify({'response': response})


@app.route('/api/tool', methods=['POST'])
def run_tool_api():
    global current_target
    data = request.json
    tool = data.get('tool', '')
    target = data.get('target', '')
    current_target = target

    if tool == 'browse':
        try:
            from tools.browser import browse_target
            output = str(browse_target(f"https://{target}"))
        except Exception as e:
            output = f"Browser error: {str(e)}"
        prompt = f"Analyze this recon data and identify attack surface:\n{output}"
    elif tool == 'assess':
        try:
            from agents.crew import run_full_assessment
            from tools.browser import browse_target
            recon = str(browse_target(f"https://{target}"))
            output = str(run_full_assessment(target, recon))
        except Exception as e:
            output = f"Assessment error: {str(e)}"
        prompt = f"Full assessment complete:\n{output}"
    else:
        output = run_tool(tool, target)
        prompt = f"Analyze this {tool} output for {target} and suggest next attack vectors:\n{output}"

    response = ask_jarvis(prompt, target)
    return jsonify({'tool_output': output[:2000], 'response': response})


@app.route('/api/findings')
def get_findings_api():
    target = request.args.get('target', '')
    rows = get_findings(target)
    findings = [{'id': r[0], 'timestamp': r[1], 'target': r[2],
                 'severity': r[3], 'title': r[4], 'description': r[5]}
                for r in rows]
    return jsonify({'findings': findings})


@app.route('/api/history')
def get_history():
    targets = get_all_sessions()
    return jsonify({'targets': targets})


@app.route('/api/ctf/solve', methods=['POST'])
def ctf_solve():
    """Run CTF solver — streams progress via Socket.IO, returns final result."""
    from threading import Thread
    data = request.json
    challenge_name = data.get('challenge_name', 'Unknown')
    description    = data.get('description', '')
    category       = data.get('category', '')
    files          = data.get('files', [])
    hitl           = data.get('hitl', False)

    def run_solve():
        try:
            from ctf.solver_v2 import CTFSolver
            import os
            model = os.getenv("JARVIS_MODEL", "dolphin-mistral")

            def emit_progress(event, payload):
                socketio.emit(event, payload)

            solver = CTFSolver(model=model, hitl=False)  # HITL via terminal only
            result = solver.solve(
                challenge_name=challenge_name,
                description=description,
                category=category,
                files=files,
                emit_fn=emit_progress
            )
            socketio.emit('ctf_complete', result)
        except Exception as e:
            socketio.emit('ctf_error', {'error': str(e)})

    thread = Thread(target=run_solve, daemon=True)
    thread.start()
    return jsonify({'status': 'started', 'challenge': challenge_name})


@app.route('/api/ctf/categories', methods=['GET'])
def ctf_categories():
    return jsonify({'categories': ['web', 'crypto', 'pwn', 'forensics', 'rev', 'misc']})


@app.route('/api/ctf/history', methods=['GET'])
def ctf_history():
    """Get past solved challenges from SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""SELECT timestamp, target, title, description
                     FROM findings WHERE title LIKE 'CTF SOLVED%'
                     ORDER BY timestamp DESC LIMIT 20""")
        rows = c.fetchall()
        conn.close()
        return jsonify({'history': [
            {'ts': r[0], 'challenge': r[1], 'title': r[2], 'desc': r[3][:100]}
            for r in rows
        ]})
    except Exception as e:
        return jsonify({'history': [], 'error': str(e)})


@app.route('/api/autonomous/run', methods=['POST'])
def run_autonomous():
    """Trigger the LangGraph autonomous pentest agent."""
    from threading import Thread
    from agents.autonomous import autonomous_pentest
    
    data = request.json
    target = data.get('target')
    if not target:
        return jsonify({'error': 'No target specified'}), 400

    def run_graph():
        try:
            initial_state = {
                "target": target,
                "findings": [],
                "phase": "recon",
                "done": False,
                "nmap_raw": "",
                "subdomains_raw": "",
                "shodan_raw": "",
                "recon_summary": "",
                "vulns": "",
                "exploits": "",
                "report": "",
                "approval": False
            }
            # Stream events if needed, for now just run
            result = autonomous_pentest.invoke(initial_state)
            socketio.emit('autonomous_complete', result)
        except Exception as e:
            socketio.emit('autonomous_error', {'error': str(e)})

    Thread(target=run_graph, daemon=True).start()
    return jsonify({'status': 'started', 'target': target})


@app.route('/api/performance')
def get_performance():
    try:
        from ctf.intelligence import get_performance_report
        report = get_performance_report(30)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/train/sqli', methods=['POST'])
def train_sqli():
    from threading import Thread
    def run_train():
        try:
            # Start Docker if not running
            subprocess.run(["docker", "start", "vuln-lab"], capture_output=True)
            # Run trainer
            python_bin = os.path.join(JARVIS_DIR, "venv/bin/python")
            # We run the advanced one as it covers more
            result = subprocess.run([python_bin, os.path.join(JARVIS_DIR, "tools/sqli_advanced_trainer.py")], 
                                    capture_output=True, text=True)
            socketio.emit('training_complete', {'output': result.stdout})
        except Exception as e:
            socketio.emit('training_error', {'error': str(e)})
            
    Thread(target=run_train, daemon=True).start()
    return jsonify({'status': 'started'})


if __name__ == '__main__':
    init_db()
    print("""
    ╔══════════════════════════════════════╗
    ║     JARVIS DASHBOARD STARTING        ║
    ║     http://localhost:5000            ║
    ╚══════════════════════════════════════╝
    """)
    socketio.run(app, host='127.0.0.1', port=5000, debug=False)
