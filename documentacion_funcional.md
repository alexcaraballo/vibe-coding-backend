# Documentación Funcional - Sistema de Carpooling

---

## A. Descripción General del Producto

### Información Explícita (de docs/)

**Contexto del Proyecto:**
Este proyecto es un MVP (Producto Mínimo Viable) de una aplicación de carpooling desarrollado en el contexto de un hackathon enfocado en "Vibecoding" - la colaboración entre humanos e inteligencia artificial usando Claude Code como entorno principal de desarrollo.

**Objetivo del MVP:**
Desarrollar un sistema funcional de carpooling que permita a los usuarios:
- Publicar trayectos como conductor
- Buscar y reservar trayectos como pasajero
- Visualizar rutas en un mapa
- Realizar matching básico entre usuarios

**Alcance Técnico:**
Backend: API REST con endpoints definidos para gestión de trayectos y reservas.

### Información Inferida

**Misión del Producto:**
Facilitar el compartir vehículo entre usuarios que realizan trayectos similares, optimizando recursos de transporte y reduciendo costos individuales.

**Problemas que Resuelve:**
- Costos elevados de transporte individual
- Congestión de tráfico por vehículos con baja ocupación
- Impacto ambiental del transporte individual
- Conexión entre usuarios con rutas compatibles

**Público Objetivo:**
- Conductores que desean compartir gastos de viaje
- Pasajeros que buscan opciones de transporte económicas
- Usuarios conscientes del medio ambiente

### ⚠️ Información Insuficiente en docs/

- **Propuesta de valor específica** diferenciadora respecto a otras apps de carpooling
- **Métricas de éxito** del producto
- **Investigación de usuarios** o validación de problema
- **Análisis de competencia**
- **Modelo de negocio** (gratuito, comisiones, suscripción)

---

## B. Requisitos Funcionales

### Información Explícita (de docs/)

#### RF-001: Publicación de Trayectos
**Descripción:** Permitir a los conductores publicar trayectos disponibles para compartir.

**Entrada:**
- Origen del trayecto
- Destino del trayecto
- Fecha y hora del viaje
- Plazas disponibles
- Identificación del conductor

**Salida:**
- Trayecto creado y almacenado en el sistema
- ID único del trayecto

**Endpoint:** `POST /trips`

**Restricciones:**
- [No especificadas en docs/]

**Reglas de Negocio:**
- [No especificadas en docs/]

---

#### RF-002: Búsqueda de Trayectos
**Descripción:** Permitir a los pasajeros buscar trayectos disponibles según origen y destino.

**Entrada:**
- Parámetro "from": origen del trayecto buscado
- Parámetro "to": destino del trayecto buscado

**Salida:**
- Lista de trayectos que coinciden con los criterios de búsqueda

**Endpoint:** `GET /trips?from=A&to=B`

**Tipo de Filtrado:**
- Puede ser exacto o aproximado por nombre de ciudad

**Restricciones:**
- [No especificadas en docs/]

---

#### RF-003: Reserva de Trayectos
**Descripción:** Permitir a los pasajeros reservar un lugar en un trayecto publicado.

**Entrada:**
- ID del trayecto a reservar
- Identificación del pasajero (implícito)

**Salida:**
- Confirmación de reserva
- Plazas disponibles actualizadas

**Endpoint:** `POST /trips/{trip_id}/book`

**Proceso:**
1. Disminuye las plazas disponibles del trayecto
2. Añade el pasajero a la lista de reservas del trayecto

**Restricciones:**
- [No especificadas en docs/]

---

#### RF-004: Listado de Reservas de Usuario
**Descripción:** Permitir a un usuario consultar todas sus reservas.

**Entrada:**
- ID del usuario

**Salida:**
- Lista de todas las reservas (bookings) del usuario

**Endpoint:** `GET /users/{id}/bookings`

---

#### RF-005: Visualización de Rutas en Mapa
**Descripción:** Permitir visualizar los trayectos en un mapa.

**Entrada:**
- Información del trayecto (origen, destino)

**Salida:**
- Representación visual de la ruta en un mapa

**⚠️ Información Insuficiente en docs/:**
- Proveedor de mapas a utilizar (Google Maps, Mapbox, OpenStreetMap)
- Nivel de detalle de la visualización
- Interactividad del mapa

---

#### RF-006: Matching Básico entre Usuarios (Motor de Asociación de Trayectos)
**Descripción:** Sistema de matching automático que identifica coincidencias entre trayectos publicados y peticiones de viaje, considerando restricciones geográficas, temporales y de desvío máximo acumulativo.

**Objetivo:**
Identificar entre los trayectos publicados aquellos que pueden admitir una nueva petición de viaje sin violar las restricciones del conductor ni las condiciones del pasajero.

**Entrada:**
- **Petición de viaje (Pasajero):**
  - Origen y destino (coordenadas geográficas: latitud, longitud)
  - Día del viaje (fecha exacta)
  - Filtros opcionales: "A partir de esta hora" / "Antes de esta hora"

- **Trayecto publicado (Conductor):**
  - Origen y destino (coordenadas geográficas)
  - Hora de salida y hora prevista de llegada
  - Desvío máximo permitido (en minutos o porcentaje de duración original)
  - Roadmap actual: lista ordenada de tramos (ej: Cádiz → Jerez → Dos Hermanas → Sevilla)
  - Desvío acumulado actual: minutos adicionales ya consumidos

**Salida:**
- Lista de trayectos sugeridos con:
  - Identificador del trayecto
  - Descripción de la ruta actual
  - Estimación del desvío adicional
  - Estado de compatibilidad (apto/no apto)
  - Nivel de coincidencia o puntuación (ranking)

**Reglas de Asociación:**

1. **Coincidencia Geográfica:**
   - Origen de la petición próximo a algún punto del trayecto
   - Destino de la petición en un punto posterior dentro del orden lógico del trayecto

2. **Coincidencia Temporal:**
   - El día debe coincidir exactamente
   - Si hay rango horario, la hora de paso prevista debe respetarlo

3. **Desvío Máximo Acumulativo (Crítico):**
   - Cada trayecto tiene un límite máximo de desvío (ej: 30 minutos)
   - Cada nueva inserción consume parte de ese margen
   - Restricción: `desvío acumulado actual + desvío adicional proyectado ≤ desvío máximo permitido`
   - Si no se cumple, el trayecto no es elegible

4. **Compatibilidad Lógica:**
   - No se permiten inserciones que alteren el orden cronológico del roadmap
   - No se consideran trayectos cuyo punto de salida ya haya sido superado

**Criterios de Priorización/Ranking:**
1. Menor desvío adicional provocado
2. Mayor proximidad entre puntos de origen/destino
3. Ajuste horario más cercano al solicitado

**Funcionalidades Principales:**
- Recepción y validación de peticiones de viaje
- Evaluación de trayectos publicados (filtrado por fecha)
- Cálculo de posibles inserciones en el roadmap
- Verificación del desvío máximo acumulativo
- Generación de resultados ordenados por adecuación

**Casos de Uso Ejemplares:**

*Caso 1: Inserción válida*
- Trayecto: Cádiz → Sevilla (9:00–10:00), desvío máximo 30 min
- Petición: Jerez → Dos Hermanas
- Desvío adicional estimado: +20 min
- **Resultado: ACEPTADO** (Desvío acumulado = 20 min)

*Caso 2: Inserción excede desvío máximo*
- Mismo trayecto con desvío acumulado de 20 min
- Nueva petición: Puerto Real → Sevilla (+15 min)
- **Resultado: RECHAZADO** (Desvío total proyectado = 35 min > 30 min)

**Restricciones Funcionales:**
- El cálculo del desvío debe ser dinámico y acumulativo
- El sistema debe evaluar varios trayectos activos simultáneamente
- Los trayectos se actualizan automáticamente tras aceptar una petición

**Documentación Técnica:** Ver `docs/match_engine.md` para detalles de implementación

---

### Funcionalidades Bonus (Si hay tiempo)

#### RF-BONUS-001: Matching Aproximado Geográfico
**Descripción:** Realizar matching por distancia geográfica usando geocodificación.

**⚠️ Información Insuficiente en docs/:**
- Radio de distancia considerado como "aproximado"
- Servicio de geocodificación a utilizar
- Precisión requerida

---

#### RF-BONUS-002: Estimación de CO₂ Evitado
**Descripción:** Calcular y mostrar el CO₂ evitado por cada trayecto compartido.

**⚠️ Información Insuficiente en docs/:**
- Fórmula de cálculo
- Factores considerados (tipo de vehículo, distancia, etc.)
- Unidades de medida

