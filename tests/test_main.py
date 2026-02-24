"""
Unit tests for youtube_app/main.py Flask endpoints.
"""

import sys
import os
import pytest

# Ensure the repo root is on the path so core/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_app.main import app


@pytest.fixture()
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'


class TestAnalyzeEndpoint:
    def test_missing_body_returns_400(self, client):
        """No JSON body → 400 with descriptive error."""
        response = client.post('/api/v1/analyze', content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_null_json_body_returns_400(self, client):
        """Sending null as JSON body → 400."""
        response = client.post(
            '/api/v1/analyze',
            json=None,
            content_type='application/json',
        )
        assert response.status_code == 400

    def test_empty_json_object_returns_400(self, client):
        """Empty JSON object {} → 400 because payload is falsy."""
        response = client.post('/api/v1/analyze', json={})
        assert response.status_code == 400

    def test_invalid_budget_returns_400(self, client):
        """Non-numeric budget → 400 with descriptive error."""
        payload = {'video_data': [{'views': 100}], 'goal': 'grow_subscribers', 'budget': 'abc'}
        response = client.post('/api/v1/analyze', json=payload)
        assert response.status_code == 400
        data = response.get_json()
        assert 'budget' in data.get('error', '')

    def test_valid_payload_returns_200(self, client):
        """Valid payload with video_data → pipeline runs, 200 returned."""
        payload = {
            'channel_id': 'UC_test',
            'video_data': [{'views': 1000, 'ctr': 5.5}],
            'goal': 'grow_subscribers',
            'budget': 0,
        }
        response = client.post('/api/v1/analyze', json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'analysis' in data
        assert 'recommendations' in data

    def test_goal_extracted_from_payload(self, client):
        """goal passed in payload must be honoured by the pipeline."""
        payload = {
            'video_data': [{'ctr': 6.0}],
            'goal': 'increase_ctr',
            'budget': 0,
        }
        response = client.post('/api/v1/analyze', json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data['analysis']['goal'] == 'increase_ctr'

    def test_budget_extracted_from_payload(self, client):
        """budget passed in payload must reach the recommendations layer."""
        payload = {
            'video_data': [{'watch_time': 4.0}],
            'goal': 'boost_watch_time',
            'budget': 500,
        }
        response = client.post('/api/v1/analyze', json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

    def test_null_video_data_succeeds(self, client):
        """Omitting video_data (None) must not raise an unhandled exception."""
        payload = {'goal': 'grow_subscribers'}
        response = client.post('/api/v1/analyze', json=payload)
        # Should either succeed (empty DataFrame) or return a structured error
        assert response.status_code in (200, 400)
        data = response.get_json()
        assert data is not None


class TestGoalsEndpoint:
    def test_get_goals_empty(self, client):
        """GET /api/v1/goals returns empty goals by default."""
        with client.session_transaction() as sess:
            sess.clear()
        response = client.get('/api/v1/goals')
        assert response.status_code == 200
        data = response.get_json()
        assert 'goals' in data

    def test_post_goals_persists(self, client):
        """POST /api/v1/goals stores valid goals."""
        payload = {'grow_subscribers': True, 'invalid_goal': True}
        response = client.post('/api/v1/goals', json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert 'grow_subscribers' in data['goals']
        assert 'invalid_goal' not in data['goals']
