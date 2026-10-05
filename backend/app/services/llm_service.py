import os
import re
from typing import Any, Dict, List, Optional
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger

SYSTEM_PROMPT = """You are an Enterprise Document Intelligence AI assistant.
Your sole mission is to provide accurate, grounded answers based strictly on the provided context passages.

Strict Behavioral Directives:
1. Grounding: Rely ONLY on the information explicitly stated in the context passages below.
2. Hallucination Prevention: Do NOT extrapolate, speculate, or draw from outside world knowledge.
3. Unavailable Information: If the context does not contain sufficient facts to answer the question, state clearly:
   "I could not find sufficient information in the uploaded documents to answer your question."
4. Source Attribution: You MUST cite the source of every factual statement using inline brackets format:
   [Document Name, Page X]
   For example: "Employees receive 20 annual leave days. [Leave Policy.pdf, Page 4]"
5. Objective Tone: Maintain a professional, concise, and clear enterprise tone.
"""


class LLMService:
    """
    Unified LLM service supporting OpenAI, Google Gemini, local Ollama,
    and a local Grounded Extractive Mock for zero-key offline testing.
    """

    @property
    def provider(self) -> str:
        return settings.LLM_PROVIDER

    def generate_grounded_answer(
        self,
        query: str,
        context_passages: List[Dict[str, Any]]
    ) -> str:
        """
        Formats context passages, applies system prompt, and queries the configured LLM provider.
        """
        if not context_passages:
            return settings.NO_ANSWER_FALLBACK

        # Format context blocks with clear document provenance
        formatted_context = self._format_context(context_passages)

        user_prompt = f"""Context Passages:
----------------------------------------
{formatted_context}
----------------------------------------

Question: {query}

Instructions: Answer the question using ONLY the context above. Cite every factual assertion as [Document Name, Page X]. If the answer is absent, state that the information was not found.

Answer:"""

        active_provider = settings.LLM_PROVIDER
        if (active_provider == "gemini" or settings.GEMINI_API_KEY) and settings.GEMINI_API_KEY:
            return self._call_gemini(user_prompt, context_passages, query)
        elif active_provider == "openai" and settings.OPENAI_API_KEY:
            return self._call_openai(user_prompt, context_passages, query)
        elif active_provider == "ollama":
            return self._call_ollama(user_prompt, context_passages, query)
        else:
            return self._call_mock_grounded_extractor(query, context_passages)

    def _format_context(self, context_passages: List[Dict[str, Any]]) -> str:
        blocks = []
        for i, p in enumerate(context_passages, 1):
            doc = p.get("document_name", "Document")
            page = p.get("page_number", 1)
            text = p.get("content", "").strip()
            blocks.append(f"Passage [{i}] - Source: {doc}, Page {page}\nContent: {text}")
        return "\n\n".join(blocks)

    def _call_openai(self, prompt: str, passages: List[Dict[str, Any]], query: str) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}. Falling back to grounded extractor.")
            return self._call_mock_grounded_extractor(query, passages)

    def _call_gemini(self, prompt: str, passages: List[Dict[str, Any]], query: str) -> str:
        key = (settings.GEMINI_API_KEY or "").strip()
        model_name = settings.GEMINI_MODEL or "gemini-1.5-flash"
        
        # 1. Primary: Direct high-speed REST API call (no deprecated SDK dependencies)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": settings.LLM_TEMPERATURE,
                "maxOutputTokens": settings.LLM_MAX_TOKENS,
            }
        }

        try:
            with httpx.Client(timeout=35.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            answer = parts[0]["text"].strip()
                            logger.info(f"Generated response via Gemini REST API ({model_name}).")
                            return answer
                logger.warning(f"Gemini API returned status {res.status_code}: {res.text}. Trying SDK fallback...")
        except Exception as e:
            logger.warning(f"Direct Gemini REST call failed: {e}. Trying SDK fallback...")

        # 2. Secondary fallback: google.generativeai SDK
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_PROMPT
            )
            response = model.generate_content(
                prompt,
                generation_config={"temperature": settings.LLM_TEMPERATURE}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini generation error: {e}. Falling back to grounded extractor.")

        # 3. Graceful fallback to zero-hallucination local extractor
        return self._call_mock_grounded_extractor(query, passages)

    def _call_ollama(self, prompt: str, passages: List[Dict[str, Any]], query: str) -> str:
        try:
            url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
                "stream": False,
                "options": {"temperature": settings.LLM_TEMPERATURE}
            }
            with httpx.Client(timeout=60.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return res.json().get("response", "").strip()
                else:
                    logger.warning(f"Ollama API returned status {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Ollama generation error: {e}.")
        return self._call_mock_grounded_extractor(query, passages)

    def _call_mock_grounded_extractor(
        self,
        query: str,
        passages: List[Dict[str, Any]]
    ) -> str:
        """
        Deterministic, grounded extractive synthesizer.
        Extracts the most salient sentences directly matching the query and attaches citations.
        Guarantees strict zero-hallucination behavior when no API key is provided.
        """
        if not passages:
            return settings.NO_ANSWER_FALLBACK

        query_words = set(re.findall(r"\w+", query.lower())) - {
            "what", "is", "the", "are", "how", "many", "does", "do", "of", "in", "to", "for", "a", "an"
        }

        matched_sentences = []
        for p in passages:
            doc = p.get("document_name", "Document")
            page = p.get("page_number", 1)
            content = p.get("content", "")
            
            # Split into sentences
            sentences = re.split(r"(?<=[.!?]) +", content)
            for s in sentences:
                s_words = set(re.findall(r"\w+", s.lower()))
                overlap = len(query_words.intersection(s_words))
                if overlap >= max(1, len(query_words) // 2):
                    matched_sentences.append({
                        "text": s.strip(),
                        "overlap": overlap,
                        "citation": f"[{doc}, Page {page}]",
                    })

        if not matched_sentences:
            return settings.NO_ANSWER_FALLBACK

        # Sort sentences by keyword overlap descending
        matched_sentences.sort(key=lambda x: x["overlap"], reverse=True)
        top_sentences = matched_sentences[:2]
        
        # Build answer
        answer_parts = [f"{item['text']} {item['citation']}" for item in top_sentences]
        return " ".join(answer_parts)
