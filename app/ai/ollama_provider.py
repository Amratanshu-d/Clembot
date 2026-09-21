import httpx
from app.ai.base import AIProvider
from app.ai.prompt_builder import prompt_builder
from app.config.settings import settings
from app.core.models import AgentPlan, ScreenContext
from app.logging.logger import logger


class OllamaProvider(AIProvider):
    """
    Local LLM planner using Ollama (e.g. Qwen, Llama).
    Communicates via localhost HTTP API.
    Uses strict schema validation with 1-retry self-correction.
    """

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{settings.ollama_host}/api/version", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def plan(self, command: str, context: ScreenContext) -> AgentPlan:
        try:
            system_instruction = prompt_builder.build_system_instruction()
            user_content = prompt_builder.build_user_prompt(command, context)

            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ]

            payload = {
                "model": settings.ollama_model,
                "messages": messages,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.3}
            }

            res = httpx.post(f"{settings.ollama_host}/api/chat", json=payload, timeout=15.0)
            if res.status_code == 200:
                raw_json = res.json().get("message", {}).get("content", "{}").strip()
                try:
                    return prompt_builder.parse_and_validate(raw_json)
                except ValueError as val_err:
                    logger.warning(f"Ollama output validation failed ({val_err}). Retrying once...")
                    retry_content = prompt_builder.build_retry_prompt(user_content, str(val_err), raw_json)
                    messages.append({"role": "assistant", "content": raw_json})
                    messages.append({"role": "user", "content": retry_content})
                    retry_payload = {
                        "model": settings.ollama_model,
                        "messages": messages,
                        "format": "json",
                        "stream": False,
                        "options": {"temperature": 0.1}
                    }
                    retry_res = httpx.post(f"{settings.ollama_host}/api/chat", json=retry_payload, timeout=15.0)
                    if retry_res.status_code == 200:
                        retry_json = retry_res.json().get("message", {}).get("content", "{}").strip()
                        return prompt_builder.parse_and_validate(retry_json)

        except Exception as e:
            logger.warning(f"Ollama plan error: {e}. Falling back to local heuristic.")

        from app.ai.local_heuristic import LocalHeuristicPlanner
        return LocalHeuristicPlanner().plan(command, context)
