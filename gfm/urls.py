from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from config.view import HomeView, UnderConstructionView
from gfm.forms import EmailAuthenticationForm
from gfm.views import TicketParticipationView, ParticipantsListView, ParticipantNoTicketCreateView, \
    AnalyticsDashboardView

urlpatterns = [

    # =========================
    # HOME / SYSTEM
    # =========================
    path("", HomeView.as_view(), name="home"),
    path("under_construction/", UnderConstructionView.as_view(), name="under_construction"),

    # =========================
    # AUTH
    # =========================
    path(
        "login/",
        LoginView.as_view(
            template_name="users/login.html",
            authentication_form=EmailAuthenticationForm
        ),
        name="login"
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    # path("register/", RegisterView.as_view(), name="register"),
    path("tickets/<uuid:ticket_uuid>/participation/", TicketParticipationView.as_view(), name="ticket_participation"),
    path("participants/", ParticipantsListView.as_view(), name="participants_list"),
    path("participants/new/no-ticket/", ParticipantNoTicketCreateView.as_view(), name="participant_create_no_ticket"),
    path('dashboard/', AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
]
