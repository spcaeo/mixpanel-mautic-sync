# ask_ai.py

import os
from enum import Enum
from dotenv import load_dotenv
import openai

load_dotenv()

class AIModel(str, Enum):
    GPT_35_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"

class AskAIClient:
    """
    Centralized class to handle calls to OpenAI, using openai.OpenAI(...) 
    and chat.completions.create(...) (compatible with openai>=1.59.x).
    """
    def __init__(self, api_key: str = None):
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables.")
        # Create an instance of openai.OpenAI with your API key
        self.client = openai.OpenAI(api_key=api_key)

    def ask_ai(
        self,
        messages: list,
        model: AIModel = AIModel.GPT_35_TURBO,
        temperature: float = 0.7,
        max_tokens: int = 100
    ) -> str:
        """
        Calls self.client.chat.completions.create(...) and returns the assistant's text.

        :param messages: A list of role-based messages, e.g.:
                         [
                           {"role": "system", "content": "..."},
                           {"role": "user", "content": "..."}
                         ]
        :param model:    The AIModel enum (GPT-3.5-turbo or GPT-4).
        :param temperature: Controls output creativity (0.0 - 1.0).
        :param max_tokens:  The maximum tokens for the assistant's reply.
        :return:         The generated text from the assistant.
        """
        response = self.client.chat.completions.create(
            model=model.value,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()