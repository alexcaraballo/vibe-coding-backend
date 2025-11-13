"""
Database cleanup script.

Drops all tables from the database to allow for a fresh seed.

Usage:
    python scripts/clear_database.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.database import async_engine, Base


async def main():
    """Drop all tables from the database."""
    print("=" * 60)
    print("🗑️  DATABASE CLEANUP SCRIPT")
    print("=" * 60)

    response = input("\n⚠️  WARNING: This will delete ALL data from the database.\n   Are you sure you want to continue? (yes/no): ")

    if response.lower() != "yes":
        print("\n❌ Operation cancelled")
        return

    try:
        print("\n🔧 Dropping all tables...")

        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        print("✅ All tables dropped successfully")

        print("\n" + "=" * 60)
        print("✅ DATABASE CLEANUP COMPLETED!")
        print("=" * 60)

        print("\n💡 Next steps:")
        print("  - Run seed script: python scripts/seed_database.py")
        print("  - Or start fresh with: python main.py")

    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
