"""
API Documentation URLs - Swagger/OpenAPI schema and UI.

Endpoints:
- /api/schema/ - OpenAPI 3.0 schema (JSON/YAML)
- /api/docs/ - Swagger UI (interactive documentation)
- /api/redoc/ - ReDoc (alternative documentation UI)
"""
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # OpenAPI 3.0 schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # Swagger UI (interactive documentation)
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # ReDoc (alternative documentation UI)
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
