# JARVIS MASTER STRATEGY: AUTONOMOUS CTF AGENT
## Goal: Surpass Claude Mythos in autonomous CTF/Cybersec performance.
## Hardware Profile: ASUS A15 (RTX 3050 4GB VRAM, 16GB RAM)
## Constraint: 4GB VRAM (Strict), Free APIs, Local-First Architecture.

### 1. Architectural Directive: The Reasoning Loop
- **Iteration:** Replace linear execution with an `execute_with_retry` loop.
- **Self-Correction:** After every failed tool call, trigger a "Reflection" prompt that asks the LLM: "The previous command failed with error X. Analyze why, suggest a modification, and try again."

### 2. Efficiency Architecture (4GB VRAM Optimization)
- **Model Selection:** Since VRAM is capped at 4GB, avoid heavy models. Use `Q4_K_M` quantization for:
    - **Reasoning:** `deepseek-r1:7b` (or `qwen2.5-coder:7b`) for planning.
    - **General/Speed:** `llama3.2:3b` for fast, low-vram orchestration.
- **Memory Management:** Keep ChromaDB lean. Use `OLLAMA_KEEP_ALIVE` to aggressively unload models.

### 3. The "Expert" Knowledge Base (CTF Payloads)
- **Central Repository:** Create `~/jarvis/ctf_payloads/`.
- **Payload Indexing:** Structure it by vulnerability type (e.g., `/ctf_payloads/xss/bypass_blacklist.txt`, `/ctf_payloads/crypto/lcg_solver.py`).
- **Pattern Matching:** Before querying the LLM, Jarvis should first check this local "Library" for a template that matches the challenge category.

### 4. Autonomous Pipeline (The Pipeline)
- **Phase A (Recon):** Fully automated discovery of tech stacks and open ports.
- **Phase B (Solver):** Trigger specific solver scripts (CTF helpers) stored in `/tools/` instead of asking the AI to "figure out" the code.
- **Phase C (Verification):** Autonomous check of the output against expected flag formats.

### 5. API Strategy (Free-Tier Resilience)
- **Fallback Chain:** 
    1. Groq (Llama 3 / DeepSeek via API) - Primary speed.
    2. Local Ollama - Primary privacy + offline failover.
- **Rate Limiting:** Implement a global request counter in `brain.py` to pause/log when free API limits are hit, ensuring the system doesn't fail silently.

---
*Plan saved as MASTER_STRATEGY.md. All future development will align with these pillars.*
