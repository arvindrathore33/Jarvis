import sqlite3
import os

DB_PATH = os.path.expanduser("~/jarvis/memory/jarvis.db")

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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions (target,command,response) VALUES (?,?,?)",
              (target, command, response))
    conn.commit()
    conn.close()

def save_finding(target, severity, title, description):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO findings (target,severity,title,description) VALUES (?,?,?,?)",
              (target, severity, title, description))
    conn.commit()
    conn.close()

def get_findings(target):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM findings WHERE target=?", (target,))
    results = c.fetchall()
    conn.close()
    return results

init_db()
