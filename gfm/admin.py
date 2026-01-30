from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from gfm.models import User
from django.utils.translation import gettext_lazy as _

from django.contrib import admin, messages
from django.db import transaction

from .models import Event, Participant, Ticket

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "date", "tickets_count", "participants_count")
    search_fields = ("name",)
    list_filter = ("date",)
    date_hierarchy = "date"
    ordering = ("-date", "name")

    @admin.display(description="Tickets")
    def tickets_count(self, obj: Event) -> int:
        return obj.tickets.count()

    @admin.display(description="Participants")
    def participants_count(self, obj: Event) -> int:
        return obj.participants.count()


class HasParticipantFilter(admin.SimpleListFilter):
    title = "Participant linked"
    parameter_name = "has_participant"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.filter(participant__isnull=False)
        if val == "no":
            return queryset.filter(participant__isnull=True)
        return queryset

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_uuid",
        "name",
        "email",
        "event",
        "linked_participant",
        "created_at",
    )
    search_fields = ("ticket_uuid", "name", "email", "event__name")
    list_filter = ("event", HasParticipantFilter, "created_at")
    autocomplete_fields = ("event",)
    readonly_fields = ("ticket_uuid", "created_at", "updated_at")

    @admin.display(description="Participant")
    def linked_participant(self, obj: Ticket):
        # Reverse OneToOne: Ticket.participant (related_name="participant")
        return getattr(obj, "participant", None)


class LinkedTicketFilter(admin.SimpleListFilter):
    title = "Ticket linked"
    parameter_name = "ticket_linked"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.filter(ticket__isnull=False)
        if val == "no":
            return queryset.filter(ticket__isnull=True)
        return queryset


@admin.action(description="Auto-link Tickets for selected Participants")
def action_autolink_tickets(modeladmin, request, queryset):
    """
    Triggert das Autolinking (Participant.save() macht den Match),
    sinnvoll wenn z.B. Tickets nachträglich importiert wurden.
    """
    updated = 0
    skipped = 0

    with transaction.atomic():
        # Sperren für konsistente Verknüpfung bei parallelen Admin-Operationen
        qs = queryset.select_for_update()
        for p in qs:
            if p.ticket_id:
                skipped += 1
                continue

            before = p.ticket_id
            p.save()  # ruft _try_autolink_ticket() aus models.py auf
            if before != p.ticket_id and p.ticket_id:
                updated += 1

    if updated:
        modeladmin.message_user(
            request,
            f"{updated} Participant(s) successfully linked to Tickets.",
            level=messages.SUCCESS,
        )
    if skipped:
        modeladmin.message_user(
            request,
            f"{skipped} Participant(s) skipped (already had a Ticket).",
            level=messages.INFO,
        )
    if not updated and not skipped:
        modeladmin.message_user(
            request,
            "No Participants processed.",
            level=messages.WARNING,
        )


@admin.action(description="Unlink Ticket from selected Participants")
def action_unlink_tickets(modeladmin, request, queryset):
    """
    Entfernt Verknüpfungen (nur wenn du das fachlich erlauben willst).
    """
    count = queryset.filter(ticket__isnull=False).update(ticket=None)
    modeladmin.message_user(
        request,
        f"Unlinked Tickets from {count} Participant(s).",
        level=messages.SUCCESS,
    )


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "event",
        "ticket",
        "paid_at",
        "amount",
        "created_at",
    )
    search_fields = ("name", "email", "event__name", "ticket__ticket_uuid", "ticket__name")
    list_filter = ("event", LinkedTicketFilter, "paid_at", "created_at")
    autocomplete_fields = ("event", "ticket")
    readonly_fields = ("created_at", "updated_at")
    actions = (action_autolink_tickets, action_unlink_tickets)
    list_select_related = ("event", "ticket")

    fieldsets = (
        ("Participant", {"fields": ("name", "email", "event")}),
        ("Payment", {"fields": ("paid_at", "amount")}),
        ("Ticket Link", {"fields": ("ticket",)}),
        ("Meta", {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("event", "ticket")

    def save_model(self, request, obj, form, change):
        """
        Speichern im Admin triggert Autolink (Participant.save()).
        Wir geben zusätzlich Feedback, wenn beim Speichern verknüpft wurde.
        """
        before = obj.ticket_id
        super().save_model(request, obj, form, change)
        after = obj.ticket_id

        if before is None and after is not None:
            self.message_user(
                request,
                "Participant was automatically linked to a matching Ticket (event + email).",
                level=messages.SUCCESS,
            )


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "last_name",
        "first_name",
        "email",
        "is_active",
        "date_joined",
        "last_login",
    )
    list_filter = ("is_active", "groups")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("last_name", "first_name")
    list_select_related = ("program",)
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Allgemein"), {"fields": ("first_name", "last_name")}),
        (_("Permissions"),
         {
             "fields": (
                 "is_active",
                 "groups",
             )
         }),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "is_active",
                    "groups",
                ),
            },
        ),
    )

    readonly_fields = ("date_joined", "last_login")
