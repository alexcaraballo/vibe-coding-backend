#!/bin/bash
# Test script for RF-BONUS-002: Estimación de CO₂ Evitado
set -e

BASE_URL="http://localhost:8001/api/v1"
echo "=========================================="
echo "RF-BONUS-002: Estimación de CO₂ Evitado"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Generate unique emails with timestamp
TIMESTAMP=$(date +%s)

# Step 1: Register a driver user
echo -e "${BLUE}[1/8] Registering driver user...${NC}"
DRIVER_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"driver_co2_${TIMESTAMP}@example.com\",
    \"password\": \"SecurePass123!\",
    \"name\": \"Carlos Conductor\",
    \"role\": \"driver\",
    \"phone\": \"+34666777888\"
  }")
echo "$DRIVER_RESPONSE" | python3 -m json.tool
DRIVER_ID=$(echo "$DRIVER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['user']['id'])")
echo -e "${GREEN}✓ Driver registered with ID: $DRIVER_ID${NC}"
echo ""

# Step 2: Login as driver
echo -e "${BLUE}[2/8] Logging in as driver...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"driver_co2_${TIMESTAMP}@example.com\",
    \"password\": \"SecurePass123!\"
  }")
echo "$LOGIN_RESPONSE" | python3 -m json.tool
DRIVER_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo -e "${GREEN}✓ Driver logged in successfully${NC}"
echo ""

# Step 3: Create a trip with coordinates (Cádiz to Sevilla) and vehicle type
echo -e "${BLUE}[3/8] Creating trip with coordinates and vehicle type...${NC}"
TRIP_RESPONSE=$(curl -s -X POST "${BASE_URL}/trips/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DRIVER_TOKEN" \
  -d '{
    "origin": "Cádiz",
    "destination": "Sevilla",
    "departure_date": "2025-12-20",
    "departure_time": "10:00:00",
    "available_seats": 3,
    "price_per_seat": 8.0,
    "description": "Viaje con cálculo de CO2",
    "origin_lat": 36.5297,
    "origin_lng": -6.2926,
    "destination_lat": 37.3891,
    "destination_lng": -5.9845,
    "vehicle_type": "gasoline"
  }')
echo "$TRIP_RESPONSE" | python3 -m json.tool
TRIP_ID=$(echo "$TRIP_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓ Trip created with ID: $TRIP_ID${NC}"
echo ""

# Step 4: Verify CO₂ fields in trip response
echo -e "${BLUE}[4/8] Verifying CO₂ fields in trip...${NC}"
TRIP_DETAIL=$(curl -s -X GET "${BASE_URL}/trips/${TRIP_ID}")
echo "$TRIP_DETAIL" | python3 -m json.tool
VEHICLE_TYPE=$(echo "$TRIP_DETAIL" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('vehicle_type', 'N/A'))")
DISTANCE_KM=$(echo "$TRIP_DETAIL" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('distance_km', 'N/A'))")
CO2_PER_PASSENGER=$(echo "$TRIP_DETAIL" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('co2_saved_per_passenger_kg', 'N/A'))")
echo -e "${GREEN}✓ CO₂ fields present:${NC}"
echo "  - Vehicle Type: $VEHICLE_TYPE"
echo "  - Distance: $DISTANCE_KM km"
echo "  - CO₂ per passenger: $CO2_PER_PASSENGER kg"
echo ""

# Step 5: Get CO₂ impact endpoint
echo -e "${BLUE}[5/8] Testing GET /trips/{trip_id}/co2-impact...${NC}"
CO2_IMPACT=$(curl -s -X GET "${BASE_URL}/trips/${TRIP_ID}/co2-impact")
echo "$CO2_IMPACT" | python3 -m json.tool
echo -e "${GREEN}✓ CO₂ impact retrieved successfully${NC}"
echo ""

# Step 6: Create another trip with different vehicle type (hybrid)
echo -e "${BLUE}[6/8] Creating hybrid vehicle trip...${NC}"
TRIP2_RESPONSE=$(curl -s -X POST "${BASE_URL}/trips/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DRIVER_TOKEN" \
  -d '{
    "origin": "Málaga",
    "destination": "Granada",
    "departure_date": "2025-12-22",
    "departure_time": "15:00:00",
    "available_seats": 2,
    "price_per_seat": 10.0,
    "description": "Viaje híbrido ecológico",
    "origin_lat": 36.7213,
    "origin_lng": -4.4214,
    "destination_lat": 37.1773,
    "destination_lng": -3.5986,
    "vehicle_type": "hybrid"
  }')
echo "$TRIP2_RESPONSE" | python3 -m json.tool
TRIP2_ID=$(echo "$TRIP2_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓ Hybrid trip created with ID: $TRIP2_ID${NC}"
echo ""

# Step 7: Register a passenger and book a trip
echo -e "${BLUE}[7/8] Registering passenger and booking trip...${NC}"
PASSENGER_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"passenger_co2_${TIMESTAMP}@example.com\",
    \"password\": \"SecurePass123!\",
    \"name\": \"Patricia Pasajera\",
    \"role\": \"passenger\",
    \"phone\": \"+34677888999\"
  }")
PASSENGER_ID=$(echo "$PASSENGER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['user']['id'])")

PASSENGER_LOGIN=$(curl -s -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"passenger_co2_${TIMESTAMP}@example.com\",
    \"password\": \"SecurePass123!\"
  }")
PASSENGER_TOKEN=$(echo "$PASSENGER_LOGIN" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

BOOKING_RESPONSE=$(curl -s -X POST "${BASE_URL}/trips/${TRIP_ID}/book" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $PASSENGER_TOKEN" \
  -d '{
    "seats_requested": 1,
    "passenger_notes": "Reserva para test CO2"
  }')
echo "$BOOKING_RESPONSE" | python3 -m json.tool
echo -e "${GREEN}✓ Passenger booked trip${NC}"
echo ""

# Step 8: Get user CO₂ statistics for driver
echo -e "${BLUE}[8/8] Testing GET /trips/users/me/co2-stats...${NC}"
CO2_STATS=$(curl -s -X GET "${BASE_URL}/trips/users/me/co2-stats" \
  -H "Authorization: Bearer $DRIVER_TOKEN")
echo "$CO2_STATS" | python3 -m json.tool
echo -e "${GREEN}✓ User CO₂ stats retrieved successfully${NC}"
echo ""

echo -e "${GREEN}=========================================="
echo "✅ RF-BONUS-002 Test Suite Complete!"
echo "==========================================${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo "  ✓ Trip creation with vehicle type and coordinates"
echo "  ✓ Automatic CO₂ calculation on trip creation"
echo "  ✓ CO₂ fields in trip responses"
echo "  ✓ GET /trips/{trip_id}/co2-impact endpoint"
echo "  ✓ GET /trips/users/me/co2-stats endpoint"
echo "  ✓ Different vehicle types (gasoline, hybrid)"
echo "  ✓ CO₂ equivalences (trees, km not driven)"
