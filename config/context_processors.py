from __future__ import annotations

from typing import List, TypedDict
from django.http import HttpRequest
from django.urls import reverse_lazy


class Tile(TypedDict):
    title: str
    description: str
    icon: str
    color: str
    url: str
    nav: bool


class SectionItem(TypedDict):
    section: str
    items: List[Tile]


def navigation_tiles(request: HttpRequest) -> dict:
    user = getattr(request, "user", None)

    # Nicht eingeloggt → nichts anzeigen
    if not getattr(user, "is_authenticated", False):
        return {"sections": []}

    sections: List[SectionItem] = []

    # Für ALLE eingeloggten User
    sections.append(
        {
            "section": "T & T",
            "items": [
                {
                    "title": "Tickets",
                    "description": "Alle Tickets anzeigen und nach Veranstaltung filtern.",
                    "icon": "bi-ticket-perforated",
                    "color": "text-primary",
                    "url": reverse_lazy("tickets_list"),
                    "nav": True,
                },
                {
                    "title": "Teilnehmer",
                    "description": "Alle Teilnehmer anzeigen und nach Veranstaltung filtern.",
                    "icon": "bi-people-fill",
                    "color": "text-primary",
                    "url": reverse_lazy("participants_list"),
                    "nav": True,
                },
            ],
        }
    )

    # NUR für Staff
    if getattr(user, "is_staff", False):
        sections.append(
            {
                "section": "Admin",
                "items": [
                    {
                        "title": "CSV importieren",
                        "description": "CSV-Export vom Eventmanager importieren.",
                        "icon": "bi-cloud-upload",
                        "color": "text-primary",
                        "url": reverse_lazy("import"),
                        "nav": True,
                    },
                    {
                        "title": "Django Admin",
                        "description": "Direkter Zugriff auf das Admin Interface.",
                        "icon": "bi-gear-fill",
                        "color": "text-dark",
                        "url": reverse_lazy("admin:index"),
                        "nav": True,
                    },
                ],
            }
        )

    return {"sections": sections}
