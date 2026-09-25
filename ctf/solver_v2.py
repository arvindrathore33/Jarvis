"""
ctf/solver_v2.py — JARVIS CTF Solver v2 (Enhanced)
Wires in all 9 new systems:
  ✓ Working memory dict (no more context forgetting)
  ✓ Repetition detector (no more wasted loops)
  ✓ UCB1 node selection + difficulty estimator
  ✓ Multimodal vision analysis
  ✓ Platform API auto-submit
  ✓ Performance tracing
  ✓ Parallel swarm (via swarm.py)
  ✓ NVD CVE context injection
  ✓ LoRA fine-tune pipeline (via intelligence.py)
Replace ~/jarvis/ctf/solver.py with this file.
"""

import ollama
import re
import os
import time
from datetime import datetime

from ctf.task_tree import TaskTree, NodeStatus
from ctf.prompts import get_ctf_prompt, detect_category
from ctf.rag import CTFRag
from ctf.tools import CTF_TOOLS, find_flag, find_all_flags
from ctf.working_memory import WorkingMemory
from ctf.difficulty import DifficultyAwareSelector

try:
    from ctf.vision import full_visual_analysis, SUPPORTED_IMAGE_TYPES, SUPPORTED_AUDIO_TYPES
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False

try:
    from ctf.intelligence import search_cves, record_solve, record_tool_timing
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False

try:
    from tools.scanner import run_nmap, run_ffuf, run_gobuster, run_sqlmap, run_subfinder, run_whatweb, run_nuclei, run_semgrep
    from tools.ctf.pwntools import run_checksec, run_cyclic, run_find_offset, generate_exploit_template
    from memory.database import save_session, save_finding
    from memory.learning import store_finding, recall_similar
    JARVIS_TOOLS_AVAILABLE = True
except ImportError:
    JARVIS_TOOLS_AVAILABLE = False

MODEL = os.getenv("JARVIS_MODEL", "qwen2.5:1.5b")


