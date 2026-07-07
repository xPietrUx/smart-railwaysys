from neo4j import Session

from app.schemas.network import NetworkGraphResponse, StationNode, TrackSegment


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


def segment_payload(start_node, relationship, end_node) -> TrackSegment:
	return TrackSegment(
		id=str(relationship.id),
		source=start_node["id"],
		target=end_node["id"],
		segmentId=relationship["segment_id"],
		line=relationship["line"],
		distKm=relationship["dist_km"],
		travelMin=relationship["travel_min"],
		vmax=relationship["vmax"],
		railTracks=relationship["rail_tracks"],
		status=relationship["status"],
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

	segments_by_id = {}
	relationship_count = 0
	for record in relationship_records:
		relationship_count += 1
		relationship = record["r"]
		segment_id = relationship["segment_id"]
		if segment_id not in segments_by_id:
			segments_by_id[segment_id] = segment_payload(
				record["n"],
				relationship,
				record["m"],
			)

	return NetworkGraphResponse(
		stations=stations,
		segments=list(segments_by_id.values()),
		relationshipCount=relationship_count,
	)
