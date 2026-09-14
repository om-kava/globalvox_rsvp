# Deployment Strategy & Guide — Vercel & Hosted MySQL

## 1. Production Architecture Overview

The assessment requires that the application is deployed and accessible via a live Vercel URL.

```text
               User / Evaluator Browser
                          │
                          │ HTTPS
                          ▼
            Vercel Edge Network / CDN
             │                     │
             │ /static/*           │ /api/* & /*
             ▼                     ▼
     Static Assets Storage    Serverless Python Function
     (HTML, CSS, JS)         (WSGI Entrypoint: api/index.py)
                                   │
                                   │ Remote TLS Connection
                                   ▼
                           Cloud-Hosted MySQL
                      (e.g., Aiven / Railway / PlanetScale / RDS)
```

---

## 2. Platform Constraints & Solutions on Vercel

### 2.1 Read-Only Filesystem
- **Constraint**: Vercel serverless lambda functions run with an ephemeral, read-only root filesystem (only `/tmp` is writable).
- **Solution**:
  - Do not write local database files (SQLite is unsuitable for persistent multi-invocation state on Vercel).
  - Use a hosted MySQL database reachable via internet over SSL.
  - In-memory processing for CSV file imports without saving temporary files to disk.

### 2.2 Serverless Execution Lifecycles
- **Constraint**: Serverless functions have execution timeout limits (typically 10–15 seconds on hobby tier).
- **Solution**:
  - The simulated call provider executes non-blocking or micro-batched calls so campaign runs stay well within invocation limits.
  - Aggregation queries are optimized with composite indexes to execute in sub-100ms.

---

## 3. Configuration Files

### 3.1 `vercel.json`
```json
{
  "version": 2,
  "builds": [
    {
      "src": "backend/wsgi.py",
      "use": "@vercel/python",
      "config": { "maxLambdaSize": "15mb", "runtime": "python3.11" }
    },
    {
      "src": "static/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "backend/wsgi.py"
    }
  ]
}
```

### 3.2 Production WSGI Entrypoint (`api/index.py` or `backend/wsgi.py`)
Standard Django WSGI application callable exported for Vercel's Python runtime.

---

## 4. Environment Variables Checklist

The following environment variables must be configured in the Vercel Project Settings:

| Variable | Description | Example / Notes |
|---|---|---|
| `SECRET_KEY` | Django cryptographic secret | High-entropy random string (never commit) |
| `DEBUG` | Django debug toggle | Must be `False` in production |
| `ALLOWED_HOSTS` | Permitted hostnames | `.vercel.app,localhost` |
| `DB_ENGINE` | Database backend | `django.db.backends.mysql` |
| `DB_NAME` | Database name | Provided by hosted MySQL provider |
| `DB_USER` | Database username | Provided by hosted MySQL provider |
| `DB_PASSWORD` | Database password | Provided by hosted MySQL provider |
| `DB_HOST` | Database remote host | E.g. `mysql.example.com` (NEVER localhost in prod) |
| `DB_PORT` | Database port | E.g. `3306` |
| `DB_SSL_CA` | Path or flag for SSL CA cert | If required by MySQL host |

---

## 5. Deployment Execution Steps
1. **Database Provisioning**:
   - Provision hosted MySQL database (Aiven/Railway/PlanetScale/AWS RDS).
   - Execute migrations via CI or one-off migration script:
     ```bash
     python manage.py migrate
     ```
2. **Collect Static Files**:
   ```bash
   python manage.py collectstatic --noinput
   ```
3. **Deploy to Vercel**:
   - Install Vercel CLI: `npm i -g vercel`.
   - Link project and set environment variables: `vercel env add ...`.
   - Deploy production build: `vercel --prod`.
4. **Verification**:
   - Open live `.vercel.app` URL.
   - Verify login, CSV import, campaign creation, execution, and dashboard metrics.
