# VUELOS-Y-ESCALAS-estructura-de-datos-
Una aerolínea regional opera una red de rutas entre ciudades de América Latina. Un viajero frecuente desea planificar sus desplazamientos de la forma más eficiente posible: maximizando los destinos visitados dentro de su presupuesto y tiempo disponibles.

La estructura que se pretende usar en este proyecto es la de capas:

SEPARACIÓN CLARA DE RESPONSABILIDADES:
main.py → punto de entrada, sin lógica.
models/ → solo definición de datos (entidades: Airport, Route, Aircraft, Itinerary).
core/ → estructuras fundamentales (grafo).
services/ → lógica de negocio (optimización, planificación, reportes).
ui/ → presentación, sin lógica de negocio.
utils/ → constantes y utilidades.

CAPAS BIEN DEFINIDAS:
Entidad (Domain Models): models/
Infraestructura (Core + Utils): core/, utils/
Aplicación (Services): services/
Presentación (UI): ui/
Entrada principal: main.py

ESTRUCTURA OBJETIVO (dispuesta a cambios): # 📁 skyroute_planner/
├── 📄 main.py                # Punto de entrada, solo lanza la app
│
├── 📁 data/
│   └── 📄 airports.json       # 30+ aeropuertos
│
├── 📁 models/                 # Solo datos, cero lógica
│   ├── 📄 airport.py          # Clase Airport (nodo)
│   ├── 📄 route.py            # Clase Route (arista)
│   ├── 📄 aircraft.py         # Tipos de aeronave y tarifas
│   └── 📄 itinerary.py        # Resultado de ruta calculada
│
├── 📁 core/                   # Solo estructura de datos
│   └── 📄 graph.py            # Grafo lista de adyacencia (desde cero)
│
├── 📁 services/               # Lógica de negocio
│   ├── 📄 base_optimizer.py   # Clase abstracta para optimizadores
│   ├── 📄 graph_loader.py     # JSON → Graph
│   ├── 📄 route_optimizer.py  # Dijkstra (costo, tiempo, distancia)
│   ├── 📄 itinerary_planner.py# Máx destinos con restricciones
│   ├── 📄 advanced_planner.py # Planificación dinámica R3
│   ├── 📄 network_manager.py  # Interrupciones R4
│   └── 📄 report_generator.py # Consolida datos de todos los módulos
│
├── 📁 ui/                     # Solo visualización, sin lógica
│   ├── 📄 app.py              # Ventana principal, une los paneles
│   ├── 📄 graph_canvas.py     # Dibuja el grafo en Canvas
│   ├── 📄 planner_panel.py    # UI de planificación básica R2
│   ├── 📄 advanced_panel.py   # UI planificación avanzada R3
│   └── 📄 report_panel.py     # UI reporte final R5
│
└── 📁 utils/
    └── 📄 constants.py        # Tarifas default aeronaves, intervalos


## Implementación actual de R3

La lógica de planificación avanzada ya no está dispersa en un solo bloque: ahora está separada entre `services/advanced_planner.py`, `services/trip_session.py` y los mixins de `services/trip_session_*.py`, mientras que `models/` concentra solo los datos y resultados que la sesión intercambia con la UI.

### 4. Planificación de itinerario avanzada

La planificación avanzada se inicia desde `AdvancedPlanner.start_session(...)`, que construye una `TripSession` con:

- `TripConfig`: presupuesto inicial, tiempo disponible, aeronaves preferidas, umbral de trabajo y sobrescrituras globales.
- `TripState`: estado mutable de la sesión, con aeropuerto actual, presupuesto restante, tiempo transcurrido, tiempo restante, itinerario, decisiones y acumuladores de comida/alojamiento.

La sesión trabaja paso a paso:

- `TripSessionTransportMixin.step_proposals()` devuelve las rutas, actividades y trabajos disponibles en el aeropuerto actual.
- `TripSessionDecisionMixin.apply_choice()` aplica la decisión elegida por el viajero y actualiza presupuesto, tiempo, itinerario y registro de decisiones.
- `StepProposalResult` resume las alternativas del paso actual.
- `ApplyResult` devuelve el estado actualizado, los eventos generados y las nuevas propuestas cuando corresponde.

Cada decisión queda registrada en `DecisionRecord`, de modo que la sesión conserva trazabilidad de vuelos, actividades, trabajos e interrupciones.

### 5. Actividades

El modelo `Activity` representa tanto actividades obligatorias como opcionales con tiempo de ejecución y costo en USD.

