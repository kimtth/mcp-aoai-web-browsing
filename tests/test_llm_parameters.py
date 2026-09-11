"""Offline request-contract checks; these do not prove model availability."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pydantic import ValidationError

from client_bridge.config import LLMConfig
from client_bridge.llm_client import LLMClient
from client_bridge.llm_config import get_default_llm_config


class RequestParametersTests(unittest.IsolatedAsyncioTestCase):
    async def request_for(self, config):
        completion = SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content="OK", tool_calls=None),
            finish_reason="stop",
        )])
        with patch("client_bridge.llm_client.OpenAI") as standard, patch(
            "client_bridge.llm_client.AzureOpenAI"
        ) as azure:
            sdk = azure if config.azure_endpoint else standard
            sdk.return_value.chat.completions.create = Mock(return_value=completion)
            client = LLMClient(config)
            await client.invoke_with_prompt("Test request")
            sdk.return_value.chat.completions.create.assert_called_once()
            return sdk.return_value.chat.completions.create.call_args.kwargs

    async def test_names_do_not_control_parameters(self):
        for name in ("gpt-6", "arbitrary-deployment", "future-model"):
            with self.subTest(name=name):
                request = await self.request_for(LLMConfig(
                    api_key="test-only", model=name, temperature=None,
                    token_limit_parameter="max_completion_tokens", max_tokens=123,
                ))
                self.assertEqual(request["model"], name)
                self.assertEqual(request["max_completion_tokens"], 123)
                self.assertNotIn("max_tokens", request)
                self.assertNotIn("temperature", request)

    async def test_explicit_legacy_parameters_and_zero_temperature(self):
        request = await self.request_for(LLMConfig(
            api_key="test-only", model="gpt-6", temperature=0,
            token_limit_parameter="max_tokens", max_tokens=42,
        ))
        self.assertEqual(request["max_tokens"], 42)
        self.assertEqual(request["temperature"], 0)
        self.assertNotIn("max_completion_tokens", request)

    async def test_legacy_azure_defaults_and_deployment_selection(self):
        request = await self.request_for(LLMConfig(
            api_key="test-only", azure_endpoint="https://example.invalid",
            deploy_name="custom-deployment", model="not-the-deployment",
        ))
        self.assertEqual(request["model"], "custom-deployment")
        self.assertEqual(request["max_tokens"], 2000)
        self.assertEqual(request["temperature"], 0.7)

    def test_v1_defaults_and_environment_override(self):
        environment = {
            "AZURE_OPEN_AI_ENDPOINT": "https://example.invalid/openai/v1/",
            "AZURE_OPEN_AI_DEPLOYMENT_MODEL": "custom-deployment",
            "AZURE_OPENAI_AD_TOKEN": "test-only",
        }
        with patch.dict(os.environ, environment, clear=True), patch(
            "client_bridge.llm_config.load_dotenv"
        ):
            config = get_default_llm_config()
            self.assertIsNone(config.azure_endpoint)
            self.assertEqual(config.model, "custom-deployment")
            self.assertEqual(config.token_limit_parameter, "max_completion_tokens")
            self.assertIsNone(config.temperature)
            os.environ["OPENAI_TOKEN_LIMIT_PARAMETER"] = "max_tokens"
            os.environ["OPENAI_TEMPERATURE"] = "0"
            config = get_default_llm_config()
            self.assertEqual(config.token_limit_parameter, "max_tokens")
            self.assertEqual(config.temperature, 0)

    def test_unknown_parameter_is_rejected(self):
        with self.assertRaises(ValidationError):
            LLMConfig(api_key="test-only", token_limit_parameter="invented")


if __name__ == "__main__":
    unittest.main()