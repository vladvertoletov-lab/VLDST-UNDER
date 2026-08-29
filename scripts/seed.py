import asyncio
from app.main import startup
asyncio.run(startup())
print("Database initialized and seeded.")
