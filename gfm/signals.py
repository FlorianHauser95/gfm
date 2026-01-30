from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Participant, Ticket


@receiver(post_save, sender=Ticket)
def autolink_participant_on_ticket_save(sender, instance: Ticket, created: bool, **kwargs):
    """
    Wenn ein Ticket registriert wird, verknüpfe es automatisch mit einem Participant,
    der für dasselbe Event+Email existiert und noch kein Ticket hat.
    """
    with transaction.atomic():
        p = (
            Participant.objects
            .select_for_update()
            .filter(
                event_id=instance.event_id,
                email__iexact=instance.email,
                ticket__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if p:
            p.ticket = instance
            p.save(update_fields=["ticket", "updated_at"])
