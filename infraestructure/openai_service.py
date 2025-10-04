# infraestructure/openai_service.py
import logging
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
                max_tokens=120,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()

        except RateLimitError:
            logging.error("Se excedió el límite de tasa de OpenAI.")
            raise ConnectionError("Se excedió el límite de tasa de OpenAI. Intente nuevamente más tarde.")
        except Exception as e:
            logging.error(f"Error al generar el mensaje de OpenAI: {str(e)}")
            raise ConnectionError("Error al generar el mensaje de OpenAI.")