La implementación actual cubre estas reglas:

- `TripSessionClockMixin.advance_time(...)` controla el paso del tiempo y dispara los cobros obligatorios.
- Alojamiento: se cobra cada 20 horas de acuerdo con el costo del aeropuerto, y si esas horas se cumplen durante un vuelo queda pendiente hasta aterrizar.
- Alimentación: se cobra cada 8 horas. Si el umbral se cumple durante un vuelo, el costo se toma del último aeropuerto visitado.
- Las actividades opcionales se presentan en `step_proposals()` para que el viajero elija si las realiza o no.

### 6. Trabajos

Los trabajos temporales se modelan con `JobOffer`, que incluye tarifa por hora y máximo de horas permitidas.

La sesión ya contempla:

- habilitar trabajos cuando el presupuesto restante cae por debajo del 35% del presupuesto inicial;
- permitir que el viajero indique cuántas horas trabajará;
- calcular el ingreso como `tarifa_por_hora × horas_trabajadas`;
- actualizar presupuesto y tiempo restante con ese trabajo;
- guardar el resultado en `state.jobs_done` y en `DecisionRecord`.

### 7. Medios de transporte

Las rutas y opciones de vuelo se representan con `RouteProposal`, `TransportOption` y `Leg`.

La lógica actual de transporte hace lo siguiente:

- calcula el costo y el tiempo del tramo según distancia y tipo de aeronave;
- usa las tarifas por defecto definidas en `utils/constants.py`;
- permite sobrescribir esas tarifas desde la configuración global o desde el JSON;
- respeta la restricción de que la distancia subsidiada no puede superar el 20% del total recorrido;
- expone en `step_proposals()` todas las alternativas de vuelo calculadas para que el viajero compare antes de decidir.

### Archivos clave de la implementación

- `services/advanced_planner.py`: crea la sesión avanzada y arma el estado inicial.
- `services/trip_session.py`: compone la sesión con los mixins de transporte, decisiones, reloj y reportes.
- `services/trip_session_transport.py`: calcula rutas, costos y tiempos, y arma las propuestas del paso.
- `services/trip_session_decisions.py`: aplica decisiones de vuelo, actividad y trabajo.
- `services/trip_session_clock.py`: avanza el tiempo y registra comida y alojamiento obligatorios.
- `services/trip_session_reporting.py`: maneja interrupciones de vuelo, recalculo de propuestas y reporte final.
- `models/`: contiene los dataclasses y entidades de salida usados por la sesión.


Contrato de endponits para que analicen:
## Error codes reference

| Code | Meaning |
|---|---|
| `400` | Bad request — missing or invalid fields in body |
| `404` | Endpoint or resource not found |
| `409` | Conflict — e.g. session already exists, route already blocked |
| `422` | Valid JSON but business rule violated — e.g. budget exceeded, no transport selected |
| `500` | Internal server error |

---

## Who owns what

| Endpoint | Owner | Day ready |
|---|---|---|
| `GET /api/health` | Int.1 | Day 1|
| `GET /api/graph` | Int.1 | Day 1 (stub) → Day 3 (real graph) |
| `POST /api/plan/basic` | Int.2 | Day 4 |
| `POST /api/plan/route` | Int.2 | Day 4 |
| `POST /api/plan/advanced/start` | Int.3 | Day 6 |
| `POST /api/plan/advanced/step` | Int.3 | Day 6 |
| `POST /api/network/block` | Int.1 | Day 6 |
| `POST /api/network/recalculate` | Int.1 | Day 7 |
| `GET /api/report/<id>` | Int.2 | Day 6 |



PARA TENER EN CUENTA CUANDO VAYAN A USAR LOS ENDPOINTS IMPORTANDO CLIENT.JS:


# SkyRoute Planner — API Contracts

**Stack:** Python + Flask (backend) · HTML / JS ES6 / D3.js (frontend)  
**Base URL:** `http://localhost:5000`  
**All requests:** `Content-Type: application/json`  
**All responses:** JSON with the standard envelope below.

---

## Standard response envelope

Every endpoint returns this shape. Components always check `error` before using `data`.

```json
{ "error": false, "data": { ... } }
{ "error": true,  "message": "Human-readable reason", "code": 400 }
```

---

## R1 — Graph (Int.1)

### `GET /api/health`

Verify the server is running and the JSON was loaded.

