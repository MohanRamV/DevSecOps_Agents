# DevSecOps AI Monitoring System

An intelligent CI/CD pipeline monitoring system that uses Groq AI agents to detect issues, provide analysis, and send automated notifications. Uses free Groq models to avoid token exhaustion issues.

## Features

- **Pipeline Monitoring**: Tracks GitHub Actions workflows and detects failures
- **Deployment Monitoring**: Monitors Kubernetes deployments for issues
- **AI-Powered Analysis**: Uses Groq (free models) to analyze issues and suggest fixes
- **Smart Notifications**: Sends alerts via Slack, Teams, or email
- **Issue Tracking**: Stores and manages pipeline issues with detailed analysis
- **REST API**: Provides endpoints for monitoring and management
- **Automated Reminders**: Sends reminders for unresolved issues

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub API    │    │   Kubernetes    │    │   Groq LLM API  │
│                 │    │      API        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI Monitoring Agents                         │
│  ┌─────────────────┐  ┌─────────────────┐   ┌─────────────────┐ │
│  │ Pipeline Monitor│  │Deployment Monitor│  │Notification Agent││
│  │     Agent       │  │     Agent       │   │                 │ │
│  └─────────────────┘  └─────────────────┘   └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Database                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │Pipeline Runs│  │   Issues    │  │Notifications│              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        REST API                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Monitor   │  │   Issues    │  │  Statistics │              │
│  │  Endpoints  │  │  Endpoints  │  │  Endpoints  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd DevSecOps_Agents

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Run the credential setup script
python setup_credentials.py

# This will securely store your credentials using the password manager
# No hardcoded values in .env files - everything is stored securely!
```

Required environment variables:

```env
# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_REPOSITORY=your-username/your-repo-name
GITHUB_OWNER=your-username

# Groq Configuration
GROQ_API_KEY=your_groq_api_key_here

# Notification Configuration (at least one required)
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
# or
TEAMS_WEBHOOK=https://your-org.webhook.office.com/webhookb2/YOUR/TEAMS/WEBHOOK
# or
EMAIL_SMTP=smtp.gmail.com:587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

### 3. Run the System

```bash
# Start the monitoring system
python main.py
```

The system will be available at `http://localhost:8000`

## API Endpoints

### Health & Status
- `GET /` - System status
- `GET /health` - Health check for all agents
- `GET /stats` - System statistics

### Monitoring
- `POST /monitor/pipeline` - Trigger pipeline monitoring
- `POST /monitor/deployment` - Trigger deployment monitoring
- `POST /monitor/all` - Trigger all monitoring agents

### Data Access
- `GET /issues` - Get pipeline issues
- `GET /issues/{issue_id}` - Get specific issue
- `GET /pipeline-runs` - Get pipeline runs
- `GET /deployments` - Get deployments
- `GET /agent-actions` - Get agent actions
- `GET /notifications` - Get notifications

### Webhooks
- `POST /webhook/github` - GitHub webhook endpoint

## Agents

### Pipeline Monitor Agent

Monitors GitHub Actions workflows and detects:
- Failed pipeline runs
- Long-running jobs
- Security vulnerabilities
- Performance issues

**Features:**
- AI-powered failure analysis
- Root cause identification
- Suggested fixes generation
- Severity assessment

### Deployment Monitor Agent

Monitors Kubernetes deployments and detects:
- Failed deployments
- Scaling issues
- Resource configuration problems
- Health check issues

**Features:**
- Pod event analysis
- Resource usage monitoring
- Health check validation
- Deployment status tracking

### Notification Agent

Sends intelligent notifications about:
- Critical issues (immediate alerts)
- Standard issues (regular notifications)
- Reminders for unresolved issues

**Channels:**
- Slack
- Microsoft Teams
- Email

## Database Schema

### PipelineRun
Stores information about CI/CD pipeline runs:
- Run ID, workflow name, status
- Duration, branch, commit information
- Job details and artifacts

### PipelineIssue
Stores detected issues:
- Issue type, severity, status
- AI analysis and suggested fixes
- Related pipeline run

### Deployment
Stores Kubernetes deployment information:
- Deployment name, namespace, image tag
- Replica counts and status
- Kubernetes metadata

### AgentAction
Tracks agent activities:
- Agent name, action type
- Execution status and results
- Timestamps

### Notification
Stores notification history:
- Channel, recipient, message
- Status and error information

## Configuration

### Monitoring Settings
```env
CHECK_INTERVAL=300          # Monitoring frequency (seconds)
ALERT_THRESHOLD=3          # Number of failures before alert
RETENTION_DAYS=30          # Data retention period
```

### Agent Settings
```env
MAX_CONCURRENT_AGENTS=5    # Maximum concurrent agents
AGENT_TIMEOUT=300          # Agent execution timeout
```

### LLM Settings
```env
GROQ_MODEL=llama-3.1-70b-versatile  # or other available models
GROQ_TEMPERATURE=0.1
GROQ_MAX_TOKENS=2000
```

## GitHub Setup

### 1. Create Personal Access Token
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token with permissions:
   - `repo` (full repository access)
   - `workflow` (workflow access)
   - `read:org` (organization access)

### 2. Setup Webhook (Optional)
1. Go to repository Settings → Webhooks
2. Add webhook with:
   - Payload URL: `https://your-domain.com/webhook/github`
   - Content type: `application/json`
   - Events: `workflow_run`, `push`

## Kubernetes Setup

### 1. Configure Access
```bash
# Set kubeconfig path
export KUBECONFIG=/path/to/your/kubeconfig

# Or use in-cluster config if running in Kubernetes
```

### 2. Required Permissions
The system needs permissions to:
- List deployments
- Get pod events
- Read pod logs

## Notification Setup

### Slack
1. Create a Slack app
2. Add webhook URL to environment
3. Configure channel notifications

### Microsoft Teams
1. Create Teams webhook
2. Add webhook URL to environment
3. Configure team notifications

### Email
1. Configure SMTP settings
2. Use app passwords for Gmail
3. Test email delivery

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_pipeline_agent.py

# Run with coverage
pytest --cov=agents
```

### Adding New Agents
1. Create agent class inheriting from `BaseAgent`
2. Implement `run()` method
3. Add to main.py orchestration
4. Update configuration

### Customizing AI Analysis
1. Modify prompt templates in agents
2. Adjust OpenAI parameters
3. Add domain-specific analysis logic



## Troubleshooting

### Common Issues

1. **GitHub API Rate Limits**
   - Use personal access token with appropriate permissions
   - Implement rate limiting in agent logic

2. **Kubernetes Connection Issues**
   - Verify kubeconfig path
   - Check cluster access permissions
   - Ensure namespace exists

3. **LLM API Errors**
   - Verify API key is valid
   - Check account billing status
   - Monitor rate limits

4. **Database Issues**
   - Ensure write permissions to database directory
   - Check SQLite file corruption
   - Verify database schema

### Logs
```bash
# View application logs
tail -f logs/app.log

# View agent-specific logs
tail -f logs/pipeline_agent.log
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the troubleshooting guide 