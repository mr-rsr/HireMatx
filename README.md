# Multi-Tenant AI Job Search Platform

A Telegram-based AI platform that automates job searching through intelligent agents. Built with Python, FastAPI, and AWS Bedrock (Claude).

## Features

- **Smart Job Search**: AI-powered job matching based on your profile
- **Resume Analysis**: Upload your resume for AI-powered analysis and optimization suggestions
- **Cover Letter Generation**: Generate tailored cover letters for each job application
- **Application Tracking**: Track all your job applications in one place
- **Daily Recommendations**: Get personalized job recommendations delivered to Telegram
- **Multi-source Scraping**: Aggregates jobs from multiple job boards

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Telegram Bot   │────▶│   FastAPI API    │────▶│   PostgreSQL    │
│  (aiogram)      │     │                  │     │   (Users, Jobs) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
           ┌──────────────┐      ┌──────────────┐
           │  AWS Bedrock │      │ Job Scrapers │
           │  (Claude)    │      │ (Celery)     │
           └──────────────┘      └──────────────┘
```

## Tech Stack

- **Backend**: Python 3.11, FastAPI
- **Database**: PostgreSQL with SQLAlchemy
- **Cache/Queue**: Redis
- **Task Queue**: Celery
- **Bot Framework**: aiogram 3.x
- **AI**: AWS Bedrock (Claude)
- **Scraping**: httpx, BeautifulSoup, Playwright

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Telegram Bot Token (from @BotFather)
- AWS Account with Bedrock access

### Setup

1. **Clone and navigate to the project**:
   ```bash
   cd Multi-Tenant_Job_Search_Application
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   ```

3. **Configure your `.env` file**:
   - Set your `TELEGRAM_BOT_TOKEN`
   - Set your AWS credentials for Bedrock
   - Adjust other settings as needed

4. **Start with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

5. **Run database migrations**:
   ```bash
   docker-compose exec api alembic upgrade head
   ```

6. **Start chatting with your bot on Telegram!**

### Manual Setup (Development)

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```

3. **Start PostgreSQL and Redis**:
   ```bash
   docker-compose up -d db redis
   ```

4. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Start the API**:
   ```bash
   cd src
   uvicorn app.main:app --reload
   ```

6. **Start the bot** (in another terminal):
   ```bash
   cd src
   python -m app.bot.bot
   ```

7. **Start Celery worker** (in another terminal):
   ```bash
   cd src
   celery -A app.workers.celery_app worker --loglevel=info
   ```

## Project Structure

```
├── src/
│   └── app/
│       ├── api/              # FastAPI routes
│       │   └── routes/       # API endpoints
│       ├── bot/              # Telegram bot
│       │   └── handlers/     # Bot command handlers
│       ├── models/           # SQLAlchemy models
│       ├── schemas/          # Pydantic schemas
│       ├── services/         # Business logic
│       ├── scrapers/         # Job board scrapers
│       ├── workers/          # Celery tasks
│       ├── config.py         # Configuration
│       └── main.py           # FastAPI app
├── alembic/                  # Database migrations
├── docker-compose.yml        # Docker services
├── Dockerfile
└── pyproject.toml
```

## API Endpoints

### Users
- `POST /api/v1/users` - Create/register user
- `GET /api/v1/users/me` - Get current user
- `PATCH /api/v1/users/me` - Update profile
- `PATCH /api/v1/users/me/preferences` - Update job preferences

### Jobs
- `GET /api/v1/jobs` - Search jobs
- `GET /api/v1/jobs/recommendations` - Get personalized recommendations
- `GET /api/v1/jobs/match/{job_id}` - Get AI match analysis
- `POST /api/v1/jobs/saved` - Save a job
- `POST /api/v1/jobs/{job_id}/dismiss` - Dismiss a job

### Applications
- `POST /api/v1/applications/drafts/generate` - Generate cover letter draft
- `POST /api/v1/applications/drafts/{id}/approve` - Approve draft
- `GET /api/v1/applications` - List applications
- `PATCH /api/v1/applications/{id}` - Update application status

### Resumes
- `POST /api/v1/resumes/upload` - Upload resume
- `POST /api/v1/resumes/{id}/process` - Process with AI
- `GET /api/v1/resumes/{id}/analysis` - Get AI analysis

## Telegram Commands

- `/start` - Start the bot / onboarding
- `/search` - Search for jobs
- `/jobs` - Get job recommendations
- `/applications` - View your applications
- `/resume` - Manage your resume
- `/settings` - Update preferences
- `/stats` - View your statistics
- `/help` - Show help

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Required |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `BEDROCK_MODEL_ID` | Claude model ID | `anthropic.claude-3-sonnet-...` |
| `AI_CALLS_PER_USER_DAILY` | Daily AI call limit | `50` |

## Job Sources

Currently supported job sources:
- **RemoteOK** - Remote job board with public API
- **Arbeitnow** - International job board with API

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black src/
ruff check src/
```

### Type Checking
```bash
mypy src/
```

## License

MIT License
