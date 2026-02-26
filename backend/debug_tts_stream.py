import asyncio
from vision_agents.plugins import elevenlabs
import inspect

async def main():
    tts = elevenlabs.TTS(api_key="test")
    if hasattr(tts, "stream_audio"):
        print("stream_audio signature:", inspect.signature(tts.stream_audio))

if __name__ == "__main__":
    asyncio.run(main())
