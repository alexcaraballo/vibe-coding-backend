#!/bin/bash
# Test script for RF-005: Visualización de Rutas en Mapa

set -e

BASE_URL="http://localhost:8001/api/v1"
echo "======================================"
echo "RF-005: Map Visualization Tests"
echo "======================================"
echo ""

# Ensure we have a trip to test with (Trip ID 1 exists from previous tests)
echo "Step 1: Testing Geocode endpoint (POST /maps/v1/geocode)"
echo "   Testing geocoding: 'Cádiz, España'"
GEOCODE_RESPONSE=$(curl -s -X POST "$BASE_URL/maps/v1/geocode" \
  -H "Content-Type: application/json" \
  -d '{"address": "Cádiz, España"}')

echo "$GEOCODE_RESPONSE" | python3 -m json.tool
echo ""

# Extract coordinates
CADIZ_LAT=$(echo "$GEOCODE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['latitude'])")
CADIZ_LNG=$(echo "$GEOCODE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['longitude'])")
echo "   ✅ Geocoded Cádiz: lat=$CADIZ_LAT, lng=$CADIZ_LNG"
echo ""

echo "Step 2: Testing Route calculation endpoint (POST /maps/v1/route)"
echo "   Testing route: Cádiz → Sevilla using addresses"
ROUTE_RESPONSE=$(curl -s -X POST "$BASE_URL/maps/v1/route" \
  -H "Content-Type: application/json" \
  -d '{
    "origin_address": "Cádiz, España",
    "destination_address": "Sevilla, España"
  }')

echo "$ROUTE_RESPONSE" | python3 -m json.tool
echo ""

# Extract route info
DISTANCE=$(echo "$ROUTE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['distance_km'])")
DURATION=$(echo "$ROUTE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['duration_minutes'])")
POLYLINE_COUNT=$(echo "$ROUTE_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['polyline']))")
echo "   ✅ Route calculated:"
echo "      Distance: $DISTANCE km"
echo "      Duration: $DURATION minutes"
echo "      Polyline points: $POLYLINE_COUNT"
echo ""

echo "Step 3: Testing Trip Route endpoint (GET /maps/v1/trip/{trip_id}/route)"
echo "   Testing route for Trip ID 1"
TRIP_ROUTE_RESPONSE=$(curl -s "$BASE_URL/maps/v1/trip/1/route")

echo "$TRIP_ROUTE_RESPONSE" | python3 -m json.tool
echo ""

# Extract trip route info
TRIP_DISTANCE=$(echo "$TRIP_ROUTE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['distance_km'])" 2>/dev/null || echo "N/A")
TRIP_DURATION=$(echo "$TRIP_ROUTE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['duration_minutes'])" 2>/dev/null || echo "N/A")
TRIP_POLYLINE_COUNT=$(echo "$TRIP_ROUTE_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['polyline']))" 2>/dev/null || echo "N/A")

if [[ "$TRIP_DISTANCE" != "N/A" ]]; then
    echo "   ✅ Trip route calculated:"
    echo "      Distance: $TRIP_DISTANCE km"
    echo "      Duration: $TRIP_DURATION minutes"
    echo "      Polyline points: $TRIP_POLYLINE_COUNT"
    echo ""
    echo "======================================"
    echo "✅ RF-005: ALL TESTS PASSED!"
    echo "======================================"
    echo ""
    echo "Summary:"
    echo "  ✅ Geocoding service working (Nominatim)"
    echo "  ✅ Route calculation working (OSRM)"
    echo "  ✅ Trip route visualization ready"
    echo "  ✅ Polyline data available for map rendering"
else
    echo "   ⚠️ Trip route test had issues, check error above"
    echo "======================================"
    echo "⚠️  RF-005: Some tests failed"
    echo "======================================"
    exit 1
fi
