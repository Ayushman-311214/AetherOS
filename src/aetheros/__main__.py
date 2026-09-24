import asyncio

from .bootstrap.application import Application




async def _main() -> None:
    app = Application()

    try:
        
        await app.start()
        
    
        await app.run()
        

    except asyncio.CancelledError:
        print("\nAetherOS shutdown requested.")

    finally:
        await app.stop()


def main() -> None:
    print("AetherOS Starting...")

    try:
        asyncio.run(_main())
        
    except KeyboardInterrupt:
        print("\nAetherOS stopped.")


if __name__ == "__main__":
    main()
