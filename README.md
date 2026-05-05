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

ESTRUCTURA OBJETIVO (dispuesta a cambios): 
#  skyroute_planner/
├──  main.py                # Punto de entrada, solo lanza la app
│
├── 📁 data/
│   └──  airports.json       # 30+ aeropuertos
│
├── 📁 models/                 # Solo datos, cero lógica
│   ├──  airport.py          # Clase Airport (nodo)
│   ├──  route.py            # Clase Route (arista)
│   ├──  aircraft.py         # Tipos de aeronave y tarifas
│   └──  itinerary.py        # Resultado de ruta calculada
│
├── 📁 core/                   # Solo estructura de datos
│   └──  graph.py            # Grafo lista de adyacencia (desde cero)
│
├── 📁 services/               # Lógica de negocio
│   ├──  base_optimizer.py   # Clase abstracta para optimizadores
│   ├──  graph_loader.py     # JSON → Graph
│   ├──  route_optimizer.py  # Dijkstra (costo, tiempo, distancia)
│   ├──  itinerary_planner.py# Máx destinos con restricciones
│   ├──  advanced_planner.py # Planificación dinámica R3
│   ├──  network_manager.py  # Interrupciones R4
│   └──  report_generator.py # Consolida datos de todos los módulos
│
├── 📁 ui/                     # Solo visualización, sin lógica
│   ├──  app.py              # Ventana principal, une los paneles
│   ├──  graph_canvas.py     # Dibuja el grafo en Canvas
│   ├──  planner_panel.py    # UI de planificación básica R2
│   ├──  advanced_panel.py   # UI planificación avanzada R3
│   └──  report_panel.py     # UI reporte final R5
│
└── 📁 utils/
    └──  constants.py        # Tarifas default aeronaves, intervalos
