# # main.py
# import asyncio

# print("AetherOS Started Successfully")
# # from src.aetheros.core.application import Application
# from src.aetheros.bootstrap.application import Application


# async def main() -> None:
#     app = Application()
#     await app.start()


# if __name__ == "__main__":
#     asyncio.run(main())

# import asyncio

# from src.aetheros.bootstrap.application import Application


# async def main() -> None:
#     app = Application()

#     try:
#         await app.start()
#         await app.run()

#     except KeyboardInterrupt:
#         print("Shutdown requested.")

#     finally:
#         await app.stop()


# if __name__ == "__main__":
#     print("AetherOS Starting...")
#     asyncio.run(main())


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