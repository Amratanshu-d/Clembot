import json
from app.ai.base import AIProvider
from app.config.settings import settings
from app.core.models import AgentAction, AgentPlan, ScreenContext
from app.logging.logger import logger


class OpenAIProvider(AIProvider):
    """
    OpenAI API provider for structured intent planning.
    """

    SYSTEM_PROMPT = """You are Clembot, an intelligent Windows voice assistant.
Translate spoken commands and Windows desktop context into a structured JSON plan.
Format your response as a JSON object:
{
  "reply": "Spoken reply to user",
  "actions": [
    {
      "type": "string",
      "path": "optional string",
      "destination": "optional string",
      "app": "optional string",
      "query": "optional string",
      "line_number": null,
      "instruction": "optional string"
    }
  ]
}
"""

    def is_available(self) -> bool:
        return bool(settings.openai_api_key)

    def plan(self, command: str, context: ScreenContext) -> AgentPlan:
        if not self.is_available():
            from app.ai.local_heuristic import LocalHeuristicPlanner
            return LocalHeuristicPlanner().plan(command, context)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)

            user_prompt = f"""Context:
- Active Window: {context.active_window_title} ({context.active_app})
- Explorer Path: {context.explorer_path}
- VS Code File: {context.vscode_file}

Spoken Command: {command}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            actions = [AgentAction(**a) for a in data.get("actions", [])]
            return AgentPlan(reply=data.get("reply", "Done."), actions=actions)

        except Exception as e:
            logger.warning(f"OpenAI planner error: {e}")
            from app.ai.local_heuristic import LocalHeuristicPlanner
            return LocalHeuristicPlanner().plan(command, context)
