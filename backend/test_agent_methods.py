from vision_agents.core import Agent
print("Agent methods:", [m for m in dir(Agent) if not m.startswith("_")])
