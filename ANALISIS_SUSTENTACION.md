# Análisis Detallado del Proyecto Vuelos y Escalas - Tu Parte

## 📋 Introducción

Este documento es una guía completa para la sustentación de tu parte del proyecto. Explica **qué hace cada archivo**, **cómo opera**, **dónde se ubica cada función** y **cómo se relacionan todas las piezas** para cumplir con las funcionalidades de planificación y reporte.

---

## 🏗️ I. ARQUITECTURA GENERAL DEL PROYECTO

El proyecto sigue una arquitectura de **3 capas**:

```
┌─────────────────────────────────────────┐
│        FRONTEND (Presentación)          │
│  HTML, CSS, JavaScript con D3.js       │
│  - Visualización del grafo              │
│  - Interfaz de usuarios                 │
│  - Paneles interactivos                 │
└──────────────┬──────────────────────────┘
               │ HTTP REST
┌──────────────▼──────────────────────────┐
│     API (Flask Blueprints)              │
│  - graph_routes.py                      │
│  - planner_routes.py                    │
│  - report_routes.py                     │
└──────────────┬──────────────────────────┘
               │ Lógica de negocio
┌──────────────▼──────────────────────────┐
│      BACKEND (Servicios)                │
│  - Algoritmos de planificación          │
│  - Generación de reportes               │
│  - Gestión del estado                   │
│  - Estructuras de datos                 │
└─────────────────────────────────────────┘
```

### Puntos de Entrada:
1. **`app.py`** - Bootstrapping de Flask, registro de blueprints
2. **`presentacion/vistas/graph_index.html`** - Interfaz inicial
3. **`routes/graph_routes.py`** - Carga del grafo y configuración
4. **`routes/planner_routes.py`** - Planificación de itinerarios
5. **`routes/report_routes.py`** - Generación de reportes

---

## 🎨 II. FRONTEND - PRESENTACIÓN Y VISUALIZACIÓN

### 2.1 Estructura de Ficheros Frontend

```
presentacion/
├── vistas/
│   └── graph_index.html              # Página principal (estructura HTML)
├── estilos/
│   └── graph-styles.css              # Estilos CSS (diseño visual)
├── scripts/
│   ├── graphOrchestrator.js          # Orquestador principal del frontend
│   ├── graphUI.js                    # Renderizado del grafo con D3.js
│   ├── flightAnimator.js             # Animaciones de vuelos
│   ├── graphConfigController.js      # Control de configuración
│   ├── routeBlockingController.js    # Control de bloqueo de rutas
│   ├── routeAnimationController.js   # Animaciones de rutas
│   ├── api/
│   │   └── client.js                 # Cliente HTTP (apiPost, apiGet)
│   ├── panels/
│   │   ├── infoPanel.js              # Panel de información del aeropuerto
│   │   ├── tripSessionPanel.js       # Panel de sesión de viaje
│   │   ├── planner/                  # Submódulo de planificación
│   │   │   ├── planner-panel.js      # Panel de interfaz de planner
│   │   │   ├── planner-api.js        # Llamadas API del planner
│   │   │   ├── planner-render.js     # Renderizado de resultados
│   │   │   └── planner-state.js      # Estado del planner
│   │   ├── report/                   # Submódulo de reportes
│   │   │   ├── report-panel.js       # Panel de reportes
│   │   │   ├── report-api.js         # Llamadas API de reportes
│   │   │   ├── report-render.js      # Renderizado de reportes
│   │   │   ├── report-state.js       # Estado de reportes
│   │   │   └── report-utils.js       # Utilidades de reportes
│   └── utils/
│       └── formatters.js              # Funciones de formato (dinero, tiempo)
```

### 2.2 Página Principal: `presentacion/vistas/graph_index.html`

**Responsabilidad:** Estructura HTML de la interfaz completa.

**Composición:**

```html
<header>                          <!-- Botones: Configuración, Cargar JSON -->
<section class="workspace-layout">
  <section id="graphContainer">
    <svg id="graphSvg"></svg>    <!-- Lienzo D3 para el grafo -->
  </section>
  
  <aside id="rightPanels">       <!-- Paneles laterales derecha -->
    <section id="airportInfoPanel">      <!-- Info del aeropuerto seleccionado -->
    <section id="tripSessionPanel">      <!-- Resumen de la sesión activa -->
    <section id="plannerPanel">          <!-- Panel de planificación -->
    <section id="reportPanel">           <!-- Panel de reportes -->
  </aside>
</section>

<!-- Modales para JSON y configuración -->
<div id="jsonModal">              <!-- Modal para cargar JSON -->
<div id="configModal">            <!-- Modal de configuración global -->
```

**Secciones interactivas:**

| Sección | Propósito |
|---------|-----------|
| **Header** | Botones globales: configuración y carga de JSON |
| **graphContainer** | Visualización D3 del grafo de aeropuertos |
| **airportInfoPanel** | Información del aeropuerto seleccionado (código, ciudad, actividades, trabajos) |
| **tripSessionPanel** | Estado actual de la sesión (presupuesto, tiempo restante) |
| **plannerPanel** | Interfaz para generar itinerarios (máx. destinos, mejor ruta) |
| **reportPanel** | Visualización del reporte final de la sesión |

---

### 2.3 Estilos: `presentacion/estilos/graph-styles.css`

**Responsabilidad:** Diseño visual, temas, y responsive layout.

**Tokens de diseño:**

```css
--bg: #f7f8fa                    /* Fondo principal */
--bg-panel: #ffffff              /* Fondo de paneles */
--blue: #3b82f6                  /* Color primario */
--green: #16a34a                 /* Color de éxito */
--red: #dc2626                   /* Color de error */

--node-default-fill: #eff6ff     /* Relleno nodos aeropuertos */
--node-root-fill: #f0fdf4        /* Relleno nodo origen */
--node-critical-fill: #fef2f2    /* Relleno nodo destino */
```

**Componentes principales:**

1. **Layout workspace:** Flexbox con header + graph + paneles
2. **Nodos del grafo:** Círculos con colores según estado (default, root, critical)
3. **Enlaces del grafo:** Flechas/líneas con etiquetas de distancia
4. **Paneles laterales:** Contenedores con scroll vertical
5. **Modales:** Fondos oscuros semitransparentes con contenido centrado
6. **Botones y controles:** Estilo coherente (hover, active, disabled)
7. **Banners de estado:** Mensajes con color según tipo (info, error, alert)

**Responsive:** El CSS utiliza flexbox para adaptarse a diferentes tamaños de pantalla. El grafo crece/encoge según el espacio disponible.

---

### 2.4 Orquestador Principal: `presentacion/scripts/graphOrchestrator.js`

**Responsabilidad:** Coordinación central del frontend. Integra todos los módulos.

**Componentes orquestados:**

```javascript
// Carga de módulos
graphUI               // Renderizado D3
flightAnimator        // Animaciones de vuelos
infoPanel             // Información del aeropuerto
tripSessionPanel      // Estado de la sesión
plannerPanel          // Planificación
reportPanel           // Reportes
configController      // Configuración global
routeBlockingController  // Bloqueo de rutas
```

**Flujo de eventos principales:**

1. **Usuario carga JSON** → `apiPost("/api/load-graph")`
2. **Backend responde con grafo** → `graphUI.render(data)` (D3 dibuja el grafo)
3. **Usuario selecciona nodo** → `infoPanel.show(airport)` (muestra información)
4. **Usuario configura parámetros** → `plannerPanel` está listo
5. **Usuario clickea "Calcular itinerario"** → `fetchBasicPlan()` o `fetchBestRoute()`
6. **Backend retorna itinerarios** → `plannerPanel.renderResults()` (muestra opciones)
7. **Usuario selecciona ruta** → `routeAnimationController.highlightRoute()`
8. **Usuario cierra sesión** → `reportPanel.loadReport(sessionId)` (muestra reporte)

**Gestión de estado global:**