---

#### RF-BONUS-003: Visualización de Reservas de Otros Usuarios
**Descripción:** Permitir ver las reservas que otros usuarios han realizado.

**⚠️ Información Insuficiente en docs/:**
- Nivel de privacidad/información mostrada
- Propósito de esta funcionalidad
- Restricciones de acceso

---

#### RF-BONUS-004: Chat Simulado
**Descripción:** Implementar un chat simulado entre pasajero y conductor.

**⚠️ Información Insuficiente en docs/:**
- Tipo de simulación (bot, mensajes predefinidos)
- Propósito del chat
- Persistencia de mensajes

---

### Información Inferida

#### Requisitos Funcionales Implícitos

**RF-INF-001: Gestión de Usuarios**
- Registro de usuarios
- Autenticación
- Perfiles de usuario (conductor/pasajero/ambos)

**RF-INF-002: Validación de Disponibilidad**
- Verificar plazas disponibles antes de confirmar reserva
- Prevenir overbooking

**RF-INF-003: Cancelación de Reservas**
- Permitir a pasajeros cancelar reservas
- Liberar plazas canceladas

**RF-INF-004: Gestión de Plazas**
- Actualización automática de plazas disponibles
- Control de capacidad máxima

---

## C. Requisitos No Funcionales

### ⚠️ Información Insuficiente en docs/

#### RNF-001: Seguridad
- **Autenticación:** No especificada (JWT, OAuth, sesiones)
- **Autorización:** No especificada (roles, permisos)
- **Protección de datos personales:** No especificada
- **Encriptación:** No especificada (HTTPS, datos en tránsito/reposo)
- **Prevención de ataques:** No especificada (CSRF, XSS, SQL Injection)
- **Privacidad:** No especificada (GDPR, datos sensibles)

#### RNF-002: Rendimiento
- **Tiempo de respuesta:** No especificado
- **Throughput:** No especificado (requests por segundo)
- **Latencia máxima aceptable:** No especificada
- **Carga concurrente soportada:** No especificada
- **Optimización de consultas:** No especificada

#### RNF-003: Escalabilidad
- **Arquitectura escalable:** No especificada (monolito, microservicios)
- **Estrategia de escalado:** No especificada (horizontal, vertical)
- **Límites de usuarios concurrentes:** No especificados
- **Capacidad de crecimiento:** No especificada

#### RNF-004: UX/UI y Accesibilidad
- **Diseño de interfaz:** No especificado
- **Responsive design:** No especificado
- **Accesibilidad (WCAG):** No especificada
- **Internacionalización:** No especificada
- **Usabilidad:** No especificada

#### RNF-005: Requisitos Legales
- **Cumplimiento GDPR/LOPD:** No especificado
- **Términos y condiciones:** No especificados
- **Política de privacidad:** No especificada
- **Responsabilidad legal:** No especificada (seguros, accidentes)
- **Edad mínima usuarios:** No especificada
- **Consentimiento de datos:** No especificado

#### RNF-006: Disponibilidad
- **Uptime requerido:** No especificado
- **Plan de backup:** No especificado
- **Recuperación ante desastres:** No especificada

#### RNF-007: Mantenibilidad
- **Documentación de código:** No especificada
- **Estándares de código:** No especificados
- **Testing:** No especificado (cobertura, tipos de tests)

#### RNF-008: Compatibilidad
- **Navegadores soportados:** No especificados
- **Versiones de SO:** No especificadas
- **Dispositivos móviles:** No especificado

---

## D. Arquitectura Lógica de la Aplicación

### Información Explícita (de docs/)

#### Patrón Arquitectónico
**API REST** - Backend que expone endpoints HTTP para operaciones CRUD y consultas.

#### Endpoints Principales
```
POST   /trips              → Crear trayecto
GET    /trips?from=A&to=B  → Buscar trayectos
POST   /trips/{id}/book    → Reservar trayecto
GET    /users/{id}/bookings → Listar reservas de usuario
```

### Información Inferida

#### Arquitectura de Capas

```
┌─────────────────────────────────────┐
│     CAPA DE PRESENTACIÓN            │
│  (Frontend/Cliente - No en scope)   │
└─────────────────────────────────────┘
              ↓ HTTP/REST
┌─────────────────────────────────────┐
│     CAPA DE API (Controllers)       │
│  - Trip Controller                  │
│  - User Controller                  │
│  - Booking Controller               │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│     CAPA DE LÓGICA DE NEGOCIO       │
│  - Trip Service                     │
│  - Booking Service                  │
│  - Matching Service                 │
│  - User Service                     │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│     CAPA DE ACCESO A DATOS          │
│  - Trip Repository                  │
│  - User Repository                  │
│  - Booking Repository               │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│     BASE DE DATOS                   │
│  (Tipo no especificado)             │
└─────────────────────────────────────┘
```

#### Módulos Principales

**1. Módulo de Trayectos (Trips)**
- Gestión de publicación de viajes
- Búsqueda y filtrado de trayectos
- Actualización de disponibilidad

**2. Módulo de Reservas (Bookings)**
- Creación de reservas
- Gestión de plazas
- Listado de reservas por usuario

**3. Módulo de Usuarios (Users)**
- Gestión de perfiles
- Rol conductor/pasajero

**4. Módulo de Matching (Motor de Asociación de Trayectos)**
- Evaluación de coincidencias geográficas y temporales
- Cálculo de desvío acumulativo y adicional
- Verificación de restricciones de desvío máximo
- Gestión de roadmap dinámico
- Priorización y ranking de sugerencias
- Algoritmo de inserción óptima en roadmap
- Servicios de geocodificación (coordenadas ↔ direcciones)

**5. Módulo de Mapas (Maps)**
- Visualización de rutas
- Geocodificación (bonus)

### ⚠️ Información Insuficiente en docs/

- **Tecnologías específicas:** Framework backend (FastAPI, Django, Express, Spring Boot)
- **Base de datos:** Tipo (SQL/NoSQL), motor específico (PostgreSQL, MongoDB, etc.)
- **ORM/ODM:** Herramienta de mapeo objeto-relacional
- **Cache:** Estrategia de caché (Redis, Memcached)
- **Message Queue:** Para procesamiento asíncrono
- **API Gateway:** Si aplica
- **Logging y Monitoring:** Herramientas de observabilidad
- **Containerización:** Docker, Kubernetes

---

## E. Especificación de Usuarios y Roles

### Información Explícita (de docs/)

#### Tipos de Usuario Identificados

**1. Conductor**
- Usuario que publica trayectos
- Ofrece plazas disponibles en su vehículo
- Responsable del viaje

**2. Pasajero**
- Usuario que busca trayectos
- Realiza reservas en trayectos publicados
- Ocupa plazas disponibles

**3. Usuario Base**
- Entidad común que puede actuar como conductor o pasajero

### Información Inferida

#### Modelo de Roles

```
Usuario (Base)
    ├── puede actuar como → Conductor
    └── puede actuar como → Pasajero
```

Un usuario puede:
- Ser solo conductor
- Ser solo pasajero
- Ser ambos (en diferentes trayectos)

#### Permisos por Rol

**Conductor:**
- ✓ Publicar trayectos (`POST /trips`)
- ✓ Gestionar sus trayectos publicados
- ✓ Ver reservas de sus trayectos
- ✓ Acceder como pasajero a trayectos de otros

**Pasajero:**
- ✓ Buscar trayectos (`GET /trips`)
- ✓ Reservar trayectos (`POST /trips/{id}/book`)
- ✓ Ver sus reservas (`GET /users/{id}/bookings`)
- ✓ Cancelar reservas (inferido)

**Usuario No Autenticado:**
- ? Buscar trayectos (no especificado)
- ✗ No puede realizar reservas
- ✗ No puede publicar trayectos

### ⚠️ Información Insuficiente en docs/

- **Roles administrativos:** Admin, moderador, soporte
- **Verificación de conductores:** Proceso de validación, documentación requerida
- **Sistema de reputación:** Ratings, reviews, valoraciones
- **Suspensión/bloqueo de usuarios:** Políticas y procesos
- **Niveles de usuario:** Usuario nuevo, verificado, premium, etc.
- **Delegación de permisos:** Co-conductores, autorizados
- **Límites por rol:** Máximo de trayectos publicados, reservas simultáneas

---

## F. Flujos Completos

### Información Explícita (de docs/)

#### Flujo 1: Publicación de Trayecto

**Actor:** Conductor

**Secuencia:**
1. Conductor accede a la funcionalidad de publicar trayecto
2. Ingresa datos del trayecto:
   - Origen
   - Destino
   - Fecha y hora
   - Plazas disponibles
