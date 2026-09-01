import asyncio

from src.aetheros.bootstrap.application import Application


async def main() -> None:
    app = Application()

    try:
        await app.start()
        await app.run()

    except asyncio.CancelledError:
        print("\nAetherOS shutdown requested.")

    finally:
        await app.stop()


if __name__ == "__main__":
    print("AetherOS Starting...")
  
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nAetherOS stopped.")