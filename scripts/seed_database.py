"""
Database seeding script for test data.

Loads JSON fixtures from features/ directory and populates the database
with test users, trips, and bookings.

Usage:
    python scripts/seed_database.py
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, date, time as datetime_time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from passlib.context import CryptContext
from sqlalchemy import select

from config.database import async_engine, async_session_maker, Base, init_db
from apps.users.infrastructure.models import UserModel, UserRole
from apps.trips.infrastructure.models import TripModel, BookingModel, TripStatus, BookingStatus, VehicleType


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def load_json_file(filename: str) -> list:
    """Load JSON data from features directory."""
    file_path = project_root / "features" / filename
    if not file_path.exists():
        print(f"❌ Error: File {file_path} not found")
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def seed_users(session) -> dict:
    """
    Seed users from features/users.json.

    Returns:
        Dict mapping email -> user_id
    """
    print("\n📋 Loading users from features/users.json...")
    users_data = load_json_file("users.json")

    if not users_data:
        print("❌ No users data found")
        return {}

    email_to_id = {}

    for user_data in users_data:
        # Hash password
        password_hash = hash_password(user_data["password"])

        # Create user model
        user = UserModel(
            email=user_data["email"],
            password_hash=password_hash,
            name=user_data["name"],
            phone=user_data.get("phone"),
            role=UserRole(user_data["role"]),
            vehicle_model=user_data.get("vehicle_model"),
            vehicle_plate=user_data.get("vehicle_plate"),
            license_number=user_data.get("license_number"),
            is_active=True,
            is_verified=True
        )

        session.add(user)
        await session.flush()  # Get the ID before commit

        email_to_id[user.email] = user.id

        print(f"  ✅ Created user: {user.name} ({user.email}) - ID: {user.id}")

    print(f"\n✅ Created {len(users_data)} users")
    return email_to_id


async def seed_trips(session, email_to_id: dict) -> dict:
    """
    Seed trips from features/trips.json.

    Args:
        email_to_id: Mapping of driver emails to user IDs

    Returns:
        Dict mapping (origin, destination, date) -> trip_id
    """
    print("\n🚗 Loading trips from features/trips.json...")
    trips_data = load_json_file("trips.json")

    if not trips_data:
        print("❌ No trips data found")
        return {}

    trip_reference_to_id = {}

    for trip_data in trips_data:
        driver_email = trip_data["driver_email"]
        driver_id = email_to_id.get(driver_email)

        if not driver_id:
            print(f"  ⚠️  Warning: Driver email '{driver_email}' not found, skipping trip")
            continue

        # Parse date and time
        departure_date = date.fromisoformat(trip_data["departure_date"])
        departure_time = datetime_time.fromisoformat(trip_data["departure_time"])

        # Create trip model
        trip = TripModel(
            origin=trip_data["origin"],
            destination=trip_data["destination"],
            origin_lat=trip_data.get("origin_lat"),
            origin_lng=trip_data.get("origin_lng"),
            destination_lat=trip_data.get("destination_lat"),
            destination_lng=trip_data.get("destination_lng"),
            departure_date=departure_date,
            departure_time=departure_time,
            available_seats=trip_data["available_seats"],
            total_seats=trip_data["total_seats"],
            driver_id=driver_id,
            price_per_seat=trip_data["price_per_seat"],
            description=trip_data.get("description"),
            status=TripStatus(trip_data.get("status", "active")),
            max_detour_minutes=trip_data.get("max_detour_minutes", 30),
            is_active=True
        )

        session.add(trip)
        await session.flush()  # Get the ID before commit

        # Create reference key for bookings
        trip_key = (trip.origin, trip.destination, trip_data["departure_date"])
        trip_reference_to_id[trip_key] = trip.id

        print(f"  ✅ Created trip: {trip.origin} → {trip.destination} on {trip.departure_date} - ID: {trip.id}")

    print(f"\n✅ Created {len(trips_data)} trips")
    return trip_reference_to_id


async def seed_bookings(session, email_to_id: dict, trip_reference_to_id: dict):
    """
    Seed bookings from features/bookings.json.

    Args:
        email_to_id: Mapping of passenger emails to user IDs
        trip_reference_to_id: Mapping of trip references to trip IDs
    """
    print("\n🎫 Loading bookings from features/bookings.json...")
    bookings_data = load_json_file("bookings.json")

    if not bookings_data:
        print("❌ No bookings data found")
        return

    for booking_data in bookings_data:
        passenger_email = booking_data["passenger_email"]
        passenger_id = email_to_id.get(passenger_email)

        if not passenger_id:
            print(f"  ⚠️  Warning: Passenger email '{passenger_email}' not found, skipping booking")
            continue

        # Find trip by reference
        trip_ref = booking_data["trip_reference"]
        trip_key = (
            trip_ref["origin"],
            trip_ref["destination"],
            trip_ref["departure_date"]
        )
        trip_id = trip_reference_to_id.get(trip_key)

        if not trip_id:
            print(f"  ⚠️  Warning: Trip {trip_key} not found, skipping booking")
            continue

        # Create booking model
        booking = BookingModel(
            trip_id=trip_id,
            passenger_id=passenger_id,
            seats_booked=booking_data["seats_booked"],
            status=BookingStatus(booking_data.get("status", "pending")),
            pickup_location=booking_data.get("pickup_location"),
            dropoff_location=booking_data.get("dropoff_location"),
            passenger_notes=booking_data.get("passenger_notes"),
            is_active=True
        )

        session.add(booking)
        await session.flush()

        # Update trip's available seats
        result = await session.execute(select(TripModel).where(TripModel.id == trip_id))
        trip = result.scalar_one()

        if booking.status == BookingStatus.CONFIRMED:
            trip.available_seats -= booking.seats_booked

        print(f"  ✅ Created booking: Passenger {passenger_id} → Trip {trip_id} ({booking.seats_booked} seat(s)) - Status: {booking.status}")

    print(f"\n✅ Created {len(bookings_data)} bookings")


async def main():
    """Main seeding function."""
    print("=" * 60)
    print("🌱 DATABASE SEEDING SCRIPT")
    print("=" * 60)

    try:
        # Step 1: Initialize database (create tables)
        print("\n🔧 Initializing database (creating tables)...")
        await init_db()
        print("✅ Database initialized")

        # Step 2: Create async session
        async with async_session_maker() as session:
            # Step 3: Seed users
            email_to_id = await seed_users(session)

            # Step 4: Seed trips
            trip_reference_to_id = await seed_trips(session, email_to_id)

            # Step 5: Seed bookings
            await seed_bookings(session, email_to_id, trip_reference_to_id)

            # Step 6: Commit transaction
            print("\n💾 Committing transaction...")
            await session.commit()
            print("✅ Transaction committed successfully")

        # Step 7: Show summary
        print("\n" + "=" * 60)
        print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"  - Users created: {len(email_to_id)}")
        print(f"  - Trips created: {len(trip_reference_to_id)}")
        print(f"  - Bookings created: {len(load_json_file('bookings.json'))}")

        print("\n🔑 Test User Credentials:")
        print("  All users have password: Pruebas1234")
        print("\n  Drivers:")
        print("    - conductor@example.com (María García)")
        print("    - carlos@example.com (Carlos Rodríguez)")
        print("  Passenger:")
        print("    - pasajero@example.com (Ana López)")

        print("\n💡 Next steps:")
        print("  - Start the API: uvicorn main:app --reload")
        print("  - Check database: sqlite3 carpooling.db")
        print("  - View tables: .tables")
        print("  - Query data: SELECT * FROM users;")

    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Close database connections
        await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
