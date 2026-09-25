"""
ctf/solver.py — JARVIS CTF Solver
The main engine: combines task tree + 2-stage RAG + specialist prompts + all tools.
Replaces the linear command loop with an autonomous branching solver.
Drop into ~/jarvis/ctf/solver.py
"""

import ollama
import re
import os
from datetime import datetime

from ctf.task_tree import TaskTree, NodeStatus
from ctf.prompts import get_ctf_prompt, detect_category, CTF_PROMPTS
from ctf.rag import CTFRag
from ctf.tools import CTF_TOOLS, find_flag, find_all_flags

# ── Also import existing JARVIS tools ───────────────────────────────────
try:
    from tools.scanner import run_nmap, run_ffuf, run_gobuster, run_sqlmap, run_subfinder, run_whatweb
    from memory.database import save_session, save_finding
    from memory.learning import store_finding, recall_similar
    JARVIS_TOOLS_AVAILABLE = True
except ImportError:
    JARVIS_TOOLS_AVAILABLE = False

MODEL = os.getenv("JARVIS_MODEL", "dolphin-mistral")


class CTFSolver:
    """
    Autonomous CTF challenge solver.
    
    Usage:
        solver = CTFSolver()
        result = solver.solve(
            challenge_name="Web Login Bypass",
            description="Login at http://chall.ctf.io:5000, find the flag",
            category="web",           # optional — auto-detected if omitted
            files=["chall.zip"],      # optional attached files
            hitl=False                # True = pause when stuck, ask human
        )
        print(result["flag"])
        print(result["writeup"])
    """

    def __init__(self, model: str = MODEL, hitl: bool = False):
        self.model  = model
        self.hitl   = hitl          # Human-in-the-loop mode
        self.rag    = CTFRag()
        self.tree   = None
        self._build_tool_map()

    def _build_tool_map(self):
        """Merge CTF tools + existing JARVIS tools into one registry."""
        self.tools = dict(CTF_TOOLS)
        if JARVIS_TOOLS_AVAILABLE:
            self.tools.update({
                "nmap":      run_nmap,
                "ffuf":      run_ffuf,
                "gobuster":  run_gobuster,
                "sqlmap":    run_sqlmap,
                "subfinder": run_subfinder,
                "whatweb":   run_whatweb,
            })

    # ═══════════════════════════════════════════════════════════
    #  MAIN SOLVE ENTRY POINT
    # ═══════════════════════════════════════════════════════════

    def solve(self, challenge_name: str, description: str,
              category: str = "", files: list = None,
              max_steps: int = 20, emit_fn=None) -> dict:
        """
        Solve a CTF challenge autonomously.
        Returns dict with: flag, category, steps, writeup, tree_summary
        """
        files = files or []
        start_time = datetime.now()

        # Step 1: Detect category if not provided
        if not category:
            category = detect_category(description + " " + challenge_name)
            self._log(f"Auto-detected category: {category}", emit_fn)

        # Step 2: Get specialist system prompt
        system_prompt = get_ctf_prompt(category)

        # Step 3: Two-stage RAG
        rag_context = self.rag.get_combined_context(description, category)
        self._log(f"RAG context loaded ({len(rag_context)} chars)", emit_fn)

        # Step 4: Initialize task tree
        self.tree = TaskTree(f"{challenge_name} [{category}]")

        # Step 5: Planning phase — LLM decomposes into subtasks
        subtasks = self._plan(
            challenge_name, description, category,
            rag_context, system_prompt, files, emit_fn
        )
        for task in subtasks:
            self.tree.add_child(self.tree.root.id, task)

        self._log(f"Planned {len(subtasks)} initial subtasks", emit_fn)

        # Step 6: Execution loop
        steps_taken = 0
        flag = None

        while not self.tree.is_solved() and steps_taken < max_steps:
            node = self.tree.get_next_node()
            if node is None:
                self._log("No more pending nodes — all paths exhausted", emit_fn)
                break

            steps_taken += 1
            self._log(f"\n[STEP {steps_taken}] Node: {node.goal}", emit_fn)

            # Run the node
            self.tree.mark_running(node.id)
            result = self._execute_node(
                node, system_prompt, rag_context,
                challenge_name, description, files, emit_fn
            )

            # Check for flag in result
            flag = find_flag(result)
            if flag:
                self.tree.set_flag(flag)
                self._log(f"\n🚩 FLAG FOUND: {flag}", emit_fn)
                break

            # Handle HITL mode — pause when stuck
            if self.hitl and node.status == NodeStatus.FAILED:
                hint = self._ask_human(node, emit_fn)
                if hint:
                    new_node = self.tree.add_sibling(node.id, hint)
                    self._log(f"[HITL] Added human hint as new task: {hint}", emit_fn)

        # Step 7: Build writeup
        writeup = self._build_writeup(challenge_name, category, start_time)

        # Step 8: Store solution in RAG if solved
        if flag and self.tree:
            self.rag.store_solution(
                challenge_name=challenge_name,
                category=category,
                description=description,
                solution_steps=writeup,
                flag=flag,
                technique=self._get_winning_technique()
            )
            # Also store in existing JARVIS memory
            if JARVIS_TOOLS_AVAILABLE:
                try:
                    store_finding(challenge_name,
                                  f"CTF SOLVED [{category}]: {description}\nFLAG: {flag}",
                                  "critical")
                except Exception:
                    pass

        summary = self.tree.summary() if self.tree else {}
        elapsed = (datetime.now() - start_time).seconds

        return {
            "flag":         flag,
            "solved":       flag is not None,
            "category":     category,
            "steps":        steps_taken,
            "elapsed_sec":  elapsed,
            "writeup":      writeup,
            "tree_summary": summary,
        }

    # ═══════════════════════════════════════════════════════════
    #  PLANNING
    # ═══════════════════════════════════════════════════════════

    def _plan(self, name, description, category, rag_context,
              system_prompt, files, emit_fn) -> list:
        """Ask LLM to decompose challenge into ordered subtasks."""
        file_list = "\n".join(f"  - {f}" for f in files) if files else "  None"
        plan_prompt = f"""You are planning how to solve a CTF challenge.

Challenge: {name}
Category: {category}
Description: {description}
Attached files:
{file_list}

{rag_context}

Decompose this challenge into 3-6 concrete subtasks.
Each subtask should be one specific action (run a tool, analyze output, try an exploit).
Output ONLY a numbered list, one subtask per line:
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

        # Parse numbered list
        tasks = []
        for line in raw.splitlines():
            match = re.match(r"^\s*\d+[\.\)]\s*(.+)", line)
            if match:
                task = match.group(1).strip()
                if task:
                    tasks.append(task)

        # Fallback if parsing fails
        if not tasks:
            tasks = [
                f"Analyze the challenge: {description}",
                f"Run initial reconnaissance tools for {category}",
                "Look for the flag in tool output"
            ]

        return tasks[:6]  # cap at 6 initial tasks

    # ═══════════════════════════════════════════════════════════
    #  NODE EXECUTION
    # ═══════════════════════════════════════════════════════════

    def _execute_node(self, node, system_prompt, rag_context,
                       challenge_name, description, files, emit_fn) -> str:
        """
        Execute a single task node using ReAct: Thought → Action → Observation.
        Returns the final observation string.
        """
        max_turns = 5   # max tool calls per node
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._build_node_prompt(
                node, rag_context, challenge_name, description, files
            )}
        ]

        for turn in range(max_turns):
            response = ollama.chat(model=self.model, messages=messages)
            llm_output = response["message"]["content"]
            self.tree.set_thought(node.id, llm_output[:300])

            # Parse Thought / Action / Action Input
            thought, action, action_input = self._parse_react(llm_output)

            if emit_fn:
                emit_fn("ctf_thought", {
                    "node": node.goal[:60],
                    "thought": thought[:200],
                    "action": action
                })

            # Terminal: ANSWER or no action found
            if action in ("answer", "done", None):
                observation = action_input or llm_output
                self.tree.mark_success(node.id, observation[:300])
                return observation

            # Execute tool
            tool_output = self._call_tool(action, action_input, files)
            self.tree.add_tool_call(node.id, action, action_input, tool_output)

            if emit_fn:
                emit_fn("ctf_tool", {
                    "tool": action,
                    "output": tool_output[:300]
                })

            # Check for flag immediately
            flag = find_flag(tool_output)
            if flag:
                self.tree.mark_success(node.id, f"FLAG: {flag}")
                return tool_output

            # Feed observation back
            messages.append({"role": "assistant", "content": llm_output})
            messages.append({
                "role": "user",
                "content": f"Tool output from {action}:\n{tool_output[:3000]}\n\nContinue."
            })

        # Max turns reached for this node
        last_obs = node.tool_calls[-1]["output"] if node.tool_calls else "No output"
        self.tree.mark_failed(node.id, "Max turns reached without finding flag")

        # Add new sibling strategies based on what we learned
        self._expand_tree(node, last_obs, emit_fn)
        return last_obs

    def _build_node_prompt(self, node, rag_context, challenge_name,
                            description, files) -> str:
        """Build prompt for executing a specific task node."""
        tree_context = self.tree.build_context()
        file_list = ", ".join(files) if files else "none"
        return f"""CTF Challenge: {challenge_name}
