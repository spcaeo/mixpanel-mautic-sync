# test_openai.py
import os
import openai
from dotenv import load_dotenv

load_dotenv()

def main():
    # 1) Check your environment & openai version
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment variables.")
        return

    client = openai.OpenAI(api_key=api_key)
    print("OpenAI Package Version:", openai.__version__)

    # 2) Try calling client.chat.completions.create
    print("\nTEST: Trying client.chat.completions.create ...")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello from OpenAI!"}]
        )
        print("TEST SUCCESS: chat.completions.create worked.\n")
        print("Response:\n", response)
    except Exception as e:
        print("TEST FAILED with error:\n", e, "\n")

    print("\n-- Summary --")
    print("Finished testing. Check if the method succeeded or failed above.\n")

if __name__ == "__main__":
    main()