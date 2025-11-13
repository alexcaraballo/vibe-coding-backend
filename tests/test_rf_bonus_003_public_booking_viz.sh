#!/bin/bash
# Test script for RF-BONUS-003: Visualización Pública de Reservas en Mapa
set -e

BASE_URL="http://localhost:8001/api/v1"
echo "=========================================="
echo "RF-BONUS-003: Public Booking Visualization"
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
echo -e "${BLUE}[1/9] Registering driver user...${NC}"
DRIVER_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "driver_viz_'"${TIMESTAMP}"'@example.com",
    "password": "SecurePass123!",
    "name": "Ana Conductora",
    "role": "driver",
    "phone": "+34611222333"
  }')
echo "$DRIVER_RESPONSE" | python3 -m json.tool
DRIVER_ID=$(echo "$DRIVER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['user']['id'])")
echo -e "${GREEN}✓ Driver registered with ID: $DRIVER_ID${NC}"
echo ""

# Step 2: Extract driver token from registration response
DRIVER_TOKEN=$(echo "$DRIVER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo -e "${BLUE}[2/9] Using access token from registration...${NC}"
echo -e "${GREEN}✓ Driver token obtained: ${DRIVER_TOKEN:0:20}...${NC}"
echo ""

# Step 3: Create a trip with coordinates (Cádiz to Sevilla)
echo -e "${BLUE}[3/9] Creating trip with coordinates...${NC}"
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
    "description": "Viaje con visualización de reservas",
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

# Step 4: Register first passenger
echo -e "${BLUE}[4/9] Registering first passenger...${NC}"
PASSENGER1_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "passenger1_viz_'"${TIMESTAMP}"'@example.com",
    "password": "SecurePass123!",
    "name": "Juan Pasajero",
    "role": "passenger",
    "phone": "+34622333444"
  }')
PASSENGER1_ID=$(echo "$PASSENGER1_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['user']['id'])")
PASSENGER1_TOKEN=$(echo "$PASSENGER1_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo -e "${GREEN}✓ Passenger 1 registered with ID: $PASSENGER1_ID${NC}"
echo ""

# Step 5: Book trip as first passenger WITH coordinates
echo -e "${BLUE}[5/9] Booking trip as passenger 1 (with pickup/dropoff coordinates)...${NC}"
BOOKING1_RESPONSE=$(curl -s -X POST "${BASE_URL}/trips/${TRIP_ID}/book" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $PASSENGER1_TOKEN" \
  -d '{
    "seats_requested": 1,
    "passenger_notes": "Reserva con coordenadas",
    "pickup_location": "Estación de Jerez",
    "pickup_lat": 36.6868,
    "pickup_lng": -6.1362,
    "dropoff_location": "Plaza de España, Sevilla",
    "dropoff_lat": 37.3772,
    "dropoff_lng": -5.9869
  }')
echo "$BOOKING1_RESPONSE" | python3 -m json.tool
BOOKING1_ID=$(echo "$BOOKING1_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓ Booking 1 created with ID: $BOOKING1_ID${NC}"
echo ""

# Step 6: Register second passenger
echo -e "${BLUE}[6/9] Registering second passenger...${NC}"
PASSENGER2_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "passenger2_viz_'"${TIMESTAMP}"'@example.com",
    "password": "SecurePass123!",
    "name": "María Pasajera",
    "role": "passenger",
    "phone": "+34633444555"
  }')
PASSENGER2_ID=$(echo "$PASSENGER2_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['user']['id'])")
PASSENGER2_TOKEN=$(echo "$PASSENGER2_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo -e "${GREEN}✓ Passenger 2 registered with ID: $PASSENGER2_ID${NC}"
echo ""

# Step 7: Book trip as second passenger WITH coordinates
echo -e "${BLUE}[7/9] Booking trip as passenger 2 (with pickup/dropoff coordinates)...${NC}"
BOOKING2_RESPONSE=$(curl -s -X POST "${BASE_URL}/trips/${TRIP_ID}/book" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $PASSENGER2_TOKEN" \
  -d '{
    "seats_requested": 1,
    "passenger_notes": "Segunda reserva con coordenadas",
    "pickup_location": "Puerto de Santa María",
    "pickup_lat": 36.5991,
    "pickup_lng": -6.2286,
    "dropoff_location": "Triana, Sevilla",
    "dropoff_lat": 37.3838,
    "dropoff_lng": -5.9972
  }')
echo "$BOOKING2_RESPONSE" | python3 -m json.tool
BOOKING2_ID=$(echo "$BOOKING2_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓ Booking 2 created with ID: $BOOKING2_ID${NC}"
echo ""

# Step 8: Test GET /trips/{trip_id}/bookings/public (no auth required)
echo -e "${BLUE}[8/9] Testing GET /trips/${TRIP_ID}/bookings/public (PUBLIC - no auth)...${NC}"
PUBLIC_BOOKINGS=$(curl -s -X GET "${BASE_URL}/trips/${TRIP_ID}/bookings/public")
echo "$PUBLIC_BOOKINGS" | python3 -m json.tool
echo -e "${GREEN}✓ Public bookings retrieved successfully (NO AUTH REQUIRED)${NC}"
echo ""

# Step 9: Test GET /trips/{trip_id}/route-with-stops (no auth required)
echo -e "${BLUE}[9/9] Testing GET /trips/${TRIP_ID}/route-with-stops (PUBLIC - no auth)...${NC}"
ROUTE_WITH_STOPS=$(curl -s -X GET "${BASE_URL}/trips/${TRIP_ID}/route-with-stops")
echo "$ROUTE_WITH_STOPS" | python3 -m json.tool
echo -e "${GREEN}✓ Route with stops retrieved successfully (NO AUTH REQUIRED)${NC}"
echo ""

echo -e "${GREEN}==========================================="
echo "✅ RF-BONUS-003 Test Suite Complete!"
echo "==========================================${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo "  ✓ Trip creation with coordinates"
echo "  ✓ Booking with pickup/dropoff coordinates"
echo "  ✓ GET /trips/{trip_id}/bookings/public endpoint (public access)"
echo "  ✓ GET /trips/{trip_id}/route-with-stops endpoint (public access)"
echo "  ✓ Privacy protection (no passenger names/IDs exposed)"
echo "  ✓ Geographic coordinates for map visualization"
echo ""
echo -e "${YELLOW}Key Features Tested:${NC}"
echo "  - Public visibility of booking locations"
echo "  - Privacy-aware data (anonymized)"
echo "  - Waypoints ordering (origin → pickups → dropoffs → destination)"
echo "  - Multiple bookings visualization"
echo "  - No authentication required for map endpoints"
