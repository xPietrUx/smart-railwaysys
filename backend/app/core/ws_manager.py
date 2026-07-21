from fastapi import WebSocket


class ConnectionManager:
	"""Rozgłasza JSON-owe wiadomości do wszystkich podłączonych klientów WebSocket.
	Martwe połączenia są cicho odrzucane, żeby jeden zerwany klient nie psuł
	broadcastu dla pozostałych."""

	def __init__(self) -> None:
		self._connections: set[WebSocket] = set()

	async def connect(self, websocket: WebSocket) -> None:
		await websocket.accept()
		self._connections.add(websocket)

	def disconnect(self, websocket: WebSocket) -> None:
		self._connections.discard(websocket)

	async def broadcast(self, message: dict) -> None:
		dead: list[WebSocket] = []
		for connection in list(self._connections):
			try:
				await connection.send_json(message)
			except Exception:
				dead.append(connection)
		for connection in dead:
			self._connections.discard(connection)

	@property
	def connection_count(self) -> int:
		return len(self._connections)
