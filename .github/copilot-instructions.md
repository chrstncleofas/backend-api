# Backend API — Copilot Instructions

## Stack

- **Framework**: Django 5.2 + Django REST Framework 3.17
- **Database**: MongoDB (Atlas / local) — **no SQLite, no Django ORM**
- **ODM**: MongoEngine 0.29 — all data models are MongoEngine `Document` subclasses
- **Raw access**: PyMongo (via `raw_queries.py` per app)
- **Auth**: Custom JWT (PyJWT + bcrypt) — **NOT** `django.contrib.auth`
- **Docs**: drf-spectacular (OpenAPI / Swagger)
- **CORS**: django-cors-headers
- **Config package**: `config/` (settings.py, urls.py, exceptions.py, s3.py, db.py, serializers.py)
- **Apps**: `users`, `products`, `orders`
- **File uploads**: boto3 → S3 (server-side upload via `config/s3.py`)

---

## Project Structure

```
backend-api/
├── config/
│   ├── settings.py          # Django settings, MongoEngine connect, DRF config
│   ├── urls.py              # Root URL routing + Swagger endpoints
│   ├── exceptions.py        # Custom DRF exception handler
│   ├── s3.py                # Reusable S3Service class (upload/delete)
│   ├── db.py                # Shared PyMongo DB access (reuses MongoEngine conn)
│   ├── serializers.py       # Shared serializers (FileUpload, MultiFileUpload)
│   ├── wsgi.py
│   └── asgi.py
├── users/
│   ├── documents.py         # MongoEngine Document definitions
│   ├── serializers.py       # DRF Serializers (plain serializers.Serializer)
│   ├── views.py             # DRF APIView classes + AvatarUploadView
│   ├── urls.py              # URL patterns for this app
│   ├── authentication.py    # Custom JWT authentication backend
│   ├── tokens.py            # JWT token generation / decoding utilities
│   └── raw_queries.py       # PyMongo direct queries
├── products/
│   ├── documents.py
│   ├── serializers.py
│   ├── views.py             # CRUD + ProductImageUploadView
│   ├── urls.py
│   └── raw_queries.py
├── orders/
│   ├── documents.py
│   ├── serializers.py
│   ├── views.py             # CRUD + OrderReceiptUploadView
│   ├── urls.py
│   └── raw_queries.py
├── manage.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Critical Rules

### What NOT to use — ever

- `django.contrib.auth` — removed from the project entirely
- `django.contrib.admin` — removed, no admin panel
- `from django.db import models` — no Django ORM models
- `django.contrib.sessions` — removed
- `django.contrib.contenttypes` — removed
- `SQLite` or any relational DB — `DATABASES = {}` (empty dict)
- `ModelSerializer` — we don't use Django ORM models
- `django.contrib.auth.hashers` — use `bcrypt` directly
- `User = get_user_model()` — our User is a MongoEngine Document
- `@login_required` — use DRF `permission_classes` + our JWT auth
- `django-rest-framework-simplejwt` — we use custom PyJWT implementation

### What TO use

- `mongoengine.Document` for all data models (in `documents.py`)
- `serializers.Serializer` (plain DRF) for all serializers
- `APIView` or `ViewSet` from DRF for all views
- `bcrypt` for password hashing
- `PyJWT` (`jwt` module) for token operations
- `users.authentication.JWTAuthentication` as the auth backend
- `config.exceptions.custom_exception_handler` for error handling
- `config.s3.s3_service` for all S3 file uploads/deletes
- `config.serializers.FileUploadSerializer` / `MultiFileUploadSerializer` for file endpoints
- `drf_spectacular.utils.extend_schema` for API documentation

---

## Code Style

### Strict Typing — Zero Tolerance for `Any`

- **Never** use `Any` as a type — not in parameters, returns, variables, or generics
- **All** function signatures must have type hints on every parameter and the return type
- Use `TypedDict` for dictionary shapes instead of `dict[str, Any]`
- Use modern built-in generics: `list[str]`, `dict[str, int]`, `set[str]`, `tuple[int, ...]` — **not** `List`, `Dict`, `Set`, `Tuple` from `typing`
- Use `X | None` instead of `Optional[X]`
- Use string literals for forward references: `'ClassName'`
- Callable types: `Callable[[str, int], bool]` — never `Callable[..., Any]`

```python
# ✅ GOOD
def find_user(email: str) -> User | None:
    ...

class UploadResult(TypedDict):
    url: str
    key: str
    content_type: str

ALLOWED_TYPES: set[str] = {'image/jpeg', 'image/png'}

