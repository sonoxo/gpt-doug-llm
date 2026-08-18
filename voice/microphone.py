import speech_recognition as sr

from .assistant import VoiceAssistant


def listen_once(recognizer: sr.Recognizer, microphone: sr.Microphone) -> str:
    with microphone as source:
        print("LISTENING...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)

    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as exc:
        return f"ERROR:{exc}"


def run_microphone() -> None:
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    doug = VoiceAssistant()

    doug.speak("GPT Doug microphone is online.")

    while True:
        try:
            text = listen_once(recognizer, microphone)
        except sr.WaitTimeoutError:
            continue
        except KeyboardInterrupt:
            break

        if not text:
            continue

        if text.startswith("ERROR:"):
            print(text)
            continue

        print("YOU:", text)

        if text.lower() in {"goodbye", "exit", "quit"}:
            doug.speak("Goodbye.")
            break

        if not text.lower().startswith("hey doug"):
            continue

        doug.speak(doug.handle(text))


if __name__ == "__main__":
    run_microphone()
