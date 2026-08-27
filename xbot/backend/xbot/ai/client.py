import asyncio
import logging
import random
from typing import Any
from openai import AsyncOpenAI
from xbot.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES_PER_MODEL = 3


class RoutingClient:
    """
    A smart facade for AsyncOpenAI that dynamically routes requests 
    to the correct API provider based on the model string prefix.
    Supports comma-separated fallback cascades (e.g. 'litellm/gemini-3.5-flash,litellm/deepseek-v4-pro,litellm/gpt-oss-120b')
    with up to 3 automated retry attempts per model with exponential jitter backoff.
    """
    def __init__(self):
        self.chat = RoutingClient.Chat()
        self.beta = RoutingClient.Beta()
        
    class Chat:
        def __init__(self):
            self.completions = RoutingClient.Completions(is_beta=False)
            
    class Beta:
        def __init__(self):
            self.chat = RoutingClient.BetaChat()
            
    class BetaChat:
        def __init__(self):
            self.completions = RoutingClient.Completions(is_beta=True)
            
    class Completions:
        def __init__(self, is_beta: bool):
            self.is_beta = is_beta
            
        def _get_provider_client(self, provider: str) -> AsyncOpenAI:
            if provider == "gemini":
                return AsyncOpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=settings.GEMINI_API_KEY, timeout=30.0, max_retries=1)
            elif provider == "mistral":
                return AsyncOpenAI(base_url="https://api.mistral.ai/v1", api_key=settings.MISTRAL_API_KEY, timeout=30.0, max_retries=1)
            elif provider == "openrouter":
                return AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.OPENROUTER_API_KEY, timeout=30.0, max_retries=1)
            elif provider == "deepseek":
                return AsyncOpenAI(base_url="https://api.deepseek.com/v1", api_key=settings.DEEPSEEK_API_KEY, timeout=30.0, max_retries=1)
            else:
                return AsyncOpenAI(base_url=settings.LITELLM_BASE_URL, api_key=settings.LITELLM_API_KEY, timeout=30.0, max_retries=1)
                
        async def create(self, model: str, **kwargs) -> Any:
            return await self._route("create", model, **kwargs)
            
        async def parse(self, model: str, **kwargs) -> Any:
            return await self._route("parse", model, **kwargs)
            
        async def _route(self, method: str, model_str: str, **kwargs) -> Any:
            models = [m.strip() for m in model_str.split(",") if m.strip()]
            if not models:
                models = [f"litellm/{settings.LITELLM_PRIMARY_MODEL}"]
                
            last_exception = None
            for idx, m in enumerate(models):
                if "/" in m:
                    provider, actual_model = m.split("/", 1)
                else:
                    provider, actual_model = "litellm", m
                    
                client = self._get_provider_client(provider)
                
                for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
                    try:
                        if method == "parse" and self.is_beta:
                            return await client.beta.chat.completions.parse(model=actual_model, **kwargs)
                        else:
                            return await client.chat.completions.create(model=actual_model, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < MAX_RETRIES_PER_MODEL:
                            backoff_sec = (0.6 * (2 ** (attempt - 1))) + random.uniform(0.1, 0.4)
                            logger.warning(
                                "AI provider '%s' model '%s' attempt %d/%d failed: %s. Retrying in %.2fs...",
                                provider, actual_model, attempt, MAX_RETRIES_PER_MODEL, e, backoff_sec
                            )
                            await asyncio.sleep(backoff_sec)
                        else:
                            logger.warning(
                                "AI provider '%s' model '%s' exhausted all %d attempts: %s. %s",
                                provider, actual_model, MAX_RETRIES_PER_MODEL, e,
                                "Trying next fallback model in cascade..." if idx < len(models) - 1 else "No more fallback models available."
                            )
            
            if last_exception:
                raise last_exception
            raise ValueError("No models available to route.")


def get_ai_client() -> Any:
    return RoutingClient()
