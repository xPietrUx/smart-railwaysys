from unittest.mock import MagicMock
from app.schemas.simulation import TrainCreateRequest
from app.services.simulation_service import (
	ACTIVE_TRAINS,
	add_train,
	clear_all_trains,
	get_all_trains,
	tick_simulation,
)
from app.schemas.routing import FastestRouteResponse


def test_add_train_and_tick():
	clear_all_trains()
	mock_driver = MagicMock()
	mock_session = MagicMock()
	mock_driver.session.return_value.__enter__.return_value = mock_session

	# Mock routing A* result
	from app.schemas.network import StationNode, TrackSegment
	mock_route = FastestRouteResponse(
		found=True,
		fromStation="KAT",
		toStation="OPO",
		trainType="IC",
		path=[
			StationNode(id="KAT", code="KAT", name="Katowice", type="station", lat=0, lon=0, platforms=1, tracks=1, dailyTrains=1),
			StationNode(id="GLI", code="GLI", name="Gliwice", type="station", lat=0, lon=0, platforms=1, tracks=1, dailyTrains=1),
			StationNode(id="OPO", code="OPO", name="Opole", type="station", lat=0, lon=0, platforms=1, tracks=1, dailyTrains=1)
		],
		segments=[
			TrackSegment(id="1", source="KAT", target="GLI", segmentId="KAT-GLI", line=1, distKm=30, travelMin=20, vmax=120, railTracks=2, status="active"),
			TrackSegment(id="2", source="GLI", target="OPO", segmentId="GLI-OPO", line=1, distKm=50.5, travelMin=25, vmax=120, railTracks=2, status="active")
		],
		totalTravelMin=45,
		totalDistKm=80.5,
		exploredNodesCount=3,
	)

	# Podmieniamy find_fastest_route_astar na czas testu
	import app.services.simulation_service as sim_svc
	old_routing = sim_svc.find_fastest_route_astar
	sim_svc.find_fastest_route_astar = MagicMock(return_value=mock_route)

	try:
		req = TrainCreateRequest(
			trainId="TEST_1",
			name="Test IC",
			trainType="IC",
			fromStation="KAT",
			toStation="OPO",
			speedKmh=120,
		)
		train = add_train(mock_driver, req)
		assert train.trainId == "TEST_1"
		assert train.status == "running"
		assert train.currentStationId == "KAT"
		assert len(get_all_trains()) == 1

		# Wykonajmy tick symulacji
		res = tick_simulation(mock_driver, delta_sec=1.0, time_scale=60.0)
		assert len(res.trains) == 1
		assert res.trains[0].progress > 0.0
	finally:
		sim_svc.find_fastest_route_astar = old_routing
		clear_all_trains()
