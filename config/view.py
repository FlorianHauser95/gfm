from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = "home.html"

class UnderConstructionView(TemplateView):
    template_name = "under_construction.html"
    extra_context = {"page_title": "Seite im Aufbau"}