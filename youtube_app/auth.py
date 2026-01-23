"""YouTube OAuth Authentication Handler
Manages OAuth flow, credential storage, and token refresh
"""

import os
import json
import pickle
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account


class YouTubeAuthHandler:
    """Handles YouTube OAuth authentication and credential management"""
    
    def __init__(self, client_secrets_file=None, scopes=None):
        self.client_secrets_file = client_secrets_file or os.environ.get(
            'YOUTUBE_CLIENT_SECRETS', 'credentials.json'
        )
        self.scopes = scopes or [
            'https://www.googleapis.com/auth/youtube.readonly',
            'https://www.googleapis.com/auth/youtube.force-ssl'
        ]
        self.credentials = None
        self.token_file = os.environ.get('TOKEN_FILE', 'youtube_token.pickle')
    
    def get_authorization_url(self, redirect_uri):
        """Generate YouTube OAuth authorization URL
        
        Args:
            redirect_uri: Callback URL after authorization
        
        Returns:
            Tuple of (authorization_url, state_token)
        """
        try:
            flow = Flow.from_client_secrets_file(
                self.client_secrets_file,
                scopes=self.scopes,
                redirect_uri=redirect_uri
            )
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            return authorization_url, state, flow
        except Exception as e:
            raise Exception(f"Failed to get authorization URL: {str(e)}")
    
    def exchange_code_for_credentials(self, flow, authorization_response):
        """Exchange authorization code for OAuth credentials
        
        Args:
            flow: OAuth flow object from get_authorization_url
            authorization_response: Full authorization response URL
        
        Returns:
            Credentials object
        """
        try:
            flow.fetch_token(authorization_response=authorization_response)
            self.credentials = flow.credentials
            self.save_credentials()
            return self.credentials
        except Exception as e:
            raise Exception(f"Failed to exchange code for credentials: {str(e)}")
    
    def load_credentials(self):
        """Load credentials from pickle file if available
        
        Returns:
            Credentials object or None
        """
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    self.credentials = pickle.load(token)
                    return self.credentials
            except Exception as e:
                print(f"Error loading credentials: {str(e)}")
        return None
    
    def save_credentials(self):
        """Save credentials to pickle file for future use"""
        if self.credentials:
            try:
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.credentials, token)
            except Exception as e:
                print(f"Error saving credentials: {str(e)}")
    
    def refresh_credentials_if_needed(self):
        """Refresh credentials if they're expired
        
        Returns:
            True if refresh was needed, False otherwise
        """
        if not self.credentials:
            return False
        
        if self.credentials.expired and self.credentials.refresh_token:
            try:
                request = Request()
                self.credentials.refresh(request)
                self.save_credentials()
                return True
            except Exception as e:
                print(f"Error refreshing credentials: {str(e)}")
                return False
        return False
    
    def is_authenticated(self):
        """Check if user is authenticated with valid credentials
        
        Returns:
            Boolean indicating authentication status
        """
        if not self.credentials:
            return False
        
        if self.credentials.expired:
            return self.refresh_credentials_if_needed() and not self.credentials.expired
        
        return True
    
    def get_access_token(self):
        """Get current access token
        
        Returns:
            Access token string or None
        """
        if self.is_authenticated():
            return self.credentials.token
        return None
    
    def revoke_credentials(self):
        """Revoke OAuth credentials
        
        Returns:
            Boolean indicating success
        """
        if self.credentials and self.credentials.token:
            try:
                requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': self.credentials.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
                self.credentials = None
                if os.path.exists(self.token_file):
                    os.remove(self.token_file)
                return True
            except Exception as e:
                print(f"Error revoking credentials: {str(e)}")
        return False
    
    def get_credentials_info(self):
        """Get information about current credentials
        
        Returns:
            Dictionary with credential metadata
        """
        if not self.credentials:
            return {'authenticated': False}
        
        return {
            'authenticated': True,
            'expired': self.credentials.expired,
            'token': self.credentials.token[:20] + '...' if self.credentials.token else None,
            'scopes': self.credentials.scopes,
            'client_id': getattr(self.credentials, 'client_id', None)
        }
