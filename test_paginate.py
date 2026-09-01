import asyncio
from app.database.connection import init_db
from app.models.user import User
from app.repositories.base import BaseRepository

async def test():
    await init_db()
    repo = BaseRepository(User)
    items, total = await repo.paginate(filters={"role": "therapist"})
    print(f"Total therapists: {total}")
    
    items_all, total_all = await repo.paginate()
    print(f"Total all: {total_all}")

if __name__ == "__main__":
    asyncio.run(test())
