"""Seed script – inserts realistic demo data for hackathon demos.

Usage (via Docker):
    make seed
    # or directly:
    docker compose run --rm backend uv run python scripts/seed.py
"""

import sys
from pathlib import Path

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal, init_db
from app.models.item import Item


def seed() -> None:
    init_db()
    db = SessionLocal()

    # Clear existing seed data
    db.query(Item).delete()
    db.commit()

    demo_items = [
        Item(
            title="🚀 Build the MVP",
            description="Core feature that wins the hackathon. Ship it first.",
        ),
        Item(
            title="🎨 Polish the UI",
            description="Make it look stunning for the demo. Judges judge by sight.",
        ),
        Item(
            title="🤖 Integrate Claude AI",
            description="Add streaming chat so the demo has a wow moment.",
        ),
        Item(
            title="📊 Load demo data",
            description="Run `make seed` to populate realistic data before the pitch.",
        ),
        Item(
            title="📝 Prepare pitch deck",
            description="Problem → Solution → Demo → Impact. 2 minutes max.",
        ),
    ]

    db.add_all(demo_items)
    db.commit()
    print(f"✅ Seeded {len(demo_items)} items into the database.")
    db.close()


if __name__ == "__main__":
    seed()