3. Sistema registra trayecto (`POST /trips`)
4. Sistema asigna ID único al trayecto
5. Trayecto queda disponible para búsqueda

**⚠️ No especificado:**
- Validación de datos
- Confirmación al conductor
- Edición posterior del trayecto

---

#### Flujo 2: Búsqueda y Reserva de Trayecto

**Actor:** Pasajero

**Secuencia:**
1. Pasajero accede a búsqueda de trayectos
2. Ingresa criterios:
   - Origen (from)
   - Destino (to)
3. Sistema busca trayectos coincidentes (`GET /trips?from=A&to=B`)
4. Sistema muestra lista de trayectos disponibles
5. Pasajero selecciona un trayecto
6. Pasajero solicita reserva
7. Sistema valida disponibilidad
8. Sistema procesa reserva (`POST /trips/{trip_id}/book`)
9. Sistema actualiza:
   - Decrementa plazas disponibles
   - Añade pasajero a lista del trayecto
10. Sistema confirma reserva

**⚠️ No especificado:**
- Filtros adicionales (fecha, hora, precio)
- Detalles mostrados de cada trayecto
- Proceso de pago
- Notificaciones al conductor

---

#### Flujo 3: Consulta de Reservas

**Actor:** Usuario (Pasajero)

**Secuencia:**
1. Usuario accede a "Mis reservas"
2. Sistema obtiene reservas del usuario (`GET /users/{id}/bookings`)
3. Sistema muestra lista de reservas con:
   - Información del trayecto
   - Estado de la reserva
   - Datos del conductor

**⚠️ No especificado:**
- Estados posibles de reserva (confirmada, pendiente, cancelada)
- Información detallada mostrada
- Acciones disponibles desde esta vista

---

#### Flujo 4: Visualización de Ruta en Mapa

**Actor:** Pasajero/Conductor

**Secuencia:**
1. Usuario selecciona un trayecto
2. Usuario solicita ver ruta en mapa
3. Sistema obtiene coordenadas de origen y destino
4. Sistema genera visualización en mapa
5. Sistema muestra ruta al usuario

**⚠️ No especificado:**
- Tecnología de mapas utilizada
- Interacciones disponibles
- Información adicional mostrada (duración, distancia, puntos intermedios)

---

#### Flujo 5: Matching Avanzado con Motor de Asociación

**Actor:** Sistema (Motor de Matching), Pasajero, Conductor

**Gatillador:** Pasajero realiza una petición de viaje (TravelRequest)

**Secuencia:**
1. Pasajero ingresa solicitud de viaje:
   - Origen (dirección o coordenadas)
   - Destino (dirección o coordenadas)
   - Fecha del viaje
   - Opcionalmente: rango horario (desde/hasta)
2. Sistema crea registro de TravelRequest
3. Sistema valida y geocodifica ubicaciones (si son direcciones, las convierte a lat/lng)
4. Motor de Matching inicia evaluación:
   - Filtra trayectos por fecha exacta
   - Descarta trayectos con salida pasada
5. Para cada trayecto compatible temporalmente:
   - Evalúa coincidencia geográfica (origen cerca de algún punto del roadmap)
   - Verifica que destino esté en un punto posterior lógico
   - Calcula posibles puntos de inserción en el roadmap
   - Estima desvío adicional que provocaría la inserción
   - Obtiene desvío acumulado actual del trayecto
   - Verifica restricción: `current_detour + additional_detour ≤ max_detour`
   - Si cumple todas las condiciones, marca trayecto como compatible
6. Sistema calcula puntuación de adecuación para cada match válido
7. Sistema ordena resultados por mejor ajuste (menor desvío, mayor proximidad, mejor hora)
8. Sistema presenta al pasajero lista de trayectos sugeridos con:
   - Información del conductor
   - Ruta actual y ruta proyectada tras inserción
   - Desvío adicional estimado
   - Puntuación de compatibilidad
9. Pasajero puede:
   - Solicitar unirse a un trayecto sugerido
   - Refinar criterios de búsqueda
   - Cancelar la petición

**Flujo alternativo: Aceptación de petición por conductor**
- Si pasajero solicita unirse a un trayecto:
  - Sistema notifica al conductor
  - Conductor puede aceptar o rechazar
  - Si acepta:
    - Sistema crea Booking
    - Sistema actualiza roadmap del Trip
    - Sistema actualiza current_detour_minutes
    - Sistema decrementa available_seats
    - Sistema actualiza estado de TravelRequest a 'accepted'

**⚠️ No especificado en docs/:**
- Proceso exacto de notificación al conductor
- Tiempo de espera para respuesta del conductor
- Qué sucede si el conductor no responde

---

### Flujos Alternativos (Inferidos)

#### Flujo Alt-1: Reserva Sin Plazas Disponibles

**Variante del Flujo 2:**
- En paso 7, sistema detecta que no hay plazas disponibles
- Sistema rechaza la reserva
- Sistema notifica al pasajero
- Sistema puede sugerir trayectos alternativos

---

#### Flujo Alt-2: Cancelación de Reserva

**Actor:** Pasajero

**Secuencia:**
1. Pasajero accede a sus reservas
2. Selecciona reserva a cancelar
3. Solicita cancelación
4. Sistema procesa cancelación
5. Sistema incrementa plazas disponibles
6. Sistema notifica al conductor

**⚠️ Completamente inferido** - no aparece en docs/

---

### ⚠️ Información Insuficiente en docs/

- **Flujos de autenticación/registro**
- **Flujos de pago**
- **Flujos de calificación/review**
- **Flujos de notificaciones**
- **Flujos de gestión de perfil**
- **Flujos de comunicación entre usuarios** (más allá del chat simulado bonus)
- **Flujos de resolución de conflictos**
- **Flujos de modificación de trayectos publicados**

---

## G. Casos de Uso Formales

### Caso de Uso 1: Publicar Trayecto

**Identificador:** CU-001

**Nombre:** Publicar Trayecto como Conductor

**Actores:**
- **Principal:** Conductor
- **Secundario:** Sistema de Base de Datos

**Precondiciones:**
- El conductor debe estar autenticado en el sistema
- El conductor debe tener un perfil válido

**Gatillador:**
El conductor desea compartir su vehículo en un próximo viaje y decide publicar el trayecto.

**Secuencia Normal:**
1. Conductor selecciona la opción "Publicar Trayecto"
2. Sistema presenta formulario de publicación
3. Conductor ingresa:
   - Punto de origen
   - Punto de destino
   - Fecha del viaje
   - Hora del viaje
   - Número de plazas disponibles
4. Conductor confirma la publicación
5. Sistema valida los datos ingresados
6. Sistema crea el registro del trayecto (`POST /trips`)
7. Sistema asigna ID único al trayecto
8. Sistema almacena el trayecto en la base de datos
9. Sistema confirma la publicación exitosa al conductor
10. Sistema hace el trayecto visible para búsquedas

**Secuencias Alternativas:**

**5a. Datos Inválidos**
- 5a.1. Sistema detecta datos incompletos o inválidos
- 5a.2. Sistema muestra mensaje de error específico
- 5a.3. Vuelve al paso 3

**6a. Error de Sistema**
- 6a.1. Sistema no puede crear el trayecto (error de BD)
- 6a.2. Sistema muestra mensaje de error técnico
- 6a.3. Sistema sugiere intentar nuevamente
- 6a.4. Caso de uso termina sin éxito

**Postcondiciones:**
- **Éxito:**
  - Trayecto creado y almacenado en el sistema
  - Trayecto visible en búsquedas
  - Conductor puede gestionar el trayecto
- **Fallo:**
  - No se crea ningún trayecto
  - Sistema permanece en estado consistente

**Reglas de Negocio:**
- ⚠️ No especificadas en docs/ (ej: fecha mínima, máximo de plazas, etc.)

---

### Caso de Uso 2: Buscar Trayecto

**Identificador:** CU-002

**Nombre:** Buscar Trayectos Disponibles

**Actores:**
- **Principal:** Pasajero
- **Secundario:** Sistema de Búsqueda, Sistema de Base de Datos

**Precondiciones:**
- ⚠️ No especificado si requiere autenticación

**Gatillador:**
El pasajero necesita transporte y desea encontrar trayectos que se ajusten a su ruta.

**Secuencia Normal:**
1. Pasajero accede a la funcionalidad de búsqueda
2. Sistema presenta interfaz de búsqueda
3. Pasajero ingresa:
   - Origen del viaje ("from")
   - Destino del viaje ("to")
