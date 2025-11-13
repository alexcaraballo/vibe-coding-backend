# Resumen de Sesión - Creación de Issues desde Documentación Funcional

**Fecha**: 2025-11-13
**Repositorio**: https://github.com/alexcaraballo/vibe-coding-backend

---

## Objetivo de la Sesión

Generar issues de GitHub automáticamente a partir de los requisitos funcionales documentados en `documentacion_funcional.md`, estructurando cada issue con información completa y etiquetas apropiadas.

---

## Trabajo Realizado

### 1. Lectura y Análisis de Documentación

Se leyó el archivo `documentacion_funcional.md` que contiene:
- 6 Requisitos Funcionales Core (RF-001 a RF-006)
- 4 Requisitos Funcionales Bonus (RF-BONUS-001 a RF-BONUS-004)
- 4 Requisitos Funcionales Inferidos (RF-INF-001 a RF-INF-004)

### 2. Creación de Labels en GitHub

Se crearon los siguientes labels para clasificar las issues:

**Labels de tipo:**
- `enhancement` - Características nuevas (ya existía)
- `functional-requirement` - Requisitos funcionales del sistema
- `bonus-feature` - Funcionalidades bonus opcionales
- `inferred-requirement` - Requisitos inferidos pero necesarios

**Labels por requisito específico:**
- `RF-001` hasta `RF-006` - Para requisitos core
- `RF-BONUS-001` hasta `RF-BONUS-004` - Para bonus features
- `RF-INF-001` hasta `RF-INF-004` - Para requisitos inferidos

### 3. Issues Creadas (Total: 14)

#### Requisitos Funcionales Core (6 issues)

| Issue # | Título | Labels | URL |
|---------|--------|--------|-----|
| #1 | [RF-001] Publicación de Trayectos | enhancement, functional-requirement, RF-001 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/1) |
| #2 | [RF-002] Búsqueda de Trayectos | enhancement, functional-requirement, RF-002 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/2) |
| #3 | [RF-003] Reserva de Trayectos | enhancement, functional-requirement, RF-003 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/3) |
| #4 | [RF-004] Listado de Reservas de Usuario | enhancement, functional-requirement, RF-004 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/4) |
| #5 | [RF-005] Visualización de Rutas en Mapa | enhancement, functional-requirement, RF-005 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/5) |
| #6 | [RF-006] Motor de Asociación de Trayectos (Matching Avanzado) | enhancement, functional-requirement, RF-006 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/6) |

#### Requisitos Funcionales Bonus (4 issues)

| Issue # | Título | Labels | URL |
|---------|--------|--------|-----|
| #7 | [RF-BONUS-001] Matching Aproximado Geográfico | enhancement, bonus-feature, functional-requirement, RF-BONUS-001 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/7) |
| #8 | [RF-BONUS-002] Estimación de CO₂ Evitado | enhancement, bonus-feature, functional-requirement, RF-BONUS-002 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/8) |
| #9 | [RF-BONUS-003] Visualización de Reservas de Otros Usuarios | enhancement, bonus-feature, functional-requirement, RF-BONUS-003 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/9) |
| #10 | [RF-BONUS-004] Chat Simulado | enhancement, bonus-feature, functional-requirement, RF-BONUS-004 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/10) |

#### Requisitos Funcionales Inferidos (4 issues)

| Issue # | Título | Labels | URL |
|---------|--------|--------|-----|
| #11 | [RF-INF-001] Gestión de Usuarios | enhancement, inferred-requirement, functional-requirement, RF-INF-001 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/11) |
| #12 | [RF-INF-002] Validación de Disponibilidad | enhancement, inferred-requirement, functional-requirement, RF-INF-002 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/12) |
| #13 | [RF-INF-003] Cancelación de Reservas | enhancement, inferred-requirement, functional-requirement, RF-INF-003 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/13) |
| #14 | [RF-INF-004] Gestión de Plazas | enhancement, inferred-requirement, functional-requirement, RF-INF-004 | [Link](https://github.com/alexcaraballo/vibe-coding-backend/issues/14) |

