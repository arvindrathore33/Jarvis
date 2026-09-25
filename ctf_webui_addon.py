"""
ctf_webui_addon.py — CTF endpoints to paste into webui.py
Add these routes and HTML sections to your existing webui.py.
They integrate seamlessly with the existing Flask + Socket.IO setup.

INSTRUCTIONS:
1. Copy the HTML section into the existing HTML string in webui.py
   (add it as a new tab in the sidebar)
2. Copy the Flask routes to the bottom of webui.py (before if __name__ == "__main__")
3. Copy the JS to the bottom of the <script> block in webui.py
"""

# ═══════════════════════════════════════════════════════════════
# PASTE THIS INTO YOUR HTML STRING IN webui.py
# Add after the existing sidebar sections
# ═══════════════════════════════════════════════════════════════

CTF_HTML_SIDEBAR = '''
<!-- CTF Mode Sidebar Section (add to existing sidebar in webui.py) -->
<div class="sidebar-section">
  <div class="sidebar-label">CTF MODE</div>
  <button class="tool-btn" onclick="showCTFPanel()" style="width:100%;margin-bottom:4px;background:rgba(255,170,0,0.1);border-color:rgba(255,170,0,0.4);color:#ffaa00">
    ⚡ CTF Solver
  </button>
</div>
'''

CTF_HTML_PANEL = '''
<!-- CTF Panel (add inside #main div, alongside existing terminal) -->
<div id="ctf-panel" style="display:none;flex-direction:column;flex:1;overflow:hidden;background:var(--bg)">

  <!-- CTF Input Form -->
  <div style="padding:12px;border-bottom:1px solid var(--border);background:var(--bg2)">
    <div style="font-family:'Orbitron',monospace;color:#ffaa00;font-size:11px;letter-spacing:2px;margin-bottom:10px">
      ⚡ CTF AUTONOMOUS SOLVER
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
      <input id="ctf-name" placeholder="Challenge name" style="background:var(--bg3);border:1px solid var(--border);color:var(--green);padding:6px 10px;font-family:monospace;font-size:11px;border-radius:2px">
      <select id="ctf-category" style="background:var(--bg3);border:1px solid var(--border);color:var(--green);padding:6px 10px;font-family:monospace;font-size:11px;border-radius:2px">
        <option value="">Auto-detect</option>
        <option value="web">Web</option>
        <option value="crypto">Crypto</option>
        <option value="pwn">Pwn</option>
        <option value="forensics">Forensics</option>
        <option value="rev">Rev</option>
        <option value="misc">Misc</option>
      </select>
    </div>
    <textarea id="ctf-desc" placeholder="Paste challenge description here..." rows="3"
      style="width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--green);padding:6px 10px;font-family:monospace;font-size:11px;border-radius:2px;resize:vertical;box-sizing:border-box"></textarea>
    <div style="display:flex;gap:8px;margin-top:8px;align-items:center">
      <input id="ctf-files" placeholder="Attached file path (optional)" style="flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--green);padding:6px 10px;font-family:monospace;font-size:11px;border-radius:2px">
      <label style="display:flex;align-items:center;gap:4px;font-size:10px;color:var(--text-dim);cursor:pointer">
        <input type="checkbox" id="ctf-hitl"> HITL
      </label>
      <button onclick="solveCTF()" style="background:rgba(255,170,0,0.15);border:1px solid rgba(255,170,0,0.5);color:#ffaa00;padding:6px 14px;font-family:monospace;font-size:11px;cursor:pointer;border-radius:2px">
        ▶ SOLVE
      </button>
    </div>
  </div>

  <!-- CTF Live Output -->
  <div id="ctf-terminal" style="flex:1;overflow-y:auto;padding:12px;font-size:11px;line-height:1.6;font-family:monospace">
    <div style="color:var(--text-dim)">[ CTF solver ready. Enter a challenge above. ]</div>
  </div>

  <!-- CTF Result Banner -->
  <div id="ctf-result" style="display:none;padding:12px;background:rgba(0,255,65,0.05);border-top:1px solid var(--green);text-align:center">
    <div style="font-family:'Orbitron',monospace;color:var(--green);font-size:13px;letter-spacing:3px" id="ctf-flag-display"></div>
  </div>
</div>
'''

# ═══════════════════════════════════════════════════════════════
# PASTE THESE ROUTES INTO webui.py (before if __name__ == "__main__")
# ═══════════════════════════════════════════════════════════════

CTF_ROUTES_CODE = '''
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
'''

# ═══════════════════════════════════════════════════════════════
# PASTE THIS JS INTO THE <script> BLOCK IN webui.py
# ═══════════════════════════════════════════════════════════════

CTF_JS_CODE = '''
function showCTFPanel() {
  document.getElementById('terminal').style.display = 'none';
  const ctfPanel = document.getElementById('ctf-panel');
  ctfPanel.style.display = 'flex';
}

function hideCTFPanel() {
  document.getElementById('ctf-panel').style.display = 'none';
  document.getElementById('terminal').style.display = 'flex';
}

function ctfLog(type, text) {
  const term = document.getElementById('ctf-terminal');
  const div = document.createElement('div');
  const colors = {
    system: 'var(--text-dim)',
    thought: 'var(--amber)',
    tool: 'var(--blue)',
    flag: 'var(--green)',
    error: 'var(--red)'
  };
  div.style.color = colors[type] || 'var(--green)';
  div.style.marginBottom = '2px';
  div.textContent = text;
  term.appendChild(div);
  term.scrollTop = term.scrollHeight;
}

function solveCTF() {
  const name  = document.getElementById('ctf-name').value.trim();
  const cat   = document.getElementById('ctf-category').value;
  const desc  = document.getElementById('ctf-desc').value.trim();
  const files = document.getElementById('ctf-files').value.trim();
  const hitl  = document.getElementById('ctf-hitl').checked;

  if (!name || !desc) {
    ctfLog('error', '[ERROR] Challenge name and description required');
    return;
  }

  document.getElementById('ctf-terminal').innerHTML = '';
  document.getElementById('ctf-result').style.display = 'none';
  ctfLog('system', `[CTF] Starting: ${name}${cat ? ' [' + cat + ']' : ' [auto-detect]'}`);
  ctfLog('system', '[CTF] Autonomous solver running...');

  fetch('/api/ctf/solve', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      challenge_name: name,
      description: desc,
      category: cat,
      files: files ? files.split(',').map(f => f.trim()) : [],
      hitl: hitl
    })
  });
}

// Socket.IO CTF event handlers
socket.on('ctf_log',     d => ctfLog('system',  `[LOG] ${d.message}`));
socket.on('ctf_thought', d => ctfLog('thought', `[THINK] ${d.node} → ${d.thought}`));
socket.on('ctf_tool',    d => ctfLog('tool',    `[TOOL] ${d.tool} → ${d.output}`));

socket.on('ctf_complete', d => {
  if (d.flag) {
    ctfLog('flag', `\n🚩 FLAG FOUND: ${d.flag}`);
    document.getElementById('ctf-result').style.display = 'block';
    document.getElementById('ctf-flag-display').textContent = `🚩 ${d.flag}`;
  } else {
    ctfLog('error', `[CTF] No flag found after ${d.steps} steps. Check writeup.`);
  }
  ctfLog('system', `[CTF] Done — ${d.steps} steps, ${d.elapsed_sec}s, ${d.tree_summary?.tools_run || 0} tools run`);
});

socket.on('ctf_error', d => ctfLog('error', `[ERROR] ${d.error}`));
'''