4. Pasajero ejecuta la búsqueda
5. Sistema consulta trayectos disponibles (`GET /trips?from=A&to=B`)
6. Sistema aplica filtros de origen y destino (exacto o aproximado por ciudad)
7. Sistema recupera lista de trayectos coincidentes
8. Sistema presenta resultados al pasajero con:
   - Información de cada trayecto
   - Datos del conductor
   - Plazas disponibles
   - Fecha y hora
9. Pasajero puede seleccionar un trayecto para más detalles

**Secuencias Alternativas:**

**7a. No se encuentran trayectos**
- 7a.1. Sistema no encuentra trayectos coincidentes
- 7a.2. Sistema muestra mensaje "No hay trayectos disponibles"
- 7a.3. Sistema sugiere modificar criterios de búsqueda
- 7a.4. Vuelve al paso 3

**7b. Error de búsqueda**
- 7b.1. Sistema experimenta error técnico
- 7b.2. Sistema muestra mensaje de error
- 7b.3. Caso de uso termina sin éxito

**Postcondiciones:**
- **Éxito:**
  - Pasajero visualiza trayectos disponibles
  - Pasajero puede proceder a reservar
- **Fallo:**
  - No se muestran resultados
  - Sistema permanece disponible para nueva búsqueda

**Reglas de Negocio:**
- La búsqueda puede ser exacta o aproximada por nombre de ciudad
- ⚠️ No especificado: criterios de aproximación, priorización de resultados

---

### Caso de Uso 3: Reservar Trayecto

**Identificador:** CU-003

**Nombre:** Reservar Plaza en Trayecto

**Actores:**
- **Principal:** Pasajero
- **Secundario:** Sistema de Reservas, Conductor (notificado)

**Precondiciones:**
- Pasajero debe estar autenticado
- Debe existir un trayecto con plazas disponibles
- Pasajero debe haber seleccionado un trayecto específico

**Gatillador:**
El pasajero encuentra un trayecto que le interesa y desea reservar una plaza.

**Secuencia Normal:**
1. Pasajero selecciona trayecto de interés
2. Sistema muestra detalles completos del trayecto
3. Pasajero solicita reservar plaza
4. Sistema valida disponibilidad de plazas
5. Sistema procesa reserva (`POST /trips/{trip_id}/book`)
6. Sistema actualiza trayecto:
   - Decrementa contador de plazas disponibles
   - Añade pasajero a lista de reservas del trayecto
7. Sistema crea registro de reserva (booking)
8. Sistema confirma reserva exitosa al pasajero
9. Sistema notifica al conductor (inferido)

**Secuencias Alternativas:**

**4a. No hay plazas disponibles**
- 4a.1. Sistema detecta que plazas disponibles = 0
- 4a.2. Sistema muestra mensaje "Trayecto completo"
- 4a.3. Sistema sugiere trayectos alternativos
- 4a.4. Caso de uso termina sin éxito

**4b. Pasajero ya tiene reserva en este trayecto**
- 4b.1. Sistema detecta reserva duplicada
- 4b.2. Sistema muestra mensaje "Ya tienes una reserva en este trayecto"
- 4b.3. Caso de uso termina sin éxito

**6a. Error en actualización**
- 6a.1. Sistema no puede actualizar el trayecto
- 6a.2. Sistema revierte transacción
- 6a.3. Sistema muestra mensaje de error
- 6a.4. Caso de uso termina sin éxito

**Postcondiciones:**
- **Éxito:**
  - Reserva creada y almacenada
  - Plazas disponibles decrementadas
  - Pasajero añadido a lista del trayecto
  - Conductor notificado de nueva reserva
- **Fallo:**
  - No se crea reserva
  - Trayecto permanece sin cambios
  - Sistema mantiene consistencia de datos

**Reglas de Negocio:**
- ⚠️ No especificadas: límite de reservas por usuario, cancelación automática, política de no-show

---

### Caso de Uso 4: Consultar Mis Reservas

**Identificador:** CU-004

**Nombre:** Listar Reservas de Usuario

**Actores:**
- **Principal:** Usuario (Pasajero)
- **Secundario:** Sistema de Base de Datos

**Precondiciones:**
- Usuario debe estar autenticado
- Usuario debe tener ID válido en el sistema

**Gatillador:**
El usuario desea revisar todas sus reservas activas o históricas.

**Secuencia Normal:**
1. Usuario accede a sección "Mis Reservas"
2. Sistema obtiene ID del usuario autenticado
3. Sistema consulta reservas del usuario (`GET /users/{id}/bookings`)
4. Sistema recupera lista de reservas de la base de datos
5. Sistema presenta listado con información de cada reserva:
   - Trayecto asociado
   - Datos del conductor
   - Fecha y hora del viaje
   - Estado de la reserva
6. Usuario puede seleccionar una reserva para ver detalles

**Secuencias Alternativas:**

**4a. Usuario sin reservas**
- 4a.1. Sistema no encuentra reservas para el usuario
- 4a.2. Sistema muestra mensaje "No tienes reservas aún"
- 4a.3. Sistema sugiere buscar trayectos
- 4a.4. Caso de uso termina exitosamente

**4b. Error al obtener reservas**
- 4b.1. Sistema experimenta error técnico
- 4b.2. Sistema muestra mensaje de error
- 4b.3. Sistema sugiere intentar nuevamente
- 4b.4. Caso de uso termina sin éxito

**Postcondiciones:**
- **Éxito:**
  - Usuario visualiza sus reservas
  - Usuario puede gestionar sus reservas
- **Fallo:**
  - No se muestran reservas
  - Sistema permanece disponible

**Reglas de Negocio:**
- ⚠️ No especificadas: filtros de reservas (activas, pasadas, canceladas), ordenamiento

---

### Caso de Uso 5: Visualizar Ruta en Mapa

**Identificador:** CU-005

**Nombre:** Ver Trayecto en Mapa

**Actores:**
- **Principal:** Usuario (Conductor o Pasajero)
- **Secundario:** Sistema de Mapas, Servicio de Geocodificación

**Precondiciones:**
- Debe existir un trayecto con origen y destino definidos

**Gatillador:**
El usuario desea visualizar la ruta del trayecto en un mapa.

**Secuencia Normal:**
1. Usuario selecciona un trayecto
2. Usuario solicita "Ver en mapa"
3. Sistema obtiene origen y destino del trayecto
4. Sistema geocodifica las ubicaciones (convierte nombres a coordenadas)
5. Sistema genera ruta entre origen y destino
6. Sistema renderiza mapa con:
   - Marcador de origen
   - Marcador de destino
   - Línea/polilínea de ruta
7. Usuario visualiza el mapa

**Secuencias Alternativas:**

**4a. Error en geocodificación**
- 4a.1. Sistema no puede convertir ubicación a coordenadas
- 4a.2. Sistema muestra mensaje de error
- 4a.3. Sistema muestra mapa genérico o placeholder
- 4a.4. Caso de uso termina parcialmente

**6a. Error al cargar mapa**
- 6a.1. Servicio de mapas no disponible
- 6a.2. Sistema muestra mensaje de error
- 6a.3. Caso de uso termina sin éxito

**Postcondiciones:**
- **Éxito:**
  - Usuario visualiza ruta del trayecto
  - Usuario tiene mejor comprensión del viaje
- **Fallo:**
  - No se muestra mapa
  - Información del trayecto permanece disponible en formato texto

**Reglas de Negocio:**
- ⚠️ No especificadas: proveedor de mapas, nivel de zoom, interactividad

---

### Caso de Uso 6: Matching Avanzado de Trayectos y Peticiones

**Identificador:** CU-006

**Nombre:** Motor de Asociación de Trayectos y Peticiones

**Actores:**
- **Principal:** Sistema (proceso automatizado del Motor de Matching)
- **Secundario:** Pasajero (solicita viaje), Conductor (publica trayectos)

**Precondiciones:**
- Deben existir trayectos activos publicados con roadmap definido
- Debe recibirse una petición de viaje válida con origen, destino y fecha
- Los trayectos deben tener configurado su desvío máximo permitido

**Gatillador:**
Pasajero realiza una petición de viaje especificando origen, destino, fecha y opcionalmente rango horario.

