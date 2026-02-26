from vision_agents.plugins import gemini, elevenlabs
import inspect

def main():
    print("gemini.VLM signature:", inspect.signature(gemini.VLM.__init__))
    print("elevenlabs.TTS signature:", inspect.signature(elevenlabs.TTS.__init__))

if __name__ == "__main__":
    main()
