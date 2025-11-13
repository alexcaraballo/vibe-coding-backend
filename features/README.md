# Test Data Fixtures

Este directorio contiene los datos de prueba para la aplicación de carpooling.

## Archivos

### `users.json`
Contiene 3 usuarios de prueba:

- **María García** (conductor@example.com) - Conductora
  - Vehículo: Toyota Prius
  - Matrícula: 1234ABC

- **Carlos Rodríguez** (carlos@example.com) - Conductor
  - Vehículo: Seat León
  - Matrícula: 5678DEF

- **Ana López** (pasajero@example.com) - Pasajera
  - Sin vehículo

**Contraseña para todos:** `Pruebas1234`

### `trips.json`
Contiene 5 trayectos de ejemplo entre ciudades andaluzas:

1. **Cádiz → Sevilla** (María, 3 plazas, €8/plaza)
2. **Sevilla → Málaga** (Carlos, 2 plazas, €12/plaza)
3. **Málaga → Granada** (María, 4 plazas, €10/plaza)
4. **Granada → Almería** (Carlos, 3 plazas, €9/plaza)
5. **Cádiz → Jerez** (María, 2 plazas, €5/plaza)

Todos los trayectos incluyen:
- Coordenadas GPS reales
- Fechas futuras (15-19 diciembre 2025)
- Descripciones detalladas en español
- Precios realistas

### `bookings.json`
Contiene 4 reservas de Ana López en varios trayectos:

1. Cádiz → Sevilla (confirmada, 1 plaza)
2. Málaga → Granada (confirmada, 1 plaza)
3. Granada → Almería (pendiente, 2 plazas)
4. Cádiz → Jerez (confirmada, 1 plaza)

## Uso

### 1. Cargar datos en la base de datos

```bash
# Desde la raíz del proyecto
python scripts/seed_database.py
```

Este script:
- Crea las tablas si no existen
- Carga todos los usuarios (hasheando contraseñas)
- Carga todos los trayectos
- Carga todas las reservas
- Actualiza las plazas disponibles automáticamente

### 2. Limpiar la base de datos

```bash
# Para borrar todos los datos y empezar de nuevo
python scripts/clear_database.py
```

**⚠️ ADVERTENCIA:** Este comando eliminará TODOS los datos de la base de datos.

### 3. Verificar los datos

```bash
# Opción 1: Usar SQLite CLI
sqlite3 carpooling.db
.tables
SELECT * FROM users;
SELECT * FROM trips;
SELECT * FROM bookings;

# Opción 2: Iniciar la API y verificar
uvicorn main:app --reload
# Visitar: http://localhost:8000/docs
```

## Credenciales de prueba

Todos los usuarios tienen la contraseña: **Pruebas1234**

### Conductores
- `conductor@example.com` (María García)
- `carlos@example.com` (Carlos Rodríguez)

### Pasajeros
- `pasajero@example.com` (Ana López)

## Estructura de datos

### Usuario
```json
{
  "email": "conductor@example.com",
  "password": "Pruebas1234",
  "name": "María García",
  "phone": "+34612345678",
  "role": "driver",
  "vehicle_model": "Toyota Prius",
  "vehicle_plate": "1234ABC",
  "license_number": "12345678X"
}
```

### Trayecto
```json
{
  "origin": "Cádiz",
  "destination": "Sevilla",
  "origin_lat": 36.5271,
  "origin_lng": -6.2886,
  "destination_lat": 37.3891,
  "destination_lng": -5.9845,
  "departure_date": "2025-12-15",
  "departure_time": "09:00:00",
  "available_seats": 3,
  "total_seats": 3,
  "driver_email": "conductor@example.com",
  "price_per_seat": 8.0,
  "description": "Viaje cómodo desde Cádiz a Sevilla...",
  "status": "active",
  "max_detour_minutes": 20
}
```

### Reserva
```json
{
  "trip_reference": {
    "origin": "Cádiz",
    "destination": "Sevilla",
    "departure_date": "2025-12-15"
  },
  "passenger_email": "pasajero@example.com",
  "seats_booked": 1,
  "status": "confirmed",
  "pickup_location": "Estación de Autobuses de Cádiz",
  "dropoff_location": "Plaza de Armas, Sevilla",
  "passenger_notes": "Llevo una maleta pequeña. Gracias!"
}
```

## Personalización

Para añadir más datos de prueba:

1. Edita los archivos JSON en este directorio
2. Asegúrate de mantener la estructura existente
3. Usa `driver_email` en trips para referenciar usuarios
4. Usa `trip_reference` en bookings para referenciar trayectos
5. Ejecuta `python scripts/clear_database.py` (opcional)
6. Ejecuta `python scripts/seed_database.py`

## Notas técnicas

- **Hash de contraseñas:** Las contraseñas se hashean con bcrypt automáticamente
- **Foreign keys:** Los emails se convierten a IDs automáticamente
- **Fechas:** Formato ISO 8601 (YYYY-MM-DD)
- **Horas:** Formato 24h (HH:MM:SS)
- **Estados:** `active`, `confirmed`, `pending`, etc.
- **Roles:** `driver`, `passenger`, `both`

## Solución de problemas

### Error: "No module named 'passlib'"
```bash
pip install passlib[bcrypt]
```

### Error: "Table already exists"
```bash
# Limpiar y volver a cargar
python scripts/clear_database.py
python scripts/seed_database.py
```

### Error: "Driver email not found"
Asegúrate de que el `driver_email` en trips.json coincide exactamente con un email en users.json

### Error: "Trip reference not found"
Asegúrate de que los campos `origin`, `destination` y `departure_date` en bookings.json coinciden exactamente con un trayecto en trips.json