```javascript
let currentSessionId = null;      // ID de sesión activa
let pendingTransportChoice = null; // Elección de transporte pendiente
const { getBlockedRoutes, isRouteBlocked, ... } = routeBlockingController;
```

---

### 2.5 Renderizado D3: `presentacion/scripts/graphUI.js`

**Responsabilidad:** Transformar datos de grafo en visualización D3.

**Función clave: `transformGraphToD3Data(graph)`**

```javascript
Input:
  graph = {
    vertices: [Airport, Airport, ...],
    edges: [Route, Route, ...]
  }

Output:
  {
    nodes: [
      { id: "BOG", name: "Bogotá", city: "Bogotá", country: "Colombia", ... },
      { id: "MDE", name: "Medellín", ... },
      ...
    ],
    links: [
      { source: "BOG", target: "MDE", distance: 250, aircrafts: ["Comercial"], ... },
      { source: "MDE", target: "BOG", distance: 250, ... },
      ...
    ]
  }
```

**Renderizado D3:**

1. **Nodos:** Círculos posicionados con fuerza-layout
   - Tamaño: proporcional al número de conexiones
   - Color: según sea hub, origen, destino o regular
   - Etiqueta: código IATA del aeropuerto

2. **Enlaces:** Flechas entre nodos
   - Grosor: según frecuencia de rutas
   - Etiqueta: distancia en km

3. **Interactividad:**
   - Drag de nodos
   - Hover muestra información
   - Click selecciona y muestra panel de información

---

### 2.6 Panel de Planificación: `presentacion/scripts/panels/planner/`

**Archivo: `planner-panel.js`**
- **Responsabilidad:** Crear y coordinar el panel de planificación
- **Componentes:**
  - Modo toggle: "Máx. destinos" vs "Mejor ruta"
  - Inputs: origen, presupuesto, tiempo, destino
  - Checkboxes: criterios (costo, tiempo, distancia), tipos de aeronaves
  - Botón: "Calcular itinerario"
  - Resultados: muestra itinerarios A y B o rutas por criterio

**Archivo: `planner-api.js`**
- **Responsabilidad:** Llamadas HTTP (sin lógica de negocio)
- **Funciones:**
  - `fetchBasicPlan({ origin, budget, time_hours, transport_types, include_secondary })`
  - `fetchBestRoute({ origin, dest, criteria, transport_types, include_secondary })`

**Archivo: `planner-render.js`**
- **Responsabilidad:** Renderizar resultados (sin modificar estado)
- **Funciones:**
  - `buildItineraryCard(label, itin, onHighlight)` - Crea tarjeta de itinerario
  - `renderResults(resultsList, resultsSection, onHighlight)` - Renderiza A, B o rutas

**Archivo: `planner-state.js`**
- **Responsabilidad:** Estado del panel
```javascript
export const state = {
  graphLoaded: false,        // ¿Hay un grafo cargado?
  loading: false,            // ¿Se está calculando?
  mode: "basic",             // "basic" o "route"
  itinerary_a: null,         // Itinerario máx. destinos por presupuesto
  itinerary_b: null,         // Itinerario máx. destinos por tiempo
  routes: null,              // Rutas por criterio
  lastRequest: null,         // Última solicitud (para debugging)
};
```

---

### 2.7 Panel de Reportes: `presentacion/scripts/panels/report/`

**Archivo: `report-panel.js`**
- **Responsabilidad:** Panel de reportes
- **Elementos:**
  - Session ID display
  - Botón "Cargar reporte"
  - Secciones: destinos visitados, tramos de vuelo, actividades, trabajos, decisiones, totales

**Archivo: `report-api.js`**
```javascript
export async function fetchSessionReport(sessionId) {
  return await apiGet(`/api/report/${sessionId}`);
}
```

**Archivo: `report-render.js`**
- **Funciones:**
  - `renderVisited(listEl, visited)` - Lista de aeropuertos visitados
  - `renderLegs(listEl, legs)` - Lista de tramos de vuelo
  - `renderActivities(listEl, activities)` - Actividades realizadas
  - `renderJobs(listEl, jobs)` - Trabajos realizados
  - `renderDecisions(listEl, decisions)` - Decisiones tomadas
  - `renderTotals(totalsBlock, totals)` - Resumen de totales

**Archivo: `report-state.js`**
```javascript
export const state = {
  sessionId: null,
  loading: false,
  report: null,
};
```

**Archivo: `report-utils.js`**
```javascript
export function legsToEdgeList(legs) {
  // Convierte lista de legs en lista de aristas para animación
  // Retorna: [{ source: "BOG", target: "MDE" }, ...]
}
```

---

### 2.8 Utilidades Frontend

**`presentacion/scripts/utils/formatters.js`**

```javascript
export function formatMoney(usd) {
  // "123.45" → "$123.45"
}

export function formatMinutes(minutes) {
  // "90" → "1h 30m"
}

export function formatDistance(km) {
  // "1234.5" → "1,234.5 km"
}
```

**`presentacion/scripts/api/client.js`**

```javascript
export async function apiPost(url, data) {
  // POST con JSON, manejo de errores
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!response.ok) throw new Error(...);
  return response.json();
}

export async function apiGet(url) {
  // GET con manejo de errores
}

export async function apiPostFormData(url, formData) {
  // POST con FormData (para archivos)
}
```

---

## 🔧 III. BACKEND - SERVICIOS Y LÓGICA

### 3.1 Punto de Entrada: `app.py`

**Responsabilidad:** Bootstrapping de Flask y registro de blueprints.

```python
# app.py
app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas las rutas

# Registrar blueprints (módulos de rutas)
app.register_blueprint(graph_bp)        # Carga del grafo
app.register_blueprint(planner_bp)      # Planificación
app.register_blueprint(report_bp)       # Reportes
app.register_blueprint(trip_session_bp) # Sesiones avanzadas

@app.route("/")
def index():
    return render_template("graph_index.html")

@app.route("/scripts/<path:filename>")
def scripts_static(filename):
    return send_from_directory(SCRIPTS_DIR, filename)
```

### 3.2 Modelos de Datos: `models/`

**Archivo: `models/airport.py`**

```python
class Airport:
    airport_id: str           # Código IATA (p.ej. "BOG")
    name: str                 # Nombre (p.ej. "Aeropuerto Internacional El Dorado")
    city: str                 # Ciudad
    country: str              # País
    timezone: str             # Zona horaria
    is_hub: bool              # ¿Es aeropuerto hub?
    accommodation_cost: float # USD por noche
    feeding_cost: float       # USD por comida
    activities: List[Activity]  # Actividades disponibles
    jobs: List[JobOffer]        # Trabajos disponibles
    adjacencies: List[Route]    # Rutas salientes
    
    def add_adjacency(self, route: Route) -> None:
        """Agrega una ruta saliente."""
    
    def to_dict(self) -> Dict:
        """Serialización para API."""
```

**Archivo: `models/route.py`**

```python
class Route:
    origin_vertex: str       # Código IATA origen
    destination_vertex: str  # Código IATA destino
    distance: float          # Distancia en km
    aircrafts: List[str]     # Tipos de aeronaves disponibles
    cost: float              # Costo base
    minimum_stay: int        # Estadía mínima en minutos
    blocked: bool            # ¿Ruta interrumpida?
```

**Archivo: `models/leg.py`**

```python
class Leg:
    origin_id: str           # Código IATA origen
    destination_id: str      # Código IATA destino
    aircraft: str            # Nombre de la aeronave usada
    distance: float          # Distancia km
    flight_time_min: float   # Tiempo de vuelo en minutos
    leg_cost: float          # Costo USD del tramo
    
    # Ejemplo: BOG → MDE en Comercial, 250 km, 35 min, $45
```

**Archivo: `models/itinerary.py`**

