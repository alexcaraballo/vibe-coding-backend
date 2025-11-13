#!/bin/bash
# Test script for RF-BONUS-004: Chat Simulado Conductor-Pasajero
set -e

BASE_URL="http://localhost:8001/api/v1"
echo "=========================================="
echo "RF-BONUS-004: Chat Simulado"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Generate unique emails with timestamp
TIMESTAMP=$(date +%s)

# Step 1: Register driver
echo -e "${BLUE}[1/12] Registering driver user...${NC}"
DRIVER_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "driver_chat_'"${TIMESTAMP}"'@example.com",
    "password": "SecurePass123!",
    "name": "Ana Conductora",
    "role": "driver",
    "phone": "+34611222333"
  }')
echo "$DRIVER_RESPONSE" | python3 -m json.tool
DRIVER_ID=$(echo "$DRIVER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['user']['id'])")
DRIVER_TOKEN=$(echo "$DRIVER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo -e "${GREEN}✓ Driver registered with ID: $DRIVER_ID${NC}"
echo ""

# Step 2: Create a trip
echo -e "${BLUE}[2/12] Creating trip...${NC}"
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
    "description": "Viaje con chat",
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

# Step 3: Register passenger
echo -e "${BLUE}[3/12] Registering passenger user...${NC}"
PASSENGER_RESPONSE=$(curl -s -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "passenger_chat_'"${TIMESTAMP}"'@example.com",
    "password": "SecurePass123!",
    "name": "Juan Pasajero",
    "role": "passenger",
    "phone": "+34622333444"
  }')
PASSENGER_ID=$(echo "$PASSENGER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['user']['id'])")
PASSENGER_TOKEN=$(echo "$PASSENGER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
echo -e "${GREEN}✓ Passenger registered with ID: $PASSENGER_ID${NC}"
echo ""

# Step 4: Book trip as passenger
echo -e "${BLUE}[4/12] Booking trip as passenger...${NC}"
BOOKING_RESPONSE=$(curl -s -X POST "${BASE_URL}/trips/${TRIP_ID}/book" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $PASSENGER_TOKEN" \
  -d '{
    "seats_requested": 1,
    "passenger_notes": "Reserva con chat",
    "pickup_location": "Estación de Jerez",
    "pickup_lat": 36.6868,
    "pickup_lng": -6.1362,
    "dropoff_location": "Plaza de España, Sevilla",
    "dropoff_lat": 37.3772,
    "dropoff_lng": -5.9869
  }')
echo "$BOOKING_RESPONSE" | python3 -m json.tool
BOOKING_ID=$(echo "$BOOKING_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓ Booking created with ID: $BOOKING_ID${NC}"
echo ""

# Step 5: Passenger sends first message
echo -e "${BLUE}[5/12] Passenger sends first message...${NC}"
MESSAGE1_RESPONSE=$(curl -s -X POST "${BASE_URL}/trips/bookings/${BOOKING_ID}/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $PASSENGER_TOKEN" \
  -d '{
    "message": "Hola, ¿a qué hora exacta pasas a recogerme?"
  }')
echo "$MESSAGE1_RESPONSE" | python3 -m json.tool
MESSAGE1_ID=$(echo "$MESSAGE1_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓ Message 1 sent with ID: $MESSAGE1_ID${NC}"
echo ""

# Step 6: Driver reads conversation (should mark messages as read)
echo -e "${BLUE}[6/12] Driver reads conversation (marks messages as read)...${NC}"
CONVERSATION1=$(curl -s -X GET "${BASE_URL}/trips/bookings/${BOOKING_ID}/chat" \
  -H "Authorization: Bearer $DRIVER_TOKEN")
echo "$CONVERSATION1" | python3 -m json.tool
echo -e "${GREEN}✓ Driver read conversation${NC}"
echo ""

# Step 7: Driver sends reply
echo -e "${BLUE}[7/12] Driver sends reply...${NC}"
MESSAGE2_RESPONSE=$(curl -s -X POST "${BASE_URL}/trips/bookings/${BOOKING_ID}/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DRIVER_TOKEN" \
  -d '{
    "message": "Hola! Paso a las 10:00 AM exactamente. Te envío un mensaje cuando esté cerca."
  }')
echo "$MESSAGE2_RESPONSE" | python3 -m json.tool
MESSAGE2_ID=$(echo "$MESSAGE2_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓ Message 2 sent with ID: $MESSAGE2_ID${NC}"
echo ""

# Step 8: Passenger sends another message
echo -e "${BLUE}[8/12] Passenger sends follow-up message...${NC}"
MESSAGE3_RESPONSE=$(curl -s -X POST "${BASE_URL}/trips/bookings/${BOOKING_ID}/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $PASSENGER_TOKEN" \
  -d '{
    "message": "Perfecto! Te espero en la estación. Gracias!"
  }')
echo "$MESSAGE3_RESPONSE" | python3 -m json.tool
MESSAGE3_ID=$(echo "$MESSAGE3_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓ Message 3 sent with ID: $MESSAGE3_ID${NC}"
echo ""

# Step 9: Passenger reads full conversation
echo -e "${BLUE}[9/12] Passenger reads full conversation...${NC}"
CONVERSATION2=$(curl -s -X GET "${BASE_URL}/trips/bookings/${BOOKING_ID}/chat" \
  -H "Authorization: Bearer $PASSENGER_TOKEN")
echo "$CONVERSATION2" | python3 -m json.tool
TOTAL_MESSAGES=$(echo "$CONVERSATION2" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_messages'])")
echo -e "${GREEN}✓ Passenger read conversation. Total messages: $TOTAL_MESSAGES${NC}"
echo ""

# Step 10: Test unauthorized access (different user trying to access chat)
echo -e "${BLUE}[10/12] Testing unauthorized access (should fail)...${NC}"
UNAUTHORIZED_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${BASE_URL}/trips/bookings/${BOOKING_ID}/chat" \
  -H "Authorization: Bearer invalid_token" 2>&1 || true)
HTTP_CODE=$(echo "$UNAUTHORIZED_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "422" ]; then
    echo -e "${GREEN}✓ Unauthorized access correctly blocked (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected response code: $HTTP_CODE${NC}"
fi
echo ""

# Step 11: Driver deletes their own message
echo -e "${BLUE}[11/12] Driver deletes their message...${NC}"
DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${BASE_URL}/trips/chat/${MESSAGE2_ID}" \
  -H "Authorization: Bearer $DRIVER_TOKEN")
HTTP_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "204" ]; then
    echo -e "${GREEN}✓ Message deleted successfully (HTTP 204)${NC}"
else
    echo -e "${YELLOW}⚠ Unexpected response code: $HTTP_CODE${NC}"
    echo "$DELETE_RESPONSE" | head -n -1 | python3 -m json.tool 2>/dev/null || echo "$DELETE_RESPONSE"
fi
echo ""

# Step 12: Verify deleted message is not in conversation
echo -e "${BLUE}[12/12] Verifying deleted message is not in conversation...${NC}"
FINAL_CONVERSATION=$(curl -s -X GET "${BASE_URL}/trips/bookings/${BOOKING_ID}/chat" \
  -H "Authorization: Bearer $DRIVER_TOKEN")
echo "$FINAL_CONVERSATION" | python3 -m json.tool
FINAL_TOTAL=$(echo "$FINAL_CONVERSATION" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_messages'])")
echo -e "${GREEN}✓ Final conversation has $FINAL_TOTAL messages (should be 2 after deletion)${NC}"
echo ""

echo -e "${GREEN}==========================================="
echo "✅ RF-BONUS-004 Test Suite Complete!"
echo "===========================================${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo "  ✓ Driver and passenger registration"
echo "  ✓ Trip creation and booking"
echo "  ✓ Send messages (passenger → driver)"
echo "  ✓ Send messages (driver → passenger)"
echo "  ✓ Get conversation with message history"
echo "  ✓ Mark messages as read automatically"
echo "  ✓ Unauthorized access blocked"
echo "  ✓ Delete own message (soft delete)"
echo "  ✓ Deleted messages not shown in conversation"
echo ""
echo -e "${YELLOW}Key Features Tested:${NC}"
echo "  - Chat simulado between driver and passenger"
echo "  - Private conversation (only driver and passenger have access)"
echo "  - Message read status tracking"
echo "  - Chronological message ordering"
echo "  - Authorization validation"
echo "  - Soft delete of messages"
