# YouTube Intelligence SaaS Application

**AI-Powered YouTube Channel Analytics & Growth Recommendations**

Part of the `ai-analyze-think-act-core` framework - a reusable AI analysis platform.

## 🎯 Overview

This YouTube Intelligence SaaS provides content creators with:
- **Real-time channel analytics** (subscribers, CTR, watch time)
- **AI-powered growth recommendations** based on data analysis
- **Goal tracking** for subscriber growth, CTR optimization, and watch time
- **Weekly automated analysis reports**
- **Beautiful dashboard UI** for insights visualization

## 🏗️ Architecture

```
youtube_app/
├── __init__.py           # Module initialization
├── main.py               # Flask app with OAuth & REST API
├── auth.py               # YouTube OAuth handler
├── weekly_analysis.py    # Analysis pipeline orchestration
└── README.md             # This file

templates/
└── dashboard.html        # Responsive dashboard UI

core/                     # Reusable AI framework
├── ingest.py             # Data ingestion
├── analysis.py           # Analysis engine
├── recommendations.py    # Recommendation engine
└── models.py             # Data models
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- YouTube Data API v3 credentials
- Google OAuth 2.0 client secrets

### Installation

```bash
# Clone the repository
git clone https://github.com/labgadget015-dotcom/ai-analyze-think-act-core.git
cd ai-analyze-think-act-core

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SECRET_KEY="your-secret-key"
export CLIENT_SECRETS_FILE="credentials.json"
export YOUTUBE_CHANNEL_ID="your-channel-id"
export DATABASE_URL="postgresql://user:pass@localhost/dbname"  # Optional
```

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **YouTube Data API v3**
4. Create OAuth 2.0 credentials (Web application)
5. Download credentials as `credentials.json`
6. Add authorized redirect URIs:
   - `http://localhost:5000/auth/youtube/callback`
   - Your production domain callback URL

### Run the Application

```bash
# Start Flask development server
python youtube_app/main.py

# Or with environment variables
HOST=0.0.0.0 PORT=5000 DEBUG=True python youtube_app/main.py
```

Visit `http://localhost:5000` to access the dashboard.

### Run Weekly Analysis Pipeline

```bash
# Run analysis for a specific channel
python youtube_app/weekly_analysis.py

# Or programmatically
from youtube_app.weekly_analysis import run_weekly_analysis
report = run_weekly_analysis('UC1234567890')
```

## 📡 API Endpoints

### Health Check
```
GET /health
Response: {"status": "healthy", "service": "youtube-intelligence-saas"}
```

### YouTube OAuth Connection
```
GET /auth/youtube/connect
Response: {"authorization_url": "https://...", "message": "..."}
```

### OAuth Callback
```
GET /auth/youtube/callback?code=...&state=...
Response: {"status": "authenticated", "message": "Successfully connected to YouTube"}
```

### Analyze Channel Data
```
POST /api/v1/analyze
Content-Type: application/json

Payload:
{
  "channel_id": "UC1234567890",
  "video_data": {
    "videos": [...],
    "metrics": {...}
  }
}

Response:
{
  "status": "success",
  "analysis": {...},
  "recommendations": {...}
}
```

### Manage Growth Goals
```
GET /api/v1/goals
Response: {"goals": {"grow_subscribers": true, ...}}

POST /api/v1/goals
Content-Type: application/json

Payload:
{
  "grow_subscribers": true,
  "increase_ctr": true,
  "boost_watch_time": true
}

Response: {"status": "success", "goals": {...}}
```

## 🧠 Core Framework Integration

The YouTube app leverages the reusable core framework:

```python
from core.ingest import DataIngestor
from core.analysis import AnalysisEngine
from core.recommendations import RecommendationEngine

# Initialize components
ingestor = DataIngestor()
analyzer = AnalysisEngine()
recommender = RecommendationEngine()

# Full pipeline
ingested_data = ingestor.ingest({'source': 'youtube', 'data': raw_data})
analysis = analyzer.analyze(ingested_data)
recommendations = recommender.recommend(analysis)
```

## 🎨 Dashboard Features

- **Metrics Overview**: Real-time display of subscribers, CTR, watch hours
- **OAuth Integration**: One-click YouTube channel connection
- **Goal Progress**: Visual progress bars for growth targets
- **AI Recommendations**: Prioritized actionable insights
- **Analysis Reports**: Historical reports grid
- **Responsive Design**: Mobile-friendly purple gradient theme

## 🔒 Security

- OAuth 2.0 for secure YouTube API access
- Credential encryption with pickle files
- Automatic token refresh
- Session-based authentication
- Environment variable configuration

## 📊 Analysis Pipeline

The `WeeklyAnalysisPipeline` orchestrates:

1. **Fetch** - Retrieve YouTube data via API
2. **Ingest** - Normalize and validate data
3. **Analyze** - Apply AI analysis algorithms
4. **Recommend** - Generate actionable recommendations
5. **Report** - Compile comprehensive weekly reports
6. **Store** - Save results to database (optional)

## 🗄️ Database Schema (Optional)

For production deployments, configure PostgreSQL:

```sql
CREATE TABLE youtube_reports (
  id SERIAL PRIMARY KEY,
  report_id VARCHAR(100) UNIQUE,
  channel_id VARCHAR(50),
  generated_at TIMESTAMP,
  summary JSONB,
  analysis JSONB,
  recommendations JSONB,
  priority_actions JSONB
);
```

## 🚢 Deployment

### AWS Lambda
```bash
# Package application
zip -r youtube-saas.zip youtube_app/ core/ templates/ requirements.txt

# Upload to Lambda with Flask adapter
# Configure API Gateway for HTTP endpoints
```

### Railway/Heroku
```bash
# Create Procfile
echo "web: python youtube_app/main.py" > Procfile

# Deploy
railway up
# or
git push heroku main
```

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "youtube_app/main.py"]
```

## 📈 Roadmap

- [x] YouTube OAuth integration
- [x] Flask REST API
- [x] Dashboard UI
- [x] Weekly analysis pipeline
- [ ] PostgreSQL integration
- [ ] Real YouTube API data fetching
- [ ] Advanced AI recommendations (GPT-4 integration)
- [ ] Email/Slack notifications
- [ ] Multi-channel support
- [ ] Competitor benchmarking

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=youtube_app tests/
```

## 📝 License

MIT License - See LICENSE file

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request

## 📞 Support

For issues or questions:
- Open GitHub Issue
- Email: support@gadgetlab.ai

---

**Built with the AI Analyze-Think-Act Framework** 🤖  
*Empowering creators with intelligent insights*
