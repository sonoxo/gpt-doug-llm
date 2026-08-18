import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

from .tools import run_tool


@dataclass
class VoiceAssistant:
    name: str = "GPT6-Doug-Zyra-LLM"
    wake_word: str = "hey doug"
    responder: Optional[Callable[[str], str]] = None

    def speak(self, text: str) -> None:
        print("DOUG:", text)
        try:
            subprocess.run(["say", text], check=False)
        except FileNotFoundError:
            pass

    def handle(self, text: str) -> str:
        cleaned = text.strip()

        if cleaned.lower().startswith(self.wake_word):
            cleaned = cleaned[len(self.wake_word):].strip(" ,")

        if not cleaned:
            return "I'm listening."

        tool_result = run_tool(cleaned)
        if tool_result:
            return tool_result

        if self.responder:
            return self.responder(cleaned)

        return "I heard: " + cleaned

    def run(self) -> None:
        self.speak("GPT6 Doug Zyra is online.")

        while True:
            try:
                text = input("YOU: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if text.lower() in {"quit", "exit", "goodbye"}:
                self.speak("Goodbye.")
                break

            self.speak(self.handle(text))


if __name__ == "__main__":
    VoiceAssistant().run()
