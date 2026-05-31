from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from core.graph import Graph


class GraphLocalStorage:
    """Persist the last loaded graph snapshot to a local JSON file.

    Responsibilities:
    - Save the current graph snapshot to disk
    - Restore a graph snapshot from disk
    - Check whether a saved graph exists
    - Clear the saved graph file
    """

    def __init__(self, storage_path: Optional[str] = None) -> None:
        """Initialize the local storage handler.

        Args:
            storage_path: Optional custom path for the storage file.
        """
        base_dir = Path(__file__).resolve().parent.parent
        default_path = base_dir / "data" / "graph_state.json"
        self.storage_path = Path(storage_path) if storage_path else default_path

    def save_graph(self, graph: Optional[Graph]) -> bool:
        """Save a graph snapshot to the local JSON file.

        Args:
            graph: Graph instance to persist.

        Returns:
            bool: True when the graph was saved successfully, False otherwise.
        """
        if graph is None:
            return False

        payload = {
            "format": "graph_snapshot_v1",
            "graph": graph.to_dict(),
        }

        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with self.storage_path.open("w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def load_graph(self) -> Optional[Graph]:
        """Load the saved graph snapshot from disk.

        Returns:
            Graph: Restored graph instance, or None if no valid snapshot exists.
        """
        if not self.storage_path.exists():
            return None

        try:
            with self.storage_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except Exception:
            return None

        graph_data: Any
        if isinstance(payload, dict) and isinstance(payload.get("graph"), dict):
            graph_data = payload["graph"]
        else:
            graph_data = payload

        if not isinstance(graph_data, dict):
            return None

        return Graph.from_dict(graph_data)

    def has_graph(self) -> bool:
        """Check whether the storage file exists.

        Returns:
            bool: True if a graph snapshot file exists, False otherwise.
        """
        return self.storage_path.exists()

    def clear(self) -> bool:
        """Delete the saved graph snapshot file.

        Returns:
            bool: True when the file was removed or was already absent, False otherwise.
        """
        try:
            if self.storage_path.exists():
                self.storage_path.unlink()
            return True
        except Exception:
            return False
