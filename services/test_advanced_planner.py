from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from acceso_datos.dataLoader import DataLoader
from services.graphDataService import GraphDataService
from services.advanced_planner import AdvancedPlanner

loader = DataLoader()
with open(PROJECT_ROOT / "data" / "airports_new_structure.json", "r", encoding="utf-8") as json_file:
	success, error = loader.load_from_stream(json_file)
	if not success:
		raise RuntimeError(error)

service = GraphDataService(loader.get_raw_data())
graph = service.build_graph()

planner = AdvancedPlanner(graph)
# Show available airports and pick a valid origin automatically
available_airports = [a.airport_id for a in graph.vertices]
print("Available airports:", available_airports)
if not available_airports:
	raise RuntimeError("No airports found in graph payload")

origin = available_airports[0]
print(f"Using origin: {origin}")
session = planner.start_session(origin, 1000, 72)

print(session.step_proposals())