"""Shared pytest configuration and autouse fixtures for offline evaluation and unit testing."""

import pytest
import google.genai.models
from google.genai import types
from agent.observability.telemetry_sink import BigQueryTelemetrySink
from agent.guardrails.model_armor import ModelArmorGuard, model_armor_guard
from agent.config import settings


@pytest.fixture(autouse=True)
def offline_pytest_environment(monkeypatch):
    """Ensures unit test suite runs 100% offline without network retries/timeouts."""
    async def mock_async_generate(model, contents, config=None):
        return types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        parts=[
                            types.Part(
                                text="### Executive Summary for AAPL (Revenue)\nApple Inc. FY2023 10-K reported Total Net Sales of $383,285 million, down 2.8% due to macroeconomic headwinds in hardware sales."
                            )
                        ],
                        role="model",
                    )
                )
            ]
        )

    def mock_sync_generate(self, model, contents, config=None):
        return types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        parts=[
                            types.Part(
                                text="### Executive Summary for AAPL (Revenue)\nApple Inc. FY2023 10-K reported Total Net Sales of $383,285 million, down 2.8% due to macroeconomic headwinds in hardware sales."
                            )
                        ],
                        role="model",
                    )
                )
            ]
        )

    monkeypatch.setattr(google.genai.models.AsyncModels, "generate_content", lambda self, model, contents, config=None: mock_async_generate(model, contents, config))
    monkeypatch.setattr(google.genai.models.Models, "generate_content", mock_sync_generate)
    monkeypatch.setattr(BigQueryTelemetrySink, "ensure_dataset_and_table", lambda self: False)
    monkeypatch.setattr(settings, "model_armor_offline_mode", True)
    monkeypatch.setattr(model_armor_guard, "offline_mode", True)
