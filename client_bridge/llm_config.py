import os

from dotenv import load_dotenv

from client_bridge.config import LLMConfig


def get_default_llm_config():
    """Set default LLM configuration for Azure OpenAI"""
    load_dotenv()
    endpoint = os.getenv("AZURE_OPEN_AI_ENDPOINT", "").rstrip("/")
    deployment = os.getenv("AZURE_OPEN_AI_DEPLOYMENT_MODEL")
    is_v1 = endpoint.endswith("/openai/v1")
    # These are configurable request defaults, not inferred model capabilities.
    temperature = os.getenv("OPENAI_TEMPERATURE")
    generation_options = {
        "token_limit_parameter": os.getenv(
            "OPENAI_TOKEN_LIMIT_PARAMETER", "max_completion_tokens" if is_v1 else "max_tokens"
        ),
        "temperature": float(temperature) if temperature else (None if is_v1 else 0.7),
    }
    if is_v1:
        # A caller-supplied Entra token is short-lived; renew it before launching.
        return LLMConfig(
            base_url=endpoint + "/",
            api_key=os.getenv("AZURE_OPEN_AI_API_KEY") or os.getenv("AZURE_OPENAI_AD_TOKEN"),
            model=deployment,
            deploy_name=deployment,
            **generation_options,
        )
    return LLMConfig(
        azure_endpoint=endpoint or None,
        api_version=os.getenv("AZURE_OPEN_AI_API_VERSION"),
        api_key=os.getenv("AZURE_OPEN_AI_API_KEY"),
        deploy_name=deployment,
        **generation_options,
    )


def get_openai_llm_config():
    """Set default LLM configuration for standard OpenAI"""
    return LLMConfig(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL"),
    )
