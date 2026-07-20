from neo4j import Session

from app.schemas.network import (
	DirectionalState,
	NetworkGraphResponse,
	StationNode,
	TrackSegment,
)


def station_payload(node) -> StationNode:
	return StationNode(
		id=node["id"],
		code=node["id"],
		name=node["name"],
		type=node["type"],
		lat=node["lat"],
		lon=node["lon"],
		platforms=node["platforms"],
		tracks=node["tracks"],
		dailyTrains=node["daily_trains"],
	)


def directional_state_payload(relationship) -> DirectionalState:
	return DirectionalState(
		status=relationship["status"],
		restrictedVmax=relationship.get("restricted_vmax"),
		activeEventId=relationship.get("active_event_id"),
	)


def fetch_network_graph(session: Session) -> NetworkGraphResponse:
	station_records = session.run("MATCH (n:Station) RETURN n ORDER BY n.name")
	stations = [station_payload(record["n"]) for record in station_records]

	relationship_records = session.run(
		"""
		MATCH (n:Station)-[r:TRACK]->(m:Station)
		RETURN n, r, m
		ORDER BY r.segment_id, n.name, m.name
		"""
	)

	# Każdy fizyczny odcinek ma w bazie dwie skierowane relacje (tam i z powrotem)
	# dzielące to samo segment_id. Łączymy je w jeden TrackSegment z osobnym stanem
	# per kierunek — "forward" to zawsze kierunek alfabetycznie mniejszy -> większy id,
	# niezależnie od kolejności, w jakiej wiersze przyjdą z bazy.
	segments_by_id: dict[str, TrackSegment] = {}
	relationship_count = 0
	for record in relationship_records:
		relationship_count += 1
		n_node, relationship, m_node = record["n"], record["r"], record["m"]
		segment_id = relationship["segment_id"]
		is_forward = n_node["id"] < m_node["id"]
		state = directional_state_payload(relationship)

		segment = segments_by_id.get(segment_id)
		if segment is None:
			forward_source, forward_target = (
				(n_node["id"], m_node["id"]) if is_forward else (m_node["id"], n_node["id"])
			)
			segment = TrackSegment(
				segmentId=segment_id,
				source=forward_source,
				target=forward_target,
				line=relationship["line"],
				distKm=relationship["dist_km"],
				travelMin=relationship["travel_min"],
				vmax=relationship["vmax"],
				railTracks=relationship["rail_tracks"],
				forward=state if is_forward else DirectionalState(status="active"),
				backward=state if not is_forward else DirectionalState(status="active"),
			)
			segments_by_id[segment_id] = segment
		elif is_forward:
			segment.forward = state
		else:
			segment.backward = state

	return NetworkGraphResponse(
		stations=stations,
		segments=list(segments_by_id.values()),
		relationshipCount=relationship_count,
	)
