"""
ctf/swarm.py — Parallel Swarm Solver
Races multiple models/strategies simultaneously — first flag wins.
Inspired by verialabs/ctf-agent that won BSidesSF 2026 with this pattern.
Drop into ~/jarvis/ctf/swarm.py

Usage:
    from ctf.swarm import SwarmSolver
    swarm = SwarmSolver()
    result = swarm.solve(
        challenge_name="Web Login",
        description="Find the flag at http://...",
        category="web"
    )
"""

import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from ctf.solver_v2 import CTFSolver


# ── Swarm configurations ─────────────────────────────────────────────────
# Each swarm member has a different model + strategy approach
# Add/remove members based on what you have installed in Ollama

SWARM_CONFIGS = [
    {
        "name":     "Qwen-Fast",
        "model":    os.getenv("JARVIS_MODEL", "qwen2.5:1.5b"),
        "strategy": "aggressive",       # tries many tools quickly
        "max_steps": 15,
    },
    {
        "name":     "Qwen-Creative",
        "model":    os.getenv("JARVIS_MODEL", "qwen2.5:1.5b"),
        "strategy": "creative",         # unconventional approaches first
        "max_steps": 12,
    },
    {
        "name":     "Qwen-Methodical",
        "model":    os.getenv("JARVIS_MODEL", "qwen2.5:1.5b"),
        "strategy": "methodical",       # follows standard methodology strictly
        "max_steps": 20,
    },
]

STRATEGY_PROMPT_ADDONS = {
    "aggressive": "\nStrategy: Move fast. Try the most likely exploit immediately. Don't do extensive recon — go straight for the vulnerability.",
    "creative":   "\nStrategy: Think unconventionally. If the obvious approach fails, try something unexpected. Look for logic flaws, misconfigurations, unintended features.",
    "methodical": "\nStrategy: Follow the standard methodology step by step. Don't skip recon. Be thorough. Document every finding before moving to exploitation.",
}


class SwarmResult:
    """Tracks the result from a single swarm member."""
    def __init__(self, member_name: str):
        self.member_name = member_name
        self.flag:   str | None = None
        self.solved: bool = False
        self.steps:  int = 0
        self.elapsed: float = 0
        self.error:  str = ""
        self.writeup: str = ""


