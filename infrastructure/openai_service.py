# infrastructure/openai_service.py
import logging
import os
import sys

# This allows the script to be run directly for testing by adding the project root to the Python path.
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

from openai import AzureOpenAI, RateLimitError
from core.settings import settings

class OpenAIMessageService:
    def __init__(self):
        self.client = AzureOpenAI(
            api_version=settings.OPENAI_API_VERSION,
            azure_endpoint=settings.OPENAI_API_ENDPOINT,
            api_key=settings.OPENAI_API_KEY,
        )

    def generate_message(self, system_prompt: str, user_prompt: str) -> str:
        try:
            logging.info(f"Requesting message to OpenAI")
            response = self.client.chat.completions.create(
                model=settings.OPENAI_API_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1024,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()

        except RateLimitError:
            logging.error("Se excedió el límite de tasa de OpenAI.")
            raise ConnectionError("Se excedió el límite de tasa de OpenAI. Intente nuevamente más tarde.")
        except Exception as e:
            logging.error(f"Error al generar el mensaje de OpenAI: {str(e)}")
            raise ConnectionError("Error al generar el mensaje de OpenAI.")


if __name__ == "__main__":
    # This block will only execute when the script is run directly
    # It's useful for testing the OpenAIMessageService
    logging.basicConfig(level=logging.INFO)
    print("Running OpenAIMessageService directly for testing...")

    try:
        service = OpenAIMessageService()
        system_prompt = "You are a helpful assistant."
        user_prompt = "Hello! Can you tell me a fun fact about space?"
        message = service.generate_message(system_prompt, user_prompt)
        print("\n--- OpenAI Response ---")
        print(message)
        print("-----------------------\n")
    except Exception as e:
        print(f"An error occurred during testing: {e}")
