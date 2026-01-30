from dataclasses import dataclass
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models, transaction
from django.db.models import OuterRef, Exists
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from django.contrib import messages
from django.urls import reverse
from django.views.generic.edit import FormView

from .forms import TicketImportForm, ParticipationSelectionForm

from gfm.forms import TicketFilterForm
from gfm.models import Ticket, Participant, Event
from gfm.permissions import RequireAdminRoleMixin


class TicketMixin(LoginRequiredMixin, RequireAdminRoleMixin):
    model = Ticket
    success_url = reverse_lazy("tickets_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "title_singular": "Ticket",
            "title_plural": "Tickets",
            "cancel_url": self.success_url,
        })
        return context


class TicketsListView(TicketMixin, ListView):
    template_name = "tickets/tickets_list.html"
    paginate_by = 10

    def get_queryset(self):
        # Basis-Queryset mit Bezahlstatus-Annotation
        paid_subquery = Participant.objects.filter(
            ticket_id=OuterRef("pk"),
            paid_at__isnull=False
        )

        qs = super().get_queryset().select_related("event").annotate(
            is_paid=Exists(paid_subquery)
        )

        # 1. Event-ID aus GET holen oder Standard (heute) bestimmen
        event_id = self.request.GET.get("event")

        # Wenn kein Filter aktiv ist, versuchen wir das Event von heute zu finden
        if event_id is None:
            today_event = Event.objects.filter(date=timezone.localdate()).first()
            if today_event:
                event_id = today_event.id

        # 2. Filtern
        if event_id:
            qs = qs.filter(event_id=event_id)

        # Suche
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                models.Q(name__icontains=q) |
                models.Q(email__icontains=q) |
                models.Q(ticket_uuid__icontains=q)
            )

        return qs.order_by("is_paid", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form_data = self.request.GET.copy()

        if "event" not in form_data:
            today_event = Event.objects.filter(date=timezone.localdate()).first()
            if today_event:
                form_data["event"] = today_event.id

        context["filter_form"] = TicketFilterForm(form_data)
        return context


class TicketImportView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "tickets/ticket_import.html"
    form_class = TicketImportForm

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        csv_file = form.cleaned_data["file"]
        try:
            stats = Ticket.objects.create_from_csv(csv_file)
            messages.success(
                self.request,
                (
                    "Import abgeschlossen: "
                    f"{stats.get('created', 0)} erstellt, "
                    f"{stats.get('updated', 0)} aktualisiert, "
                    f"{stats.get('deleted', 0)} gelöscht, "
                    f"{stats.get('skipped', 0)} übersprungen."
                )
            )
            return super().form_valid(form)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        except Exception as e:
            form.add_error(None, f"Unerwarteter Fehler: {str(e)}")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("ticket_list")


@dataclass(frozen=True)
class TicketOptionVM:
    ticket: Ticket
    checked: bool


@dataclass(frozen=True)
class EventRowVM:
    event: object  # Event instance
    tickets: list[TicketOptionVM]
    no_ticket_checked: bool


@dataclass(frozen=True)
class TicketVM:
    ticket: Ticket
    checked: bool


@dataclass(frozen=True)
class TicketGroupVM:
    event: object  # Event
    tickets: list[TicketVM]


@dataclass(frozen=True)
class NoTicketEventVM:
    event: object
    checked: bool


class TicketParticipationView(LoginRequiredMixin, RequireAdminRoleMixin, View):
    template_name = "tickets/ticket_participation.html"
    success_url = reverse_lazy("tickets_list")

    def _build_viewmodel(self, *, email: str):
        events = list(Participant.objects.events_all())
        tickets = list(Participant.objects.tickets_for_email(email))

        # Prechecked: vorhandene Participants
        checked_ticket_ids = set(
            Participant.objects.filter(email__iexact=email, ticket__isnull=False)
            .values_list("ticket_id", flat=True)
        )
        checked_no_ticket_event_ids = set(
            Participant.objects.filter(email__iexact=email, ticket__isnull=True)
            .values_list("event_id", flat=True)
        )

        # Tickets nach Event gruppieren
        tickets_by_event_id: dict[int, list[Ticket]] = {}
        for t in tickets:
            tickets_by_event_id.setdefault(t.event_id, []).append(t)

        ticket_groups: list[TicketGroupVM] = []
        for e in events:
            if e.id not in tickets_by_event_id:
                continue
            ticket_groups.append(
                TicketGroupVM(
                    event=e,
                    tickets=[TicketVM(ticket=t, checked=(t.ticket_uuid in checked_ticket_ids)) for t in
                             tickets_by_event_id[e.id]],
                )
            )

        # No-ticket Events: NUR dort anzeigen, wo es KEINE Tickets zur Email für dieses Event gibt
        no_ticket_events: list[NoTicketEventVM] = []
        for e in events:
            if e.id in tickets_by_event_id:
                continue
            no_ticket_events.append(
                NoTicketEventVM(event=e, checked=(e.id in checked_no_ticket_event_ids))
            )

        # Form choices (Validierung)
        return ticket_groups, no_ticket_events, tickets, events

    def get(self, request, ticket_uuid):
        source_ticket = get_object_or_404(Ticket.objects.select_related("event"), ticket_uuid=ticket_uuid)
        email = source_ticket.email
        ticket_groups, no_ticket_events, _tickets, _events = self._build_viewmodel(email=email)

        # Form initialisieren mit den Daten für den Layout-Aufbau
        form = ParticipationSelectionForm(
            ticket_groups=ticket_groups,
            no_ticket_events=no_ticket_events,
            cancel_url=reverse('tickets_list')
        )

        return render(request, self.template_name, {
            "title": "Teilnahme / Zahlung bestätigen",
            "source_ticket": source_ticket,
            "email": email,
            "form": form,  # Wir brauchen ticket_groups etc. nicht mehr im Context
        })

    def post(self, request, ticket_uuid):
        source_ticket = get_object_or_404(Ticket.objects.select_related("event"), ticket_uuid=ticket_uuid)
        email = source_ticket.email
        paid_at = timezone.localdate()

        ticket_groups, no_ticket_events, tickets, events = self._build_viewmodel(email=email)

        # Form mit POST-Daten binden
        form = ParticipationSelectionForm(
            request.POST,
            ticket_groups=ticket_groups,
            no_ticket_events=no_ticket_events,
            cancel_url=reverse('tickets_list')
        )

        if not form.is_valid():
            return render(request, self.template_name, {
                "title": "Teilnahme / Zahlung bestätigen",
                "source_ticket": source_ticket,
                "email": email,
                "form": form,
            })

        # WICHTIG: Nutze jetzt cleaned_data (durch die Form aggregiert)
        selected_ticket_uuids = set(form.cleaned_data.get("tickets", []))
        selected_no_ticket_event_ids = set(form.cleaned_data.get("no_ticket_events", []))

        # 1) Ticket-Teilnahmen
        ticket_by_uuid = {str(t.ticket_uuid): t for t in tickets}
        upserted = 0

        for uuid_str in selected_ticket_uuids:
            t = ticket_by_uuid.get(uuid_str)
            if not t:
                continue

            p, created = Participant.objects.get_or_create(
                ticket=t,
                defaults={
                    "event_id": t.event_id,
                    "email": email,
                    "name": source_ticket.name or email,
                    "paid_at": paid_at,
                    "amount": Decimal("23.00"),
                }
            )
            if not created:
                p.event_id = t.event_id
                p.email = email
                if not p.name:
                    p.name = source_ticket.name or email
                p.paid_at = paid_at
                p.amount = Decimal("23.00")
                p.save(update_fields=["event", "email", "name", "paid_at", "amount", "updated_at"])
            upserted += 1

        # 2) No-ticket Teilnahmen (nur Events, die tatsächlich in no_ticket_events angeboten wurden)
        allowed_no_ticket_event_ids = {str(vm.event.id) for vm in no_ticket_events}
        selected_no_ticket_event_ids = selected_no_ticket_event_ids.intersection(allowed_no_ticket_event_ids)

        event_by_id = {str(e.id): e for e in events}
        for event_id_str in selected_no_ticket_event_ids:
            e = event_by_id.get(event_id_str)
            if not e:
                continue

            p = Participant.objects.filter(event=e, email__iexact=email, ticket__isnull=True).first()
            if p is None:
                Participant.objects.create(
                    event=e,
                    email=email,
                    name=source_ticket.name or email,
                    ticket=None,
                    paid_at=paid_at,
                    amount=Decimal("23.00"),
                )
            else:
                p.paid_at = paid_at
                p.amount = Decimal("23.00")
                if not p.name:
                    p.name = source_ticket.name or email
                p.save(update_fields=["paid_at", "amount", "name", "updated_at"])
            upserted += 1

        messages.success(request, f"{upserted} Teilnahme(n) gespeichert.")
        return redirect(f"{self.success_url}")