**Secuencia Normal:**
1. Sistema recibe petición de viaje del pasajero
2. Sistema valida que la fecha sea válida y el rango horario sea coherente
3. Sistema transforma direcciones/coordenadas a formato interno estándar
4. Sistema filtra trayectos publicados por coincidencia de fecha exacta
5. Para cada trayecto compatible temporalmente:
   - 5.1. Sistema evalúa coincidencia geográfica (origen próximo a algún punto del trayecto)
   - 5.2. Sistema verifica que el destino esté en un punto posterior del roadmap
   - 5.3. Sistema calcula posibles puntos de inserción en el roadmap actual
   - 5.4. Sistema estima el desvío adicional que provocaría la inserción
   - 5.5. Sistema obtiene el desvío acumulado actual del trayecto
   - 5.6. Sistema verifica: `desvío_acumulado_actual + desvío_adicional ≤ desvío_máximo_permitido`
   - 5.7. Si la verificación es exitosa, el trayecto se marca como compatible
6. Sistema calcula puntuación de adecuación para cada trayecto compatible basándose en:
   - Menor desvío adicional
   - Mayor proximidad origen/destino
   - Mejor ajuste horario
7. Sistema ordena resultados por puntuación (mejor ajuste primero)
8. Sistema devuelve lista de trayectos sugeridos con:
   - ID del trayecto
   - Ruta actual y ruta proyectada tras inserción
   - Desvío adicional estimado
   - Puntuación de compatibilidad
9. Sistema presenta sugerencias al pasajero

**Secuencias Alternativas:**

**3a. Error en geocodificación**
- 3a.1. Sistema no puede convertir ubicación a coordenadas válidas
- 3a.2. Sistema muestra mensaje de error "No se pudo procesar la ubicación"
- 3a.3. Caso de uso termina sin éxito

**4a. No hay trayectos en la fecha solicitada**
- 4a.1. Sistema no encuentra trayectos publicados para ese día
- 4a.2. Sistema muestra mensaje "No hay trayectos disponibles para la fecha seleccionada"
- 4a.3. Sistema sugiere buscar en fechas cercanas
- 4a.4. Caso de uso termina exitosamente sin resultados

**5.6a. Desvío máximo excedido**
- 5.6a.1. Sistema detecta que `desvío_acumulado + desvío_adicional > desvío_máximo`
- 5.6a.2. Trayecto se marca como NO COMPATIBLE
- 5.6a.3. Se excluye de los resultados finales
- 5.6a.4. Sistema continúa evaluando siguientes trayectos

**5a. No hay coincidencia geográfica**
- 5a.1. Origen de petición no está próximo a ningún punto del trayecto
- 5a.2. Trayecto se descarta
- 5a.3. Sistema continúa con siguiente trayecto

**7a. Ningún trayecto cumple todas las restricciones**
- 7a.1. Todos los trayectos evaluados fueron descartados
- 7a.2. Sistema muestra mensaje "No se encontraron trayectos compatibles"
- 7a.3. Sistema sugiere modificar criterios de búsqueda
- 7a.4. Caso de uso termina exitosamente sin resultados

**Postcondiciones:**
- **Éxito:**
  - Pasajero recibe lista priorizada de trayectos compatibles
  - Cada sugerencia incluye estimación clara del desvío
  - Sistema mantiene integridad de las restricciones de los conductores
  - Pasajero puede proceder a solicitar unirse a un trayecto
- **Fallo:**
  - No se muestran sugerencias
  - No se alteran los trayectos existentes
  - Sistema mantiene estado consistente

**Reglas de Negocio:**
1. **Coincidencia de fecha exacta obligatoria** - No se permiten aproximaciones de fecha
2. **Desvío máximo acumulativo es restrictivo** - Cada conductor define su límite de tolerancia
3. **Orden cronológico del roadmap inmutable** - No se permiten inserciones que alteren la secuencia lógica
4. **Trayectos con salida pasada se excluyen** - No se consideran trayectos cuyo punto de salida ya ocurrió
5. **Cálculo de desvío dinámico** - El desvío se recalcula en base al roadmap actual, no al trayecto original vacío
6. **Priorización por menor impacto** - Se favorecen las inserciones que menos afecten al trayecto original

**Datos de Ejemplo:**

*Ejemplo 1: Matching exitoso*
- **Petición:** Jerez → Dos Hermanas, 15 de marzo, entre 9:00-11:00
- **Trayecto:** Cádiz (9:00) → Sevilla (10:00), desvío máx: 30 min, desvío actual: 0 min
- **Evaluación:**
  - Coincidencia fecha: ✓
  - Jerez está en la ruta: ✓
  - Dos Hermanas está después en la ruta: ✓
  - Desvío adicional: +20 min
  - Verificación: 0 + 20 ≤ 30 ✓
- **Resultado:** COMPATIBLE, puntuación alta

*Ejemplo 2: Matching rechazado por desvío*
- **Petición:** Puerto Real → Sevilla, 15 de marzo
- **Trayecto:** Mismo trayecto anterior, ahora con desvío actual: 20 min (ya aceptó Jerez-Dos Hermanas)
- **Evaluación:**
  - Coincidencia fecha: ✓
  - Ruta geográfica compatible: ✓
  - Desvío adicional estimado: +15 min
  - Verificación: 20 + 15 = 35 > 30 ✗
- **Resultado:** NO COMPATIBLE (excede desvío máximo)

**Referencias:**
- Documento técnico: `docs/match_engine.md`
- Requisito funcional asociado: RF-006

---

### ⚠️ Información Insuficiente en docs/

**Casos de Uso No Documentados:**
- CU-AUTH: Registro e inicio de sesión
- CU-PROFILE: Gestión de perfil de usuario
- CU-CANCEL: Cancelación de reservas
- CU-EDIT: Edición de trayectos publicados
- CU-DELETE: Eliminación de trayectos
- CU-RATE: Calificación de conductor/pasajero
- CU-CHAT: Comunicación entre usuarios (bonus mencionado, no detallado)
- CU-CO2: Cálculo de CO₂ evitado (bonus mencionado, no detallado)
- CU-NOTIFY: Sistema de notificaciones
- CU-PAYMENT: Gestión de pagos (si aplica)

---

## H. Modelo de Datos

### Información Explícita (de docs/)

#### Entidades Identificadas

Las siguientes entidades se mencionan en `objetivo.md` a través de los endpoints:

**1. Trip (Trayecto)**
**2. User (Usuario)**
**3. Booking (Reserva)** - implícita en "añade pasajero a lista"

Las siguientes se identifican en el diagrama handwritten:
**4. Driver (Conductor)**
**5. Passenger (Pasajero)**

---

### Modelo de Datos - Entidades y Atributos

#### Entidad: User

| Atributo | Tipo | Restricciones | Descripción |
|----------|------|---------------|-------------|
| id | UUID/Integer | PK, NOT NULL, UNIQUE | Identificador único del usuario |
| name | String | - | Nombre del usuario |
| email | String | - | Email del usuario |
| phone | String | - | Teléfono de contacto |
| created_at | DateTime | - | Fecha de registro |

**⚠️ Atributos no especificados:**
- password/authentication
- profile_picture
- bio/description
- verification_status
- rating/reputation
- preferences
- role (driver/passenger/both)

---

#### Entidad: Driver

| Atributo | Tipo | Restricciones | Descripción |
|----------|------|---------------|-------------|
| id | UUID/Integer | PK, NOT NULL, FK(User) | Referencia a User |
| vehicle_model | String | - | Modelo del vehículo |
| vehicle_plate | String | - | Matrícula del vehículo |
| license_number | String | - | Número de licencia |

**⚠️ Atributos no especificados:**
- vehicle_capacity (max seats)
- vehicle_year
- vehicle_color
- license_expiry
- verification_documents
- insurance_info

**Nota:** Esta entidad puede ser una extensión de User o atributos adicionales en User.

---

#### Entidad: Passenger

| Atributo | Tipo | Restricciones | Descripción |
|----------|------|---------------|-------------|
| id | UUID/Integer | PK, NOT NULL, FK(User) | Referencia a User |

**⚠️ Atributos no especificados:**
- preferences
- emergency_contact
- special_requirements

**Nota:** Puede ser solo un rol en User en lugar de entidad separada.

---

#### Entidad: Trip (Trayecto)

**Información Explícita (de endpoint POST /trips):**

| Atributo | Tipo | Restricciones | Descripción |
|----------|------|---------------|-------------|
| id | UUID/Integer | PK, NOT NULL, UNIQUE, AUTO | Identificador único del trayecto |
| origin | String | NOT NULL | Punto de origen del viaje |
| destination | String | NOT NULL | Punto de destino del viaje |
| departure_date | Date | NOT NULL | Fecha del viaje |
| departure_time | Time | NOT NULL | Hora de salida |
| available_seats | Integer | NOT NULL, >= 0 | Plazas disponibles |
| driver_id | UUID/Integer | FK(User/Driver), NOT NULL | Conductor del trayecto |
| created_at | DateTime | AUTO | Fecha de creación del trayecto |

