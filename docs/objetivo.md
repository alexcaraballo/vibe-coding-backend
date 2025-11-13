## 🎯 Objetivo del Reto
El objetivo de este hackathon es poner a prueba la creatividad, la colaboración y la capacidad técnica de los equipos utilizando Claude Code como entorno principal de desarrollo.

Durante el reto, los participantes deberán concebir, construir, desplegar localmente y presentar una aplicación funcional, desarrollada íntegramente con Claude Code. El enfoque no está en el tipo de aplicación, sino en la calidad del proceso de co-creación entre humanos e inteligencia artificial, aprovechando al máximo las capacidades del entorno: agents, hooks, comands y skills personalizados.

El propósito central es explorar el potencial del “Vibecoding”: una forma de programar donde la intuición humana, la creatividad y la inteligencia artificial trabajan en sintonía para alcanzar resultados de alta calidad técnica y conceptual.

Los equipos deberán demostrar:

¿Cómo utilizaron Claude Code como copiloto y herramienta integral de desarrollo?

¿Qué estrategias de prompting, automatización o agentes aplicaron?

¿Cómo lograron transformar una idea inicial en un producto funcional, claro y presentable?

Y finalmente, ¿Cómo fueron capaces de transmitir la experiencia de colaboración humano-IA durante su demo en vivo?

El hackathon no busca solo código, sino vibración, propósito y excelencia técnica, premiando la capacidad de cada equipo para usar la inteligencia artificial de manera consciente, creativa y productiva.


## ✅ Alcance funcional
Desarrollar MVP funcional de un sistema de Carpooling que permita como mínimo:

Publicar trayectos como conductor.

Buscar y reservar trayectos como pasajero.

Visualizar rutas en un mapa.

Simular matching básico entre usuarios.

1. Backend: API REST (backend)
El backend deberá exponer endpoints para:

🔸 Publicación de trayectos (POST /trips)
Datos: origen, destino, fecha/hora, plazas disponibles, conductor

🔸 Búsqueda de trayectos (GET /trips?from=A&to=B)
Filtrado por origen/destino (puede ser exacto o aproximado por nombre de ciudad)

🔸 Reserva de trayectos (POST /trips/{trip_id}/book)
Disminuye plazas disponibles y añade pasajero a la lista

🔸 Listado de reservas de un usuario (GET /users/{id}/bookings)

## 💡 Bonus Features (solo si da tiempo)
Matching aproximado (por distancia geográfica usando geocodificación).

Estimación de CO₂ evitado por trayecto.

Visualización de reservas de otros usuarios.

Chat simulado entre pasajero y conductor.