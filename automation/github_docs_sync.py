#!/usr/bin/env python3
"""
GitHub to Google Docs Sync Automation
Automatically documents GitHub commits to Google Docs
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from dotenv import load_dotenv

# Google Docs API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery

# GitHub API
from github import Github

# OpenAI API
import openai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class GitHubDocsSync:
    """Synchronize GitHub commits to Google Docs"""
    
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.docs_document_id = os.getenv('DOCS_DOCUMENT_ID')
        self.repo_owner = os.getenv('REPO_OWNER')
        self.repo_name = os.getenv('REPO_NAME')
        
        # Initialize API clients
        self.github = Github(self.github_token)
        openai.api_key = self.openai_key
        self.docs_service = self._init_google_docs()
        
    def _init_google_docs(self):
        """Initialize Google Docs API client"""
        SCOPES = ['https://www.googleapis.com/auth/documents']
        creds = None
        
        # Load existing credentials
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # Get new credentials if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        return discovery.build('docs', 'v1', credentials=creds)
    
    def get_recent_commits(self, hours: int = 24) -> List[Dict]:
        """Get recent commits from GitHub repository"""
        try:
            repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")
            since = datetime.utcnow() - timedelta(hours=hours)
            
            commits = []
            for commit in repo.get_commits(since=since):
                commits.append({
                    'sha': commit.sha[:7],
                    'message': commit.commit.message,
                    'author': commit.commit.author.name,
                    'date': commit.commit.author.date.isoformat(),
                    'url': commit.html_url
                })
            
            logger.info(f"Found {len(commits)} commits in last {hours} hours")
            return commits
        
        except Exception as e:
            logger.error(f"Error fetching commits: {e}")
            return []
    
    def generate_summary(self, commits: List[Dict]) -> str:
        """Generate AI-powered summary of commits"""
        if not commits:
            return "No new commits found."
        
        commit_text = "\n".join([
            f"- {c['message']} ({c['author']}, {c['sha']})"
            for c in commits
        ])
        
        prompt = f"""Summarize the following Git commits in a concise development update:
        
{commit_text}

Provide:
1. Executive summary
2. Key changes
3. Impact areas"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a technical documentation expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response['choices'][0]['message']['content']
        
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Error generating AI summary"
    
    def append_to_document(self, content: str) -> bool:
        """Append content to Google Doc"""
        try:
            requests = [{
                'insertText': {
                    'text': content,
                    'location': {'index': 1}
                }
            }]
            
            body = {'requests': requests}
            response = self.docs_service.documents().batchUpdate(
                documentId=self.docs_document_id,
                body=body).execute()
            
            logger.info(f"Successfully appended {len(content)} characters to document")
            return True
        
        except Exception as e:
            logger.error(f"Error appending to document: {e}")
            return False
    
    def sync(self, hours: int = 24) -> bool:
        """Main sync function"""
        logger.info("Starting GitHub to Google Docs sync...")
        
        # Get commits
        commits = self.get_recent_commits(hours)
        if not commits:
            logger.info("No commits to sync")
            return True
        
        # Generate summary
        summary = self.generate_summary(commits)
        
        # Format document content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"""
\n=== Development Update - {timestamp} ===

Commits Synced: {len(commits)}

AI Summary:
{summary}

Detailed Commits:
"""
        
        for commit in commits:
            content += f"\n- [{commit['sha']}] {commit['message']}\n  Author: {commit['author']}\n  Date: {commit['date']}\n  URL: {commit['url']}"
        
        # Append to Google Doc
        return self.append_to_document(content)

if __name__ == "__main__":
    sync = GitHubDocsSync()
    success = sync.sync(hours=24)
    exit(0 if success else 1)
