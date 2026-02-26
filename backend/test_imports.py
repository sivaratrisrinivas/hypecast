import asyncio
import os
from vision_agents.plugins import gemini, elevenlabs, getstream
from vision_agents.core import Agent

def main():
    print("gemini has VLM?", hasattr(gemini, "VLM"))
    print("elevenlabs has TTS?", hasattr(elevenlabs, "TTS"))
    print("Agent has tts attr?", hasattr(Agent, "tts"))

if __name__ == "__main__":
    main()
