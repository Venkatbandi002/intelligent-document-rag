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

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        logger.info(f"Initialized LLMService with provider '{self.provider}'.")

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

        if self.provider == "openai" and settings.OPENAI_API_KEY:
            return self._call_openai(user_prompt)
        elif self.provider == "gemini" and settings.GEMINI_API_KEY:
            return self._call_gemini(user_prompt)
        elif self.provider == "ollama":
            return self._call_ollama(user_prompt)
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

    def _call_openai(self, prompt: str) -> str:
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
            return self._call_mock_grounded_extractor(prompt, [])

    def _call_gemini(self, prompt: str) -> str:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=SYSTEM_PROMPT
            )
            response = model.generate_content(
                prompt,
                generation_config={"temperature": settings.LLM_TEMPERATURE}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini generation error: {e}. Falling back to grounded extractor.")
            return self._call_mock_grounded_extractor(prompt, [])

    def _call_ollama(self, prompt: str) -> str:
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
        return self._call_mock_grounded_extractor(prompt, [])

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
