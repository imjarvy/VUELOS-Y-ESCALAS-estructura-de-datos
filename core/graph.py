"""Graph model.

Optional global configuration:
- aircrafts: dict[str, dict] (cost_per_km, time_per_km)
- min_budget_pct: float (default 35)
- accommodation_interval: int (hours)
- feeding_interval: int (hours)

This class holds vertices and provides basic helpers such as
`add_vertex(vertex)`. Serialization and path algorithms belong
in other modules or helper methods.
"""

class Graph:
    def __init__(self) -> None:
        self.vertices = []

    def add_vertex(self, vertex) -> None:
        """Add a vertex (Airport) to the graph's vertex list."""
        self.vertices.append(vertex)