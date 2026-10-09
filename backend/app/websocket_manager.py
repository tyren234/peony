"""WebSocket connection manager for real-time telemetry streaming (Bonus requirement)."""

from typing import Any, Dict, List
from fastapi import WebSocket


class TelemetryBroadcaster:
    """Manages active WebSocket client connections and broadcasts live telemetry measurements."""

    def __init__(self) -> None:
        self.active_websocket_connections: List[WebSocket] = []

    async def register_connection(self, websocket_client: WebSocket) -> None:
        """Accept and register incoming WebSocket connection."""
        await websocket_client.accept()
        self.active_websocket_connections.append(websocket_client)

    def unregister_connection(self, websocket_client: WebSocket) -> None:
        """Remove WebSocket connection from active pool."""
        if websocket_client in self.active_websocket_connections:
            self.active_websocket_connections.remove(websocket_client)

    async def broadcast_measurement(self, measurement_payload: Dict[str, Any]) -> None:
        """Broadcast newly created measurement to all active WebSocket clients."""
        disconnected_clients: List[WebSocket] = []
        for single_connection in list(self.active_websocket_connections):
            try:
                await single_connection.send_json(measurement_payload)
            except Exception:
                disconnected_clients.append(single_connection)

        for stale_connection in disconnected_clients:
            self.unregister_connection(stale_connection)


telemetry_broadcaster = TelemetryBroadcaster()
