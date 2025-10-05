
## Deployment (Docker + Nginx + HTTPS)

1. Prepare server
- Install Docker and Docker Compose
- Open ports 80 and 443

2. Env
- Copy `env.example` to `.env` and set values:
  - `DJANGO_SETTINGS_MODULE=karakoldelivery.settings_prod`
  - `ALLOWED_HOSTS=your-domain.com`
  - `DATABASE_URL=postgres://user:pass@db/karakol_delivery` (or use compose vars)
  - `REDIS_URL=redis://redis:6379/0`
  - `FCM_SERVER_KEY=...` (optional pushes)
  - `SENTRY_*` (optional)

3. Build & run
- `docker compose up -d --build`

4. Nginx reverse-proxy (sample)
```
server {
  listen 80;
  server_name your-domain.com;
  location /.well-known/acme-challenge/ { root /var/www/certbot; }
  location / { return 301 https://$host$request_uri; }
}

server {
  listen 443 ssl http2;
  server_name your-domain.com;

  ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

  client_max_body_size 25m;

  location /static/ { alias /opt/karakol/staticfiles/; }
  location /media/ { alias /opt/karakol/media/; }

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  location /ws/ {
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_pass http://127.0.0.1:8000;
  }
}
```

5. Certificates
- Use certbot/letsencrypt docker or package to issue SSL for `your-domain.com`
- Reload nginx

6. Migrations & static
- The container `backend` runs `migrate` and `collectstatic` on startup via `entrypoint.sh`

7. Celery & WebSockets
- `docker compose` already starts `celery_worker` and `celery_beat`
- Channels uses Redis (`REDIS_URL`). Ensure Redis port is accessible only internally

8. Health
- Check `https://your-domain.com/health/` returns `{ "status": "ok" }`
