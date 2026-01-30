from django.contrib import admin
from django.urls import path, include

from gfm.views import TicketsListView, TicketImportView

urlpatterns = [
    path("gfm/admin/", admin.site.urls),

    path("gfm/", include("gfm.urls")),

    path("gfm/tickets/", TicketsListView.as_view(), name="tickets_list"),
    path("gfm/tickets/import/", TicketImportView.as_view(), name="import"),
]