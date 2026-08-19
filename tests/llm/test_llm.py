import asyncio

from src.aetheros.llm.config import LLMConfig
from src.aetheros.llm.providers.openai_compatible import (
    OpenAICompatibleProvider,
)


async def main() -> None:

    config = LLMConfig.from_env()

    provider = OpenAICompatibleProvider(
        config,
        provider_name="test",
    )

    await provider.initialize()

    print(
        "Provider:",
        provider.name,
    )

    print(
        "Model:",
        provider.model,
    )

    print(
        "Healthy:",
        await provider.health_check(),
    )

    result = await provider.generate(
        messages=[
            {
                "role": "user",
                "content": "Say hello in one sentence.",
            }
        ]
    )

    print(
        "Response:",
        result,
    )

    await provider.shutdown()


if __name__ == "__main__":
    asyncio.run(main())