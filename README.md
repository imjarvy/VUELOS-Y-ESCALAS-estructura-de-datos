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

