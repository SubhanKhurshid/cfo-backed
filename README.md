# AI CFO Financial Analysis API

A FastAPI-based service that provides comprehensive financial analysis for uploaded documents including P&L, Balance Sheet, Cash Flow, and AR/AP Aging reports.

## Features

- Upload financial documents (CSV, XLSX, XLS, PDF)
- Comprehensive financial analysis
- Support for multiple file formats
- RESTful API with automatic documentation
- Health check endpoints

## Quick Start with Docker

### Local Development

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

2. **Or build and run manually:**
   ```bash
   # Build the image
   docker build -t ai-cfo-api .
   
   # Run the container
   docker run -p 8000:8000 ai-cfo-api
   ```

3. **Access the API:**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - Root Endpoint: http://localhost:8000/

### Deploy to Railway

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway:**
   ```bash
   railway login
   ```

3. **Deploy:**
   ```bash
   railway init
   railway up
   ```

4. **Set environment variables (if needed):**
   ```bash
   railway variables set OPENAI_API_KEY=your_api_key_here
   ```

### Deploy to Other Platforms

#### Heroku
```bash
# Create Procfile
echo "web: uvicorn main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
heroku create your-app-name
git push heroku main
```

#### DigitalOcean App Platform
- Connect your GitHub repository
- Select the Dockerfile as build method
- Set port to 8000

#### AWS ECS/Fargate
- Use the provided Dockerfile
- Set environment variables in task definition
- Configure load balancer for port 8000

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /upload-financial-document` - Upload single file for analysis
- `POST /analyze-multiple-files` - Upload multiple files for analysis

## Environment Variables

- `OPENAI_API_KEY` - Your OpenAI API key (if using OpenAI features)
- `PORT` - Port to run the server on (default: 8000)

## File Support

- **CSV**: Comma-separated values
- **XLSX/XLS**: Excel spreadsheets
- **PDF**: Portable Document Format

## Development

### Prerequisites
- Python 3.11+
- Docker (for containerized deployment)

### Local Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py
```

## Docker Commands

```bash
# Build image
docker build -t ai-cfo-api .

# Run container
docker run -p 8000:8000 ai-cfo-api

# Run with environment variables
docker run -p 8000:8000 -e OPENAI_API_KEY=your_key ai-cfo-api

# Run in background
docker run -d -p 8000:8000 --name ai-cfo-container ai-cfo-api

# View logs
docker logs ai-cfo-container

# Stop container
docker stop ai-cfo-container
```

## Health Checks

The application includes health checks that verify:
- API is responding
- All endpoints are accessible
- Service is healthy

## Troubleshooting

1. **Port already in use:**
   ```bash
   # Find process using port 8000
   lsof -i :8000
   # Kill the process
   kill -9 <PID>
   ```

2. **Docker build fails:**
   - Ensure Docker is running
   - Check internet connection for package downloads
   - Verify Dockerfile syntax

3. **API not responding:**
   - Check container logs: `docker logs <container_name>`
   - Verify port mapping: `docker ps`
   - Test health endpoint: `curl http://localhost:8000/health`

## License

This project is licensed under the MIT License.
