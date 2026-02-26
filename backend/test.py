import asyncio
import os
os.environ["GOOGLE_API_KEY"] = "fake_key"
from vision_agents.plugins.gemini.gemini_realtime import GeminiRealtime
from vision_agents.core.llm.llm import AudioLLM

async def main():
    llm = GeminiRealtime()
    print("AudioLLM?", isinstance(llm, AudioLLM))

if __name__ == "__main__":
    asyncio.run(main())
