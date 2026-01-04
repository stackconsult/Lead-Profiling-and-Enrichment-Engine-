# Production Deployment Guide

## Environment Variables

### Required Environment Variables

| Variable | Description | Example | Production |
|----------|-------------|---------|------------|
| `ENV` | Application environment | `production` | **Required** |
| `PYTHON_ENV` | Python environment | `production` | **Required** |
| `API_TOKEN` | API authentication token | `secure-random-token` | **Required** |
| `VALKEY_URL` | Redis/Valkey connection URL | `redis://valkey-instance:6379` | **Required** |
| `VALKEY_HOST` | Redis/Valkey host | `valkey-instance` | Optional |
| `VALKEY_PORT` | Redis/Valkey port | `6379` | Optional |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | API server host | `0.0.0.0` |
| `PORT` | API server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Production Setup

### 1. Valkey/Redis Service

**Critical**: Production requires a real Redis/Valkey instance. Do NOT use localhost.

```bash
# Example: AWS ElastiCache Redis
export VALKEY_URL=redis://your-redis-cluster.xxxxxx.0001.use1.cache.amazonaws.com:6379

# Example: Render Redis
export VALKEY_URL=redis://your-render-redis:6379

# Example: DigitalOcean Redis
export VALKEY_URL=redis://your-do-redis:6379
```

### 2. API Token

Generate a secure API token:

```bash
# Generate secure token (Linux/macOS)
export API_TOKEN=$(openssl rand -hex 32)

# Or use any secure random string
export API_TOKEN="your-secure-api-token-here"
```

### 3. Environment Detection

The application automatically detects production environment when:
- `RENDER_SERVICE_ID` is set (Render deployment)
- `ENV=production`
- `PYTHON_ENV=production`

### 4. Startup Validation

The application validates configuration on startup and will fail fast if:
- Required environment variables are missing
- In production with localhost Redis/Valkey
- Using placeholder API tokens

## Deployment Examples

### Render Deployment

Add these environment variables in Render dashboard:

```
ENV=production
PYTHON_ENV=production
API_TOKEN=your-secure-api-token
VALKEY_URL=redis://your-redis-instance:6379
```

### Docker Deployment

```dockerfile
# Dockerfile
ENV ENV=production
ENV PYTHON_ENV=production
ENV VALKEY_URL=redis://valkey:6379
ENV API_TOKEN=your-secure-api-token
```

### Kubernetes Deployment

```yaml
# deployment.yaml
env:
- name: ENV
  value: "production"
- name: PYTHON_ENV
  value: "production"
- name: API_TOKEN
  valueFrom:
    secretKeyRef:
      name: api-secrets
      key: api-token
- name: VALKEY_URL
  value: "redis://redis-service:6379"
```

## Health Checks

### Application Health

```bash
curl https://your-app.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "valkey": "connected"
}
```

### Workspace Operations

```bash
# Test workspace creation
curl -X POST https://your-app.com/api/workspaces \
  -H "Content-Type: application/json" \
  -H "X-API-TOKEN: your-api-token" \
  -d '{"provider": "openai", "keys": {"provider": "openai", "openai_key": "sk-test"}}'

# Test workspace listing
curl https://your-app.com/api/workspaces \
  -H "X-API-TOKEN: your-api-token"
```

## Troubleshooting

### Common Issues

1. **Valkey Connection Failed**
   - Ensure VALKEY_URL is set to real Redis instance
   - Check network connectivity to Redis
   - Verify Redis is running and accessible

2. **Configuration Validation Failed**
   - Check all required environment variables
   - Ensure API_TOKEN is not a placeholder
   - Verify ENV is set to "production"

3. **Application Won't Start**
   - Check logs for configuration validation errors
   - Verify Redis/Valkey service is accessible
   - Ensure proper environment variables

### Debug Mode

For debugging, you can temporarily set:
```bash
ENV=development
PYTHON_ENV=development
```

This will allow fallback to FakeValkey for testing, but **never use in production**.

## Security Notes

- Never commit real API tokens to source control
- Use environment variables or secret management
- Rotate API tokens regularly
- Use HTTPS in production
- Secure Redis/Valkey with passwords and TLS
- Network restrictions for Redis/Valkey access
