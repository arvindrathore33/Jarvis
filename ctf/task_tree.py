"""
ctf/task_tree.py — Stateful Task Tree
CTFAgent's #1 innovation: instead of a flat linear loop, build a branching
tree of subtasks. When one path fails, branch to sibling. Never dead-ends.
Drop into ~/jarvis/ctf/task_tree.py
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional


class NodeStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCESS   = "success"
    FAILED    = "failed"
    SKIPPED   = "skipped"


class TaskNode:
    def __init__(self, goal: str, parent_id: Optional[str] = None, depth: int = 0):
        self.id         = str(uuid.uuid4())[:8]
        self.goal       = goal
        self.parent_id  = parent_id
        self.depth      = depth
        self.status     = NodeStatus.PENDING
        self.children   = []           # child TaskNode ids
        self.tool_calls = []           # list of {"tool": str, "input": str, "output": str}
        self.observation= ""           # what we learned from this node
        self.thought    = ""           # LLM reasoning for this node
        self.created_at = datetime.now().isoformat()
        self.attempts   = 0
        self.max_attempts = 3

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "status": self.status.value,
            "depth": self.depth,
            "thought": self.thought,
            "observation": self.observation,
            "tool_calls": self.tool_calls,
            "children": self.children,
            "attempts": self.attempts,
        }


class TaskTree:
    """
    Manages the branching task tree for a single CTF challenge solve attempt.
    
    Usage:
        tree = TaskTree("Get the flag from web challenge at http://chall.ctf.io:5000")
        root = tree.root
        
        # Add subtasks discovered during planning
        sub1 = tree.add_child(root.id, "Enumerate endpoints with ffuf")
        sub2 = tree.add_child(root.id, "Check for SQL injection in login form")
        
        # Mark attempts
        tree.mark_running(sub1.id)
        tree.add_tool_call(sub1.id, "ffuf", "http://...", "Found /admin, /api/users")
        tree.mark_success(sub1.id, "Found /admin panel and /api/users endpoint")
        
        # If sub2 fails, add new sibling strategy
        tree.mark_failed(sub2.id, "Login uses prepared statements, no SQLi")
        sub3 = tree.add_sibling(sub2.id, "Try default credentials admin:admin")
    """

    def __init__(self, challenge: str):
        self.root    = TaskNode(f"SOLVE: {challenge}")
        self.nodes   = {self.root.id: self.root}
        self.challenge = challenge
        self.flag    = None           # set when found
        self.created = datetime.now().isoformat()

    # ── Node management ────────────────────────────────────────────────────

    def add_child(self, parent_id: str, goal: str) -> TaskNode:
        parent = self.nodes[parent_id]
        child  = TaskNode(goal, parent_id=parent_id, depth=parent.depth + 1)
        parent.children.append(child.id)
        self.nodes[child.id] = child
        return child

    def add_sibling(self, node_id: str, goal: str) -> TaskNode:
        """Add a new approach when a node fails — same parent, new sibling."""
        node   = self.nodes[node_id]
        if node.parent_id is None:
            return self.add_child(self.root.id, goal)
        return self.add_child(node.parent_id, goal)

    # ── Status transitions ─────────────────────────────────────────────────

    def mark_running(self, node_id: str):
        node = self.nodes[node_id]
        node.status   = NodeStatus.RUNNING
        node.attempts += 1

    def mark_success(self, node_id: str, observation: str):
        node = self.nodes[node_id]
        node.status      = NodeStatus.SUCCESS
        node.observation = observation

    def mark_failed(self, node_id: str, reason: str):
        node = self.nodes[node_id]
        node.status      = NodeStatus.FAILED
        node.observation = f"FAILED: {reason}"

    def mark_skipped(self, node_id: str, reason: str = ""):
        node = self.nodes[node_id]
        node.status = NodeStatus.SKIPPED
        if reason:
            node.observation = f"SKIPPED: {reason}"

    # ── Tool call tracking ─────────────────────────────────────────────────

    def add_tool_call(self, node_id: str, tool: str, tool_input: str, tool_output: str):
        node = self.nodes[node_id]
        node.tool_calls.append({
            "tool":   tool,
            "input":  tool_input,
            "output": tool_output[:2000],   # cap to avoid context explosion
            "ts":     datetime.now().isoformat()
        })

    def set_thought(self, node_id: str, thought: str):
        self.nodes[node_id].thought = thought

    # ── Tree queries ───────────────────────────────────────────────────────

    def get_pending_nodes(self) -> list:
        return [n for n in self.nodes.values() if n.status == NodeStatus.PENDING]

    def get_next_node(self) -> Optional[TaskNode]:
        """BFS: return shallowest pending node."""
        pending = self.get_pending_nodes()
        if not pending:
            return None
        return min(pending, key=lambda n: n.depth)

    def get_failed_nodes(self) -> list:
        return [n for n in self.nodes.values() if n.status == NodeStatus.FAILED]

    def can_retry(self, node_id: str) -> bool:
        node = self.nodes[node_id]
        return node.attempts < node.max_attempts

    def is_solved(self) -> bool:
        return self.flag is not None

    def set_flag(self, flag: str):
        self.flag = flag
        self.root.status = NodeStatus.SUCCESS
        self.root.observation = f"FLAG FOUND: {flag}"

    # ── Context building for LLM ───────────────────────────────────────────

    def build_context(self, max_nodes: int = 8) -> str:
        """
        Build a compact context string for the LLM showing current tree state.
        Only includes relevant nodes — not the full tree.
        """
        lines = [f"CHALLENGE: {self.challenge}", "TASK TREE STATUS:"]

        # Show root
        root = self.root
        lines.append(f"  [ROOT] {root.goal} → {root.status.value}")

        # Show recent/active nodes
        shown = 0
        for node in list(self.nodes.values())[1:]:  # skip root
            if shown >= max_nodes:
                break
            indent = "  " + ("  " * node.depth)
            status_icon = {
                NodeStatus.PENDING: "○",
                NodeStatus.RUNNING: "►",
                NodeStatus.SUCCESS: "✓",
                NodeStatus.FAILED:  "✗",
                NodeStatus.SKIPPED: "—",
            }[node.status]
            lines.append(f"{indent}[{status_icon}] {node.goal}")
            if node.observation:
                lines.append(f"{indent}    → {node.observation[:120]}")
            shown += 1

        # Show last tool output if any running node
        for node in self.nodes.values():
            if node.status == NodeStatus.RUNNING and node.tool_calls:
                last = node.tool_calls[-1]
                lines.append(f"\nLAST TOOL: {last['tool']} → {last['output'][:500]}")
                break

        return "\n".join(lines)

    def summary(self) -> dict:
        total    = len(self.nodes)
        success  = sum(1 for n in self.nodes.values() if n.status == NodeStatus.SUCCESS)
        failed   = sum(1 for n in self.nodes.values() if n.status == NodeStatus.FAILED)
        pending  = sum(1 for n in self.nodes.values() if n.status == NodeStatus.PENDING)
        tools_run= sum(len(n.tool_calls) for n in self.nodes.values())
        return {
            "total_nodes":  total,
            "success":      success,
            "failed":       failed,
            "pending":      pending,
            "tools_run":    tools_run,
            "flag":         self.flag,
            "solved":       self.is_solved(),
        }
