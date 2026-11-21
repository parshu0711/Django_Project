from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "PolarOps Administration"
admin.site.site_title = "PolarOps Admin"
admin.site.index_title = "Indian Antarctic Stations - data administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("api/", include("polarops.api_urls")),
    path("stations/", include("stations.urls")),
    path("personnel/", include("personnel.urls")),
    path("inventory/", include("inventory.urls")),
    path("operations/", include("operations.urls")),
    path("telemetry/", include("telemetry.urls")),
    path("research/", include("research.urls")),
    path("", include("core.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
