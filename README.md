# Backend API

Django REST Framework API with MongoDB — Experimentation Project

## Tech Stack

- **Framework**: Django 5.2 + Django REST Framework 3.17
- **Database**: MongoDB (via MongoEngine ODM + PyMongo for raw access)
- **Auth**: Custom JWT (PyJWT + bcrypt)
- **Docs**: Swagger/OpenAPI (drf-spectacular)
- **CORS**: django-cors-headers
- **Environment**: python-decouple (.env.local)

## Setup

### Prerequisites

- Python 3.12+
- Docker Desktop (for Docker workflows)

### 1. Environment Variables

```bash
# Copy the example env file
cp .env.example .env.local
# Windows:
copy .env.example .env.local

# Fill in your values — required fields:
# SECRET_KEY, MONGODB_URI, MONGODB_NAME
```

> `.env.local` is gitignored and never baked into the Docker image.

---

### 2. Local Development (no Docker)

Best for day-to-day coding. Uses MongoDB Atlas (cloud) via `MONGODB_URI`.

```bash
cd backend-api

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate        # Windows
source venv/bin/activate       # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run development server
python manage.py runserver
```

API at: http://localhost:8000
Swagger UI at: http://localhost:8000/api/schema/swagger-ui/

---

### 3. Docker — Local Dev (API + local MongoDB)

Runs both the Django API and a local MongoDB instance in Docker.

```bash
# Build and start
docker compose -f docker-compose.dev.yml up --build

# Run in background
docker compose -f docker-compose.dev.yml up --build -d

# View API logs
docker compose -f docker-compose.dev.yml logs -f api

# Stop
docker compose -f docker-compose.dev.yml down

# Stop and wipe local MongoDB data
docker compose -f docker-compose.dev.yml down -v
```

> `GUNICORN_RELOAD=true` is set automatically in dev — gunicorn restarts on code changes.

---

### 4. Docker — Production (API only, MongoDB Atlas)

Runs only the API container. MongoDB connection uses the Atlas URI from `.env.local`.

```bash
# Build and start in background
docker compose -f docker-compose.prod.yml up --build -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop
docker compose -f docker-compose.prod.yml down
```

**Resource limits:** 1 CPU, 512MB RAM
**Gunicorn workers:** auto-calculated as `(2 x CPU cores) + 1`

Override worker count without rebuilding:
```bash
GUNICORN_WORKERS=5 docker compose -f docker-compose.prod.yml up -d
```

---

### 5. Health Check

All environments expose a health check endpoint:

```bash
curl http://localhost:8000/api/health/
# {"success": true, "status": "ok"}
```

Used by Docker, load balancers, Render, Railway, and AWS ECS to verify the app is live.

---

### Compose File Reference

| File | Use Case | MongoDB |
|------|----------|---------|
| `docker-compose.dev.yml` | Local development | Local container (port 27017) |
| `docker-compose.prod.yml` | Production / staging | MongoDB Atlas (via `MONGODB_URI`) |

---

### Gunicorn Configuration

All gunicorn settings live in `gunicorn.conf.py` — no need to rebuild to change workers or timeouts.

| Setting | Default | Override via env |
|---------|---------|------------------|
| Workers | `(2 x cores) + 1` | `GUNICORN_WORKERS=5` |
| Hot reload | `false` | `GUNICORN_RELOAD=true` |
| Bind | `0.0.0.0:8000` | — |
| Timeout | 120s | — |

---

## API Endpoints

### Authentication
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/users/register/` | No | Register new user |
| POST | `/api/v1/users/login/` | No | Login, get JWT tokens |
| POST | `/api/v1/users/token/refresh/` | No | Refresh access token |
| GET | `/api/v1/users/profile/` | Yes | Get current user profile |
| PATCH | `/api/v1/users/profile/` | Yes | Update profile |
| POST | `/api/v1/users/change-password/` | Yes | Change password |

### Products
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/products/` | No | List products (with search, filter) |
| POST | `/api/v1/products/` | Yes | Create product |
| GET | `/api/v1/products/:id/` | No | Get product detail |
| PATCH | `/api/v1/products/:id/` | Yes | Update product (owner only) |
| DELETE | `/api/v1/products/:id/` | Yes | Delete product (owner only) |

### Orders
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/orders/` | Yes | List orders (role-based) |
| POST | `/api/v1/orders/` | Yes | Create order |
| GET | `/api/v1/orders/:id/` | Yes | Get order detail |
| PATCH | `/api/v1/orders/:id/status/` | Yes | Update order status |

### Health
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health/` | No | Health check (Docker/LB probe) |

### Documentation
| Endpoint | Description |
|----------|-------------|
| `/api/schema/swagger-ui/` | Swagger UI |
| `/api/schema/redoc/` | ReDoc |
| `/api/schema/` | Raw OpenAPI schema |

## MongoDB Approaches

This project uses **2 MongoDB approaches**:

### 1. MongoEngine (Primary ODM)
Used in `*/documents.py` — Pythonic ODM similar to Django ORM:
```python
from users.documents import User
user = User.objects(email='test@example.com').first()
```

### 2. PyMongo (Raw Access)
Used in `*/raw_queries.py` — Direct MongoDB driver:
```python
from users.raw_queries import get_all_users, count_users_by_role
users = get_all_users()
```

## Project Structure

```
backend-api/
├── config/
│   ├── settings.py          # Main config (MongoDB, DRF, JWT, CORS, Swagger)
│   ├── urls.py              # Root URL routing + /api/health/
│   ├── exceptions.py        # Custom DRF exception handler
│   ├── s3.py                # S3Service singleton (file uploads)
│   ├── db.py                # Shared PyMongo DB access
│   ├── serializers.py       # FileUpload / MultiFileUpload serializers
│   ├── wsgi.py
│   └── asgi.py
├── users/
│   ├── documents.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── authentication.py
│   ├── tokens.py
│   └── raw_queries.py
├── products/
│   ├── documents.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── raw_queries.py
├── orders/
│   ├── documents.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── raw_queries.py
├── .env.local               # Environment variables (not in git)
├── .env.example             # Template — copy to .env.local
├── requirements.txt
├── Dockerfile               # Multi-stage build (builder + runtime)
├── docker-compose.dev.yml   # Local dev: API + MongoDB container
├── docker-compose.prod.yml  # Production: API only (uses Atlas)
├── gunicorn.conf.py         # Gunicorn server config
└── manage.py
```