### 4. Estructura de Cada Issue

Cada issue sigue esta estructura consistente:

```markdown
## Descripción
[Explicación clara del requisito]

## Contexto
[Contexto de negocio e importancia]

## Criterios de aceptación
- [Criterios en bullet points]

## Reglas de negocio
- [Reglas específicas]

## Flujo principal
1. [Pasos numerados del flujo]

## Flujos alternativos / excepciones
- [Casos alternativos y manejo de errores]

## Dependencias
- [Otros requisitos o servicios necesarios]

## Notas técnicas
- [Detalles de implementación, endpoints, modelos de datos, etc.]

> Origen del requisito: RF-XXXX
```

### 5. Actualización Posterior - RF-006

Tras actualización de `documentacion_funcional.md`, se actualizó la **Issue #6** con información detallada del Motor de Asociación de Trayectos incluyendo:

**Nuevos conceptos añadidos:**
- Sistema de desvío máximo acumulativo
- Gestión de roadmap dinámico con waypoints
- Nueva entidad `TravelRequest` (Petición de Viaje)
- Algoritmo de matching con pseudocódigo
- Campos adicionales en Trip:
  - `origin_lat`, `origin_lng`, `destination_lat`, `destination_lng`
  - `estimated_arrival_time`
  - `max_detour_minutes` (default 30)
  - `current_detour_minutes` (default 0)
  - `roadmap` (JSON)
- Casos de uso ejemplares con cálculos reales
- Restricción crítica: `desvío_actual + desvío_adicional ≤ desvío_máximo`
- Endpoints sugeridos para sistema de peticiones
- Funciones auxiliares necesarias

---

## Beneficios Logrados

✅ **14 issues bien estructuradas** con información completa
✅ **Sistema de labels consistente** para facilitar filtrado
✅ **Documentación técnica detallada** en cada issue
✅ **Trazabilidad clara** entre docs y issues
✅ **Priorización implícita** (core vs bonus vs inferidos)
✅ **Base sólida** para planificación de sprints

---

## Comandos Útiles

### Ver todas las issues
```bash
gh issue list --limit 20
```

### Filtrar por label
```bash
gh issue list --label "functional-requirement"
gh issue list --label "bonus-feature"
gh issue list --label "inferred-requirement"
```

### Filtrar por requisito específico
```bash
gh issue list --label "RF-001"
gh issue list --label "RF-006"
```

### Ver issue específica
```bash
gh issue view 6
```

---

## Próximos Pasos Sugeridos

1. **Priorización**: Revisar y asignar story points a cada issue
2. **Asignación**: Distribuir issues entre el equipo
3. **Milestones**: Crear milestones para MVP, Bonus Features, etc.
4. **Dependencies**: Usar GitHub Projects para visualizar dependencias
5. **Sprint Planning**: Agrupar issues en sprints según prioridad

---

## Archivos Relacionados

- `documentacion_funcional.md` - Documentación fuente de requisitos
- `docs/objetivo.md` - Objetivos del MVP
- `docs/match_engine.md` - Especificación detallada del motor de matching
- `docs/5814446323997019017.jpg` - Diagrama arquitectónico inicial

---

## Notas Importantes

⚠️ **RF-006 (Motor de Matching)** es el requisito más complejo y requiere:
- Algoritmos de cálculo de rutas y desvíos
- Servicios de geocodificación
- Manejo de coordenadas geográficas
- Testing exhaustivo de casos edge

⚠️ **RF-INF-001 (Gestión de Usuarios)** es requisito base crítico aunque no esté explícito en docs originales

⚠️ Considerar implementar **RF-001 a RF-004** primero antes de abordar RF-005 y RF-006

---

**Repositorio**: https://github.com/alexcaraballo/vibe-coding-backend
**Issues URL**: https://github.com/alexcaraballo/vibe-coding-backend/issues
