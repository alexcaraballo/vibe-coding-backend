
# Redacción del modelo de asignación

## **Módulo: Motor de Asociación de Trayectos y Peticiones**

---

### **1. Objetivo del sistema**

El objetivo del motor de asociación es identificar, entre los trayectos publicados por conductores, aquellos que pueden **admitir una nueva petición de viaje** sin violar las restricciones definidas por los conductores ni las condiciones solicitadas por los pasajeros.

El sistema debe sugerir los trayectos más adecuados para cada petición entrante, considerando factores como la ruta, la fecha, el rango horario, y el desvío máximo permitido por cada conductor.

---

### **2. Alcance**

El módulo forma parte del sistema de carpooling y se encarga exclusivamente del **proceso de búsqueda y filtrado** que determina las coincidencias entre:

- Una **petición de viaje entrante** (solicitud de un pasajero).
- Los **trayectos activos o publicados** (creados por conductores).

El resultado del módulo son **sugerencias de trayectos compatibles**, priorizadas según su nivel de adecuación.  
No forma parte de este módulo la gestión de usuarios, pagos, notificaciones o planificación de rutas detallada posterior.

---

### **3. Actores implicados**

- **Pasajero:** realiza una petición de viaje indicando origen, destino, fecha y posibles filtros de hora.
- **Conductor:** publica trayectos con su ruta, horario y desvío máximo permitido.
- **Sistema de Matching:** componente funcional que analiza peticiones entrantes, evalúa trayectos disponibles y devuelve coincidencias posibles.

---

### **4. Entradas**

#### 4.1. Petición de viaje (input del pasajero)

Cada petición incluye:
- **Origen:** coordenadas geográficas (latitud, longitud).
- **Destino:** coordenadas geográficas (latitud, longitud).
- **Día del viaje:** fecha en la que se desea realizar el trayecto.
- **Filtros opcionales:**
    - “A partir de esta hora”.
    - “Antes de esta hora”.

#### 4.2. Trayecto publicado (input del conductor)

Cada trayecto disponible incluye:

- **Origen y destino:** coordenadas geográficas.
- **Hora de salida y hora prevista de llegada.**
- **Desvío máximo permitido (expresado en minutos o porcentaje de duración original).**
- **Roadmap actual:** lista ordenada de tramos resultantes de las peticiones ya aceptadas (por ejemplo, Cádiz → Jerez → Dos Hermanas → Sevilla).
- **Desvío acumulado actual:** minutos adicionales que ya se han consumido respecto al trayecto original.

---

### **5. Salidas**

El sistema devuelve una **lista de trayectos sugeridos**, cada uno con:
- Identificador del trayecto.
- Descripción de la ruta actual.
- Estimación del desvío adicional que supondría insertar la nueva petición.
- Estado de compatibilidad (apto/no apto).
- Nivel de coincidencia o puntuación de ajuste (ranking).

---

### **6. Funcionalidades principales**

1. **Recepción y validación de peticiones de viaje.**
    - Comprobación de que el día y el rango horario son válidos.
    - Transformación de direcciones o coordenadas a formato interno estándar.
2. **Evaluación de trayectos publicados.**
    - Filtrado por coincidencia de fecha.
    - Evaluación de posibles inserciones de la nueva petición en el roadmap del trayecto.
    - Cálculo del impacto temporal (nuevo tiempo total del trayecto).
3. **Verificación del desvío máximo acumulativo.**
    - Determinar el **desvío total actual** del trayecto.
    - Calcular el **nuevo desvío proyectado** al insertar la petición.
    - Validar que el total no supere el **desvío máximo establecido por el conductor**.
4. **Generación de resultados.**
    - Solo se devuelven los trayectos que cumplan todas las restricciones.
    - Los resultados pueden ordenarse por cercanía de origen/destino, menor desvío, o mejor ajuste horario.

---

### **7. Reglas de asociación o coincidencia**

1. **Coincidencia geográfica:**
    - El origen de la petición debe estar razonablemente próximo a algún punto del trayecto (inicio, parada intermedia o segmento).
    - El destino de la petición debe encontrarse en un punto posterior dentro del orden lógico del trayecto.
2. **Coincidencia temporal:**
    - El día debe coincidir exactamente.
    - Si la petición tiene rango horario, la hora de paso prevista por el trayecto debe respetarlo.
3. **Desvío máximo acumulativo:**
    - Cada trayecto tiene un **límite máximo de desvío** (por ejemplo, 30 minutos).
    - Cada nueva inserción consume parte de ese margen.
    - El sistema debe garantizar que la suma del **desvío acumulado actual + desvío adicional proyectado ≤ desvío máximo permitido**.
    - Si esta condición no se cumple, el trayecto no es elegible para esa petición.
4. **Compatibilidad lógica:**
    - No se permiten inserciones que alteren el orden cronológico del roadmap.
    - No se consideran trayectos cuyo punto de salida ya haya sido superado respecto al momento actual.

---

### **8. Criterios de priorización o ranking**

El sistema debe poder asignar un **nivel de adecuación** a cada coincidencia válida.  
Los criterios principales pueden ser:
1. **Menor desvío adicional provocado.**
2. **Mayor proximidad entre los puntos de origen/destino del pasajero y los del trayecto.**
3. **Ajuste horario más cercano al solicitado.**

---

### **9. Restricciones funcionales**

- El cálculo del desvío debe ser dinámico y acumulativo, basado en la ruta real tras cada inserción.
- El sistema debe poder evaluar varios trayectos activos simultáneamente.
- Los trayectos se actualizan automáticamente tras aceptar una nueva petición (recomposición del roadmap y actualización del desvío acumulado).

---

### **10. Casos de uso ejemplares**

#### Caso 1: Inserción válida
- Trayecto: Cádiz → Sevilla (9:00–10:00), desvío máximo 30 min.
- Petición: Jerez → Dos Hermanas.
- Desvío adicional estimado: +20 min.
- Resultado: **Aceptado.** Desvío acumulado = 20 min.

#### Caso 2: Inserción excede desvío máximo
- Mismo trayecto con desvío acumulado de 20 min.
- Nueva petición: Puerto Real → Sevilla (+15 min).
- Resultado: **Rechazado.** Desvío total proyectado = 35 min > 30 min.

---
