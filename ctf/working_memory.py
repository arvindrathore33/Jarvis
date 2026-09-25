"""
ctf/working_memory.py — Persistent working memory across all task tree nodes
Fixes the #1 agent failure: context forgetting (18% of all failures)
Every key finding is stored here and injected at EVERY step of the solver.
Drop into ~/jarvis/ctf/working_memory.py
"""

from datetime import datetime
from typing import Any


class WorkingMemory:
    """
    A global fact store that persists across the entire solve session.
    Unlike the task tree (which stores per-node observations), this stores
    the IMPORTANT facts extracted from those observations — credentials,
    open ports, endpoints, file paths, error messages, partial flags.

    Injected into every LLM prompt so the agent never re-discovers what it found.
    """

    CATEGORIES = [
        "credentials",      # username:password pairs found
        "ports",            # open ports and services
        "endpoints",        # URLs, API paths, admin panels
        "files",            # interesting file paths found
        "technologies",     # frameworks, languages, versions
        "errors",           # error messages (often leak info)
        "hashes",           # hashes found, cracked or not
        "keys",             # crypto keys, secrets, tokens
        "flags",            # partial or full flags
        "notes",            # general observations
    ]

    def __init__(self):
        self._store: dict[str, list[dict]] = {c: [] for c in self.CATEGORIES}
        self._tried: set[tuple] = set()          # (tool, input) dedup set
        self._step_count: int = 0

    # ── Adding facts ─────────────────────────────────────────────────────

    def add(self, category: str, value: str, source: str = "", confidence: str = "medium"):
        """Store a discovered fact."""
        if category not in self._store:
            category = "notes"
        # Dedup — don't store the same value twice
        existing = [f["value"] for f in self._store[category]]
        if value.strip() in existing:
            return
        self._store[category].append({
            "value":      value.strip(),
            "source":     source,
            "confidence": confidence,
            "step":       self._step_count,
            "ts":         datetime.now().strftime("%H:%M:%S"),
        })

    def add_credential(self, username: str, password: str, source: str = ""):
        self.add("credentials", f"{username}:{password}", source, "high")

    def add_port(self, port: int, service: str, source: str = "nmap"):
        self.add("ports", f"{port}/{service}", source, "high")

    def add_endpoint(self, url: str, note: str = "", source: str = ""):
        val = f"{url}" + (f" ({note})" if note else "")
        self.add("endpoints", val, source)

    def add_file(self, filepath: str, note: str = "", source: str = ""):
        val = f"{filepath}" + (f" — {note}" if note else "")
        self.add("files", val, source)

    def add_hash(self, hash_value: str, cracked: str = "", source: str = ""):
        val = hash_value + (f" → {cracked}" if cracked else " [uncracked]")
        self.add("hashes", val, source)

    def add_flag(self, flag: str, source: str = ""):
        self.add("flags", flag, source, "high")

    def add_tech(self, tech: str, source: str = ""):
        self.add("technologies", tech, source)

    def add_error(self, error: str, source: str = ""):
        self.add("errors", error[:200], source, "low")

    def add_key(self, key: str, key_type: str = "", source: str = ""):
        val = f"[{key_type}] {key}" if key_type else key
        self.add("keys", val, source, "high")

    # ── Repetition prevention ─────────────────────────────────────────────

    def already_tried(self, tool: str, tool_input: str) -> bool:
        """Return True if this exact (tool, input) was already executed."""
        key = (tool.lower().strip(), tool_input.strip()[:200])
        return key in self._tried

    def mark_tried(self, tool: str, tool_input: str):
        """Record that a tool was called with this input."""
        key = (tool.lower().strip(), tool_input.strip()[:200])
        self._tried.add(key)
        self._step_count += 1

    def tried_count(self) -> int:
        return len(self._tried)

    # ── Context injection ─────────────────────────────────────────────────

    def to_prompt_context(self, max_per_category: int = 5) -> str:
        """
        Build a compact context block to inject into every LLM prompt.
        Shows only non-empty categories, capped per category to avoid flooding.
        """
        lines = ["[WORKING MEMORY — facts found so far]"]
        has_content = False

        for cat in self.CATEGORIES:
            items = self._store[cat]
            if not items:
                continue
            has_content = True
            lines.append(f"\n{cat.upper()}:")
            for item in items[-max_per_category:]:   # most recent N
                conf_tag = f"[{item['confidence']}]" if item["confidence"] != "medium" else ""
                lines.append(f"  • {item['value']} {conf_tag}")

        if not has_content:
            return ""   # Don't inject empty memory block

        if self._tried:
            lines.append(f"\nALREADY TRIED: {len(self._tried)} tool calls")
            # Show last 5 tried combos
            recent = list(self._tried)[-5:]
            for tool, inp in recent:
                lines.append(f"  • {tool}({inp[:60]})")

        lines.append("\nDo NOT re-discover facts already listed above.")
        return "\n".join(lines)

    # ── Auto-extraction from tool output ─────────────────────────────────

    def extract_from_output(self, tool_name: str, output: str):
        """
        Auto-parse common patterns from tool outputs and store relevant facts.
        Called automatically by solver.py after every tool execution.
        """
        import re
        out = output[:5000]  # cap for performance

        # Credentials
        for pattern in [
            r"(?:password|passwd|pwd)[:\s=]+([^\s\n]{4,50})",
            r"(?:username|user|login)[:\s=]+(\S+).*(?:password|pass)[:\s=]+(\S+)",
            r"admin:(\S+)",
            r"root:(\S+)",
        ]:
            for m in re.finditer(pattern, out, re.IGNORECASE):
                if m.lastindex == 2:
                    self.add_credential(m.group(1), m.group(2), tool_name)
                else:
                    self.add("credentials", m.group(0)[:80], tool_name)

        # Open ports (nmap output)
        for m in re.finditer(r"(\d+)/tcp\s+open\s+(\S+)", out):
            self.add_port(int(m.group(1)), m.group(2), tool_name)

        # URLs / endpoints
        for m in re.finditer(r"(https?://[^\s\"'<>]{5,120})", out):
            url = m.group(1).rstrip(".,;)")
            self.add_endpoint(url, source=tool_name)

        # File paths
        for m in re.finditer(r"(/(?:etc|var|home|usr|tmp|opt|root|proc)/[^\s\"'<>]{3,80})", out):
            self.add_file(m.group(1), source=tool_name)

        # Hashes (MD5/SHA patterns)
        for m in re.finditer(r"\b([a-f0-9]{32})\b|\b([a-f0-9]{40})\b|\b([a-f0-9]{64})\b", out):
            h = m.group(0)
            if len(set(h)) > 4:   # skip boring repeated chars
                self.add_hash(h, source=tool_name)

        # Errors that reveal info
        for pattern in [
            r"(SQL syntax.*?near[^\n]{0,80})",
            r"(Warning: mysql[^\n]{0,80})",
            r"(Fatal error:[^\n]{0,80})",
            r"(Notice: Undefined[^\n]{0,80})",
            r"(Stack trace:[^\n]{0,80})",
        ]:
            for m in re.finditer(pattern, out, re.IGNORECASE):
                self.add_error(m.group(1), tool_name)

        # Tech stack
        for tech_pattern in [
            (r"PHP/(\S+)", "PHP"),
            (r"Apache/(\S+)", "Apache"),
            (r"nginx/(\S+)", "nginx"),
            (r"WordPress\s*([\d.]+)?", "WordPress"),
            (r"Django\s*([\d.]+)?", "Django"),
            (r"Flask\s*([\d.]+)?", "Flask"),
            (r"Node\.js\s*([\d.]+)?", "Node.js"),
        ]:
            for m in re.finditer(tech_pattern[0], out, re.IGNORECASE):
                ver = m.group(1) if m.lastindex else ""
                self.add_tech(f"{tech_pattern[1]} {ver}".strip(), tool_name)

        # Flag patterns
        import sys, os
        sys.path.insert(0, os.path.expanduser("~/jarvis"))
        try:
            from ctf.tools import find_all_flags
            for flag in find_all_flags(out):
                self.add_flag(flag, tool_name)
        except ImportError:
            pass

    # ── Summary ───────────────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            cat: [f["value"] for f in items]
            for cat, items in self._store.items()
            if items
        }

    def has_flag(self) -> str | None:
        flags = self._store.get("flags", [])
        return flags[-1]["value"] if flags else None

    def total_facts(self) -> int:
        return sum(len(v) for v in self._store.values())

    def reset(self):
        """Reset for a new challenge."""
        self.__init__()