```python
class Itinerary:
    optimization_criteria: str  # "cost", "time", "distance"
    legs: List[Leg]            # Secuencia de vuelos
    
    @property
    def total_cost(self) -> float:
        """Suma de todos los leg_cost."""
    
    @property
    def total_time_min(self) -> float:
        """Suma de todos los flight_time_min."""
    
    @property
    def visited_airports(self) -> List[str]:
        """Lista de códigos IATA visitados: [origen, dest1, dest2, ...]"""
    
    def add_leg(self, leg: Leg) -> None:
        """Agrega un tramo validando conectividad."""
```

---

### 3.3 Estructura del Grafo: `core/graph.py`

**Responsabilidad:** Estructura de datos del grafo (vértices y aristas).

```python
class Graph:
    vertices: List[Airport]              # Nodos
    _vertex_map: Dict[str, Airport]      # Índice rápido por código IATA
    
    # Operaciones con vértices
    def add_vertex(self, airport: Airport) -> None:
        """Agrega un aeropuerto al grafo."""
    
    def get_vertex(self, airport_id: str) -> Optional[Airport]:
        """Busca un aeropuerto por código IATA."""
    
    # Operaciones con aristas
    def add_edge(self, route: Route) -> None:
        """Agrega una ruta (arista) al grafo."""
    
    def get_neighbors(self, airport_id: str) -> List[Route]:
        """Retorna las rutas salientes de un aeropuerto."""
    
    def remove_edge(self, origin_id: str, destination_id: str) -> bool:
        """Elimina una ruta (para bloquear)."""
    
    def has_edge(self, origin_id: str, destination_id: str) -> bool:
        """Verifica si existe una ruta entre dos aeropuertos."""
    
    # Serialización
    def to_dict(self) -> Dict:
        """Serializa el grafo completo a diccionario (para API)."""
    
    @classmethod
    def from_dict(cls, data: Dict) -> Graph:
        """Reconstruye un grafo desde un diccionario."""
```

---

### 3.4 Servicios Principales

#### 3.4.1 Carga de Datos: `services/graphDataService.py`

**Responsabilidad:** Parsear JSON y convertir en objetos de dominio.

```python
class GraphDataService:
    def __init__(self, raw_data: Dict):
        self.raw_data = raw_data  # {"airports": [...], "routes": [...]}
    
    def get_parsed_airports(self) -> List[Airport]:
        """Convierte JSON airports → objetos Airport."""
        # Acepta múltiples claves: airport_id, id, code, iata
        # Extrae actividades y trabajos
    
    def get_parsed_routes(self) -> List[Route]:
        """Convierte JSON routes → objetos Route."""
        # Normaliza tipos de aeronaves: "Comercial" → "commercial"
    
    def build_graph(self) -> Graph:
        """Construye el grafo a partir del JSON."""
```

**Flujo de carga:**

```
JSON file
   ↓
graphDataService.get_parsed_airports()
graphDataService.get_parsed_routes()
   ↓
Graph.add_vertex(airport) × N
Graph.add_edge(route) × M
   ↓
graph ← grafo completo en memoria
```

---

#### 3.4.2 Gestión del Estado del Grafo: `services/graph_state.py`

**Responsabilidad:** Singleton que mantiene el grafo en memoria.

```python
# Módulo-nivel (no una clase)
_current_graph: Optional[Graph] = None

def set_graph(graph: Graph) -> None:
    """Almacena el grafo cargado (escrito por graph_routes.py)."""

def get_graph() -> Optional[Graph]:
    """Retorna el grafo actual (leído por planner_routes.py)."""
```

**Uso:**
```python
# En graph_routes.py (POST /api/load-graph)
graph = GraphDataService(json_data).build_graph()
graph_state.set_graph(graph)

# En planner_routes.py (POST /api/plan/basic)
graph = graph_state.get_graph()
itinerary = planner.plan(graph, origin, budget)
```

---

#### 3.4.3 Optimización de Rutas: `services/route_optimizer.py`

**Responsabilidad:** Dijkstra para encontrar la mejor ruta entre dos aeropuertos.

**Clases:**

```python
class BaseOptimizer(ABC):
    """Clase abstracta para todos los optimizadores."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Retorna "cost", "time" o "distance"."""
    
    @abstractmethod
    def optimize(
        self,
        graph: Graph,
        origin: str,
        dest: str,
        transport_types: Optional[List[str]] = None,
        include_secondary: bool = True,
    ) -> Optional[Itinerary]:
        """Retorna el mejor itinerario (o None si no existe ruta)."""


class CostOptimizer(BaseOptimizer):
    """Dijkstra minimizando USD."""

class TimeOptimizer(BaseOptimizer):
    """Dijkstra minimizando minutos."""

class DistanceOptimizer(BaseOptimizer):
    """Dijkstra minimizando km."""
```

**Algoritmo de Dijkstra (simplificado):**

```python
def _dijkstra(
    graph: Graph,
    origin: str,
    dest: str,
    weight_fn: Callable,  # (distance, rates) → float
    allowed_keys: Set[str],  # Tipos de aeronaves permitidas
    include_secondary: bool,
) -> Optional[Tuple[List[str], Dict]]:
    """
    Retorna (camino, predecessores) o None si no hay ruta.
    
    Ejemplo:
      weight_fn(distance=100, rates) = 100 * 0.18 = $18
      ↑ Esto hace que sea "CostOptimizer"
    """
    dist = {origin: 0, ...}
    pred = {origin: None, ...}
    unvisited = {todos los nodos}
    
    while unvisited:
        u = min(unvisited, key=lambda n: dist[n])
        if u == dest:
            break  # Encontrado
        
        for route in graph.get_neighbors(u):
            v = route.destination_vertex
            if v in unvisited:
                edge_weight = _pick_best_aircraft(...)
                alt = dist[u] + edge_weight
                if alt < dist[v]:
                    dist[v] = alt
                    pred[v] = u
    
    # Reconstruir camino usando pred
    path = [dest]
    current = dest
    while pred[current]:
        current = pred[current]
        path.insert(0, current)
    
    return path, pred
```

**Normalización de aeronaves:**

```python
_AIRCRAFT_NAME_MAP = {
    "Comercial": "commercial",
    "comercial": "commercial",
    "Commercial": "commercial",
    "Regional": "regional",
    "regional": "regional",
    "Hélice": "propeller",
    "helice": "propeller",
    # ... etc
}
```

**Selección de aeronave:**

```python
def _pick_best_aircraft(
    route_aircrafts: List[str],
    distance: float,
    weight_fn: Callable,
    allowed_keys: Optional[Set[str]],
) -> Tuple[float, str, str]:
    """
    Retorna (weight, aircraft_name, aircraft_key) que minimiza weight.
    
    Ejemplo:
      Ruta: 100 km, aircrafts = ["Comercial", "Regional"]
      allowed_keys = {"commercial", "regional"}
      
      Comercial: weight = 100 * 0.18 = $18
      Regional: weight = 100 * 0.25 = $25
      
      Retorna ($18, "Comercial", "commercial")
    """
```

---

#### 3.4.4 Planificador de Itinerarios Máximos: `services/itinerary_planner.py`

**Responsabilidad:** DFS con backtracking para maximizar destinos bajo restricción.

**Algoritmo:**

```python
class ItineraryPlanner:
    def plan_max_destinations(
        self,
        graph: Graph,
        origin: str,
        resource_limit: float,  # Presupuesto USD o tiempo min
        weight_fn: Callable,    # (distance, rates) → float
        allowed_keys: Optional[Set[str]],
        include_secondary: bool,
        required_types: Optional[Set[str]],
    ) -> Itinerary:
        """
        DFS + backtracking para encontrar el camino que visita
        la máxima cantidad de aeropuertos sin exceder resource_limit.
        
        Ejemplo:
          origin = "BOG", budget = $600
          
          Path 1: BOG → MDE → LIM → CCS
            Cost: $50 + $70 + $80 = $200 ✓
            Airports: 4
          
          Path 2: BOG → MDE → LIM → CCS → GYE
            Cost: $200 + $100 = $300 ✓
            Airports: 5
          
          Path 3: BOG → MDE → LIM → CCS → GYE → QUE
            Cost: $300 + $150 = $450 ✓
            Airports: 6
          
          Path 4: BOG → MDE → LIM → CCS → GYE → QUE → UIO
            Cost: $450 + $200 = $650 ✗ (exceeds budget)
            → backtrack
          
          Retorna Path 3 (máx. 6 destinos con $450)
        """
```

