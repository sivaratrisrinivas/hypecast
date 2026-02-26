from vision_agents.plugins import elevenlabs
import inspect

def main():
    tts = elevenlabs.TTS(api_key="test")
    print("ElevenLabs TTS methods:", [m for m in dir(tts) if not m.startswith("_")])
    if hasattr(tts, "synthesize"):
        print("Synthesize signature:", inspect.signature(tts.synthesize))
    
    # Check if it has something else like 'generate' or 'speak'
    for candidate in ["generate", "generate_audio", "speak", "stream"]:
        if hasattr(tts, candidate):
            print(f"Found {candidate} signature:", inspect.signature(getattr(tts, candidate)))

if __name__ == "__main__":
    main()
