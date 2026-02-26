from vision_agents.core import Agent
from vision_agents.plugins import gemini, elevenlabs, getstream
import inspect

def main():
    sig = inspect.signature(Agent.__init__)
    print("Agent.__init__ parameters:", list(sig.parameters.keys()))

if __name__ == "__main__":
    main()
