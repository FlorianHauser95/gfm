from django.contrib import admin
from django.urls import path, include

from gfm.views import TicketsListView, TicketImportView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("gfm.urls")),

    path("tickets/", TicketsListView.as_view(), name="tickets_list"),
    path("tickets/import/", TicketImportView.as_view(), name="import"),
]