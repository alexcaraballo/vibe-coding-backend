#!/bin/bash

# Get tokens for both users
PASSENGER_TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=passenger2@example.com&password=testpass123" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

DRIVER_TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testdriver@example.com&password=testpass123" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "=========================================="
echo "=== RF-004: Listado de Reservas ===="
echo "=========================================="
echo ""

# First, let's create a new booking to test with
echo "=== Setup: Create a test booking ==="
curl -s -X POST http://localhost:8001/api/v1/trips/1/book \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $PASSENGER_TOKEN" \
  -d '{"seats_requested": 1, "passenger_notes": "Test booking for RF-004"}' | python3 -m json.tool | head -20
echo ""
echo ""

# Test 1: Get booking details with driver info
echo "=== Test 1: Get booking details (with driver info) ==="
echo "Expected: Booking details + Trip info + Driver info"
curl -s http://localhost:8001/api/v1/trips/bookings/1 \
  -H "Authorization: Bearer $PASSENGER_TOKEN" | python3 -m json.tool
echo ""
echo ""

# Test 2: List all my bookings
echo "=== Test 2: List all my bookings ==="
echo "Expected: List of all bookings with trip and driver info"
curl -s http://localhost:8001/api/v1/trips/bookings/my \
  -H "Authorization: Bearer $PASSENGER_TOKEN" | python3 -m json.tool
echo ""
echo ""

# Test 3: List my bookings with status filter
echo "=== Test 3: List my bookings (filter by confirmed status) ==="
curl -s "http://localhost:8001/api/v1/trips/bookings/my?status=confirmed" \
  -H "Authorization: Bearer $PASSENGER_TOKEN" | python3 -m json.tool
echo ""
echo ""

# Test 4: List with pagination
echo "=== Test 4: List my bookings (pagination: limit=1) ==="
curl -s "http://localhost:8001/api/v1/trips/bookings/my?limit=1" \
  -H "Authorization: Bearer $PASSENGER_TOKEN" | python3 -m json.tool
echo ""
echo ""

# Test 5: Verify driver can see their trip bookings
echo "=== Test 5: Driver views bookings for their trip ==="
echo "Expected: List of bookings for trip #1"
curl -s http://localhost:8001/api/v1/trips/1/bookings \
  -H "Authorization: Bearer $DRIVER_TOKEN" | python3 -m json.tool
echo ""
echo ""

echo "=========================================="
echo "=== RF-004 Testing Complete ==="
echo "=========================================="
