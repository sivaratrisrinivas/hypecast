from vision_agents.core import Agent
import inspect

def main():
    print("Agent.run_forever signature:", inspect.signature(Agent.run_forever))

if __name__ == "__main__":
    main()