**DFS pseudo-código:**

```python
def _dfs(
    graph: Graph,
    current_id: str,
    visited: Set[str],  # Nodos visitados en este camino
    legs: List[Leg],    # Tramos acumulados
    used_types: Set[str],  # Tipos de aeronaves usadas
    best: Dict,         # {count, legs} del mejor camino encontrado
    weight_fn: Callable,
    allowed_keys: Optional[Set[str]],
    include_secondary: bool,
    resource_remaining: float,
    required_types: Set[str],
) -> None:
    """
    Mutations:
      - visited: agregado de next_id
      - legs: agregado de nuevo leg
      - used_types: agregado de aircraft_key
      - best: actualizado si encontramos un camino mejor
    
    Backtracking:
      - Al retornar, deshacer: visited.remove(next_id), legs.pop(), etc.
      - best NO se deshace (solo crece).
    """
    
    # Snapshot del mejor camino si este path es mejor
    if len(legs) > best["count"]:
        best["count"] = len(legs)
        best["legs"] = list(legs)  # Copia
    
    # Explorar vecinos
    for route in graph.get_neighbors(current_id):
        if route.blocked:
            continue  # Ruta interrumpida
        
        next_id = route.destination_vertex
        
        # Validación 1: no revisitar
        if next_id in visited:
            continue
        
        # Validación 2: solo hubs intermedios si required
        if not include_secondary:
            airport = graph.get_vertex(next_id)
            if airport and not airport.is_hub:
                continue
        
        # Validación 3: seleccionar mejor aeronave para este criterio
        edge_weight, aircraft_name, aircraft_key = _pick_best_aircraft(...)
        
        if edge_weight == ∞:  # No hay aeronave válida
            continue
        
        # Validación 4: presupuesto/tiempo
        if edge_weight > resource_remaining:
            continue
        
        # Crear leg
        rates = AIRCRAFT_RATES.get(aircraft_key)
        leg = Leg(
            origin_id=current_id,
            destination_id=next_id,
            aircraft=aircraft_name,
            distance=route.distance,
            flight_time_min=route.distance * rates["time_per_km_min"],
            leg_cost=route.distance * rates["cost_per_km"],
        )
        
        # ── IR MÁS PROFUNDO ──
        legs.append(leg)
        visited.add(next_id)
        used_types.add(aircraft_key)
        
        _dfs(graph, next_id, visited, legs, used_types, best, ...)
        
        # ── BACKTRACK ──
        legs.pop()
        visited.remove(next_id)
        used_types = _rebuild_used_types(legs)
```

**Modo basic vs route:**

```python
# Modo BASIC: dos itinerarios automáticos
itinerary_a = planner.plan_max_destinations(
    graph, origin, budget, 
    weight_fn=lambda dist, rates: dist * rates["cost_per_km"]
)

itinerary_b = planner.plan_max_destinations(
    graph, origin, time_hours * 60,
    weight_fn=lambda dist, rates: dist * rates["time_per_km_min"]
)

# Modo ROUTE: mejor ruta entre dos puntos
itinerary_cost = CostOptimizer().optimize(graph, origin, dest)
itinerary_time = TimeOptimizer().optimize(graph, origin, dest)
itinerary_distance = DistanceOptimizer().optimize(graph, origin, dest)
```

---

#### 3.4.5 Generador de Reportes: `services/report_generator.py`

**Responsabilidad:** Combinar Itinerary + TripReport → reporte final.

```python
class ReportGenerator:
    def generate(
        self,
        graph: Graph,
        itinerary: Optional[Itinerary] = None,
        trip_report: Optional[TripReport] = None,
        decisions: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retorna:
        {
            "visited": [...],      # Aeropuertos visitados
            "legs": [...],         # Tramos de vuelo
            "activities": [...],   # Actividades realizadas
            "jobs": [...],         # Trabajos realizados
            "decisions": [...],    # Decisiones tomadas
            "totals": {            # Resumen de totales
                "budget_initial": 1000,
                "budget_spent": 450,
                "budget_earned": 200,
                "budget_remaining": 750,
                "time_total_min": 480,
            }
        }
        """
```

**Procesos internos:**

```python
# 1. Aeropuertos visitados
_serialize_visited(visited_raw, graph)
# Agrega nombre, ciudad, país, zona horaria desde graph

# 2. Tramos de vuelo
_serialize_legs(legs)
# Convierte Leg → {origin_id, destination_id, aircraft, distance, ...}

# 3. Actividades
_serialize_activities(activities)
# Convierte ActivityRecord → {name, type, duration_min, cost_usd, ...}

# 4. Trabajos
_serialize_jobs(jobs)
# Convierte JobRecord → {name, hourly_rate, hours_worked, income_usd}

# 5. Decisiones
_serialize_decisions(decisions)
# Convierte DecisionRecord → {timestamp_min, kind, details}
```

---

### 3.5 Gestión de Estado de Sesiones: `services/session_state.py`

**Responsabilidad:** Registro en memoria de sesiones activas.

```python
_sessions: Dict[str, "TripSession"] = {}

def register_session(session: "TripSession") -> str:
    """Almacena una sesión y retorna su ID."""
    _sessions[session.session_id] = session
    return session.session_id

def get_session(session_id: str) -> Optional["TripSession"]:
    """Retorna una sesión por ID."""
    return _sessions.get(session_id)
```

---

### 3.6 Configuración Global: `utils/constants.py`

**Responsabilidad:** Valores por defecto para tasas de aeronaves y reglas.

```python
GRAPH_CONFIG_DEFAULTS = {
    "aeronaves": {
        "commercial": {"costoKm": 0.18, "tiempoKm": 0.7},
        "regional": {"costoKm": 0.25, "tiempoKm": 1.1},
        "propeller": {"costoKm": 0.12, "tiempoKm": 2.5},
    },
    "presupuestoMinimoPorc": 35.0,       # % mínimo de presupuesto para habilitar trabajos
    "intervaloAlojamiento": 20.0,       # horas
    "intervaloAlimentacion": 8.0,       # horas
}

AIRCRAFT_RATES = {
    "commercial": {"cost_per_km": 0.18, "time_per_km_min": 0.7},
    "regional": {"cost_per_km": 0.25, "time_per_km_min": 1.1},
    "propeller": {"cost_per_km": 0.12, "time_per_km_min": 2.5},
}

DEFAULTS = {
    "budget_threshold_pct": 35.0,
    "lodging_interval_h": 20.0,
    "meal_interval_h": 8.0,
    "max_subsidized_distance_frac": 0.20,
}
```

---

## 🌐 IV. API ENDPOINTS - RUTAS Y CONEXIONES

### 4.1 Blueprint de Grafo: `routes/graph_routes.py`

**Responsabilidad:** Cargar grafo, configuración, bloqueo de rutas.

#### `GET /api/config`
```
Request:  ninguno
Response: {
  "aeronaves": {...},
  "presupuestoMinimoPorc": 35.0,
  "intervaloAlojamiento": 20.0,
  "intervaloAlimentacion": 8.0,
}
```

#### `POST /api/config`
```
Request:  Misma estructura anterior (actualizar valores)
Response: { "success": true }
```

#### `GET /api/config/status`
```
Response: {
  "locked": false,
  "active_session_count": 0,
  "active_route_count": 0,
  "message": "La configuración está disponible."
}
```

#### `POST /api/load-graph`
```
Request:  FormData con campo "file" (JSON)
Response: {
  "vertices": [
    {
      "airport_id": "BOG",
      "name": "Aeropuerto Internacional El Dorado",
      "city": "Bogotá",
      "country": "Colombia",
      "timezone": "America/Bogota",
      "is_hub": true,
      "activities": [...],
      "jobs": [...],
      "adjacencies": [...]
    },
    ...
  ],
  "airports": 18
}
```