class SwarmSolver:
    """
    Races multiple solver instances in parallel.
    First to find the flag cancels all others.
    Losing results are stored for analysis.
    """

    def __init__(self, configs: list = None, max_workers: int = 3):
        self.configs     = configs or SWARM_CONFIGS
        self.max_workers = min(max_workers, len(self.configs))
        self._winner_event = threading.Event()
        self._winner_result: SwarmResult | None = None
        self._lock = threading.Lock()
        self._all_results: list[SwarmResult] = []

    def solve(self, challenge_name: str, description: str,
              category: str = "", files: list = None,
              timeout: int = 600) -> dict:
        """
        Launch all swarm members in parallel.
        Returns as soon as any member finds the flag.
        """
        files = files or []
        self._winner_event.clear()
        self._winner_result = None
        self._all_results = []

        elapsed = 0.0
        start = time.time()
        
        # Check if local model is used (running via Ollama) and VRAM might be constrained.
        # Since local GPU capacity is typically limited to serial execution, running multiple Ollama models
        # concurrently causes extreme thrashing/slowdown or OOM. We run them sequentially instead,
        # stopping immediately if one solves the challenge.
        is_local_ollama = any("local" in str(cfg.get("model", "")).lower() or ":" in str(cfg.get("model", "")) for cfg in self.configs[:self.max_workers])
        
        if is_local_ollama:
            print("[SWARM] Constrained environment detected (Ollama local model). Running swarm members sequentially to protect VRAM...")
            for cfg in self.configs[:self.max_workers]:
                if self._winner_event.is_set():
                    break
                name = cfg["name"]
                print(f"\n[SWARM] Running swarm member sequentially: {name} ({cfg['model']})...")
                try:
                    result = self._run_member(
                        config=cfg,
                        challenge_name=challenge_name,
                        description=description,
                        category=category,
                        files=files
                    )
                    with self._lock:
                        self._all_results.append(result)
                    if result.solved:
                        with self._lock:
                            self._winner_result = result
                        self._winner_event.set()
                        print(f"\n[SWARM] 🚩 WINNER: {name} found flag in {result.steps} steps!")
                        break
                except Exception as e:
                    print(f"[SWARM] {name} sequential run failed: {e}")
        else:
            # Non-local API models (e.g. Claude, Groq, Gemini) can run in parallel safely
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(
                        self._run_member,
                        config=cfg,
                        challenge_name=challenge_name,
                        description=description,
                        category=category,
                        files=files,
                    ): cfg["name"]
                    for cfg in self.configs[:self.max_workers]
                }

                for future in as_completed(futures, timeout=timeout):
                    name = futures[future]
                    try:
                        result = future.result()
                        with self._lock:
                            self._all_results.append(result)
                        if result.solved and not self._winner_event.is_set():
                            with self._lock:
                                self._winner_result = result
                            self._winner_event.set()
                            print(f"\n[SWARM] 🚩 WINNER: {name} found flag in {result.steps} steps!")
                            for f in futures:
                                f.cancel()
                            break
                    except Exception as e:
                        print(f"[SWARM] {name} crashed: {e}")

        elapsed = time.time() - start

        # Build final result
        winner = self._winner_result
        if winner:
            return {
                "flag":         winner.flag,
                "solved":       True,
                "winner":       winner.member_name,
                "steps":        winner.steps,
                "elapsed_sec":  round(elapsed, 1),
                "writeup":      winner.writeup,
                "all_results":  self._swarm_summary(),
            }
        else:
            # No winner — return partial results
            best = self._get_best_partial()
            return {
                "flag":         None,
                "solved":       False,
                "winner":       None,
                "elapsed_sec":  round(elapsed, 1),
                "writeup":      best.writeup if best else "",
                "all_results":  self._swarm_summary(),
                "message":      "No solver found the flag. Review writeups for partial progress.",
            }

    def _run_member(self, config: dict, challenge_name: str,
                     description: str, category: str, files: list) -> SwarmResult:
        """Run a single swarm member. Called in thread."""
        result = SwarmResult(config["name"])
        start = time.time()

        try:
            # Build strategy-modified description
            strategy_addon = STRATEGY_PROMPT_ADDONS.get(config["strategy"], "")
            modified_desc = description + strategy_addon

            # Check if winner already found (early exit)
            if self._winner_event.is_set():
                result.error = "cancelled — another solver won"
                return result

            solver = CTFSolver(
                model=config["model"],
                hitl=False
            )

            solve_result = solver.solve(
                challenge_name=f"{challenge_name} [{config['name']}]",
                description=modified_desc,
                category=category,
                files=files,
                max_steps=config["max_steps"],
                emit_fn=lambda event, data: self._swarm_log(config["name"], event, data)
            )

            result.flag    = solve_result.get("flag")
            result.solved  = solve_result.get("solved", False)
            result.steps   = solve_result.get("steps", 0)
            result.writeup = solve_result.get("writeup", "")
            result.elapsed = time.time() - start

        except Exception as e:
            result.error   = str(e)
            result.elapsed = time.time() - start

        return result

    def _swarm_log(self, member_name: str, event: str, data: dict):
        """Log swarm member progress (throttled to avoid spam)."""
        if event in ("ctf_log", "ctf_thought"):
            msg = data.get("message", data.get("thought", ""))[:80]
            print(f"  [{member_name}] {msg}")

    def _swarm_summary(self) -> list:
        return [
            {
                "member":  r.member_name,
                "solved":  r.solved,
                "flag":    r.flag,
                "steps":   r.steps,
                "elapsed": round(r.elapsed, 1),
                "error":   r.error,
            }
            for r in self._all_results
        ]

    def _get_best_partial(self) -> SwarmResult | None:
        """Return the result with the most steps taken (most progress)."""
        if not self._all_results:
            return None
        return max(self._all_results, key=lambda r: r.steps)


# ── Convenience: auto-pick swarm vs single based on challenge difficulty ──

def smart_solve(challenge_name: str, description: str,
                category: str = "", files: list = None,
                difficulty_hint: str = "medium") -> dict:
    """
    Use swarm for hard/unknown challenges, single solver for easy ones.
    difficulty_hint: 'easy' | 'medium' | 'hard' | 'unknown'
    """
    files = files or []

    if difficulty_hint in ("hard", "unknown"):
        print(f"[SMART] Hard/unknown challenge → launching swarm")
        swarm = SwarmSolver()
        return swarm.solve(challenge_name, description, category, files)
    else:
        print(f"[SMART] {difficulty_hint} challenge → single solver")
        import os
        solver = CTFSolver(model=os.getenv("JARVIS_MODEL", "qwen2.5:1.5b"))
        return solver.solve(challenge_name, description, category, files)
