# SSL/HTTPS Setup for lmcemr.com.ng

This guide sets up Let's Encrypt SSL using Certbot with Nginx as a reverse proxy.

## Architecture

```
Internet (port 80/443) → Nginx (system) → Docker app (port 8080)
```

- **Nginx** handles HTTPS, SSL termination, and proxies to the app
- **App container** runs on port **8080** (not 80, so Nginx can use 80/443)

---

## Step 1: Change Docker to Use Port 8080

Edit `docker-compose.standalone.yml` and change the app ports:

```yaml
    ports:
      - "8080:80"   # was "80:80"
```

Then restart:

```bash
docker compose -f docker-compose.standalone.yml down
docker compose -f docker-compose.standalone.yml up -d
```

Verify the app responds on 8080:

```bash
curl -I http://127.0.0.1:8080/health
```

---

## Step 2: Install Nginx and Certbot

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

---

## Step 3: Create Nginx Config

Copy the reverse proxy config and enable it:

```bash
sudo cp docker/nginx.ssl.reverse-proxy.conf /etc/nginx/sites-available/lmcemr.com.ng
sudo ln -sf /etc/nginx/sites-available/lmcemr.com.ng /etc/nginx/sites-enabled/
```

Remove the default site if it conflicts:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

Test and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Step 4: Get SSL Certificate

Make sure:
- `lmcemr.com.ng` and `www.lmcemr.com.ng` point to your server's public IP (DNS A records)

Then run:

```bash
sudo certbot --nginx -d lmcemr.com.ng -d www.lmcemr.com.ng
```

Follow the prompts:
- Enter email for renewal notices
- Agree to terms
- Choose whether to redirect HTTP → HTTPS (recommended: Yes)

Certbot will update your Nginx config automatically and reload it.

---

## Step 5: Enable Secure Settings in Django

Add to your server's `.env` file:

```
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_PROXY_SSL_HEADER=X-Forwarded-Proto
```

Then restart the app:

```bash
docker compose -f docker-compose.standalone.yml restart app
```

---

## Step 6: Auto-Renewal

Certbot installs a renewal timer. Test it:

```bash
sudo certbot renew --dry-run
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 80 in use | Stop Docker app first: `docker compose down`, then start Nginx |
| Certbot fails | Ensure DNS points to server, port 80 is open in cloud firewall |
| Mixed content | Ensure `SECURE_SSL_REDIRECT=True` and `CORS_ALLOWED_ORIGINS` includes `https://lmcemr.com.ng` |
| 502 Bad Gateway | App not running on 8080; run `docker compose ps` and check logs |

---

## Quick Reference

```bash
# Full SSL setup sequence
cd ~/lifeway-emr
# 1. Edit docker-compose: ports "8080:80"
docker compose -f docker-compose.standalone.yml down
docker compose -f docker-compose.standalone.yml up -d
# 2. Install nginx + certbot, copy config, run certbot
sudo certbot --nginx -d lmcemr.com.ng -d www.lmcemr.com.ng
# 3. Add SECURE_* vars to .env, restart app
docker compose -f docker-compose.standalone.yml restart app
```
