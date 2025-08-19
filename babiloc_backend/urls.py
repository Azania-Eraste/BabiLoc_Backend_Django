"""
URL configuration for babiloc_backend project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static

schema_view = get_schema_view(
    openapi.Info(
        title="BabiLoc API",
        default_version='v1',
        description="API de gestion des réservations pour BabiLoc",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@babiloc.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('Auths.urls')),
    path('api/location/', include('reservation.urls')),
    path('api/chat/', include('chat.urls')),  # 🎯 Nouvelle ligne pour l'app chat
    
    # Documentation Swagger
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API Root
    path('api/', schema_view.with_ui('swagger', cache_timeout=0), name='api-root'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)