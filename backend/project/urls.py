# project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken.views import obtain_auth_token
from django.views.static import serve
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # adjust as needed

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("api-auth/", include("rest_framework.urls")),# browsable login for session auth
    path("api-token-auth/", obtain_auth_token),
    path("samples/<path:filename>", lambda request, filename: serve(request, filename, document_root=str(PROJECT_ROOT / "samples"))),
]

# serve media in dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