**Backend logic:**
```python
@graph_bp.route("/api/load-graph", methods=["POST"])
def load_graph():
    file = request.files.get("file")
    
    raw_data = json.load(file)  # JSON bruto
    svc = GraphDataService(raw_data)
    
    airports = svc.get_parsed_airports()
    routes = svc.get_parsed_routes()
    
    graph = Graph()
    for airport in airports:
        graph.add_vertex(airport)
    for route in routes:
        graph.add_edge(route)
    
    graph_state.set_graph(graph)
    _LAST_GRAPH = graph
    _GRAPH_STORAGE.save_graph(graph)
    
    return jsonify(_graph_payload(graph))
```

---

### 4.2 Blueprint de Planificación: `routes/planner_routes.py`

**Responsabilidad:** Endpoints de itinerarios.

#### `POST /api/plan/basic`

**Propósito:** Generar dos itinerarios alternativos desde un origen.

```
Request:
{
  "origin": "BOG",
  "budget": 600.0,           # USD
  "time_hours": 50.0,
  "transport_types": ["Comercial", "Regional"],  # [] = todos
  "include_secondary": true
}

Response:
{
  "origin": "BOG",
  "itinerary_a": {
    "optimization_criteria": "cost",
    "visited_airports": ["BOG", "MDE", "LIM", "CCS"],
    "legs": [
      {
        "origin_id": "BOG",
        "destination_id": "MDE",
        "aircraft": "Comercial",
        "distance": 250.5,
        "flight_time_min": 35.0,
        "leg_cost": 45.09
      },
      ...
    ],
    "total_cost": 199.87,
    "total_time_min": 130.5
  },
  "itinerary_b": {
    "optimization_criteria": "time",
    ...
  }
}
```

**Backend logic:**
```python
@planner_bp.route("/api/plan/basic", methods=["POST"])
def plan_basic():
    graph = graph_state.get_graph()
    body = request.get_json()
    
    origin = body["origin"]
    budget = body["budget"]
    time_hours = body["time_hours"]
    transport_types = body["transport_types"]
    include_secondary = body["include_secondary"]
    
    # Itinerario A: máx destinos con presupuesto
    itinerary_a = _planner.plan_max_destinations(
        graph, origin, budget,
        weight_fn=lambda dist, rates: dist * rates["cost_per_km"],
        allowed_keys=_normalize_transport_keys(transport_types),
        include_secondary=include_secondary,
    )
    
    # Itinerario B: máx destinos con tiempo
    itinerary_b = _planner.plan_max_destinations(
        graph, origin, time_hours * 60,
        weight_fn=lambda dist, rates: dist * rates["time_per_km_min"],
        allowed_keys=_normalize_transport_keys(transport_types),
        include_secondary=include_secondary,
    )
    
    return jsonify({
        "origin": origin,
        "itinerary_a": itinerary_a.to_dict(),
        "itinerary_b": itinerary_b.to_dict(),
    })
```

#### `POST /api/plan/route`

**Propósito:** Encontrar la mejor ruta entre dos aeropuertos según criterio.

```
Request:
{
  "origin": "BOG",
  "dest": "CCS",
  "criteria": ["cost", "time"],  # Criterios deseados
  "transport_types": ["Comercial"],
  "include_secondary": false
}

Response:
{
  "cost": {
    "optimization_criteria": "cost",
    "visited_airports": ["BOG", "MDE", "CCS"],
    "legs": [...],
    "total_cost": 95.0,
    "total_time_min": 65.0
  },
  "time": {
    "optimization_criteria": "time",
    "visited_airports": ["BOG", "MDE", "CCS"],
    "legs": [...],
    "total_cost": 95.0,
    "total_time_min": 65.0
  }
}
```

**Backend logic:**
```python
@planner_bp.route("/api/plan/route", methods=["POST"])
def plan_route():
    graph = graph_state.get_graph()
    body = request.get_json()
    
    origin = body["origin"]
    dest = body["dest"]
    criteria = body["criteria"]
    transport_types = body["transport_types"]
    include_secondary = body["include_secondary"]
    
    result = {}
    for criterion in criteria:
        optimizer = _optimizers.get(criterion)
        if optimizer:
            itinerary = optimizer.optimize(
                graph, origin, dest,
                transport_types=transport_types,
                include_secondary=include_secondary,
            )
            if itinerary:
                result[criterion] = itinerary.to_dict()
    
    return jsonify(result)
```

---

### 4.3 Blueprint de Reportes: `routes/report_routes.py`

**Responsabilidad:** Endpoints de reportes de sesión.

#### `GET /api/report/<session_id>`

**Propósito:** Obtener reporte completo de una sesión.

```
Response:
{
  "session_id": "abc123xyz",
  "visited": [
    {
      "airport_id": "BOG",
      "name": "Aeropuerto Internacional El Dorado",
      "city": "Bogotá",
      "country": "Colombia",
      "timezone": "America/Bogota"
    },
    ...
  ],
  "legs": [
    {
      "origin_id": "BOG",
      "destination_id": "MDE",
      "aircraft": "Comercial",
      "distance": 250.5,
      "flight_time_min": 35.0,
      "leg_cost": 45.09
    },
    ...
  ],
  "activities": [
    {
      "name": "Tour histórico",
      "type": "cultural",
      "duration_min": 120,
      "cost_usd": 30.0,
      "performed_at_min": 150
    },
    ...
  ],
  "jobs": [
    {
      "name": "Guía turístico",
      "hourly_rate": 25.0,
      "hours_worked": 8.0,
      "income_usd": 200.0
    },
    ...
  ],
  "decisions": [
    {
      "timestamp_min": 0,
      "kind": "transport",
      "details": {
        "origin": "BOG",
        "destination": "MDE",
        "aircraft": "Comercial",
        "cost_usd": 45.09,
        "time_min": 35.0,
        "is_subsidized": false
      }
    },
    ...
  ],
  "totals": {
    "budget_initial": 1000.0,
    "budget_spent": 450.87,
    "budget_earned": 200.0,
    "budget_remaining": 749.13,
    "time_total_min": 480.0
  }
}
```

**Backend logic:**
```python
@report_bp.route("/api/report/<session_id>", methods=["GET"])
def get_report(session_id: str):
    session = _SESSIONS.get(session_id)
    if not session:
        return jsonify({"error": "Sesión no encontrada"}), 404
    
    graph = graph_state.get_graph()
    trip_report = session.finalize_and_report()
    decisions = list(getattr(session.state, "decisions", []) or [])
    
    report = ReportGenerator().generate(
        graph=graph,
        trip_report=trip_report,
        decisions=decisions,
    )
    
    return jsonify({
        "session_id": session_id,
        **report,
    })
```

---

## 🔗 V. CONEXIONES Y FLUJO DE DATOS

### 5.1 Flujo Completo: Cargar Grafo

```
1. Usuario clickea "Cargar JSON" en header
   ↓
2. graphOrchestrator.js abre modal de archivo
   ↓
3. Usuario selecciona file.json local
   ↓
4. JavaScript: apiPostFormData("/api/load-graph", formData)
   ↓
5. Backend: graph_routes.load_graph()
   - Parsea JSON con GraphDataService
   - Construye Graph (add_vertex + add_edge)
   - Almacena en graph_state.set_graph()
   - Retorna JSON serializado
   ↓
6. Frontend: graphUI.transformGraphToD3Data(response)
   - Convierte vértices/aristas → nodos/links D3
   ↓
7. D3 renderiza:
   - Círculos para aeropuertos
   - Flechas para rutas
   - Etiquetas IATA
   ↓
8. graphOrchestrator.showGraphPanels()
   - Hace visibles los paneles laterales
   - Habilita botones de planner
```

### 5.2 Flujo Completo: Planificación Básica