Description: {description}
Files: {file_list}

Your current task: {node.goal}

{tree_context}

Available tools: {', '.join(list(self.tools.keys())[:20])}

Use ReAct format:
Thought: [what you know and what to do]
Action: [tool name]
Action Input: [target/file/value for the tool]

When you find the flag or complete the task:
Thought: [what you found]
Action: answer
Action Input: [your finding / the flag]"""

    def _expand_tree(self, failed_node, observation: str, emit_fn):
        """When a node fails, add new sibling strategies based on what we learned."""
        category = self.tree.challenge.split("[")[-1].rstrip("]") if "[" in self.tree.challenge else "misc"

        expand_prompt = f"""A CTF approach failed. Based on what we learned, suggest 2 alternative approaches.

Failed task: {failed_node.goal}
What we observed: {observation[:500]}

Output ONLY 2 new approaches, one per line (no numbering, no explanation):"""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": get_ctf_prompt(category)},
                    {"role": "user",   "content": expand_prompt}
                ]
            )
            raw = response["message"]["content"]
            new_tasks = [line.strip() for line in raw.splitlines()
                         if line.strip() and not line.strip().startswith("#")][:2]
            for task in new_tasks:
                if len(task) > 10:
                    new_node = self.tree.add_sibling(failed_node.id, task)
                    self._log(f"[TREE] Added fallback: {task}", emit_fn)
        except Exception as e:
            self._log(f"[TREE] Expand failed: {e}", emit_fn)

    # ═══════════════════════════════════════════════════════════
    #  TOOL DISPATCH
    # ═══════════════════════════════════════════════════════════

    def _call_tool(self, tool_name: str, tool_input: str, files: list) -> str:
        """Dispatch tool call, resolve file paths automatically."""
        tool_name = tool_name.lower().strip()
        if tool_name not in self.tools:
            # Fuzzy match
            close = [t for t in self.tools if tool_name in t or t in tool_name]
            if close:
                tool_name = close[0]
                self._log(f"[TOOL] Fuzzy matched '{tool_name}'")
            else:
                return f"[ERROR] Unknown tool: {tool_name}. Available: {list(self.tools.keys())}"

        # Resolve file input — use attached challenge files if input looks like a filename
        resolved_input = tool_input
        if files and (not tool_input or tool_input in ("", "challenge", "binary", "file")):
            resolved_input = files[0]  # default to first attached file

        try:
            return str(self.tools[tool_name](resolved_input))
        except TypeError:
            # Some tools take no args
            try:
                return str(self.tools[tool_name]())
            except Exception as e:
                return f"[ERROR] Tool {tool_name} failed: {e}"
        except Exception as e:
            return f"[ERROR] Tool {tool_name} failed: {e}"

    # ═══════════════════════════════════════════════════════════
    #  REACT PARSER
    # ═══════════════════════════════════════════════════════════

    def _parse_react(self, text: str):
        thought = ""
        action  = None
        a_input = ""

        t_match = re.search(r"Thought:\s*(.+?)(?=Action:|$)", text, re.DOTALL | re.IGNORECASE)
        a_match = re.search(r"Action:\s*([a-zA-Z_]+)", text, re.IGNORECASE)
        i_match = re.search(r"Action Input:\s*(.+?)(?=Thought:|Observation:|$)",
                            text, re.DOTALL | re.IGNORECASE)

        if t_match: thought  = t_match.group(1).strip()
        if a_match: action   = a_match.group(1).strip().lower()
        if i_match: a_input  = i_match.group(1).strip()

        return thought, action, a_input

    # ═══════════════════════════════════════════════════════════
    #  HITL MODE
    # ═══════════════════════════════════════════════════════════

    def _ask_human(self, node, emit_fn) -> str:
        """Pause and ask human for guidance (HITL mode)."""
        print(f"\n[JARVIS HITL] Stuck on: {node.goal}")
        print(f"[JARVIS HITL] Last observation: {node.observation[:200]}")
        print(f"[JARVIS HITL] Enter hint or next approach (or press Enter to skip): ", end="")
        try:
            hint = input().strip()
            return hint if hint else None
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════════
    #  WRITEUP GENERATION
    # ═══════════════════════════════════════════════════════════

    def _build_writeup(self, challenge_name: str, category: str,
                        start_time: datetime) -> str:
        """Generate a structured writeup from the task tree."""
        if not self.tree:
            return "No solve attempt recorded."

        lines = [
            f"# CTF Writeup: {challenge_name}",
            f"**Category:** {category}",
            f"**Date:** {start_time.strftime('%Y-%m-%d %H:%M')}",
            f"**Flag:** {self.tree.flag or 'NOT FOUND'}",
            "",
            "## Approach",
            ""
        ]

        step = 1
        for node in self.tree.nodes.values():
            if node.id == self.tree.root.id:
                continue
            status_icon = "✓" if node.status == NodeStatus.SUCCESS else "✗"
            lines.append(f"### Step {step}: {node.goal} [{status_icon}]")
            if node.tool_calls:
                for tc in node.tool_calls:
                    lines.append(f"- Tool: `{tc['tool']}` → `{tc['input']}`")
                    lines.append(f"  Output: {tc['output'][:200]}")
            if node.observation:
                lines.append(f"**Finding:** {node.observation[:300]}")
            lines.append("")
            step += 1

        summary = self.tree.summary()
        lines += [
            "## Summary",
            f"- Nodes explored: {summary['total_nodes']}",
            f"- Tools run: {summary['tools_run']}",
            f"- Solved: {'Yes' if summary['solved'] else 'No'}",
        ]

        return "\n".join(lines)

    def _get_winning_technique(self) -> str:
        """Extract the technique from the node that found the flag."""
        if not self.tree:
            return ""
        for node in self.tree.nodes.values():
            if "FLAG" in node.observation:
                return node.goal
        return ""

    def _log(self, message: str, emit_fn=None):
        print(f"[CTF] {message}")
        if emit_fn:
            emit_fn("ctf_log", {"message": message})
