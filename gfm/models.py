from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Tuple, Optional

from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin, Group
from django.core.validators import MinValueValidator

import csv
import io
import uuid as uuid_lib

from django.db import models, transaction
from django.db.models import ProtectedError
from django.utils import timezone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError



class Event(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateField()

    class Meta:
        ordering = ["date", "name"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["name"]),
        ]

    @classmethod
    def available(cls):
        """
        Definiert 'verfügbare Events'. Aktuell: ab heute (inkl).
        """
        today = timezone.localdate()
        return cls.objects.filter(date__gte=today).order_by("date", "name")

    def __str__(self) -> str:
        return f"{self.name} ({self.date})"

class TicketManager(models.Manager):
    DELIMITER = ","

    REQUIRED_FIELDS = {
        "Teilnehmer Ticket UUID",
        "Name",
        "E-Mail",
        "Veranstaltung",
    }

    OPTIONAL_FIELDS = {
        "Buchungskommentar",
    }

    STATUS_MAP = {
         "FREIGEGEBEN": "REGISTERED",
        "ABGESAGT": "CANCELED",
    }

    def _normalize_first_line(self, line: str) -> str:
        """
        Normalisiert eine CSV-Zeile für Erkennung von Metazeilen:
        - trimmt Whitespace
        - entfernt führende/abschließende Quotes
        """
        s = (line or "").strip()
        if s.startswith('"') and s.endswith('"') and len(s) >= 2:
            s = s[1:-1].strip()
        return s

    def _parse_csv(self, csv_file):
        try:
            raw = csv_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("CSV muss UTF-8-kodiert sein (UTF-8/UTF-8-SIG).")

        lines = raw.splitlines()

        # Führende Leerzeilen weg
        while lines and not lines[0].strip():
            lines.pop(0)

        if not lines:
            raise ValueError("CSV ist leer.")

        # Metazeile "Exportiert am ..." (auch wenn sie quoted ist) überspringen
        first = self._normalize_first_line(lines[0])
        if first.startswith("Exportiert am"):
            lines.pop(0)

        # Danach nochmal führende Leerzeilen weg (in deiner Datei ist eine Leerzeile danach)
        while lines and not lines[0].strip():
            lines.pop(0)

        if not lines:
            raise ValueError("CSV enthält keinen Header nach der Metazeile.")

        reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=self.DELIMITER)

        if not reader.fieldnames:
            raise ValueError("CSV enthält keinen Header.")

        missing = self.REQUIRED_FIELDS - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"Ungültiges CSV-Format. Fehlende Spalten: {', '.join(sorted(missing))}"
            )

        return reader

    def _get_or_create_event_by_name(self, event_name: str, cache: dict) -> Event:
        key = event_name.strip()
        if key in cache:
            return cache[key]

        event = Event.objects.filter(name=key).order_by("-date", "-id").first()
        if not event:
            event = Event.objects.create(name=key, date=timezone.localdate())

        cache[key] = event
        return event

    def create_from_csv(self, csv_file):
        reader = self._parse_csv(csv_file)

        deleted = 0
        created = 0
        updated = 0
        skipped = 0
        event_cache: dict[str, Event] = {}

        with transaction.atomic():
            for line_no, row in enumerate(reader, start=2):
                for f in self.REQUIRED_FIELDS:
                    if not row.get(f) or not str(row[f]).strip():
                        raise ValueError(f"Leeres Pflichtfeld '{f}' in Zeile {line_no}")

                raw_uuid = str(row["Teilnehmer Ticket UUID"]).strip()
                try:
                    ticket_uuid = uuid_lib.UUID(raw_uuid)
                except ValueError:
                    raise ValueError(f"Ungültige Ticket-UUID '{raw_uuid}' in Zeile {line_no}")

                email = str(row["E-Mail"]).strip()
                try:
                    validate_email(email)
                except ValidationError:
                    raise ValueError(f"Ungültige E-Mail '{email}' in Zeile {line_no}")

                # Status mappen (Abgesagt/Freigegeben)
                raw_status = str(row["Status"]).strip().upper()
                if raw_status not in self.STATUS_MAP:
                    raise ValueError(f"Unbekannter Status '{row['Status']}' in Zeile {line_no}")
                status = self.STATUS_MAP[raw_status]

                # Wenn abgesagt: Ticket (sofern vorhanden) löschen und nächste Zeile
                if status == "CANCELED":
                    try:
                        deleted_count, _ = self.filter(ticket_uuid=ticket_uuid).delete()
                    except ProtectedError:
                        raise ValueError(
                            f"Ticket {ticket_uuid} kann in Zeile {line_no} nicht gelöscht werden."
                        )

                    if deleted_count:
                        deleted += 1
                    else:
                        skipped += 1
                    continue

                # Event über Name finden/erstellen (Datum initial: today)
                event_name = str(row["Veranstaltung"]).strip()
                event = self._get_or_create_event_by_name(event_name, event_cache)

                # Optional: Kommentar
                comment = str(row.get("Buchungskommentar") or "").strip()

                # Ticket upsert über PK
                obj, was_created = self.update_or_create(
                    ticket_uuid=ticket_uuid,
                    defaults={
                        "event": event,
                        "name": str(row["Name"]).strip(),
                        "email": email,
                        "comment": comment,
                    },
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

        return {"created": created, "updated": updated, "skipped": skipped,"deleted": deleted}


class Ticket(models.Model):
    ticket_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255)
    email = models.EmailField()
    comment = models.TextField(blank=True)

    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name="tickets",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TicketManager()

    class Meta:
        indexes = [
            models.Index(fields=["event"]),
            models.Index(fields=["email"]),
        ]

    @classmethod
    def registered_for_email(cls, email: str):
        """
        Liefert REGISTERED Tickets für eine Email, inkl. Event.
        """
        return (
            cls.objects
            .filter(email__iexact=email)
            .select_related("event")
            .order_by("event__date", "event__name", "-created_at")
        )

    @classmethod
    def newest_per_event_for_email(cls, email: str):
        """
        Liefert pro Event genau ein Ticket (das 'neueste' nach created_at),
        für diese Email (REGISTERED).
        """
        tickets = list(cls.registered_for_email(email))
        seen = set()
        result = []
        for t in tickets:
            if t.event_id in seen:
                continue
            seen.add(t.event_id)
            result.append(t)
        return result

    def __str__(self) -> str:
        return f"{self.name} - {self.event}"