```
1. Usuario ingresa parámetros en plannerPanel:
   - Origen: "BOG"
   - Presupuesto: 600 USD
   - Tiempo: 50 horas
   - Tipos de aeronave: ["Comercial", "Regional"]
   - Incluir secundarios: true
   ↓
2. Usuario clickea "Calcular itinerario"
   ↓
3. plannerPanel.submitBasic()
   - Valida inputs
   - state.loading = true (muestra "Calculando...")
   ↓
4. JavaScript: fetchBasicPlan({ origin, budget, time_hours, ... })
   - POST a /api/plan/basic
   ↓
5. Backend: planner_routes.plan_basic()
   - Obtiene graph = graph_state.get_graph()
   - Parsea request JSON
   
   // Itinerario A: máx destinos por presupuesto
   - itinerary_a = ItineraryPlanner().plan_max_destinations(
       graph, "BOG", 600,
       weight_fn = lambda d, r: d * r["cost_per_km"],
       allowed_keys = {"commercial", "regional"},
       include_secondary = true,
     )
   - Usa DFS + backtracking
   - Retorna Itinerary con legs ordenados
   
   // Itinerario B: máx destinos por tiempo
   - itinerary_b = ItineraryPlanner().plan_max_destinations(
       graph, "BOG", 50 * 60 = 3000,
       weight_fn = lambda d, r: d * r["time_per_km_min"],
       ...
     )
   
   - Retorna JSON: {
       "origin": "BOG",
       "itinerary_a": {...},
       "itinerary_b": {...},
     }
   ↓
6. Frontend: recibe JSON y actualiza state
   - state.itinerary_a = data.itinerary_a
   - state.itinerary_b = data.itinerary_b
   ↓
7. plannerPanel.renderResults(resultsList, ...)
   - Crea dos tarjetas (A y B)
   - Cada una muestra:
     * Etiqueta (ej: "A — Máx. destinos por presupuesto")
     * Criterio (cost, time)
     * Tags: # aeropuertos, costo total, tiempo total
     * Lista de legs (BOG→MDE→LIM→CCS)
     * Botón "Ver en el mapa"
   ↓
8. Usuario clickea "Ver en el mapa" en itinerario A
   - routeAnimationController.highlightRoute(itinerary_a)
   - D3 resalta nodos visitados (color especial)
   - D3 resalta rutas (líneas más gruesas)
   - Anima un "avión" siguiendo la ruta
```

### 5.3 Flujo Completo: Reporte Final

```
1. Una sesión avanzada termina
   - Usuario decide interrumpir sesión
   - Datos almacenados en session.finalize_and_report()
   ↓
2. Frontend: reportPanel.setSessionId(session_id)
   - Muestra ID en panel
   - Habilita botón "Cargar reporte"
   ↓
3. Usuario clickea "Cargar reporte"
   ↓
4. JavaScript: fetchSessionReport(sessionId)
   - GET a /api/report/{sessionId}
   ↓
5. Backend: report_routes.get_report(session_id)
   - session = _SESSIONS.get(session_id)
   - trip_report = session.finalize_and_report()
   - graph = graph_state.get_graph()
   
   - ReportGenerator().generate(
       graph=graph,
       trip_report=trip_report,
       decisions=decisions,
     )
   
   - Procesos internos:
     * _serialize_visited(visited_raw, graph)
       → Agrega nombre, ciudad, país de cada aeropuerto
     * _serialize_legs(legs)
       → Convierte Leg → dict serializable
     * _serialize_activities(activities)
       → Convierte ActivityRecord → dict
     * _serialize_jobs(jobs)
       → Convierte JobRecord → dict
     * _serialize_decisions(decisions)
       → Convierte DecisionRecord → dict
   
   - Retorna JSON completo
   ↓
6. Frontend: reportPanel actualiza estado y renderiza
   - reportRender.renderVisited(listEl, visited)
   - reportRender.renderLegs(listEl, legs)
   - reportRender.renderActivities(listEl, activities)
   - reportRender.renderJobs(listEl, jobs)
   - reportRender.renderDecisions(listEl, decisions)
   - reportRender.renderTotals(totalsBlock, totals)
   ↓
7. Usuario ve reporte completo con:
   - Lista de destinos visitados
   - Detalle de cada tramo de vuelo
   - Actividades realizadas
   - Trabajos completados
   - Decisiones tomadas paso a paso
   - Resumen de totales (presupuesto, tiempo)
```

---

## 💼 VI. FUNCIONALIDADES PRINCIPALES

### 6.1 Planificación Básica: Dos Itinerarios Automáticos

**Propósito:** Desde un aeropuerto origen, generar dos alternativas automáticamente:
- **A:** Máxima cantidad de destinos sin exceder presupuesto
- **B:** Máxima cantidad de destinos sin exceder tiempo disponible

**Ubicación del código:**
- **Backend:** `services/itinerary_planner.py` - `ItineraryPlanner.plan_max_destinations()`
- **Frontend:** `presentacion/scripts/panels/planner/planner-panel.js` - `submitBasic()`
- **API:** `routes/planner_routes.py` - `POST /api/plan/basic`

**Algoritmo (DFS + Backtracking):**

1. **Inicialización:**
   - `visited = {origen}`
   - `best = {count: 0, legs: []}`
   - `resource_remaining = budget` (o tiempo)

2. **Recursión DFS:**
   - Para cada ruta saliente del aeropuerto actual:
     - Si destino ya visitado → skip
     - Si no hay aeronave válida → skip
     - Si el costo/tiempo excede remaining → skip
     - Crear Leg con cost y flight_time calculados
     - Agregar a visited y legs
     - **Llamar recursivamente** con nuevo estado
     - **Backtrack:** remover de visited y legs

3. **Snapshot de mejor solución:**
   - Cada vez que visitamos N aeropuertos > best["count"]
   - Guardamos `best["legs"] = list(legs)` (copia)
   - Continuamos explorando otras ramas

4. **Retorno:**
   - Itinerario con el máximo número de destinos encontrado

**Restricciones aplicadas:**
- ✓ No más de una escala en el mismo aeropuerto
- ✓ Presupuesto es restricción dura (no exceder)
- ✓ Tiempo es restricción dura (no exceder)
- ✓ Filtro de tipos de transporte (si se especifica)
- ✓ Filtro de aeropuertos secundarios (si se requiere)

**Ejemplo de ejecución:**

```
Entrada: BOG, presupuesto=$500, tipos=[Comercial]

DFS-path 1: BOG → MDE ($45) → LIM ($70) → CCS ($80) = $195 ✓
  Snapshot: best = {count: 3, legs: [BOG→MDE, MDE→LIM, LIM→CCS]}

DFS-path 2: BOG → MDE → LIM → CCS → GYE ($120) = $315 ✓
  Snapshot: best = {count: 4, legs: [...5 edges]}

DFS-path 3: BOG → MDE → LIM → CCS → GYE → QUE ($150) = $465 ✓
  Snapshot: best = {count: 5, legs: [...]}

DFS-path 4: BOG → MDE → LIM → CCS → GYE → QUE → UIO ($200) = $665 ✗
  Prune: exceeds $500

Backtrack: explorar otras ramas desde CCS, LIM, MDE...

Resultado final: Itinerario con 5 destinos visitados, $465 gastados
```

---

### 6.2 Búsqueda de Mejor Ruta

**Propósito:** Encontrar la ruta óptima entre dos aeropuertos según criterio (costo, tiempo, distancia).

**Ubicación del código:**
- **Backend:** `services/route_optimizer.py` - `CostOptimizer.optimize()`, etc.
- **Frontend:** `presentacion/scripts/panels/planner/planner-panel.js` - `submitRoute()`
- **API:** `routes/planner_routes.py` - `POST /api/plan/route`

**Algoritmo:** Dijkstra

1. **Inicialización:**
   - `dist[v] = ∞ para todos los v`
   - `dist[origen] = 0`
   - `pred[v] = None` (predecesor en ruta)

