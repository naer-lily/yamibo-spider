"""AI Provider 工厂 — 根据配置动态构造 pydantic-ai Model"""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.google import GoogleProvider

from server.config import AIProviderConfig


def build_model(cfg: AIProviderConfig):
    """根据 AIProviderConfig 构造对应的 pydantic-ai Model 实例"""
    match cfg.provider:
        case "openai":
            return OpenAIChatModel(
                cfg.model,
                provider=OpenAIProvider(api_key=cfg.api_key),
            )
        case "deepseek":
            return OpenAIChatModel(
                cfg.model,
                provider=DeepSeekProvider(api_key=cfg.api_key),
            )
        case "google":
            return GoogleModel(
                cfg.model,
                provider=GoogleProvider(api_key=cfg.api_key),
            )
        case "anthropic":
            return AnthropicModel(
                cfg.model,
                provider=AnthropicProvider(api_key=cfg.api_key),
            )
        case "openai_compat":
            return OpenAIChatModel(
                cfg.model,
                provider=OpenAIProvider(
                    base_url=cfg.base_url,
                    api_key=cfg.api_key,
                ),
            )
        case _:
            raise ValueError(f"不支持的 provider: {cfg.provider}")
