# test_cli.py
import asyncio
from src.aetheros.cli.tool_commands import ToolCommandService

async def main():
    service = ToolCommandService()  # ✅ Create instance
    print(service.list_tools())     # ✅ Call on instance

if __name__ == "__main__":
    asyncio.run(main())