**Atributos para Motor de Matching (de match_engine.md):**

| Atributo | Tipo | Restricciones | Descripción |
|----------|------|---------------|-------------|
| origin_lat | Decimal | NOT NULL | Latitud del punto de origen |
| origin_lng | Decimal | NOT NULL | Longitud del punto de origen |
| destination_lat | Decimal | NOT NULL | Latitud del punto de destino |
| destination_lng | Decimal | NOT NULL | Longitud del punto de destino |
| estimated_arrival_time | Time | NOT NULL | Hora prevista de llegada |
| max_detour_minutes | Integer | NOT NULL, >= 0, DEFAULT 30 | Desvío máximo permitido (en minutos) |
| current_detour_minutes | Integer | NOT NULL, >= 0, DEFAULT 0 | Desvío acumulado actual (en minutos) |
| roadmap | JSON/Array | NOT NULL | Lista ordenada de waypoints/tramos actuales |

**Atributos Inferidos:**

| Atributo | Tipo | Restricciones | Descripción |
|----------|------|---------------|-------------|
| total_seats | Integer | >= 1 | Capacidad total del vehículo |
| status | Enum | DEFAULT 'active' | Estado: active, completed, cancelled |
| price | Decimal | >= 0 | Precio por plaza (opcional) |
| updated_at | DateTime | AUTO | Última actualización |

**⚠️ Atributos no especificados:**
- estimated_duration
- distance_km
- route_details (waypoints)
- flexible_timing (boolean)
- allowed_luggage
- pets_allowed
- smoking_allowed
- music_preferences
- conversation_preferences
- co2_saved (bonus feature)

---

#### Entidad: Booking (Reserva)

**Información Implícita (de endpoint POST /trips/{id}/book):**

| Atributo | Tipo | Restricciones | Descripción |
|----------|------|---------------|-------------|
| id | UUID/Integer | PK, NOT NULL, UNIQUE, AUTO | Identificador de la reserva |
| trip_id | UUID/Integer | FK(Trip), NOT NULL | Trayecto reservado |
| passenger_id | UUID/Integer | FK(User), NOT NULL | Pasajero que reserva |
| booking_date | DateTime | AUTO, NOT NULL | Fecha de la reserva |
| seats_booked | Integer | DEFAULT 1, >= 1 | Número de plazas reservadas |
| status | Enum | DEFAULT 'confirmed' | Estado: confirmed, cancelled, completed |

**Atributos Inferidos:**

| Atributo | Tipo | Restricciones | Descripción |
|----------|------|---------------|-------------|
| created_at | DateTime | AUTO | Timestamp de creación |
| updated_at | DateTime | AUTO | Timestamp de actualización |
| cancellation_date | DateTime | NULL | Fecha de cancelación si aplica |

**⚠️ Atributos no especificados:**
- payment_status
- payment_amount
- pickup_location (si difiere del origen)
- dropoff_location (si difiere del destino)
- passenger_notes
- rating_to_driver
- rating_to_passenger

---

#### Entidad: TravelRequest (Petición de Viaje)

**Información de match_engine.md:**

| Atributo | Tipo | Restricciones | Descripción |
|----------|------|---------------|-------------|
| id | UUID/Integer | PK, NOT NULL, UNIQUE, AUTO | Identificador de la petición |
| passenger_id | UUID/Integer | FK(User), NOT NULL | Pasajero que solicita el viaje |
| origin_lat | Decimal | NOT NULL | Latitud del punto de origen solicitado |
| origin_lng | Decimal | NOT NULL | Longitud del punto de origen solicitado |
| destination_lat | Decimal | NOT NULL | Latitud del punto de destino solicitado |
| destination_lng | Decimal | NOT NULL | Longitud del punto de destino solicitado |
| travel_date | Date | NOT NULL | Día del viaje solicitado |
| time_from | Time | NULL | Filtro: hora mínima de salida (opcional) |
| time_to | Time | NULL | Filtro: hora máxima de salida (opcional) |
| status | Enum | DEFAULT 'pending' | Estado: pending, matched, accepted, cancelled |
| created_at | DateTime | AUTO | Fecha de creación de la petición |
| updated_at | DateTime | AUTO | Última actualización |

**Atributos Adicionales Inferidos:**

| Atributo | Tipo | Restricciones | Descripción |
|----------|------|---------------|-------------|
| origin_address | String | NULL | Dirección textual del origen |
| destination_address | String | NULL | Dirección textual del destino |
| seats_requested | Integer | DEFAULT 1, >= 1 | Número de plazas solicitadas |
| passenger_notes | Text | NULL | Notas adicionales del pasajero |
| matched_trip_id | UUID/Integer | FK(Trip), NULL | Trayecto con el que se hizo match |

**Descripción:**
Esta entidad representa las solicitudes de viaje realizadas por pasajeros, que son evaluadas por el Motor de Matching para encontrar trayectos compatibles.

---

### Relaciones entre Entidades

```
User (1) ──< actúa como >── (0..1) Driver
User (1) ──< actúa como >── (0..1) Passenger

Driver (1) ──< publica >── (0..*) Trip
Trip (1) ──< tiene >── (0..*) Booking
Passenger (1) ──< realiza >── (0..*) Booking
Passenger (1) ──< solicita >── (0..*) TravelRequest
TravelRequest (0..1) ──< es evaluada contra >── (0..*) Trip
TravelRequest (0..1) ──< resulta en >── (0..1) Booking

Equivalente a:
User (1) ──< publica (como conductor) >── (0..*) Trip
User (1) ──< reserva (como pasajero) >── (0..*) Booking
User (1) ──< solicita (como pasajero) >── (0..*) TravelRequest
Trip (1) ──< contiene >── (0..*) Booking
Trip (0..*) ──< es sugerido para >── (0..*) TravelRequest
```

**Cardinalidades:**

| Relación | Cardinalidad | Descripción |
|----------|--------------|-------------|
| User → Driver | 1:0..1 | Un usuario puede ser conductor (opcional) |
| User → Passenger | 1:0..1 | Un usuario puede ser pasajero (opcional) |
| Driver → Trip | 1:0..* | Un conductor puede publicar múltiples trayectos |
| Trip → Booking | 1:0..* | Un trayecto puede tener múltiples reservas |
| Passenger → Booking | 1:0..* | Un pasajero puede hacer múltiples reservas |
| Passenger → TravelRequest | 1:0..* | Un pasajero puede hacer múltiples peticiones de viaje |
| TravelRequest → Trip | *:0..1 | Una petición puede resultar en match con un trayecto (opcional) |
| TravelRequest → Booking | 1:0..1 | Una petición puede resultar en una reserva (opcional) |
| Trip → Driver | *:1 | Cada trayecto tiene un único conductor |
| Booking → Trip | *:1 | Cada reserva pertenece a un único trayecto |
| Booking → Passenger | *:1 | Cada reserva es de un único pasajero |
| TravelRequest → Passenger | *:1 | Cada petición pertenece a un único pasajero |

---

### Diagrama Entidad-Relación (Textual)

```
┌─────────────────────┐
│        USER         │
├─────────────────────┤
│ id (PK)             │
│ name                │
│ email               │
│ phone               │
│ created_at          │
└─────────────────────┘
        │
        │ inherits/extends
        │
        ├──────────────────────────────┐
        │                              │
┌───────▼─────────┐          ┌────────▼──────────┐
│    DRIVER       │          │   PASSENGER       │
├─────────────────┤          ├───────────────────┤
│ id (PK,FK)      │          │ id (PK,FK)        │
│ vehicle_model   │          └───────────────────┘
│ vehicle_plate   │                    │
│ license_number  │                    │ 1
└─────────────────┘                    │
        │ 1                            │ requests
        │                              │
        │ publishes                    │ *
        │                    ┌─────────▼──────────────┐
        │ *                  │   TRAVEL_REQUEST       │
┌───────▼─────────────────┐  ├────────────────────────┤
│         TRIP            │  │ id (PK)                │
├─────────────────────────┤  │ passenger_id (FK)      │
│ id (PK)                 │  │ origin_lat/lng         │
│ origin                  │  │ destination_lat/lng    │
│ destination             │  │ travel_date            │
│ origin_lat/lng          │  │ time_from/to           │
│ destination_lat/lng     │  │ status                 │
│ departure_date          │  │ matched_trip_id (FK)   │
│ departure_time          │  └────────────────────────┘
│ estimated_arrival_time  │            │ *
│ available_seats         │            │ is_evaluated_against
│ total_seats             │            │
│ max_detour_minutes      │◄───────────┘ 0..*
│ current_detour_minutes  │
│ roadmap (JSON)          │
│ driver_id (FK)          │      ┌──────────────────┐
│ status                  │      │    BOOKING       │
│ created_at              │      ├──────────────────┤
└─────────────────────────┘      │ id (PK)          │
          │ 1                    │ trip_id (FK)     │
          │ contains             │ passenger_id(FK) │
          │                      │ booking_date     │
          │ *                    │ seats_booked     │
          └─────────────────────►│ status           │
                                 └──────────────────┘
```

