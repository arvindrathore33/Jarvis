# core/react_agent.py
class ReactAgent:
    def __init__(self, tools, memory, llm):
        self.tools = tools      # dict of tool_name: callable
        self.memory = memory
        self.llm = llm
        self.scratchpad = []

    def run(self, goal: str, max_steps: int = 10):
        prompt = self._build_prompt(goal)
        for step in range(max_steps):
            response = self.llm.chat(prompt)
            thought, action, action_input = self._parse(response)

            self.scratchpad.append(f"Thought: {thought}")
            if action == "FINISH":
                return action_input  # final answer

            # Execute the tool
            obs = self.tools[action](action_input)
            self.scratchpad.append(f"Observation: {obs}")
            prompt = self._rebuild_prompt(goal)  # inject observation

    def _parse(self, text):
        # Parse: Thought: ... Action: ... Action Input: ...
        ...