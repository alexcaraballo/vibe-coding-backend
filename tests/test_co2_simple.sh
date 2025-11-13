#!/bin/bash
# Simple CO₂ endpoint test
set -e

BASE_URL="http://localhost:8001/api/v1"

echo "=========================================="
echo "Testing RF-BONUS-002: CO₂ Endpoints"
echo "=========================================="
echo ""

# Register driver
echo "[1/5] Creating driver..."
curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d @- << 'REGISTER' | tee /tmp/register.json | python3 -m json.tool
{
  "email": "co2test@example.com",
  "password": "SecurePass123!",
  "name": "Test Driver",
  "role": "driver",
  "phone": "+34600000000"
}
REGISTER
echo ""

# Extract token
TOKEN=$(python3 -c "import json; data=json.load(open('/tmp/register.json')); print(data['access_token'])")
echo "Token: ${TOKEN:0:20}..."
echo ""

# Create trip with CO₂ data
echo "[2/5] Creating trip with coordinates..."
curl -s -X POST "${BASE_URL}/trips/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @- << 'TRIP' | tee /tmp/trip.json | python3 -m json.tool
{
  "origin": "Cádiz",
  "destination": "Sevilla",
  "departure_date": "2025-12-25",
  "departure_time": "10:00:00",
  "available_seats": 3,
  "price_per_seat": 8.0,
  "origin_lat": 36.5297,
  "origin_lng": -6.2926,
  "destination_lat": 37.3891,
  "destination_lng": -5.9845,
  "vehicle_type": "gasoline"
}
TRIP
echo ""

# Extract trip ID
TRIP_ID=$(python3 -c "import json; data=json.load(open('/tmp/trip.json')); print(data['id'])")
echo "Trip ID: $TRIP_ID"
echo ""

# Check CO₂ fields in trip
echo "[3/5] Verifying CO₂ fields..."
python3 << 'VERIFY'
import json
data = json.load(open('/tmp/trip.json'))
print(f"✓ Vehicle Type: {data.get('vehicle_type', 'MISSING')}")
print(f"✓ Distance KM: {data.get('distance_km', 'MISSING')}")
print(f"✓ CO₂ per passenger: {data.get('co2_saved_per_passenger_kg', 'MISSING')} kg")
print(f"✓ Total CO₂ saved: {data.get('total_co2_saved_kg', 'MISSING')} kg")
VERIFY
echo ""

# Test CO₂ impact endpoint
echo "[4/5] Testing GET /trips/${TRIP_ID}/co2-impact..."
curl -s -X GET "${BASE_URL}/trips/${TRIP_ID}/co2-impact" | python3 -m json.tool
echo ""

# Test user CO₂ stats endpoint
echo "[5/5] Testing GET /trips/users/me/co2-stats..."
curl -s -X GET "${BASE_URL}/trips/users/me/co2-stats" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "=========================================="
echo "✅ CO₂ Tests Complete!"
echo "=========================================="