---

### Reglas de Integridad

**Explícitas:**
- Cuando se crea una Booking, available_seats en Trip debe decrementarse
- Cuando se añade una Booking, el passenger_id debe añadirse a la lista del Trip

**Inferidas:**
- available_seats nunca puede ser negativo
- available_seats <= total_seats
- booking.seats_booked <= trip.available_seats (al momento de reservar)
- Un pasajero no puede reservar dos veces el mismo trayecto
- Un conductor no puede reservar su propio trayecto
- departure_date debe ser fecha futura (al crear)

**Del Motor de Matching (match_engine.md):**
- **Restricción de Desvío Acumulativo:** En todo momento debe cumplirse:
  ```
  trip.current_detour_minutes + nuevo_desvio_adicional ≤ trip.max_detour_minutes
  ```
- **Restricción de Roadmap Ordenado:** El roadmap debe mantener un orden cronológico y geográfico lógico. No se permiten inserciones que alteren la secuencia.
- **Restricción de Fecha Exacta:** Las TravelRequest solo pueden hacer match con Trips cuyo `departure_date` coincida exactamente con `travel_date`
- **Restricción de Rango Horario:** Si TravelRequest especifica `time_from` o `time_to`, el Trip debe cumplir:
  - Si `time_from` existe: `trip.departure_time >= travel_request.time_from`
  - Si `time_to` existe: `trip.departure_time <= travel_request.time_to`
- **Restricción de Disponibilidad Temporal:** No se evalúan Trips cuyo `departure_time` ya haya pasado respecto al momento actual
- **Actualización Automática del Roadmap:** Cuando se acepta una Booking derivada de un match, el Trip debe:
  1. Actualizar su `roadmap` para incluir los nuevos waypoints
  2. Recalcular y actualizar `current_detour_minutes`
  3. Decrementar `available_seats`
- **Integridad de Coordenadas:** Los atributos `origin_lat`, `origin_lng`, `destination_lat`, `destination_lng` deben contener coordenadas geográficas válidas:
  - Latitud: -90 ≤ lat ≤ 90
  - Longitud: -180 ≤ lng ≤ 180

### ⚠️ Información Insuficiente en docs/

**Entidades Potenciales No Documentadas:**
- **Location:** Geocoordenadas, direcciones detalladas
- **Route:** Ruta detallada con waypoints
- **Review/Rating:** Sistema de calificaciones
- **Message:** Chat entre usuarios (bonus mencionado)
- **Notification:** Sistema de notificaciones
- **Payment:** Transacciones y pagos
- **Report:** Reportes de usuarios
- **Vehicle:** Detalles completos del vehículo

**Atributos y Relaciones No Especificados:**
- Timestamps completos (created_at, updated_at, deleted_at)
- Soft deletes
- Índices para optimización
- Constraints específicos
- Triggers o stored procedures
- Políticas de cascade (ON DELETE, ON UPDATE)

---

## I. Roadmap y Backlog Inicial

### Información Explícita (de docs/)

#### Fase 1: MVP (Producto Mínimo Viable)

**Objetivo:** Sistema básico funcional de carpooling

**Características Core:**

1. **Publicación de Trayectos**
   - Endpoint: `POST /trips`
   - Criterio de Aceptación:
     - ✓ Conductor puede crear trayecto con origen, destino, fecha/hora y plazas
     - ✓ Sistema asigna ID único
     - ✓ Trayecto se almacena correctamente

2. **Búsqueda de Trayectos**
   - Endpoint: `GET /trips?from=A&to=B`
   - Criterio de Aceptación:
     - ✓ Pasajero puede buscar por origen y destino
     - ✓ Sistema retorna trayectos coincidentes
     - ✓ Búsqueda puede ser exacta o aproximada por ciudad

3. **Reserva de Trayectos**
   - Endpoint: `POST /trips/{trip_id}/book`
   - Criterio de Aceptación:
     - ✓ Pasajero puede reservar plaza en trayecto disponible
     - ✓ Sistema decrementa plazas disponibles
     - ✓ Sistema añade pasajero a lista del trayecto
     - ✓ Validación de disponibilidad antes de confirmar

4. **Listado de Reservas**
   - Endpoint: `GET /users/{id}/bookings`
   - Criterio de Aceptación:
     - ✓ Usuario puede ver todas sus reservas
     - ✓ Información completa de cada reserva
     - ✓ Datos del trayecto y conductor visibles

5. **Visualización en Mapa**
   - Criterio de Aceptación:
     - ✓ Ruta se muestra visualmente en un mapa
     - ✓ Origen y destino claramente marcados
     - ✓ Integración funcional con servicio de mapas

6. **Matching Básico**
   - Criterio de Aceptación:
     - ✓ Sistema identifica coincidencias entre trayectos y usuarios
     - ✓ Algoritmo básico de matching implementado
     - ✓ Simulación funcional

**Dependencias MVP:**
- Backend API funcional
- Base de datos configurada
- Servicio de mapas integrado

**⚠️ No especificado en MVP:**
- Frontend/interfaz de usuario
- Autenticación completa
- Sistema de pagos
- Notificaciones

---

#### Fase 2: Bonus Features (Si hay tiempo)

**Características Opcionales:**

1. **Matching Aproximado Geográfico**
   - Descripción: Matching por distancia geográfica usando geocodificación
   - Criterio de Aceptación:
     - ✓ Sistema usa coordenadas geográficas
     - ✓ Matching considera proximidad, no solo coincidencia exacta
     - ✓ Radio de distancia configurable
   - Dependencias: Servicio de geocodificación integrado
   - **⚠️ Prioridad:** No especificada
   - **⚠️ Complejidad:** No estimada

2. **Estimación de CO₂ Evitado**
   - Descripción: Calcular y mostrar CO₂ evitado por trayecto
   - Criterio de Aceptación:
     - ✓ Sistema calcula emisiones por trayecto
     - ✓ Muestra CO₂ evitado al compartir viaje
     - ✓ Datos basados en distancia y tipo de vehículo
   - **⚠️ Dependencias:** No especificadas (fórmulas de cálculo, factores de emisión)
   - **⚠️ Prioridad:** No especificada
   - **⚠️ Complejidad:** No estimada

3. **Visualización de Reservas de Otros Usuarios**
   - Descripción: Ver reservas realizadas por otros usuarios
   - Criterio de Aceptación:
     - ✓ Sistema permite consultar reservas públicas
     - ✓ Información de privacidad respetada
   - **⚠️ Propósito:** No especificado
   - **⚠️ Nivel de detalle:** No especificado
   - **⚠️ Prioridad:** No especificada

4. **Chat Simulado**
   - Descripción: Comunicación simulada entre pasajero y conductor
   - Criterio de Aceptación:
     - ✓ Interfaz de chat funcional
     - ✓ Mensajes entre usuarios específicos de un trayecto
   - **⚠️ Tipo de simulación:** No especificada (¿bot? ¿mensajes predefinidos?)
   - **⚠️ Persistencia:** No especificada
   - **⚠️ Prioridad:** No especificada

---

### Roadmap Inferido

#### Sprint 0: Setup y Configuración
**Duración:** ⚠️ No especificada

- Configuración del entorno de desarrollo
- Selección de tecnologías (framework, BD)
- Setup de repositorio y CI/CD básico
- Configuración de base de datos
- Configuración de Claude Code y agents

#### Sprint 1: Backend Core - Trayectos
**Duración:** ⚠️ No especificada

**User Stories:**
- US-001: Como conductor, quiero publicar un trayecto para compartir mi vehículo
  - Implementar `POST /trips`
  - Validación de datos
  - Persistencia en BD

- US-002: Como pasajero, quiero buscar trayectos para encontrar transporte
  - Implementar `GET /trips?from=A&to=B`
  - Lógica de búsqueda y filtrado
  - Optimización de consultas

**Entregables:**
- API endpoints de Trip funcionales
- Tests unitarios e integración
- Documentación de API

**Dependencias:**
- Base de datos modelada y configurada

