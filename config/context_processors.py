from __future__ import annotations

from typing import List, TypedDict


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


from django.http import HttpRequest
from django.urls import reverse_lazy


def navigation_tiles(request: HttpRequest) -> dict:
    user = getattr(request, "user", None)

    if not getattr(user, "is_authenticated", False):
        return {"sections": []}

    if not getattr(user, "is_staff", False):
        return {"sections": []}

    return {
        "sections": [
            {
                "section": "Admin",
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
        ]
    }
