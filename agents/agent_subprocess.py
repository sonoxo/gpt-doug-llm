import json
import sys

from agents import llm_backend


def main():
    payload = json.load(sys.stdin)

    result = llm_backend.chat_once(
        payload["messages"],
        payload["model"],
        payload["options"],
    )

    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