---

#### Sprint 2: Backend Core - Reservas
**Duración:** ⚠️ No especificada

**User Stories:**
- US-003: Como pasajero, quiero reservar un trayecto para asegurar mi plaza
  - Implementar `POST /trips/{id}/book`
  - Lógica de decremento de plazas
  - Validaciones de disponibilidad
  - Manejo de transacciones

- US-004: Como usuario, quiero ver mis reservas para gestionar mis viajes
  - Implementar `GET /users/{id}/bookings`
  - Relación Trip-Booking-User

**Entregables:**
- Sistema de reservas funcional
- Tests de casos edge (overbooking, etc.)
- Documentación actualizada

**Dependencias:**
- Sprint 1 completado

---

#### Sprint 3: Integraciones - Mapas y Matching
**Duración:** ⚠️ No especificada

**User Stories:**
- US-005: Como usuario, quiero ver el trayecto en un mapa para visualizar la ruta
  - Integración con servicio de mapas
  - Geocodificación de ubicaciones
  - Renderizado de ruta

- US-006: Como usuario, quiero recibir sugerencias de trayectos compatibles
  - Implementar algoritmo de matching básico
  - Simulación de notificaciones/sugerencias

**Entregables:**
- Visualización de mapas funcional
- Sistema de matching básico
- Tests de integración con servicios externos

**Dependencias:**
- Sprint 2 completado
- Cuenta/API key de servicio de mapas

---

#### Sprint 4 (Opcional): Bonus Features
**Duración:** ⚠️ No especificada

**User Stories:**
- US-BONUS-001: Matching geográfico aproximado
- US-BONUS-002: Cálculo de CO₂ evitado
- US-BONUS-003: Visualización de reservas públicas
- US-BONUS-004: Chat simulado

**Criterio de Inclusión:**
Solo si hay tiempo disponible después de completar MVP.

**Priorización:** ⚠️ No especificada - Se sugiere:
1. Matching geográfico (mejora significativa de UX)
2. CO₂ evitado (valor agregado, conciencia ambiental)
3. Chat simulado (mejora comunicación)
4. Visualización de reservas públicas (menos clara la utilidad)

---

### Backlog Inicial - User Stories del MVP

**Épica: Gestión de Trayectos**

- [ ] US-001: Publicar trayecto como conductor
  - Prioridad: ALTA
  - Story Points: ⚠️ No estimado
  - DoD: Endpoint funcional, validaciones, tests, documentación

- [ ] US-002: Buscar trayectos disponibles
  - Prioridad: ALTA
  - Story Points: ⚠️ No estimado
  - DoD: Búsqueda exacta y aproximada, filtros, tests

**Épica: Gestión de Reservas**

- [ ] US-003: Reservar plaza en trayecto
  - Prioridad: ALTA
  - Story Points: ⚠️ No estimado
  - DoD: Booking funcional, actualización de plazas, validaciones, tests

- [ ] US-004: Ver mis reservas
  - Prioridad: ALTA
  - Story Points: ⚠️ No estimado
  - DoD: Listado completo, información detallada, tests

**Épica: Visualización y Matching**

- [ ] US-005: Visualizar trayecto en mapa
  - Prioridad: ALTA
  - Story Points: ⚠️ No estimado
  - DoD: Integración con mapas, geocodificación, ruta visible

- [ ] US-006: Matching básico entre usuarios
  - Prioridad: ALTA
  - Story Points: ⚠️ No estimado
  - DoD: Algoritmo implementado, simulación funcional, tests

**Épica: Bonus Features**

- [ ] US-BONUS-001: Matching geográfico aproximado
  - Prioridad: BAJA (opcional)
  - Story Points: ⚠️ No estimado

- [ ] US-BONUS-002: Estimación de CO₂ evitado
  - Prioridad: BAJA (opcional)
  - Story Points: ⚠️ No estimado

- [ ] US-BONUS-003: Visualización de reservas públicas
  - Prioridad: BAJA (opcional)
  - Story Points: ⚠️ No estimado

- [ ] US-BONUS-004: Chat simulado
  - Prioridad: BAJA (opcional)
  - Story Points: ⚠️ No estimado

---

### Hitos y Dependencias

**Hito 1: Backend API Básico**
- Fecha: ⚠️ No especificada
- Criterio: Endpoints de trayectos y reservas funcionales
- Dependencias: Ninguna

**Hito 2: MVP Completo**
- Fecha: ⚠️ No especificada
- Criterio: Todas las funcionalidades core implementadas y probadas
- Dependencias: Hito 1

**Hito 3: Demo Funcional**
- Fecha: ⚠️ Según timeline del hackathon
- Criterio: Sistema desplegado localmente, demo preparada
- Dependencias: Hito 2

**Hito 4 (Opcional): MVP + Bonus**
- Fecha: ⚠️ Si hay tiempo
- Criterio: Al menos 2 features bonus implementadas
- Dependencias: Hito 2

---

### Riesgos e Impedimentos Potenciales (Inferidos)

⚠️ **IMPORTANTE:** Los siguientes riesgos son inferidos, NO están en docs/

1. **Integración con servicio de mapas**
   - Riesgo: APIs complejas, límites de uso
   - Mitigación: Seleccionar proveedor con buen free tier

2. **Autenticación de usuarios**
   - Riesgo: No está especificada pero es necesaria
   - Mitigación: Implementación simplificada para MVP

3. **Tiempo limitado de hackathon**
   - Riesgo: No completar MVP
   - Mitigación: Priorización estricta, features bonus realmente opcionales

4. **Algoritmo de matching**
   - Riesgo: Complejidad no estimada
   - Mitigación: Versión "básica" simplificada para MVP

---

### ⚠️ Información Insuficiente en docs/

**Planificación:**
- **Timeline específico:** Duración del hackathon, deadlines
- **Estimaciones:** Story points, tiempo por feature
- **Recursos:** Tamaño del equipo, roles
- **Tecnologías:** Stack tecnológico específico
- **Entorno:** Setup de desarrollo, despliegue

**Criterios de Aceptación Detallados:**
- Definición de Done (DoD) específica
- Criterios de calidad (cobertura de tests, performance)
- Proceso de QA

**Backlog Secundario:**
- Historias de infraestructura
- Historias de testing
- Historias de documentación
- Historias de UX/UI (frontend fuera de scope pero necesario para demo)

**Post-MVP:**
- Visión a largo plazo
- Roadmap post-hackathon
- Plan de evolución del producto

---

## Resumen de Lagunas de Información

### Documentación Completa ✅
- Objetivo del hackathon y contexto
- Funcionalidades core del MVP
- Endpoints básicos de API
- Estructura de datos básica (parcial)
- **Motor de Matching detallado (docs/match_engine.md):**
  - Reglas de asociación geográfica y temporal
  - Sistema de desvío máximo acumulativo
  - Algoritmo de inserción en roadmap
  - Criterios de priorización y ranking
  - Casos de uso ejemplares

### Documentación Parcial ⚠️
- Modelo de datos (entidades identificadas pero atributos incompletos)
- Flujos de usuario (inferibles de los endpoints)
- Casos de uso (construibles a partir de funcionalidades)

### Documentación Ausente ❌
- Requisitos no funcionales completos
- Seguridad y autenticación
- Detalles de implementación técnica
- Frontend/UI specifications
- Testing strategy
- Deployment plan
- Timeline específico
- Estimaciones de esfuerzo
- Criterios de aceptación detallados
- Reglas de negocio específicas
- Manejo de errores y casos edge
- Políticas de datos y privacidad

---

**Nota Final:** Esta documentación ha sido construida a partir de la información disponible en:
- `docs/objetivo.md` - Objetivos principales del MVP y funcionalidades core
- `docs/5814446323997019017.jpg` - Diagrama handwritten de arquitectura inicial
- `docs/match_engine.md` - Especificación detallada del Motor de Asociación de Trayectos y Peticiones

Todas las secciones marcadas con ⚠️ indican áreas donde la información en `docs/` es insuficiente o inexistente. Las secciones inferidas están claramente marcadas como tal y se basan en prácticas estándar de desarrollo de software aplicadas al contexto del proyecto.

**Actualización:** El documento ha sido enriquecido con información detallada del motor de matching, incluyendo:
- Reglas de asociación geográfica y temporal
- Sistema de desvío máximo acumulativo
- Gestión dinámica de roadmap
- Criterios de priorización y ranking
- Nueva entidad TravelRequest en el modelo de datos
- Atributos adicionales en la entidad Trip para soportar matching avanzado
- Reglas de integridad específicas del motor de matching