# ❌ BAD
def find_user(email) -> Any:       # Missing param type, Any return
def process(data: dict[str, Any]): # Any in generic
from typing import List, Optional  # Old-style imports
```

### Clean Coding

- **Max 30 lines per function** — extract helpers if longer
- **Early returns** over deep nesting — check errors first, happy path last
- **Single responsibility** — one function does one thing
- **No nested try/except** — keep error handling flat
- **No copy-paste** — if logic appears twice, extract to a shared function in `config/`
- **Constants** in UPPER_SNAKE_CASE at module level, never magic values inline
- **f-strings** for formatting — never `.format()` or `%`

### Reusability

- Shared services live in `config/` — `s3.py`, `db.py`, `serializers.py`
- If two apps need the same logic, it belongs in `config/`
- Parameterize differences — one function with params, not two similar functions
- Use module-level singletons for clients: `s3_service = S3Service()` in `config/s3.py`

### Python Naming

- **snake_case** for variables, functions, modules
- **PascalCase** for classes
- **UPPER_SNAKE_CASE** for constants
- **Explicit imports** — no wildcard `from x import *`

### Imports Order

```python
# 1. Standard library
from datetime import datetime, timezone

# 2. Third-party
import jwt
import bcrypt
import mongoengine
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

# 3. Django
from django.conf import settings

# 4. Local app
from users.documents import User
from users.serializers import UserSerializer
```

---

## MongoEngine Documents (`documents.py`)

### Pattern

```python
import mongoengine
from datetime import datetime


class Product(mongoengine.Document):
    name = mongoengine.StringField(required=True, max_length=200)
    description = mongoengine.StringField()
    price = mongoengine.DecimalField(required=True, min_value=0, precision=2)
    category = mongoengine.StringField(max_length=100)
    merchant_id = mongoengine.StringField(required=True)
    is_available = mongoengine.BooleanField(default=True)
    images = mongoengine.ListField(mongoengine.StringField())
    created_at = mongoengine.DateTimeField(default=datetime.utcnow)
    updated_at = mongoengine.DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'products',
        'indexes': ['category', 'merchant_id', '-created_at'],
        'ordering': ['-created_at'],
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
```

### Rules

- Always define `meta` with `collection`, `indexes`, and `ordering`
- Always include `created_at` and `updated_at` with `_utcnow` helper using `datetime.now(timezone.utc)`
- Override `save()` to auto-update `updated_at`
- Use specific field types: `StringField`, `IntField`, `DecimalField`, `BooleanField`, `ListField`, `EmbeddedDocumentField`, `DateTimeField`
- Set `required=True` on mandatory fields
- **Never** inherit from `django.db.models.Model`

---

## DRF Serializers (`serializers.py`)

### Pattern

```python
from rest_framework import serializers


class ProductSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=200)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
```

### Rules

- Always use `serializers.Serializer` — **never** `ModelSerializer`
- Separate read serializers from write/create serializers when fields differ
- Use `read_only=True` for output-only fields (`id`, timestamps)
- Use `write_only=True` for sensitive input fields (`password`)
- Keep serializers thin — validation only, no business logic

---

## Views (`views.py`)

### Pattern

```python
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema


class ProductListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ProductSerializer(many=True)})
    def get(self, request) -> Response:
        products = Product.objects(is_available=True)
        return Response({
            'success': True,
            'data': ProductSerializer(products, many=True).data,
        })
```

### Rules

- Always use `@extend_schema()` on every view method for Swagger docs
- Always set `permission_classes` at class level
- Use `AllowAny` for public endpoints (register, login)
- Use `IsAuthenticated` for protected endpoints
- `request.user` is a MongoEngine `User` document (from `JWTAuthentication`)
- Validate input with serializers before processing

---

## API Response Format

**Every response** must follow this envelope:

```python
# Success
{'success': True, 'data': { ... }}
{'success': True, 'data': { ... }, 'message': 'Created successfully.'}

# Error
{'success': False, 'error': 'Human-readable error message.'}
{'success': False, 'error': {'status_code': 400, 'detail': { ... }}}
```

- `success` is always present and boolean
- On success: include `data` (object or list). Optional `message`
- On error: include `error` (string or object)
- Unhandled exceptions are caught by `config.exceptions.custom_exception_handler`

---

## JWT Authentication

### Token Flow

1. **Register** → returns `{access_token, refresh_token}` + user data
2. **Login** → returns `{access_token, refresh_token}` + user data
3. **Authenticated requests** → `Authorization: Bearer <access_token>`
4. **Refresh** → POST `refresh_token` to get new tokens

### Token Utilities (`users/tokens.py`)

- `generate_tokens(user_id)` → `{access_token, refresh_token}`
- `generate_access_token(user_id)` → access JWT string
- `generate_refresh_token(user_id)` → refresh JWT string
- `decode_token(token)` → decoded payload dict

### Password Hashing

```python
import bcrypt

