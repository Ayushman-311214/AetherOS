from __future__ import annotations

import json
from typing import Any

from ..tools.executor import ToolExecutor
from .engine import LLMEngine
from .tool_schema import get_llm_tools


class LLMToolLoop:
    """
    Main LLM ↔ ToolExecutor loop.
    """

    def __init__(
        self,
        engine: LLMEngine,
        executor: ToolExecutor,
    ) -> None:

        self._engine = engine
        self._executor = executor

    async def run(
        self,
        user_message: str,
        *,
        system_prompt: str = (
            "You are AetherOS, an autonomous "
            "computer operator."
        ),
        max_iterations: int = 10,
    ) -> str:

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        tools = get_llm_tools()

        for _ in range(max_iterations):

            response = (
                await self._engine.tool_call(
                    messages=messages,
                    tools=tools,
                )
            )

            content = response.get(
                "content",
                "",
            )

            tool_calls = response.get(
                "tool_calls",
                [],
            )

            # --------------------------------------------------
            # Normal answer
            # --------------------------------------------------

            if not tool_calls:
                return content

            # --------------------------------------------------
            # Assistant tool-call message
            # --------------------------------------------------

            assistant_tool_calls = []

            for call in tool_calls:

                assistant_tool_calls.append(
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(
                                call["arguments"]
                            ),
                        },
                    }
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": assistant_tool_calls,
                }
            )

            # --------------------------------------------------
            # Execute each requested tool
            # --------------------------------------------------

            for call in tool_calls:

                result = (
                    await self._executor.execute(
                        call["name"],
                        call["arguments"],
                    )
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(
                            result,
                            default=str,
                        ),
                    }
                )

        raise RuntimeError(
            "LLM tool-call loop exceeded "
            "maximum iteration limit."
        )