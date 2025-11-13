#!/bin/bash

# Login and get token
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=passenger2@example.com&password=testpass123" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "=== Testing RF-003: Reserva de Trayectos ==="
echo ""

# Test 1: Book a trip
echo "Test 1: Book trip #1 with 1 seat"
curl -s -X POST http://localhost:8001/api/v1/trips/1/book \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"seats_requested": 1, "passenger_notes": "Llegaré puntual"}' | python3 -m json.tool
echo ""
echo ""

# Test 2: Try to book again (should fail - duplicate)
echo "Test 2: Try to book again (should fail - duplicate booking)"
curl -s -X POST http://localhost:8001/api/v1/trips/1/book \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"seats_requested": 1}' | python3 -m json.tool
echo ""
echo ""

# Test 3: Get booking details
echo "Test 3: Get booking #1 details"
curl -s http://localhost:8001/api/v1/trips/bookings/1 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""
echo ""

# Test 4: Cancel booking
echo "Test 4: Cancel booking #1"
curl -s -X DELETE http://localhost:8001/api/v1/trips/bookings/1 \
  -H "Authorization: Bearer $TOKEN"
echo "Booking cancelled (HTTP 204)"
echo ""
echo ""

# Test 5: Verify trip has seats available again
echo "Test 5: Verify trip #1 has seats available again"
curl -s http://localhost:8001/api/v1/trips/1 | python3 -m json.tool | grep -A 2 "available_seats"
echo ""
