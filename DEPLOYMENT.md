# Production Deployment Guide

## 🚀 Deploy to Production in 15 Minutes

This guide will get your Decision Platform running in production.

---

## Prerequisites

- Docker & Docker Compose installed
- Domain name (optional, can use IP)
- 4GB RAM minimum (8GB recommended)
- Ports 80, 443 available (or custom ports)

---

## Quick Start

### 1. Clone/Extract the Platform

```bash
# If you have the tar.gz
tar -xzf decision-platform-full.tar.gz
cd decision-platform

# Or if you have the directory
cd decision-platform
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Minimum Required Changes in `.env`:**
```env
# Change this to a secure random string!
SECRET_KEY=your-super-secret-key-change-this-in-production

# Database password
POSTGRES_PASSWORD=your-secure-database-password

# Optional: Add API keys if you want real AI
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Start the Platform

```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy (30-60 seconds)
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f api
```

### 4. Initialize Database

```bash
# Run database migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Create default admin user
docker-compose -f docker-compose.prod.yml exec api python scripts/create_admin.py
```

### 5. Verify It Works

```bash
# Health check
curl http://localhost:8000/health

# Login and get token
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin123"
  }'

# You should get back an access_token
```

### 6. Access the Application

- **API:** http://your-domain:8000
- **API Docs:** http://your-domain:8000/docs
- **Frontend:** http://your-domain:3000

Default credentials:
- **Email:** admin@example.com
- **Password:** admin123 (CHANGE THIS IMMEDIATELY)

---

## Production Checklist

### Security

- [ ] Change SECRET_KEY in .env
- [ ] Change database passwords
- [ ] Change default admin password
- [ ] Enable HTTPS (see below)
- [ ] Configure firewall rules
- [ ] Set up backup strategy

### Performance

- [ ] Increase worker count for high load
- [ ] Configure database connection pooling
- [ ] Set up Redis for caching
- [ ] Enable CDN for static files

### Monitoring

- [ ] Set up log aggregation
- [ ] Configure health check monitoring
- [ ] Set up alerts for errors
- [ ] Monitor disk space

---

## HTTPS Setup (Recommended)

### Option 1: Using Caddy (Easiest)

Add to `docker-compose.prod.yml`:

```yaml
caddy:
  image: caddy:2-alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./Caddyfile:/etc/caddy/Caddyfile
    - caddy_data:/data
    - caddy_config:/config
  networks:
    - decision_platform
```

Create `Caddyfile`:
```
your-domain.com {
    reverse_proxy api:8000
}
```

### Option 2: Using Nginx + Let's Encrypt

```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
    - ./certbot/conf:/etc/letsencrypt
    - ./certbot/www:/var/www/certbot
  networks:
    - decision_platform
```

---

## Scaling

### Horizontal Scaling

```yaml
# In docker-compose.prod.yml
api:
  # ... existing config ...
  deploy:
    replicas: 3  # Run 3 API instances
  
worker:
  # ... existing config ...
  deploy:
    replicas: 5  # Run 5 worker instances
```

### Database Scaling

For high load, use managed databases:
- **AWS RDS** (PostgreSQL)
- **Google Cloud SQL**
- **Azure Database**

Update DATABASE_URL in .env to point to managed service.

---

## Backup Strategy

### Database Backup

```bash
# Create daily backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T db pg_dump -U postgres decision_platform | \
  gzip > backups/db_backup_$DATE.sql.gz

# Keep only last 30 days
find backups/ -name "db_backup_*.sql.gz" -mtime +30 -delete
EOF

chmod +x backup.sh

# Add to crontab
crontab -e
# Add line: 0 2 * * * /path/to/backup.sh
```

### Document Backup

```bash
# Backup S3/MinIO data
docker-compose exec -T minio mc mirror /data backups/minio/
```

---

## Monitoring

### Health Check Endpoint

```bash
# Add to your monitoring system
curl http://your-domain:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2026-02-01T10:00:00",
  "version": "1.0.0"
}
```

### Prometheus Metrics

Add to `docker-compose.prod.yml`:

```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## Troubleshooting

### API Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs api

# Common issues:
# - Database not ready: wait 60 seconds
# - Port in use: change port in docker-compose.prod.yml
# - Missing env vars: check .env file
```

### Database Connection Error

```bash
# Check database is running
docker-compose -f docker-compose.prod.yml ps db

# Check connection
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -c "SELECT version();"
```

### Out of Memory

```bash
# Increase Docker memory limit
# Docker Desktop: Settings > Resources > Memory (8GB recommended)

# Or reduce worker count
# In docker-compose.prod.yml: deploy.replicas: 2
```

---

## Updating

```bash
# Pull latest code
git pull origin main

# Rebuild containers
docker-compose -f docker-compose.prod.yml build

# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

---

## Support

### Logs Location

- **API logs:** `docker-compose logs api`
- **Worker logs:** `docker-compose logs worker`
- **Database logs:** `docker-compose logs db`

### Common Commands

```bash
# View all services status
docker-compose -f docker-compose.prod.yml ps

# Restart a service
docker-compose -f docker-compose.prod.yml restart api

# View logs for specific service
docker-compose -f docker-compose.prod.yml logs -f api

# Access database
docker-compose -f docker-compose.prod.yml exec db psql -U postgres decision_platform

# Run Django-style shell
docker-compose -f docker-compose.prod.yml exec api python -m app.shell
```

---

## Performance Tuning

### Database

```sql
-- In PostgreSQL
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '16MB';
```

### Redis

```yaml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### API

```yaml
api:
  environment:
    - WORKERS=4  # Number of Uvicorn workers
    - TIMEOUT=60  # Request timeout in seconds
```

---

## Security Hardening

### 1. Environment Variables

Never commit .env to git:
```bash
echo ".env" >> .gitignore
```

### 2. Database

```sql
-- Create separate database user
CREATE USER app_user WITH PASSWORD 'secure_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
```

### 3. API Rate Limiting

Add to API:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

### 4. Firewall

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

---

## Cost Optimization

### AWS Deployment (Estimated)

- **t3.medium EC2:** $30/month
- **RDS db.t3.micro:** $15/month
- **S3 storage:** $5/month
- **Total:** ~$50/month for 1000 cases/day

### Cost Saving Tips

1. Use spot instances for workers
2. Set up auto-scaling (scale down at night)
3. Use CloudFront CDN for static files
4. Archive old cases to cheaper storage

---

## Next Steps

1. ✅ Deploy and verify
2. 📧 Configure email notifications
3. 🔐 Set up OAuth (Google, Microsoft)
4. 📊 Add custom analytics
5. 🌍 Set up multi-region deployment

---

**Your platform is now production-ready! 🎉**

For support, refer to README.md and ARCHITECTURE.md
