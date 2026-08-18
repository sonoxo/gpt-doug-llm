from datetime import datetime


def run_tool(command: str) -> str:
    text = command.lower().strip()

    if "what time is it" in text or text == "time":
        return datetime.now().strftime("It is %I:%M %p.")

    return ""
