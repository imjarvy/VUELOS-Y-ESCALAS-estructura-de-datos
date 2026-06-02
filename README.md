# Vuelos y Escalas

Aplicación web para explorar una red de aeropuertos, cargar grafos desde JSON y planificar rutas e itinerarios de viaje con restricciones de presupuesto, tiempo y tipos de transporte.

El proyecto combina un backend en Flask con una interfaz web en HTML, CSS y JavaScript. La visualización principal se apoya en D3.js para dibujar el grafo de aeropuertos y sus rutas.

## Qué hace el proyecto

La aplicación permite:

- cargar un grafo de aeropuertos y rutas desde un archivo JSON;
- visualizar la red en forma de grafo dirigido;
- consultar la información detallada de cada aeropuerto;
- configurar parámetros globales del planificador y tarifas por tipo de aeronave;
- bloquear o reactivar rutas durante la simulación;
- generar planes básicos de viaje por costo, tiempo o distancia;
- iniciar sesiones avanzadas de viaje con decisiones paso a paso;
- ver reportes finales de una sesión con el recorrido, actividades, trabajos y totales.

## Estructura del proyecto

```text
app.py                      # Punto de entrada de Flask
acceso_datos/               # Carga y persistencia de datos del grafo
core/                       # Estructuras base del grafo
data/                       # Archivos JSON del grafo y su estado guardado
models/                     # Modelos y dataclasses del dominio
presentacion/
  estilos/                  # CSS de la interfaz
  scripts/                  # Lógica frontend en JavaScript
  vistas/                   # Plantillas HTML
routes/                     # Endpoints REST
services/                   # Lógica de negocio y planificación
utils/                      # Constantes y utilidades
```

## Tecnologías usadas

- Python
- Flask
- Flask-CORS
- HTML5
- CSS3
- JavaScript ES Modules
- D3.js

## Cómo ejecutarlo

El punto de entrada es `app.py`. Desde la raíz del proyecto puedes arrancarlo así:

```bash
python app.py
```

Luego abre en el navegador:

```text
http://127.0.0.1:5000
```

Si prefieres usar Flask directamente, también funciona:

```bash
flask --app app run
```

## Instalación de dependencias

```bash
pip install flask flask-cors
```

Si vas a trabajar dentro de un entorno virtual, actívalo antes de instalar los paquetes.

## Funcionalidades principales

### Visualización del grafo

La pantalla principal muestra los aeropuertos y sus conexiones en un grafo interactivo. Desde ahí puedes abrir paneles laterales con información del aeropuerto seleccionado, rutas, actividades y trabajos disponibles.

### Carga y persistencia del grafo

La aplicación puede cargar archivos JSON con la estructura de aeropuertos y rutas. Además, guarda el último grafo cargado para restaurarlo al volver a abrir la interfaz.

### Configuración global

Puedes ajustar parámetros como:

- el porcentaje mínimo de presupuesto para habilitar trabajos;
- el intervalo de alojamiento;
- el intervalo de alimentación;
- las tarifas y tiempos por kilómetro de cada tipo de aeronave.

### Bloqueo de rutas

El sistema permite interrumpir rutas entre aeropuertos para simular cierres, cancelaciones o condiciones adversas. Esa interrupción afecta la planificación y puede recalcular itinerarios activos.

### Planificación básica

El planificador básico genera alternativas de viaje desde un aeropuerto origen usando criterios como costo, tiempo o distancia. También permite limitar los tipos de transporte y decidir si se incluyen aeropuertos secundarios.

### Sesiones avanzadas de viaje

La sesión avanzada maneja un flujo interactivo paso a paso. En cada momento el sistema propone vuelos, actividades y trabajos disponibles, y luego aplica la decisión del usuario sobre el estado del viaje.

### Reportes

Al cerrar una sesión, el backend genera un reporte con el resumen final del viaje: trayecto recorrido, decisiones tomadas, actividades realizadas, trabajos ejecutados y acumulados totales.

## Backend y rutas importantes

El backend expone las siguientes rutas principales:

- `GET /` muestra la interfaz principal;
- `GET /api/config` obtiene la configuración actual;
- `POST /api/config` guarda cambios globales;
- `GET /api/current-graph` recupera el último grafo cargado;
- `POST /api/load-graph` carga un grafo desde un archivo JSON;
- `POST /api/interrupt-route` bloquea o desbloquea una ruta;
- `POST /api/plan/basic` genera itinerarios básicos;
- `POST /api/plan/route` busca rutas óptimas entre dos aeropuertos;
- `POST /api/session/start` inicia una sesión avanzada;
- `GET /api/session/<session_id>/proposals` obtiene propuestas actuales;
- `POST /api/session/<session_id>/choice` aplica una decisión;
- `GET /api/session/<session_id>/report` genera el reporte de la sesión;
- `GET /api/report/<session_id>` devuelve el resumen final de una sesión.

## Estructura de archivos clave

- `app.py`: crea la aplicación Flask, registra blueprints y sirve la interfaz.
- `routes/graph_routes.py`: carga el grafo, configura parámetros y maneja interrupciones de rutas.
- `routes/planner_routes.py`: expone la planificación básica y la búsqueda de rutas óptimas.
- `routes/trip_session_routes.py`: administra sesiones avanzadas de viaje.
- `routes/report_routes.py`: construye reportes finales de una sesión.
- `services/`: contiene el cálculo de rutas, la planificación, la lógica de sesiones y la generación de reportes.
- `presentacion/scripts/`: coordina la interfaz, animaciones y consumo de APIs.