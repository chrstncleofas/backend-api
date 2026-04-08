from django.conf import settings
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request: Request) -> Response:
    return Response({'success': True, 'status': 'ok'})


urlpatterns = [
    path('', RedirectView.as_view(url='/api/schema/swagger-ui/', permanent=False)),

    # Health check — used by Docker, load balancers, and PaaS platforms
    path('api/health/', health_check, name='health-check'),

    # Versioned business API routes
    path(f'api/{settings.API_VERSION}/users/', include('users.urls')),
    path(f'api/{settings.API_VERSION}/products/', include('products.urls')),
    path(f'api/{settings.API_VERSION}/orders/', include('orders.urls')),

    # Swagger / OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
