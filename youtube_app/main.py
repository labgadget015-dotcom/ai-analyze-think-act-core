"""YouTube Intelligence SaaS Main Application
Flask app with YouTube OAuth integration and core framework wiring
"""

import os
import json
from flask import Flask, request, jsonify, redirect, session, url_for
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import sys

# Add parent directory to path for core module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ingest import ingest, IngestConfig
from core.analysis import analyze, AnalysisRequest
from core.recommendations import recommend, RecommendationRequest
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# YouTube OAuth Configuration
CLIENT_SECRETS_FILE = os.environ.get('CLIENT_SECRETS_FILE', 'credentials.json')
SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']


class YouTubeApp:
    """Main YouTube Intelligence SaaS Application Class"""
    
    def __init__(self):
        pass
    
    def process_youtube_data(self, channel_data, goal='grow_subscribers', budget=0):
        """Full pipeline: ingest -> analyze -> recommend"""
        try:
            # Step 1: Ingest YouTube data
            # Convert channel_data to DataFrame format expected by ingest
            if isinstance(channel_data, dict):
                df = pd.DataFrame([channel_data])
            else:
                df = pd.DataFrame(channel_data)
            
            # Step 2: Analyze data
            analysis_request = AnalysisRequest(
                dataset=df,
                goal=goal,
                constraints={'budget': budget, 'timeframe_days': 30}
            )
            analysis_result = analyze(analysis_request)
            
            # Step 3: Generate recommendations
            recommendation_request = RecommendationRequest(
                insights={'analysis': analysis_result},
                goal=goal,
                budget=budget
            )
            recommendations = recommend(recommendation_request)
            
            return {
                'status': 'success',
                'analysis': {
                    'goal': analysis_result.goal,
                    'diagnosis': analysis_result.diagnosis,
                    'trends': analysis_result.trends,
                    'anomalies': analysis_result.anomalies,
                    'rankings': analysis_result.rankings,
                    'predictions': analysis_result.predictions,
                    'metrics_to_watch': analysis_result.metrics_to_watch
                },
                'recommendations': [
                    {
                        'id': action.id,
                        'description': action.description,
                        'priority': action.priority.value,
                        'effort': action.effort.value,
                        'expected_impact_metric': action.expected_impact_metric,
                        'rationale': action.rationale,
                        'budget_required': action.budget_required
                    }
                    for action in recommendations
                ]
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


youtube_app = YouTubeApp()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'youtube-intelligence-saas'}), 200


@app.route('/auth/youtube/connect', methods=['GET'])
def youtube_oauth_connect():
    """Initiate YouTube OAuth flow"""
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=url_for('youtube_oauth_callback', _external=True)
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        session['state'] = state
        return jsonify({
            'authorization_url': authorization_url,
            'message': 'Redirect to this URL to authorize'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/auth/youtube/callback', methods=['GET'])
def youtube_oauth_callback():
    """Handle YouTube OAuth callback"""
    try:
        state = session.get('state')
        code = request.args.get('code')
        
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            state=state,
            redirect_uri=url_for('youtube_oauth_callback', _external=True)
        )
        
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Store credentials in session
        session['youtube_credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        return jsonify({
            'status': 'authenticated',
            'message': 'Successfully connected to YouTube'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/analyze', methods=['POST'])
def analyze_channel():
    """Analyze YouTube channel data endpoint
    Expected payload: {"channel_id": "...", "video_data": {...}}
    """
    try:
        payload = request.get_json()
        results = youtube_app.process_youtube_data(payload.get('video_data'))
        return jsonify(results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/v1/goals', methods=['GET', 'POST'])
def youtube_goals():
    """Manage YouTube channel growth goals
    GET: Retrieve configured goals
    POST: Set new goals (grow_subscribers, increase_ctr, boost_watch_time)
    """
    if request.method == 'GET':
        try:
            goals = session.get('youtube_goals', {})
            return jsonify({'goals': goals}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            payload = request.get_json()
            # Validate goals
            valid_goals = ['grow_subscribers', 'increase_ctr', 'boost_watch_time']
            goals = {k: v for k, v in payload.items() if k in valid_goals}
            session['youtube_goals'] = goals
            return jsonify({'status': 'success', 'goals': goals}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    # Development server
    app.run(
        host=os.environ.get('HOST', 'localhost'),
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('DEBUG', False)
    )
