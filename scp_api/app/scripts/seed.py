import asyncio

from app.db.session import get_engine


async def run_seed() -> None:
    engine = get_engine()
    async with engine.begin():
        print("Seed stub: add data here")


def main() -> None:
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
