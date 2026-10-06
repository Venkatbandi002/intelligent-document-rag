import os
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger

router = APIRouter(prefix="/settings", tags=["Settings"])


class LLMSettingsRequest(BaseModel):
    provider: Literal["gemini", "openai", "ollama", "mock"] = Field(..., description="LLM provider name")
    gemini_api_key: Optional[str] = Field(None, description="Google Gemini API key")
    gemini_model: Optional[str] = Field("gemini-1.5-flash", description="Gemini model name")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_model: Optional[str] = Field("gpt-4o-mini", description="OpenAI model name")
    ollama_model: Optional[str] = Field("llama3", description="Ollama model name")
    ollama_base_url: Optional[str] = Field("http://localhost:11434", description="Ollama API base URL")


class LLMSettingsResponse(BaseModel):
    provider: str
    active_model: str
    has_gemini_key: bool
    has_openai_key: bool
    status: str
    message: str


@router.get("/llm", response_model=LLMSettingsResponse)
async def get_llm_settings():
    if settings.LLM_PROVIDER == "gemini":
        active_model = settings.GEMINI_MODEL
        status_str = "online" if settings.GEMINI_API_KEY else "not_configured"
    elif settings.LLM_PROVIDER == "openai":
        active_model = settings.OPENAI_MODEL
        status_str = "online" if settings.OPENAI_API_KEY else "not_configured"
    elif settings.LLM_PROVIDER == "ollama":
        active_model = settings.OLLAMA_MODEL
        status_str = "configured"
    else:
        active_model = "Grounded Extractor"
        status_str = "mock_mode"

    return LLMSettingsResponse(
        provider=settings.LLM_PROVIDER,
        active_model=active_model,
        has_gemini_key=bool(settings.GEMINI_API_KEY),
        has_openai_key=bool(settings.OPENAI_API_KEY),
        status=status_str,
        message=f"Current active provider is {settings.LLM_PROVIDER.upper()}.",
    )


@router.post("/llm", response_model=LLMSettingsResponse)
async def update_llm_settings(payload: LLMSettingsRequest):
    """
    Updates active LLM provider and credentials at runtime.
    Validates Gemini API key with a test generation call if provider is set to gemini.
    Validates Ollama endpoint connectivity if provider is set to ollama.
    """
    if payload.provider == "gemini":
        key = payload.gemini_api_key or settings.GEMINI_API_KEY
        if not key or not key.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid Google Gemini API key is required when selecting 'gemini' provider."
            )
        
        model_name = payload.gemini_model or settings.GEMINI_MODEL

        # Quick validation ping to Gemini API endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key.strip()}"
        test_payload = {
            "contents": [{"parts": [{"text": "Reply with 'OK'"}]}],
            "generationConfig": {"maxOutputTokens": 5}
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=test_payload)
                if res.status_code != 200:
                    err_msg = res.json().get("error", {}).get("message", res.text)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Gemini API verification failed ({res.status_code}): {err_msg}"
                    )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection to Gemini API failed: {str(e)}"
            )

        # Update runtime settings
        settings.LLM_PROVIDER = "gemini"
        settings.GEMINI_API_KEY = key.strip()
        settings.GEMINI_MODEL = model_name
        
        # Persist to .env for restarts
        _persist_env_key("LLM_PROVIDER", "gemini")
        _persist_env_key("GEMINI_API_KEY", key.strip())
        _persist_env_key("GEMINI_MODEL", model_name)

        logger.info(f"Switched LLM provider to Google Gemini ({model_name}).")
        return LLMSettingsResponse(
            provider="gemini",
            active_model=model_name,
            has_gemini_key=True,
            has_openai_key=bool(settings.OPENAI_API_KEY),
            status="online",
            message=f"Successfully connected to Google Gemini ({model_name})!",
        )

    elif payload.provider == "ollama":
        base_url = (payload.ollama_base_url or settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
        model_name = payload.ollama_model or settings.OLLAMA_MODEL or "llama3"

        # Check if Ollama is reachable
        is_reachable = False
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{base_url}/api/tags")
                if res.status_code == 200:
                    is_reachable = True
        except Exception:
            is_reachable = False

        settings.LLM_PROVIDER = "ollama"
        settings.OLLAMA_BASE_URL = base_url
        settings.OLLAMA_MODEL = model_name

        _persist_env_key("LLM_PROVIDER", "ollama")
        _persist_env_key("OLLAMA_BASE_URL", base_url)
        _persist_env_key("OLLAMA_MODEL", model_name)

        if is_reachable:
            logger.info(f"Connected to local Ollama ({model_name}) at {base_url}.")
            return LLMSettingsResponse(
                provider="ollama",
                active_model=model_name,
                has_gemini_key=bool(settings.GEMINI_API_KEY),
                has_openai_key=bool(settings.OPENAI_API_KEY),
                status="online",
                message=f"Connected to Ollama! Active model: {model_name} (at {base_url}).",
            )
        else:
            logger.warning(f"Switched provider to Ollama ({model_name}), but Ollama is not currently reachable at {base_url}.")
            return LLMSettingsResponse(
                provider="ollama",
                active_model=model_name,
                has_gemini_key=bool(settings.GEMINI_API_KEY),
                has_openai_key=bool(settings.OPENAI_API_KEY),
                status="configured",
                message=f"Switched to Ollama ({model_name}). Start Ollama with 'ollama run {model_name}' on your system — until then, queries will safely use the local grounded extractor fallback.",
            )

    elif payload.provider == "mock":
        settings.LLM_PROVIDER = "mock"
        _persist_env_key("LLM_PROVIDER", "mock")
        logger.info("Switched LLM provider to local mock grounded extractor.")
        return LLMSettingsResponse(
            provider="mock",
            active_model="Grounded Extractor",
            has_gemini_key=bool(settings.GEMINI_API_KEY),
            has_openai_key=bool(settings.OPENAI_API_KEY),
            status="mock_mode",
            message="Switched to local offline Grounded Extractor.",
        )

    else:
        settings.LLM_PROVIDER = payload.provider
        _persist_env_key("LLM_PROVIDER", payload.provider)
        return LLMSettingsResponse(
            provider=payload.provider,
            active_model=payload.provider,
            has_gemini_key=bool(settings.GEMINI_API_KEY),
            has_openai_key=bool(settings.OPENAI_API_KEY),
            status="configured",
            message=f"Switched provider to {payload.provider}.",
        )


def _persist_env_key(key: str, value: str):
    env_path = settings.BASE_DIR / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