class ParticipantManager(models.Manager):
    """
    Stark vereinfacht: genau zwei Methoden.
    """

    def tickets_for_email(self, email: str):
        # "organisiert alle tickets" = alle REGISTERED Tickets für Email, inkl. event
        return (
            Ticket.objects
            .filter(email__iexact=email)
            .select_related("event")
            .order_by("event__date", "event__name", "-created_at")
        )

    def events_all(self):
        # "organisiert über events alle events" = alle Events, keine Zeitlimits
        return Event.objects.all().order_by("date", "name")

class Participant(models.Model):
    """
    Participant kann ohne Ticket existieren.
    Später wird ein Ticket registriert; Matching erfolgt über (event, email).
    """

    name = models.CharField(max_length=255)
    email = models.EmailField()

    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name="participants",
    )

    # optionales Ticket (wird später gesetzt)
    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.SET_NULL,
        related_name="participant",
        null=True,
        blank=True,
        db_column="ticket_uuid",
    )

    paid_at = models.DateField(null=True, blank=True)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Gezahlter Betrag in EUR",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ParticipantManager()

    class Meta:
        indexes = [
            models.Index(fields=["event", "email"]),
            models.Index(fields=["paid_at"]),
        ]
        constraints = [
            # max 1 no-ticket pro (event,email)
            models.UniqueConstraint(
                fields=["event", "email"],
                condition=models.Q(ticket__isnull=True),
                name="uniq_no_ticket_participant_per_event_email",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.event} ({self.amount} EUR)"

    def clean(self) -> None:
        # Wenn ticket gesetzt ist, muss Ticket zu event+email passen (Konsistenz).
        if self.ticket_id:
            if self.ticket.event_id != self.event_id:
                raise ValidationError({"ticket": "Ticket gehört zu einem anderen Event."})
            if self.ticket.email.lower() != self.email.lower():
                raise ValidationError({"ticket": "Ticket-E-Mail passt nicht zur Participant-E-Mail."})

    def _try_autolink_ticket(self) -> None:
        """
        Versucht, automatisch ein Ticket zu verknüpfen, falls noch keines gesetzt ist.
        Matching: event + email
        """
        if self.ticket_id or not self.event_id or not self.email:
            return

        qs = Ticket.objects.filter(
            event_id=self.event_id,
            email__iexact=self.email
        )

        ticket = qs.order_by("-created_at").first()
        if ticket:
            self.ticket = ticket

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self._try_autolink_ticket()
            super().save(*args, **kwargs)


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(
            email=self.normalize_email(email),
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        user = self.create_user(
            email,
            password=password,
            **extra_fields
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)

    groups = models.ManyToManyField(Group, related_name="custom_users", blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Benutzer'
        verbose_name_plural = 'Benutzer'

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email