# Hash
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Verify
bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
```

---

## URL Routing

### Root (`config/urls.py`)

```python
path('api/users/', include('users.urls')),
path('api/products/', include('products.urls')),
path('api/orders/', include('orders.urls')),
```

### App URLs (`<app>/urls.py`)

```python
from django.urls import path
from products.views import ProductListView, ProductDetailView

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('<str:pk>/', ProductDetailView.as_view(), name='product-detail'),
]
```

- All API routes are prefixed with `api/`
- Use `<str:pk>` for MongoDB ObjectId path params (they're strings)
- Name every URL pattern

---

## Error Handling

- Let DRF handle validation via `serializer.is_valid(raise_exception=True)`
- Custom handler in `config/exceptions.py` wraps all errors in standard envelope
- For business logic errors, return explicit `Response` with error envelope:

```python
return Response(
    {'success': False, 'error': 'Email already registered.'},
    status=status.HTTP_409_CONFLICT,
)
```

- **Never** let raw exceptions bubble to the client
- Use appropriate HTTP status codes: `400` validation, `401` auth, `403` forbidden, `404` not found, `409` conflict

---

## Security

- **Never** return password hashes in API responses
- **Always** validate input through DRF serializers before processing
- Use `CORS_ALLOWED_ORIGINS` — never `CORS_ALLOW_ALL_ORIGINS = True` in production
- JWT tokens must always have `exp` claim
- Validate token `type` claim (`access` vs `refresh`) to prevent misuse

---

## S3 File Uploads (`config/s3.py`)

### Architecture

- **One service, all apps** — `config.s3.s3_service` is a module-level singleton
- **Server-side upload** — frontend sends file to backend, backend uploads to S3
- **Typed results** — `UploadResult` TypedDict: `{url, key, content_type}`

### S3 Folder Layout

```
bucket/
├── products/{product_id}/{uuid}.jpg     # Product images (multi)
├── avatars/{user_id}/{uuid}.jpg         # User avatar (single)
└── orders/{order_id}/{uuid}.pdf         # Order receipt (single)
```

### Upload Endpoints

| Endpoint | Method | Serializer | Service Method |
|----------|--------|------------|----------------|
| `/api/products/<id>/images/` | POST / DELETE | `MultiFileUploadSerializer` | `s3_service.upload_image()` |
| `/api/users/profile/avatar/` | POST / DELETE | `FileUploadSerializer` | `s3_service.upload_image()` |
| `/api/orders/<id>/receipt/` | POST | `FileUploadSerializer` | `s3_service.upload_document()` |

### Constraints

- All file types: min **5 MB**, max **25 MB**
- `ValueError` = validation fail (bad type / too large) → return `400`
- `ClientError` = S3 transport error → return `502` + log exception
- Always validate ownership before uploading (merchant owns product, user owns avatar, rider/merchant owns order)

### Pattern for Upload Views

```python
from config.s3 import s3_service
from config.serializers import FileUploadSerializer

class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request: Request) -> Response:
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = s3_service.upload_image(serializer.validated_data['file'], f"avatars/{user_id}")
        except ValueError as exc:
            return Response({'success': False, 'error': str(exc)}, status=400)
        ...
```

---

## Testing

- Place tests in `<app>/tests.py` or `<app>/tests/` directory
- Use DRF's `APIClient` for endpoint testing
- Test both success and error paths
- Test authentication: valid token, expired token, missing token, wrong token type
- Use a separate test MongoDB database
- Clean up test documents in `setUp` / `tearDown`

---

## Checklist Before Generating Code

1. Am I using MongoEngine Documents, not Django ORM models?
2. Am I using `serializers.Serializer`, not `ModelSerializer`?
3. Does the response follow `{success, data/error}` format?
4. Did I add `@extend_schema()` for Swagger?
5. Did I set `permission_classes`?
6. Did I type-hint **every** parameter and return type (no `Any`)?  
7. Am I importing from the correct local modules?
8. Did I avoid `django.contrib.auth` entirely?
9. Is my function ≤ 30 lines? If not, extract a helper.
10. Am I reusing shared services (`config/s3.py`, `config/db.py`) instead of duplicating logic?
11. For file uploads: am I using `s3_service` + `FileUploadSerializer`/`MultiFileUploadSerializer`?
