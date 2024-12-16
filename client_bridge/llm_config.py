import os
from client_bridge.config import LLMConfig


def get_default_llm_config():
    """Set default LLM configuration"""
    return LLMConfig(
        azure_endpoint=os.getenv("AZURE_OPEN_AI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPEN_AI_API_VERSION"),
        api_key=os.getenv("AZURE_OPEN_AI_API_KEY"),
        deploy_name=os.getenv("AZURE_OPEN_AI_DEPLOYMENT_MODEL"),
    )