**Response**
```json
{
  "error": false,
  "status": "ok",
  "airports": 31,
  "routes": 102,
  "graph_loaded": true
}
```

---

### `GET /api/graph`

Full airport network for D3.js visualization.

**Response**
```json
{
  "error": false,
  "data": {
    "nodes": [
      {
        "id": "BOG",
        "nombre": "Aeropuerto El Dorado",
        "ciudad": "Bogotá",
        "pais": "Colombia",
        "zonaHoraria": "America/Bogota",
        "esHub": true,
        "costoAlojamiento": 55,
        "costoAlimentacion": 10,
        "actividades": [
          { "nombre": "Tour La Candelaria", "tipo": "opcional", "duracionMin": 180, "costoUSD": 35 }
        ],
        "trabajos": [
          { "nombre": "Cargador de equipaje", "tarifaHora": 9, "maxHoras": 8 }
        ]
      }
    ],
    "links": [
      {
        "source": "BOG",
        "target": "MDE",
        "distanciaKm": 230,
        "aeronaves": ["Regional", "Helice"],
        "costoBase": null,
        "estanciaMinima": 120
      }
    ]
  }
}
```

---

## R2 — Basic planning (Int.2)

### `POST /api/plan/basic`

Generate two itinerary alternatives from a given origin with budget and time constraints.