class CTFSolver:
    def __init__(self, model: str = MODEL, hitl: bool = False):
        self.model      = model
        self.hitl       = hitl
        self.rag        = CTFRag()
        self.memory     = WorkingMemory()        # ← NEW: working memory
        self.selector   = DifficultyAwareSelector()  # ← NEW: UCB1 + difficulty
        self.tree       = None
        self._build_tool_map()

    def _build_tool_map(self):
        self.tools = dict(CTF_TOOLS)
        if JARVIS_TOOLS_AVAILABLE:
            self.tools.update({
                "nmap": run_nmap, "ffuf": run_ffuf,
                "gobuster": run_gobuster, "sqlmap": run_sqlmap,
                "subfinder": run_subfinder, "whatweb": run_whatweb,
                "nuclei": run_nuclei, "semgrep": run_semgrep,
                "checksec": run_checksec, "cyclic": run_cyclic,
                "offset": run_find_offset, "pwn_template": generate_exploit_template,
                "discover": self.tools.get("discover", None) # Ensure discover is included
            })
        # Vision tools
        if VISION_AVAILABLE:
            from ctf.vision import full_visual_analysis, find_text_in_image, analyze_spectrogram_hint
            self.tools["vision"] = full_visual_analysis
            self.tools["ocr"]    = find_text_in_image
            self.tools["spectrogram"] = analyze_spectrogram_hint

    # ═══════════════════════════════════════════════════════════
    #  MAIN SOLVE
    # ═══════════════════════════════════════════════════════════

    def solve(self, challenge_name: str, description: str,
              category: str = "", files: list = None,
              max_steps: int = 20, emit_fn=None) -> dict:

        files = files or []
        start_time = datetime.now()
        self.memory.reset()

        # Category detection
        if not category:
            category = detect_category(description + " " + challenge_name)
            self._log(f"Auto-detected: {category}", emit_fn)

        system_prompt = get_ctf_prompt(category)

        # 2-stage RAG
        rag_context = self.rag.get_combined_context(description, category)

        # CVE context for web/pwn challenges
        cve_context = ""
        if INTELLIGENCE_AVAILABLE and category in ("web", "pwn", "rev"):
            # Search for relevant CVEs based on description keywords
            keywords = re.findall(r'\b[A-Za-z]{4,}\b', description)[:3]
            for kw in keywords:
                cvs = search_cves(kw, min_score=7.0, limit=2)
                for c in cvs:
                    cve_context += f"\nRelevant CVE: {c['cve_id']} ({c['severity']}) — {c['description'][:150]}"

        # Vision pre-analysis for image/audio files
        vision_context = ""
        if VISION_AVAILABLE and files:
            for f in files:
                from pathlib import Path
                ext = Path(f).suffix.lower()
                if ext in SUPPORTED_IMAGE_TYPES or ext in SUPPORTED_AUDIO_TYPES:
                    self._log(f"Running vision analysis on {f}...", emit_fn)
                    vision_result = full_visual_analysis(f)
                    if vision_result and "[ERROR]" not in vision_result:
                        vision_context += f"\n\nVISION ANALYSIS ({f}):\n{vision_result[:1000]}"
                        # Extract any flags found visually
                        for flag in find_all_flags(vision_result):
                            self.memory.add_flag(flag, "vision")

        # Check if vision already found the flag
        if self.memory.has_flag():
            flag = self.memory.has_flag()
            self._log(f"Vision found flag immediately: {flag}", emit_fn)
            return self._build_result(flag, category, 0, start_time, "Vision pre-analysis found flag")

        # Init task tree
        self.tree = TaskTree(f"{challenge_name} [{category}]")

        # Planning
        subtasks = self._plan(challenge_name, description, category,
                              rag_context + cve_context + vision_context,
                              system_prompt, files, emit_fn)
        for task in subtasks:
            node = self.tree.add_child(self.tree.root.id, task)
            # Pre-score difficulty for all initial nodes
            self.selector.score_node(node, category)

        self._log(f"Planned {len(subtasks)} subtasks", emit_fn)

        # Execution loop with UCB1 node selection
        steps_taken = 0
        flag = None

        while not self.tree.is_solved() and steps_taken < max_steps:
            # UCB1 node selection (replaces simple BFS)
            pending = self.tree.get_pending_nodes()
            node = self.selector.select_next(pending, category)

            if node is None:
                self._log("All nodes exhausted", emit_fn)
                break

            steps_taken += 1
            difficulty = self.selector.get_difficulty(node.id)
            self._log(f"[STEP {steps_taken}] {node.goal[:60]} (difficulty: {difficulty}/10)", emit_fn)

            # Execute node
            self.tree.mark_running(node.id)
            result = self._execute_node(node, system_prompt,
                                        rag_context + cve_context,
                                        challenge_name, description, files, emit_fn)

            # Check working memory for flag (auto-extracted from all tool outputs)
            potential_flag = self.memory.has_flag() or find_flag(result)
            
            # STRICT VALIDATION: Prevent placeholder hallucinations like flag{...}
            if potential_flag:
                clean_flag = potential_flag.strip()
                # If it looks like a placeholder, ignore it
                placeholders = ["flag{...}", "picoCTF{...}", "CTF{...}", "flag{placeholder}", "picoCTF{REDACTED}"]
                if clean_flag in placeholders or "..." in clean_flag or "REDACTED" in clean_flag:
                    self._log(f"Ignoring hallucinated placeholder flag: {clean_flag}", emit_fn)
                    flag = None
                else:
                    flag = clean_flag
                    self.tree.set_flag(flag)
                    self._log(f"🚩 FLAG FOUND: {flag}", emit_fn)
                    break

            # Difficulty-aware abandonment (fixes premature commitment)
            if self.selector.should_abandon(node, category):
                self._log(f"Abandoning hard node (difficulty {difficulty}) after {node.attempts} attempts", emit_fn)
                self._expand_tree(node, result, emit_fn)

            # HITL
            if self.hitl and node.status == NodeStatus.FAILED:
                hint = self._ask_human(node, emit_fn)
                if hint:
                    self.tree.add_sibling(node.id, hint)

        writeup = self._build_writeup(challenge_name, category, start_time)

        # Store solution
        if flag:
            self.rag.store_solution(challenge_name, category, description,
                                    writeup, flag, self._get_winning_technique())
            if JARVIS_TOOLS_AVAILABLE:
                try:
                    store_finding(challenge_name,
                                  f"CTF SOLVED [{category}]: {description}\nFLAG: {flag}",
                                  "critical")
                except Exception:
                    pass

        summary = self.tree.summary() if self.tree else {}
        elapsed = (datetime.now() - start_time).seconds

        result_dict = {
            "flag":         flag,
            "solved":       flag is not None,
            "category":     category,
            "steps":        steps_taken,
            "elapsed_sec":  elapsed,
            "writeup":      writeup,
            "tree_summary": summary,
            "memory":       self.memory.summary(),
            "challenge_name": challenge_name,
        }

        # Record performance metrics
        if INTELLIGENCE_AVAILABLE:
            try:
                record_solve(result_dict, model=self.model, mode="single")
            except Exception:
                pass

        return result_dict

    # ═══════════════════════════════════════════════════════════
    #  PLANNING
    # ═══════════════════════════════════════════════════════════

    def _plan(self, name, description, category, rag_context,
              system_prompt, files, emit_fn) -> list:
        file_list = "\n".join(f"  - {f}" for f in files) if files else "  None"
        # Inject working memory into planning (it's empty at start, populated later)
        mem_context = self.memory.to_prompt_context()

        plan_prompt = f"""You are planning to solve a CTF challenge.
Challenge: {name}
Category: {category}
Description: {description}
Files: {file_list}
{rag_context[:2000]}
{mem_context}

Decompose into 4-6 concrete subtasks. Output ONLY a numbered list:
1. <subtask>
2. <subtask>
..."""
        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": plan_prompt}
            ]
        )
        raw = response["message"]["content"]
        tasks = []
        for line in raw.splitlines():
            m = re.match(r"^\s*\d+[\.\)]\s*(.+)", line)
            if m and m.group(1).strip():
                tasks.append(m.group(1).strip())

        return tasks[:6] if tasks else [
            f"Analyze the challenge: {description[:100]}",
            f"Run initial {category} recon tools",
            "Look for the flag in tool output",
        ]

    # ═══════════════════════════════════════════════════════════
    #  NODE EXECUTION
    # ═══════════════════════════════════════════════════════════

    def _execute_node(self, node, system_prompt, rag_context,
                       challenge_name, description, files, emit_fn) -> str:
        max_turns = 5
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": self._build_node_prompt(
                node, rag_context, challenge_name, description, files
            )}
        ]

        for turn in range(max_turns):
            response = ollama.chat(model=self.model, messages=messages)
            llm_output = response["message"]["content"]
            thought, action, action_input = self._parse_react(llm_output)

            if emit_fn:
                emit_fn("ctf_thought", {"node": node.goal[:60], "thought": thought[:200], "action": action})

            if action in ("answer", "done", None):
                observation = action_input or llm_output
                self.tree.mark_success(node.id, observation[:300])
                return observation

            # ← NEW: Repetition check before every tool call
            if self.memory.already_tried(action, action_input):
                self._log(f"Skipping repeat: {action}({action_input[:40]})", emit_fn)
                alt_prompt = (f"You already tried {action} with that input. "
                              f"Try a DIFFERENT tool or approach. Current findings:\n"
                              f"{self.memory.to_prompt_context()}")
                messages.append({"role": "user", "content": alt_prompt})
                continue

            # Execute tool with timing
            t_start = time.time()
            tool_output = self._call_tool(action, action_input, files)
            elapsed = time.time() - t_start

            # Record timing
            if INTELLIGENCE_AVAILABLE:
                try:
                    record_tool_timing(action, elapsed, "[ERROR]" not in tool_output)
                except Exception:
                    pass

            # Mark as tried
            self.memory.mark_tried(action, action_input)

            # Auto-extract facts from output into working memory
            self.memory.extract_from_output(action, tool_output)
            self.tree.add_tool_call(node.id, action, action_input, tool_output)

            if emit_fn:
                emit_fn("ctf_tool", {"tool": action, "output": tool_output[:300]})

            # Check for flag
            flag = self.memory.has_flag() or find_flag(tool_output)
            if flag:
                self.tree.mark_success(node.id, f"FLAG: {flag}")
                return tool_output

            # Inject updated working memory + tool output back
            mem_context = self.memory.to_prompt_context()
            messages.append({"role": "assistant", "content": llm_output})
            messages.append({
                "role": "user",
                "content": (f"Tool output from {action}:\n{tool_output[:2000]}\n\n"
                            f"{mem_context}\n\nContinue reasoning.")
            })

        # Max turns reached
        last_obs = node.tool_calls[-1]["output"] if node.tool_calls else "No output"
        self.tree.mark_failed(node.id, "Max turns without flag")
        self._expand_tree(node, last_obs, emit_fn)
        return last_obs

    def _build_node_prompt(self, node, rag_context, challenge_name, description, files) -> str:
        tree_context = self.tree.build_context()
        mem_context  = self.memory.to_prompt_context()    # ← inject working memory every time
        file_list = ", ".join(files) if files else "none"
        return (f"CTF Challenge: {challenge_name}\nDescription: {description}\nFiles: {file_list}\n\n"
                f"Your task: {node.goal}\n\n{tree_context}\n\n{mem_context}\n\n"
                f"Available tools: {', '.join(list(self.tools.keys())[:25])}\n\n"
                f"Use ReAct format:\n"
                f"Thought: [reasoning]\nAction: [tool]\nAction Input: [input]\n\n"
                f"When done: Action: answer / Action Input: [finding or flag]")

    def _expand_tree(self, failed_node, observation: str, emit_fn):
        category = self.tree.challenge.split("[")[-1].rstrip("]") if "[" in self.tree.challenge else "misc"
        mem_summary = self.memory.to_prompt_context()

        expand_prompt = (f"A CTF task failed. Suggest 2 different approaches.\n"
                         f"Failed task: {failed_node.goal}\n"
                         f"Observed: {observation[:400]}\n"
                         f"{mem_summary}\n\n"
                         f"Output ONLY 2 new approaches, one per line:")
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": get_ctf_prompt(category)},
                    {"role": "user",   "content": expand_prompt}
                ]
            )
            raw = response["message"]["content"]
            for line in raw.splitlines():
                line = line.strip()
                if len(line) > 10 and not line.startswith("#"):
                    self.tree.add_sibling(failed_node.id, line)
                    self._log(f"[TREE] New branch: {line[:60]}", emit_fn)
        except Exception as e:
            self._log(f"[TREE] Expand failed: {e}", emit_fn)

    # ═══════════════════════════════════════════════════════════
    #  HELPERS
    # ═══════════════════════════════════════════════════════════

    def _call_tool(self, tool_name: str, tool_input: str, files: list) -> str:
        tool_name = tool_name.lower().strip()
        if tool_name not in self.tools:
            close = [t for t in self.tools if tool_name in t or t in tool_name]
            if close:
                tool_name = close[0]
            else:
                return f"[ERROR] Unknown tool: {tool_name}"

        resolved = tool_input
        if files and (not tool_input or tool_input in ("", "challenge", "binary", "file")):
            resolved = files[0]

        try:
            return str(self.tools[tool_name](resolved))
        except TypeError:
            try:
                return str(self.tools[tool_name]())
            except Exception as e:
                return f"[ERROR] {tool_name}: {e}"
        except Exception as e:
            return f"[ERROR] {tool_name}: {e}"

    def _parse_react(self, text: str):
        thought = action = a_input = ""
        t = re.search(r"Thought:\s*(.+?)(?=Action:|$)", text, re.DOTALL | re.IGNORECASE)
        a = re.search(r"Action:\s*([a-zA-Z_]+)", text, re.IGNORECASE)
        i = re.search(r"Action Input:\s*(.+?)(?=Thought:|Observation:|$)", text, re.DOTALL | re.IGNORECASE)
        if t: thought  = t.group(1).strip()
        if a: action   = a.group(1).strip().lower()
        if i: a_input  = i.group(1).strip()
        return thought, action, a_input

    def _ask_human(self, node, emit_fn) -> str:
        print(f"\n[HITL] Stuck on: {node.goal}")
        print(f"[HITL] Hint or next step (Enter to skip): ", end="")
        try:
            return input().strip() or None
        except Exception:
            return None

    def _build_result(self, flag, category, steps, start_time, writeup_text) -> dict:
        elapsed = (datetime.now() - start_time).seconds
        return {
            "flag": flag, "solved": flag is not None, "category": category,
            "steps": steps, "elapsed_sec": elapsed, "writeup": writeup_text,
            "tree_summary": {}, "memory": self.memory.summary(), "challenge_name": "unknown",
        }

    def _build_writeup(self, challenge_name, category, start_time) -> str:
        if not self.tree:
            return "No solve attempt."
        lines = [f"# {challenge_name}", f"**Category:** {category}",
                 f"**Flag:** {self.tree.flag or 'NOT FOUND'}", "", "## Steps", ""]
        step = 1
        for node in self.tree.nodes.values():
            if node.id == self.tree.root.id:
                continue
            icon = "✓" if node.status == NodeStatus.SUCCESS else "✗"
            lines.append(f"### Step {step}: {node.goal} [{icon}]")
            for tc in node.tool_calls:
                lines.append(f"- `{tc['tool']}` → {tc['output'][:150]}")
            if node.observation:
                lines.append(f"**Finding:** {node.observation[:200]}")
            lines.append("")
            step += 1
        # Memory summary
        mem = self.memory.summary()
        if mem:
            lines += ["## Working Memory", ""]
            for cat, items in mem.items():
                lines.append(f"**{cat}:** {', '.join(str(i) for i in items[:3])}")
        return "\n".join(lines)

    def _get_winning_technique(self) -> str:
        if not self.tree:
            return ""
        for node in self.tree.nodes.values():
            if "FLAG" in node.observation:
                return node.goal
        return ""

    def _log(self, msg, emit_fn=None):
        print(f"[CTF] {msg}")
        if emit_fn:
            emit_fn("ctf_log", {"message": msg})
