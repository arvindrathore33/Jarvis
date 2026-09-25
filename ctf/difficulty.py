"""
ctf/difficulty.py — Task Difficulty Estimator + UCB1 Node Selector
Fixes 16% premature commitment failures and 12% exploration-exploitation imbalance.
Drop into ~/jarvis/ctf/difficulty.py

The difficulty estimator scores each task node 1-10 before execution.
Nodes scoring >7 after 2 failed attempts get abandoned — new siblings are spawned.
UCB1 balances exploring new branches vs exploiting promising ones.
"""

import math
import ollama
import os
import re
from ctf.task_tree import TaskNode, NodeStatus


MODEL = os.getenv("JARVIS_MODEL", "deepseek-coder-v2:16b")


# ═══════════════════════════════════════════════════════════════
#  DIFFICULTY ESTIMATOR
# ═══════════════════════════════════════════════════════════════

# Heuristic difficulty keywords — instant scoring without LLM call (fast path)
HARD_KEYWORDS = [
    "heap exploitation", "kernel exploit", "zero day", "0day",
    "custom crypto", "unknown cipher", "aes cbc", "rsa 4096",
    "anticheat", "obfuscated", "vm bytecode", "pcode",
    "active directory", "kerberos", "domain controller",
    "bypass waf", "cloudflare", "perimeter x",
]

EASY_KEYWORDS = [
    "sql injection", "default credentials", "directory listing",
    "robots.txt", "source code comment", "base64 decode",
    "caesar cipher", "rot13", "strings", "exiftool", "binwalk",
    "nmap scan", "subfinder", "whatweb", "gobuster",
]


def estimate_difficulty_fast(task_goal: str, category: str = "") -> int:
    """
    Fast heuristic difficulty estimate without calling LLM.
    Returns 1-10. Used for initial tree planning.
    """
    text = (task_goal + " " + category).lower()

    # Check hard keywords
    hard_hits = sum(1 for k in HARD_KEYWORDS if k in text)
    easy_hits = sum(1 for k in EASY_KEYWORDS if k in text)

    if hard_hits >= 2:
        return 9
    elif hard_hits == 1:
        return 7
    elif easy_hits >= 2:
        return 2
    elif easy_hits == 1:
        return 3

    # Category base difficulty
    base = {
        "web":       4,
        "crypto":    5,
        "forensics": 3,
        "rev":       6,
        "pwn":       8,
        "misc":      4,
    }.get(category.lower(), 5)

    return base


def estimate_difficulty_llm(task_goal: str, category: str,
                              context: str = "", model: str = MODEL) -> int:
    """
    LLM-based difficulty estimation. More accurate, slower.
    Use only for nodes that survive the fast heuristic filter.
    Returns 1-10.
    """
    prompt = f"""Rate the difficulty of this CTF task from 1-10.
Category: {category}
Task: {task_goal}
Context (what we know so far): {context[:500] if context else 'None'}

Scoring guide:
1-3 = Trivial (run a tool, decode base64, check robots.txt)
4-5 = Moderate (standard SQLi, directory brute force, simple crypto)
6-7 = Hard (requires exploit chaining, custom scripting, deep analysis)
8-9 = Very hard (heap exploitation, novel crypto, kernel-level)
10  = Research-level (zero-day, never-seen technique)

Reply with ONLY a single integer 1-10. Nothing else."""

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0}
        )
        text = response["message"]["content"].strip()
        # Extract first integer
        m = re.search(r"\d+", text)
        if m:
            return max(1, min(10, int(m.group())))
    except Exception:
        pass

    # Fallback to fast estimate
    return estimate_difficulty_fast(task_goal, category)


class DifficultyAwareSelector:
    """
    Selects the next task node using UCB1 (Upper Confidence Bound).
    Balances:
      - Exploitation: go deeper on promising nodes
      - Exploration: try unexplored siblings
      - Difficulty: abandon nodes that are too hard after N attempts
    """

    def __init__(self, abandon_threshold: int = 7, max_attempts_hard: int = 2,
                 max_attempts_easy: int = 4):
        self.abandon_threshold  = abandon_threshold   # difficulty score above which we abandon sooner
        self.max_attempts_hard  = max_attempts_hard   # attempts before abandoning hard nodes
        self.max_attempts_easy  = max_attempts_easy   # attempts before abandoning easy nodes
        self._difficulty_cache: dict[str, int] = {}   # node_id → difficulty score
        self._ucb_scores: dict[str, float] = {}
        self._total_selections: int = 0

    def score_node(self, node: TaskNode, category: str = "",
                   use_llm: bool = False, context: str = "") -> int:
        """Score a node's difficulty and cache it."""
        if node.id in self._difficulty_cache:
            return self._difficulty_cache[node.id]

        if use_llm:
            score = estimate_difficulty_llm(node.goal, category, context)
        else:
            score = estimate_difficulty_fast(node.goal, category)

        self._difficulty_cache[node.id] = score
        return score

    def should_abandon(self, node: TaskNode, category: str = "") -> bool:
        """
        Return True if this node should be abandoned and a sibling spawned.
        """
        difficulty = self.score_node(node, category)

        if difficulty >= self.abandon_threshold:
            max_attempts = self.max_attempts_hard
        else:
            max_attempts = self.max_attempts_easy

        return node.attempts >= max_attempts and node.status == NodeStatus.FAILED

    def select_next(self, pending_nodes: list, category: str = "") -> TaskNode | None:
        """
        UCB1 node selection from pending nodes.
        Prefers:
          1. Shallow nodes (lower depth)
          2. Easy nodes (lower difficulty)
          3. Unexplored nodes (not yet attempted)
        """
        if not pending_nodes:
            return None

        if len(pending_nodes) == 1:
            return pending_nodes[0]

        self._total_selections += 1
        N = self._total_selections

        best_node = None
        best_score = float("-inf")

        for node in pending_nodes:
            difficulty = self.score_node(node, category)
            attempts   = node.attempts
            depth      = node.depth

            # UCB1 formula adapted for CTF node selection:
            # Higher score = better candidate to explore next
            #   +  Exploration bonus for unattempted nodes
            #   -  Penalty for high difficulty
            #   -  Penalty for deep nodes (prefer shallow)
            #   +  Bonus for easy tasks

            if attempts == 0:
                exploration_bonus = 2.0    # Strongly prefer unvisited
            else:
                exploration_bonus = math.sqrt(2 * math.log(N) / attempts)

            difficulty_penalty = (difficulty - 1) / 9.0 * 2.0   # 0..2
            depth_penalty      = depth * 0.3
            score = exploration_bonus - difficulty_penalty - depth_penalty

            if score > best_score:
                best_score = score
                best_node  = node

        return best_node

    def get_difficulty(self, node_id: str) -> int:
        return self._difficulty_cache.get(node_id, 5)

    def difficulty_summary(self, nodes: list) -> dict:
        """Return difficulty breakdown for all nodes."""
        return {
            node.goal[:50]: self._difficulty_cache.get(node.id, "unscored")
            for node in nodes
        }
