# Clase Graph
# Contrato de datos:
# - nodos: dict[str, Airport] (clave: código IATA, valor: objeto Airport)
# - aristas: dict[str, list[Route]] (clave: código IATA origen, valor: lista de rutas salientes)
# - Configuración global (opcional):
#     - aeronaves: dict[str, dict] (costoKm y tiempoKm por tipo de aeronave)
#     - presupuestoMinimoPorc: float (default: 35%)
#     - intervaloAlojamiento: int (default: 20 horas)
#     - intervaloAlimentacion: int (default: 8 horas)
