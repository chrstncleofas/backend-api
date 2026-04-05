# Backend API

Django REST Framework API with MongoDB — Experimentation Project

## Tech Stack

- **Framework**: Django 5.2 + Django REST Framework 3.17
- **Database**: MongoDB (via MongoEngine ODM + PyMongo for raw access)
- **Auth**: Custom JWT (PyJWT + bcrypt)
- **Docs**: Swagger/OpenAPI (drf-spectacular)
- **CORS**: django-cors-headers
- **Environment**: python-decouple (.env)

## Setup

### Prerequisites

- Python 3.12+
- MongoDB running locally (or via Docker)

### Local Development

```bash
# Navigate to project
cd backend-api

# Create & activate virtual environment
python -m venv venv
.\venv\Scripts\activate        # Windows
source venv/bin/activate       # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your settings

# Run Django migrations (for Django internals - admin, sessions)
python manage.py migrate

# Start development server
python manage.py runserver
```

### Docker

```bash
# Start API + MongoDB
docker-compose up --build

# Stop
docker-compose down
```

## API Endpoints

### Authentication
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/users/register/` | No | Register new user |
| POST | `/api/users/login/` | No | Login, get JWT tokens |
| POST | `/api/users/token/refresh/` | No | Refresh access token |
| GET | `/api/users/profile/` | Yes | Get current user profile |
| PATCH | `/api/users/profile/` | Yes | Update profile |
| POST | `/api/users/change-password/` | Yes | Change password |

### Products
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/products/` | No | List products (with search, filter) |
| POST | `/api/products/` | Yes | Create product |
| GET | `/api/products/:id/` | No | Get product detail |
| PATCH | `/api/products/:id/` | Yes | Update product (owner only) |
| DELETE | `/api/products/:id/` | Yes | Delete product (owner only) |

### Orders
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/orders/` | Yes | List orders (role-based) |
| POST | `/api/orders/` | Yes | Create order |
| GET | `/api/orders/:id/` | Yes | Get order detail |
| PATCH | `/api/orders/:id/status/` | Yes | Update order status |

### Documentation
| Endpoint | Description |
|----------|-------------|
| `/api/schema/swagger-ui/` | Swagger UI |
| `/api/schema/redoc/` | ReDoc |
| `/api/schema/` | Raw OpenAPI schema |

## MongoDB Approaches

This project demonstrates **3 MongoDB approaches**:

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
stats = count_users_by_role()
```

### 3. Djongo (Excluded)
Incompatible with Django 5.x (requires sqlparse==0.2.4). Not recommended — poorly maintained.

## Project Structure

```
backend-api/
├── config/             # Django project settings
│   ├── settings.py     # Main config (MongoDB, DRF, JWT, CORS, Swagger)
│   ├── urls.py         # Root URL routing
│   ├── exceptions.py   # Custom DRF exception handler
│   ├── wsgi.py
│   └── asgi.py
├── users/              # User auth & management
│   ├── documents.py    # MongoEngine User document
│   ├── serializers.py  # DRF serializers
│   ├── views.py        # Register, Login, Profile, etc.
│   ├── urls.py
│   ├── authentication.py  # Custom JWT auth backend
│   ├── tokens.py       # JWT token generation/decoding
│   └── raw_queries.py  # PyMongo examples
├── products/           # Product CRUD
│   ├── documents.py    # MongoEngine Product document
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── raw_queries.py
├── orders/             # Order management
│   ├── documents.py    # MongoEngine Order/OrderItem documents
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── raw_queries.py
├── .env                # Environment variables (not in git)
├── .env.example        # Template for .env
├── requirements.txt    # Python dependencies
├── Dockerfile
├── docker-compose.yml  # API + MongoDB
└── manage.py
```