**Body**
```json
{
  "origin": "BOG",
  "budget": 800,
  "timeHours": 72,
  "includeSecondary": true,
  "transportTypes": ["Comercial", "Regional", "Helice"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `origin` | string | ✅ | IATA code of departure airport |
| `budget` | number | ✅ | Total budget in USD |
| `timeHours` | number | ✅ | Total available travel time in hours |
| `includeSecondary` | boolean | ✅ | If false, exclude non-hub airports from routes |
| `transportTypes` | string[] | ✅ | At least one of: `"Comercial"`, `"Regional"`, `"Helice"` |

**Response**
```json
{
  "error": false,
  "data": {
    "itineraryA": {
      "description": "Maximum destinations within budget",
      "legs": [
        {
          "origin": "BOG",
          "destination": "MDE",
          "aircraft": "Regional",
          "distanceKm": 230,
          "flightTimeMin": 253,
          "costUSD": 57.5,
          "cumulativeCostUSD": 57.5
        }
      ],
      "totalDestinations": 4,
      "totalCostUSD": 320.5,
      "totalTimeMin": 1440
    },
    "itineraryB": {
      "description": "Maximum destinations in minimum time",
      "legs": [ ],
      "totalDestinations": 3,
      "totalCostUSD": 410.0,
      "totalTimeMin": 980
    }
  }
}
```

---

### `POST /api/plan/route`

Calculate the best route between two airports by one or more criteria.
If multiple criteria are given, returns one result per criterion.

**Body**
```json
{
  "origin": "BOG",
  "destination": "SCL",
  "criteria": ["cost", "time", "distance"],
  "includeSecondary": true,
  "transportTypes": ["Comercial", "Regional"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `origin` | string | IATA code |
| `destination` | string | IATA code |
| `criteria` | string[] | One or more of: `"cost"`, `"time"`, `"distance"` |
| `includeSecondary` | boolean  | Include or exclude non-hub airports |
| `transportTypes` | string[]  | Allowed aircraft types |

**Response**
```json
{
  "error": false,
  "data": {
    "byCost": {
      "criterion": "cost",
      "legs": [
        {
          "origin": "BOG",
          "destination": "LIM",
          "aircraft": "Comercial",
          "distanceKm": 1900,
          "flightTimeMin": 1330,
          "costUSD": 342.0,
          "cumulativeCostUSD": 342.0
        }
      ],
      "totalCostUSD": 342.0,
      "totalTimeMin": 1330,
      "totalDistanceKm": 1900
    },
    "byTime": { "criterion": "time", "legs": [ ], "totalCostUSD": 0, "totalTimeMin": 0, "totalDistanceKm": 0 },
    "byDistance": { "criterion": "distance", "legs": [ ], "totalCostUSD": 0, "totalTimeMin": 0, "totalDistanceKm": 0 }
  }
}
```

---

## R3 — Advanced planning (Int.3)

### `POST /api/plan/advanced/start`

Start a step-by-step planning session. Returns the initial state.

**Body**
```json
{
  "origin": "BOG",
  "budget": 1000
}
```

**Response**
```json
{
  "error": false,
  "data": {
    "sessionId": "abc123",
    "currentAirport": "BOG",
    "budgetRemaining": 1000,
    "budgetInitial": 1000,
    "elapsedTimeMin": 0,
    "visitedAirports": ["BOG"],
    "availableFlights": [
      {
        "destination": "MDE",
        "aircraft": "Regional",
        "distanceKm": 230,
        "costUSD": 57.5,
        "flightTimeMin": 253
      }
    ],
    "availableActivities": [
      { "nombre": "Tour La Candelaria", "tipo": "opcional", "duracionMin": 180, "costoUSD": 35 }
    ],
    "availableJobs": [],
    "canWork": false,
    "log": []
  }
}
```

> `canWork` is `true` when `budgetRemaining < budgetInitial * 0.35`.

---

### `POST /api/plan/advanced/step`

Send the traveler's decision for the current step. Returns the updated state.

**Body**
```json
{
  "sessionId": "abc123",
  "decision": {
    "type": "fly",
    "destination": "MDE",
    "aircraft": "Regional"
  }
}
```

| `decision.type` | Required extra fields | Description |
|---|---|---|
| `"fly"` | `destination`, `aircraft` | Travel to next airport |
| `"activity"` | `activityName` | Perform an optional activity at current airport |
| `"work"` | `jobName`, `hoursWorked` | Accept a temporary job (only when `canWork: true`) |
| `"finish"` | — | End the trip and generate the report |

**Response** — same shape as `/start` with updated values + new entry in `log`.

```json
{
  "error": false,
  "data": {
    "sessionId": "abc123",
    "currentAirport": "MDE",
    "budgetRemaining": 942.5,
    "elapsedTimeMin": 253,
    "visitedAirports": ["BOG", "MDE"],
    "availableFlights": [ ],
    "availableActivities": [ ],
    "availableJobs": [],
    "canWork": false,
    "log": [
      {
        "type": "fly",
        "from": "BOG",
        "to": "MDE",
        "aircraft": "Regional",
        "costUSD": 57.5,
        "timeMin": 253
      }
    ]
  }
}
```

---

## R4 — Network interruptions (Int.1)

### `POST /api/network/block`

Block a route, update the graph, and detect if the traveler is currently in transit.

**Body**
```json
{
  "origin": "BOG",
  "destination": "MDE",
  "reason": "weather",
  "sessionId": "abc123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `origin` | string  | IATA code of the blocked route's origin |
| `destination` | string  | IATA code of the blocked route's destination |
| `reason` | string  | One of: `"weather"`, `"airspace"`, `"cancellation"` |
| `sessionId` | string | If provided, checks if active session uses this route |

**Response**
```json
{
  "error": false,
  "data": {
    "blocked": { "origin": "BOG", "destination": "MDE", "reason": "weather" },
    "travelerInTransit": false,
    "rerouted": false,
    "alternativeRoute": null
  }
}
```

> If `travelerInTransit: true`, the frontend must animate the plane returning to origin.  
> `alternativeRoute` contains the recalculated leg if one was found, or `null` if no path exists.

---

### `POST /api/network/recalculate`

Recalculate the best available route from the traveler's current position.
Called after the transit animation completes.

**Body**
```json
{
  "sessionId": "abc123",
  "currentAirport": "BOG"
}
```

**Response**
```json
{
  "error": false,
  "data": {
    "newRoute": {
      "legs": [
        {
          "origin": "BOG",
          "destination": "CTG",
          "aircraft": "Regional",
          "distanceKm": 670,
          "flightTimeMin": 737,
          "costUSD": 167.5
        }
      ],
      "totalCostUSD": 167.5,
      "totalTimeMin": 737
    },
    "noAlternativeFound": false
  }
}
```

> If `noAlternativeFound: true`, the frontend should notify the user that the trip cannot continue.

---

## R5 — Report (Int.2)

### `GET /api/report/<session_id>`

Return the full trip summary for a completed or in-progress session.

**Response**
```json
{
  "error": false,
  "data": {
    "sessionId": "abc123",
    "visitedAirports": [
      {
        "id": "BOG",
        "ciudad": "Bogotá",
        "pais": "Colombia",
        "stayTimeMin": 180,
        "totalSpentUSD": 92.5
      }
    ],
    "legs": [
      {
        "origin": "BOG",
        "destination": "MDE",
        "aircraft": "Regional",
        "distanceKm": 230,
        "flightTimeMin": 253,
        "costUSD": 57.5
      }
    ],
    "activities": [
      {
        "airport": "BOG",
        "nombre": "Tour La Candelaria",
        "tipo": "opcional",
        "duracionMin": 180,
        "costoUSD": 35
      }
    ],
    "jobs": [
      {
        "airport": "MDE",
        "nombre": "Cargador de equipaje",
        "hoursWorked": 4,
        "earnedUSD": 36
      }
    ],
    "totals": {
      "budgetInitialUSD": 1000,
      "totalSpentUSD": 420.5,
      "totalEarnedUSD": 36,
      "balanceUSD": 615.5,
      "totalTravelTimeMin": 1440,
      "totalDestinations": 4
    }
  }
}
```

---

### **ENDPOINT PARA CARGAR OTRO .JSON
POST. /api/graph/upload 
envia el archivo .json con el endpoint y luego guarda y reemplaza los datos 

**response**
{
  "error": false,
  "data": {
    "nodes": [
      {
        "id": "CLO",
        "nombre": "Aeropuerto Alfonso Bonilla Aragón",
        "ciudad": "Cali",
        "pais": "Colombia",
        "zonaHoraria": "America/Bogota",
        "esHub": false,
        "costoAlojamiento": 40,
        "costoAlimentacion": 12,
        "actividades": [
          { "nombre": "Tour Cristo Rey", "tipo": "opcional", "duracionMin": 120, "costoUSD": 20 }],
        "trabajos": [
          { "nombre": "Atención al pasajero", "tarifaHora": 11, "maxHoras": 6 } ]
      },
      {
        "id": "BOG",
        "nombre": "Aeropuerto El Dorado",
        "ciudad": "Bogotá",
        "pais": "Colombia",
        "zonaHoraria": "America/Bogota",
        "esHub": true,
        "costoAlojamiento": 55,
        "costoAlimentacion": 10,
        "actividades": [
          { "nombre": "Tour La Candelaria", "tipo": "opcional", "duracionMin": 180, "costoUSD": 35 }],
        "trabajos": [
          { "nombre": "Cargador de equipaje", "tarifaHora": 9, "maxHoras": 8 }]
      }
    ],
    "links": [
      {
        "source": "CLO",
        "target": "BOG",
        "distanciaKm": 300,
        "aeronaves": ["Jet", "Regional"],
        "costoBase": 50,
        "estanciaMinima": 90
      },
      {
        "source": "BOG",
        "target": "MDE",
        "distanciaKm": 230,
        "aeronaves": ["Regional", "Helice"],
        "costoBase": null,
        "estanciaMinima": 120
      }
    ]
  }
}


### EN EL ARCHIVO "route_optimizer.py" QUE COPIE EL ALGORITMO DEL COLLAB DEL PROFE TENER EN CUENTA: 
   Mapping from notebook → this implementation:
        Grafo            → Graph
        Vertice          → Airport  (accessed via graph.get_vertex)
        Arista           → Route    (accessed via graph.get_neighbors)
        arista.getPeso() → _pick_best_aircraft(...)  (dynamic per criterion)
        identificador    → airport_id
        mapa_vertices    → graph._vertex_map  (built into Graph)
        no_visitados     → unvisited (same set structure)
        pred[v] = u      → pred[v] = (u, aircraft_name, aircraft_key)
                           (extended to store aircraft choice for Leg building)

    Args:
        graph:             live Graph built by GraphDataService.
        origin:            IATA code of departure airport.
        dest:              IATA code of arrival airport.
        weight_fn:         converts (distance, rates) to a float weight.
        allowed_keys:      allowed aircraft type keys, or None for all.
        include_secondary: if False, non-hub intermediate airports are skipped.

    Returns:
        (path, pred) on success, None if destination is unreachable.

---

## Reporte plan basico con optimización (generacion del reporte)

### Frontend (JavaScript)

#### planner-state.js
Ubicación: `presentacion/scripts/panels/planner-state.js`

Almacena el estado central del planificador de rutas sin lógica DOM. Mantiene sincronizado:
- Si el grafo está cargado o no
- Si se está calculando una ruta
- El modo activo (básico o por criterios específicos)
- Los itinerarios calculados que se mostrarán al usuario

#### planner-panel.js
Ubicación: `presentacion/scripts/panels/planner-panel.js`

El coordinador principal del panel de planificación. Conecta la interfaz con la lógica:
- Maneja los eventos del usuario (clics, formularios)
- Realiza llamadas a la API del backend
- Actualiza el estado y dispara renders

Nota: Actualmente está vacío, pero será el punto de entrada principal para toda la interacción del usuario con el planificador.

#### planner-render.js
Ubicación: `presentacion/scripts/panels/planner-render.js`

Se encarga exclusivamente de construir y actualizar el HTML del planificador. Incluye:
- Renderización de tarjetas de itinerarios con toda la información del viaje
- Resumen visual con aeropuertos visitados, costo total y duración
- Lista detallada de cada tramo (origen, destino, aeronave, distancia, etc.)
- Botón "Ver en el mapa" que resalta la ruta en el grafo interactivo
- Funciones auxiliares para formatear dinero y tiempo de manera legible

### Backend (Python)

#### report_generator.py
Ubicación: `services/report_generator.py`

Genera el reporte final del viaje que se envía al frontend. Integra toda la información del viaje en un formato único:

Lo que incluye:
- Aeropuertos visitados: Con detalles del grafo (nombre, ciudad, país, zona horaria)
- Tramos: Cada vuelo con origen, destino, duración y costo
- Actividades: Las actividades realizadas durante el viaje (ej: hospedaje, comidas)
- Trabajos: Los trabajos desempeñados para ganar dinero
- Decisiones: Registro de cada decisión tomada con timestamp
- Totales: Resumen final (presupuesto usado, dinero ganado, tiempo total, distancia)

Flexibilidad: Maneja tanto viajes simples (planificación básica) como sesiones interactivas completas (R3) con actividades y trabajos.

# Resumen sesión — 30 mayo 2026  
Proyecto **VUELOS-Y-ESCALAS**

---

## 1. PlannerPanel
- Oculto por `hidden` y `aside#rightPanels`  
- `createPlannerPanel()` borra `<h3>` inicial  

**Frontend R2**  
`planner-api.js` → HTTP  
`planner-state.js` → estado  
`planner-render.js` → DOM  
`planner-panel.js` → coordinador  

**Backend**  
- Máx. destinos → `itinerary_planner.py` (DFS)  
- Mejor ruta → `route_optimizer.py` (Dijkstra)  

---

## 2. Bug `route_optimizer.py`
- No normalizaba `"Comercial"/"Hélice"`  
- Fix: `_normalize_transport_keys()` con `_AIRCRAFT_NAME_MAP`

---

## 3. Aeropuertos
- Hub: `"is_hub": true` → `Airport.is_hub = True`  
- Secundario: `"is_hub": false` → `Airport.is_hub = False`  
- Sin secundarios → solo hubs como escalas

---

## 4. Rutas en grafo
`graphUI.js`  
- `highlightRoute()` → azul  
- `clearRouteHighlight()` → limpia  
- Planner: botón “Ver en mapa”  
- Reporte: carga todos los tramos

---

## 5. Reporte R5 Backend
Archivos:  
- `report_generator.py` → JSON  
- `report_service.py` → orquesta  
- `session_state.py` → sesiones  
- `report_routes.py` → `GET /api/report/<id>`

---

## 6. Reporte R5 Frontend
`report-api/state/render/utils/panel.js`  
- 6 secciones: destinos, tramos, actividades, trabajos, decisiones, totales  
- Auto-actualiza tras cada decisión  
- Usa `graphUi.highlightRoute()`

---

## 7. Refactor SOLID
Planner → `panels/planner/`  
Reporte → `panels/report/`  
Patrón: `*-api/state/render/panel.js`  
Se eliminó `components/`

---

## 8. Verificación R5
- Actividades: `type`, `cost_usd`, `duration_min` → corregido  
- Trabajos: `hours_worked`, `income_usd`, `hourly_rate` → ok  
- Totales: fórmula `final_balance = init + gained - spent` verificada

---

## 9. Endpoints
- `POST /api/load-graph`  
- `POST /api/plan/basic`  
- `POST /api/plan/route`  
- `POST /api/session/start`  
- `POST /api/session/{id}/choice`  
- `GET /api/report/{id}`  

---

## 10. Pendientes
- README usa camelCase, API snake_case  
- `graphOrchestrator.js` → no meter más lógica  
- `tripSessionPanel.js` → migrar formatters a `utils`

---

## Flujo completo
1. `python app.py` → abrir web  
2. Cargar JSON  
3. Planificador → calcular → ver mapa  
4. Sesión R3 → iniciar → decisiones  
5. Reporte R5 → panel auto-actualizado  
6. API directa → `GET /api/report/{session_id}`