2. **Bucle principal:**
   - Mientras haya nodos no visitados:
     - `u = nodo no visitado con dist[u] mínimo`
     - Si `u == destino` → encontrado, salir
     - Para cada ruta saliente `(u, v)`:
       - Calcular `weight = _pick_best_aircraft(...)`
       - `alt = dist[u] + weight`
       - Si `alt < dist[v]`:
         - `dist[v] = alt`
         - `pred[v] = u`

3. **Reconstrucción de ruta:**
   - Comenzar en destino
   - Seguir predesores hacia atrás hasta origen
   - Invertir para obtener ruta origen → destino

4. **Conversión a Itinerary:**
   - Para cada par de aeropuertos en ruta:
     - Buscar ruta directa en grafo
     - Crear Leg con costo y tiempo

**Ejemplo:**

```
Entrada: BOG → CCS, criterio=COSTO, tipos=[Comercial]

Inicialización:
  dist = {BOG: 0, MDE: ∞, LIM: ∞, CCS: ∞, ...}
  unvisited = {todos}

Iteración 1:
  u = BOG (dist=0, mínimo)
  Vecinos: MDE (100km, $18), LIM (300km, $54)
  dist[MDE] = 0 + 18 = 18, pred[MDE] = BOG
  dist[LIM] = 0 + 54 = 54, pred[LIM] = BOG

Iteración 2:
  u = MDE (dist=18, mínimo no visitado)
  Vecinos: CCS (250km, $45), LIM (150km, $27)
  dist[CCS] = 18 + 45 = 63, pred[CCS] = MDE
  dist[LIM] = min(54, 18 + 27) = 45, pred[LIM] = MDE

Iteración 3:
  u = LIM (dist=45, mínimo no visitado)
  Vecinos: CCS (200km, $36)
  dist[CCS] = min(63, 45 + 36) = 63 (no cambia)

Iteración 4:
  u = CCS (dist=63) → ¡encontrado!

Reconstrucción:
  CCS ← MDE ← BOG
  Ruta: BOG → MDE → CCS
  Costo total: $63
```

**Tres variantes (tres criterios):**

| Optimizer | Weight Function | Resultado |
|-----------|-----------------|-----------|
| **CostOptimizer** | `distance × cost_per_km` | Ruta más barata |
| **TimeOptimizer** | `distance × time_per_km_min` | Ruta más rápida |
| **DistanceOptimizer** | `distance` (km) | Ruta más corta |

---

### 6.3 Visualización y Reporte Final

**Propósito:** Mostrar resulta dos de planificación en el mapa y generar reporte detallado al finalizar sesión.

**Ubicación del código:**
- **Resaltado de rutas:** `presentacion/scripts/routeAnimationController.js`
- **Generador de reportes:** `services/report_generator.py`
- **Panel de reportes:** `presentacion/scripts/panels/report/report-panel.js`
- **Renderizado de reportes:** `presentacion/scripts/panels/report/report-render.js`

**Resaltado en mapa (D3):**

```javascript
// 1. Obtener lista de aristas desde itinerario
const edges = legsToEdgeList(itinerary.legs);
// → [{source: "BOG", target: "MDE"}, {source: "MDE", target: "LIM"}, ...]

// 2. Aplicar estilos especiales
d3.selectAll("circle")
  .style("fill", n => {
    if (itinerary.visited_airports.includes(n.id))
      return "var(--node-critical-fill)";  // Color especial
    return "var(--node-default-fill)";
  });

d3.selectAll("line")
  .style("stroke", link => {
    if (edges.some(e => e.source === link.source && e.target === link.target))
      return "var(--red)";  // Color rojo para ruta
    return "var(--border)";
  })
  .style("stroke-width", link => {
    if (edges.some(...))
      return "3px";  // Más grueso
    return "1px";
  });

// 3. Animar "avión" siguiendo la ruta
FlightAnimator.animate(edges);
```

**Reporte Final (datos):**

El reporte incluye 6 secciones principales:

| Sección | Contenido | Ubicación |
|---------|-----------|-----------|
| **Visited** | Aeropuertos visitados con detalles | `report_generator.py:_serialize_visited()` |
| **Legs** | Tramos de vuelo (origen, destino, costo, tiempo) | `report_generator.py:_serialize_legs()` |
| **Activities** | Actividades realizadas (nombre, duración, costo) | `report_generator.py:_serialize_activities()` |
| **Jobs** | Trabajos completados (nombre, horas, ingreso) | `report_generator.py:_serialize_jobs()` |
| **Decisions** | Decisiones tomadas paso a paso (transporte, actividades, trabajos) | `report_generator.py:_serialize_decisions()` |
| **Totals** | Resumen: presupuesto inicial, gastado, ganado, saldo, tiempo | `report_generator.py:generate()` |

**Renderizado en frontend:**

```javascript
// report-render.js
renderVisited(listEl, visited)
  → Para cada aeropuerto: nombre, ciudad, país, zona horaria

renderLegs(listEl, legs)
  → Para cada leg: BOG→MDE, Comercial, 250km, $45, 35min

renderActivities(listEl, activities)
  → Para cada actividad: nombre, tipo, duración, costo

renderJobs(listEl, jobs)
  → Para cada trabajo: nombre, horas, ingreso

renderDecisions(listEl, decisions)
  → Para cada decisión: timestamp, tipo (vuelo/actividad/trabajo), detalles

renderTotals(totalsBlock, totals)
  → Presupuesto: $1000 inicial, $450 gastado, $200 ganado = $750 restante
  → Tiempo: 480 minutos totales
```

---

## 🔐 VII. RESTRICCIONES DEL SISTEMA

### 7.1 Restricciones Duras (No Negociables)

| Restricción | Descripción | Implementación |
|------------|-------------|-----------------|
| **No revisitar aeropuertos** | Un viajero no puede escalar más de una vez en el mismo aeropuerto | `itinerary_planner.py:visited.add(next_id)` - pruna branches |
| **Presupuesto limitado** | El costo total no puede exceder el presupuesto especificado | `weight > resource_remaining` → prune |
| **Tiempo limitado** | El tiempo total de vuelo no puede exceder el disponible | `weight > resource_remaining` → prune |
| **Rutas dirigidas** | Si A→B existe, B→A debe declararse explícitamente | `route_optimizer.py:graph.get_neighbors(airport_id)` retorna solo salientes |
| **Rutas bloqueadas** | Las rutas interrumpidas no se pueden usar | `if route.blocked: continue` en _dfs y _dijkstra |

### 7.2 Configuración Ajustable

| Parámetro | Valor por defecto | Rango | Propósito |
|-----------|------------------|-------|----------|
| **Costo Comercial** | $0.18/km | > 0 | Tarifa base de aeronaves comerciales |
| **Costo Regional** | $0.25/km | > 0 | Tarifa base de aeronaves regionales |
| **Costo Hélice** | $0.12/km | > 0 | Tarifa base de helicópteros |
| **Tiempo Comercial** | 0.7 min/km | > 0 | Velocidad de crucero comercial |
| **Tiempo Regional** | 1.1 min/km | > 0 | Velocidad de crucero regional |
| **Tiempo Hélice** | 2.5 min/km | > 0 | Velocidad de crucero helicóptero |
| **Presupuesto Mínimo %** | 35% | 0-100 | % de presupuesto para habilitar trabajos |
| **Intervalo Alojamiento** | 20 horas | > 0 | Cada cuánto el viajero debe alojarse |
| **Intervalo Alimentación** | 8 horas | > 0 | Cada cuánto el viajero debe comer |

### 7.3 Normalización de Datos

**Tipos de aeronaves:** Aceptados en minúsculas, mayúsculas, español e inglés

```python
_AIRCRAFT_NAME_MAP = {
    "Comercial": "commercial",
    "comercial": "commercial",
    "Commercial": "commercial",
    "Commercial": "commercial",
    # ... y así para Regional y Propeller
}
```

**Códigos IATA:** Convertidos a mayúsculas
```python
origin = body.get("origin", "").strip().upper()  # "bog" → "BOG"
```

---

## 🎯 VIII. RESUMEN ARQUITECTÓNICO

### Estructura de Capas (Separación de Responsabilidades)

