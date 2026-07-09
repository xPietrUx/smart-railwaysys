from unittest.mock import MagicMock
from app.services.network_service import update_segment_status


def test_update_segment_status_success():
	mock_session = MagicMock()
	mock_record = {"updated_count": 2}
	mock_result = MagicMock()
	mock_result.single.return_value = mock_record
	mock_session.run.return_value = mock_result

	res = update_segment_status(mock_session, "SEG01", "blocked")
	assert res is True
	mock_session.run.assert_called_once()


def test_update_segment_status_not_found():
	mock_session = MagicMock()
	mock_record = {"updated_count": 0}
	mock_result = MagicMock()
	mock_result.single.return_value = mock_record
	mock_session.run.return_value = mock_result

	res = update_segment_status(mock_session, "INVALID", "blocked")
	assert res is False
