import asyncio
import logging
import random
import time
from typing import Any
from openai import AsyncOpenAI
from xbot.config import settings
from xbot.ai.prompt_logger import log_ai_interaction_async

logger = logging.getLogger(__name__)

MAX_RETRIES_PER_MODEL = 3


MODEL_ALIASES: dict[str, str] = {
    "gemini-flash-latest-lite": "gemini-3.1-flash-lite",
}


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
            
        def _get_provider_client(self, provider: str, timeout: float | None = None) -> Any:
            ai_timeout = timeout if timeout is not None else float(getattr(settings, "AI_REQUEST_TIMEOUT", 300.0))
            if provider == "chatgpt":
                from xbot.ai.chatgpt_adapter import ChatGPTBridgeAdapter
                return ChatGPTBridgeAdapter()
            elif provider == "gemini":
                return AsyncOpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=settings.GEMINI_API_KEY, timeout=ai_timeout, max_retries=0)
            elif provider == "mistral":
                return AsyncOpenAI(base_url="https://api.mistral.ai/v1", api_key=settings.MISTRAL_API_KEY, timeout=ai_timeout, max_retries=0)
            elif provider == "openrouter":
                return AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=settings.OPENROUTER_API_KEY, timeout=ai_timeout, max_retries=0)
            elif provider == "deepseek":
                return AsyncOpenAI(base_url="https://api.deepseek.com/v1", api_key=settings.DEEPSEEK_API_KEY, timeout=ai_timeout, max_retries=0)
            else:
                return AsyncOpenAI(base_url=settings.LITELLM_BASE_URL, api_key=settings.LITELLM_API_KEY, timeout=ai_timeout, max_retries=0)
                
        async def create(self, model: str, **kwargs) -> Any:
            return await self._route("create", model, **kwargs)
            
        async def parse(self, model: str, **kwargs) -> Any:
            return await self._route("parse", model, **kwargs)
            
        async def _route(self, method: str, model_str: str, **kwargs) -> Any:
            models = [m.strip() for m in model_str.split(",") if m.strip()]
            if not models:
                models = [f"litellm/{settings.LITELLM_PRIMARY_MODEL}"]
                
            last_exception = None
            from xbot.ai.temporal import inject_temporal_anchor_to_messages
            messages = inject_temporal_anchor_to_messages(kwargs.get("messages", []))
            kwargs["messages"] = messages
            action_type = kwargs.pop("action_type", "general")
            profile_slug = kwargs.pop("profile_slug", None)
            tier_timeout = kwargs.pop("timeout", None) or float(getattr(settings, "AI_REQUEST_TIMEOUT", 300.0))

            for idx, m in enumerate(models):
                if "/" in m:
                    provider, raw_model = m.split("/", 1)
                else:
                    provider, raw_model = "litellm", m
                    
                actual_model = MODEL_ALIASES.get(raw_model, raw_model)
                client = self._get_provider_client(provider, timeout=tier_timeout)
                
                for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
                    t0 = time.time()
                    try:
                        if method == "parse" and self.is_beta:
                            res = await client.beta.chat.completions.parse(model=actual_model, **kwargs)
                        else:
                            res = await client.chat.completions.create(model=actual_model, **kwargs)

                        latency_ms = int((time.time() - t0) * 1000)
                        resp_text = ""
                        if hasattr(res, "choices") and res.choices:
                            c = res.choices[0]
                            msg = getattr(c, "message", None)
                            if msg:
                                if getattr(msg, "content", None):
                                    resp_text = str(msg.content)
                                elif getattr(msg, "parsed", None):
                                    resp_text = str(msg.parsed)
                                elif getattr(msg, "reasoning_content", None):
                                    resp_text = str(msg.reasoning_content)
                                    msg.content = resp_text
                                elif method != "parse":
                                    raise ValueError(f"Provider '{provider}' model '{actual_model}' returned empty content (finish_reason={getattr(c, 'finish_reason', None)})")
                        elif isinstance(res, str):
                            resp_text = res

                        # Only check for upstream HTML challenge/block pages if the response is an HTML document or raw error string
                        is_html_doc = resp_text.strip().startswith("<") and any(tag in resp_text.lower() for tag in ["<html", "<!doctype", "<head", "<body"])
                        if isinstance(res, str) or is_html_doc:
                            if any(err_sig in resp_text.lower() for err_sig in ["unusual activity coming from your system", "attention required! | cloudflare", "access denied", "something went wrong. if this issue persists"]):
                                raise ValueError(f"Upstream provider error block: {resp_text[:100]}")

                        tier_label = f" (Tier {idx + 1})" if len(models) > 1 else ""
                        asyncio.create_task(
                            log_ai_interaction_async(
                                messages=messages,
                                response_text=resp_text,
                                model=f"{actual_model}{tier_label}",
                                provider=provider,
                                latency_ms=latency_ms,
                                status="success",
                                action_type=action_type,
                                profile_slug=profile_slug,
                            )
                        )
                        return res
                    except Exception as e:
                        last_exception = e
                        latency_ms = int((time.time() - t0) * 1000)
                        tier_label = f" (Tier {idx + 1})" if len(models) > 1 else ""
                        asyncio.create_task(
                            log_ai_interaction_async(
                                messages=messages,
                                response_text=None,
                                model=f"{actual_model}{tier_label}",
                                provider=provider,
                                latency_ms=latency_ms,
                                status="error",
                                action_type=action_type,
                                profile_slug=profile_slug,
                                error_message=str(e),
                            )
                        )
                        err_str = str(e).lower()
                        is_fatal = (
                            provider == "chatgpt"
                            or "upstream provider error block" in err_str
                            or "not found" in err_str
                            or "404" in err_str
                            or "410" in err_str
                            or "timeout" in err_str
                            or "timed out" in err_str
                        )
                        if is_fatal:
                            logger.warning(
                                "AI provider '%s' model '%s' failed (%s). Fast-failing to next tier in cascade.",
                                provider, actual_model, e
                            )
                            break

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