```
┌─────────────────────────────────────────────────┐
│ PRESENTACIÓN (Frontend)                         │
│ - HTML: estructura                              │
│ - CSS: estilos                                  │
│ - JavaScript: interactividad y UI               │
│ - D3.js: visualización del grafo                │
└──────────────────┬──────────────────────────────┘
                   │ JSON REST
┌──────────────────▼──────────────────────────────┐
│ API (Blueprints de Flask)                       │
│ - Parseo de request                             │
│ - Validación de datos                           │
│ - Orquestación de servicios                     │
│ - Serialización de response                     │
└──────────────────┬──────────────────────────────┘
                   │ Lógica
┌──────────────────▼──────────────────────────────┐
│ SERVICIOS (Lógica de Negocio)                   │
│ - Algoritmos: Dijkstra, DFS, backtracking       │
│ - Transformación de datos                       │
│ - Gestión de estado                             │
└──────────────────┬──────────────────────────────┘
                   │ Estructuras
┌──────────────────▼──────────────────────────────┐
│ MODELOS & CORE (Estructuras de Datos)           │
│ - Graph: vértices (Airport) + aristas (Route)   │
│ - Itinerary: secuencia de Legs                  │
│ - Constants: configuración global               │
└─────────────────────────────────────────────────┘
```

### Flujo de Datos Típico

```
Usuario
  ↓ input HTML
Frontend (JavaScript)
  ↓ apiPost/apiGet (JSON)
API Endpoint (Flask Blueprint)
  ↓ request.get_json()
Service Layer
  ↓ algoritmo, transformación
Model Layer
  ↓ cálculo, lógica pura
Service Layer
  ↓ resultado objeto
API Endpoint
  ↓ obj.to_dict() + jsonify()
Frontend
  ↓ response.json()
HTML DOM
  ↓ render()
Usuario 👁️
```

### Patrones de Diseño Aplicados

| Patrón | Ubicación | Propósito |
|--------|-----------|----------|
| **Singleton** | `graph_state.py` | Un único grafo en memoria |
| **Blueprint Registry** | `app.py` | Módulos de rutas independientes |
| **Strategy Pattern** | `BaseOptimizer` + `CostOptimizer`, `TimeOptimizer`, `DistanceOptimizer` | Intercambiar criterios de optimización |
| **Factory Pattern** | `GraphDataService` | Crear Graph a partir de JSON |
| **Separation of Concerns** | `*-api.js`, `*-render.js`, `*-state.js` | Cada módulo tiene única responsabilidad |
| **DFS + Backtracking** | `itinerary_planner.py` | Exploración de soluciones |
| **Dijkstra + Priority Queue** | `route_optimizer.py` | Busqueda óptima |

---

## 🚀 IX. CONSIDERACIONES PARA LA SUSTENTACIÓN

### Puntos Clave a Explicar

1. **Arquitectura de 3 capas:**
   - Cómo se separan responsabilidades
   - Por qué es escalable y mantenible

2. **Frontend modular:**
   - Cómo los paneles (`planner`, `report`, `info`) son independientes
   - Comunicación vía eventos y estado

3. **Algoritmos:**
   - DFS + backtracking: búsqueda exhaustiva vs. eficiente
   - Dijkstra: garantías de optimalidad
   - Normalización de datos: robustez

4. **Restricciones:**
   - Cómo se aplican (validaciones, pruning)
   - Trade-off entre flexibilidad y seguridad

5. **Datos:**
   - Flujo JSON → Graph → Itinerary → Report
   - Serialización bidireccional

### Posibles Preguntas y Respuestas

**P: ¿Por qué usaste DFS + backtracking en lugar de Dijkstra para planificación básica?**

R: DFS + backtracking explora TODAS las soluciones posibles y encuentra la que **maximiza el número de destinos** sin exceder restricciones. Dijkstra está optimizado para encontrar "la mejor ruta entre dos puntos" según un criterio. Son problemas diferentes: planificación básica es "máximo coverage bajo restricción", mejor ruta es "shortest path".

**P: ¿Cómo se garantiza que el presupuesto nunca se exceda?**

R: En la línea `if edge_weight > resource_remaining: continue`, cualquier leg que causar
a exceso de presupuesto es podado inmediatamente. Es una restricción dura verificada en tiempo real durante DFS.

**P: ¿Por qué separar `*-api.js`, `*-render.js`, y `*-state.js` en el frontend?**

R: Separation of Concerns. `*-api.js` maneja solo HTTP (testeable, reutilizable). `*-render.js` maneja solo DOM (sin lógica, fácil de debuggear). `*-state.js` maneja estado (la fuente de verdad). Cada archivo tiene una responsabilidad única.

**P: ¿Qué pasa si un usuario carga un JSON con rutas cíclicas (BOG→MDE→BOG)?**

R: El algoritmo de DFS + backtracking lo maneja: cuando intenta revisitar BOG desde MDE, la validación `if next_id in visited: continue` lo prune. El ciclo se ignora, es inofensivo.

**P: ¿Cómo escalarías el proyecto para 1,000 aeropuertos?**

R: 1. Índices adicionales en Graph (ej: index por país). 2. Lazy loading de rutas (no todas en memoria). 3. Caché de rutas frecuentes. 4. Backend asincrónico con colas de trabajos (Celery + Redis). 5. Frontend virtual scrolling para listas largas.

---

## 📚 X. DOCUMENTACIÓN DE REFERENCIA RÁPIDA

### Archivos Clave (en orden de importancia)

| Archivo | Líneas | Responsabilidad |
|---------|--------|-----------------|
| `services/itinerary_planner.py` | ~200 | Algoritmo DFS + backtracking |
| `routes/planner_routes.py` | ~150 | Endpoints de planificación |
| `presentacion/scripts/panels/planner/` | ~300 | Panel de planificación UI |
| `services/route_optimizer.py` | ~200 | Algoritmo Dijkstra |
| `services/report_generator.py` | ~250 | Generador de reportes |
| `presentacion/scripts/graphOrchestrator.js` | ~250 | Orquestador frontend |
| `presentacion/scripts/graphUI.js` | ~200 | D3.js rendering |
| `core/graph.py` | ~100 | Estructura del grafo |

### Configuración Global

**Default aircraft rates** (USD/km, min/km):
```python
commercial: 0.18, 0.7
regional:   0.25, 1.1
propeller:  0.12, 2.5
```

**Default constraints:**
```
presupuesto_minimo: 35%
intervalo_alojamiento: 20h
intervalo_alimentacion: 8h
```

### Validaciones Clave

1. **Airport ID:** Código IATA 3 caracteres, no vacío, único
2. **Route:** origen ≠ destino, distance ≥ 0, cost ≥ 0
3. **Leg:** distance ≥ 0, flight_time_min ≥ 0, leg_cost ≥ 0
4. **Budget/Time:** > 0, valores numéricos
5. **Transport types:** no vacío si se especifica

---

## 🎓 CONCLUSIÓN

Tu parte del proyecto implementa una **aplicación web para planificación de viajes aéreos** con:

✅ **Visualización interactiva** de grafos (D3.js)
✅ **Planificación automática** de itinerarios (DFS + backtracking)
✅ **Búsqueda de rutas óptimas** (Dijkstra)
✅ **Reporte detallado** de viajes (aggregación de datos)
✅ **Arquitectura escalable** (3 capas, separación de responsabilidades)
✅ **Restricciones duras** (presupuesto, tiempo, no revisitar)
✅ **Frontend modular** (componentes independientes)
✅ **Backend robusto** (validaciones, normalización)

El proyecto demuestra conocimientos en:
- Estructuras de datos (Graph, Itinerary)
- Algoritmos (Dijkstra, DFS, Backtracking)
- Arquitectura de software (3 capas, MVC)
- Frontend interactivo (JavaScript, D3.js, modales)
- Backend REST (Flask, Blueprints)
- Persistencia (JSON, serialización)

---

**Éxito en tu sustentación. Estás muy bien preparado.** 🚀
