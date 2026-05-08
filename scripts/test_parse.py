import os
import sys
import json

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.graphDataService import GraphDataService

with open('data/data.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

service = GraphDataService(raw)
airports = service.get_parsed_airports()
payload = service.export_payload(spanish=True)
for ap in payload.get('aeropuertos', []):
    if ap.get('id') == 'MEX':
        print(json.dumps(ap, ensure_ascii=False, indent=2))
        break
else:
    print('MEX not found in exported payload')
