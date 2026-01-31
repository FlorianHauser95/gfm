from django import forms
from django.contrib.auth.forms import AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Row, Column, Button, Layout, Submit, HTML, Div, Field
from django.urls import reverse
from django.utils.html import format_html

from gfm.models import Event


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="E-Mail")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.add_input(Submit("submit", "Einloggen"))


class TicketFilterForm(forms.Form):
    event = forms.ModelChoiceField(
        queryset=Event.objects.all().order_by("-date", "name"),
        required=False,
        label="Veranstaltung",
        empty_label="Alle Veranstaltungen",
    )

    q = forms.CharField(
        required=False,
        label="Suche",
        help_text="Name, Email oder Ticket-UUID",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_show_labels = True

        self.helper.layout = Layout(
            Row(
                Column("event", css_class="col-12 col-md-5"),
                Column("q", css_class="col-12 col-md-4"),
            ),
            Row(
                Column(
                    Submit("submit", "Filtern", css_class="btn btn-primary"),
                    css_class="col-12 d-flex justify-content-end",
                ),
            ),
        )


class TicketImportForm(forms.Form):
    file = forms.FileField(
        label="Ticket-Export (CSV)",
        help_text="CSV aus dem Export hochladen (erste Zeile 'Exportiert am ...' wird ignoriert)."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.add_input(Submit("submit", "Tickets importieren"))
        self.helper.add_input(
            Button(
                "cancel",
                "Abbrechen",
                css_class="btn-outline-secondary",
                onclick=f"window.location.href='{reverse('tickets_list')}'"
            )
        )

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".csv"):
            raise forms.ValidationError("Bitte eine gültige CSV-Datei hochladen.")
        return f


class ParticipationSelectionForm(forms.Form):
    def __init__(self, *args, ticket_groups=None, no_ticket_events=None, cancel_url="#", **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout()

        # --- 1. Tickets ---
        if ticket_groups:
            self.helper.layout.append(HTML('<h6 class="fw-bold mb-3">Tickets</h6>'))

            for group in ticket_groups:
                # Container für das Event starten
                self.helper.layout.append(
                    HTML(f'<div class="card mb-3 border-0 shadow-sm"><div class="card-body py-3">'))
                self.helper.layout.append(HTML(
                    f'<div class="fw-bold mb-3 text-center">{group.event.name} <span class="fw-normal text-muted small">({group.event.date.strftime("%d.%m.%Y")})</span></div>'))

                selectable_choices = []

                for opt in group.tickets:
                    # --- A) Button Text generieren ---
                    # Standard: Nur der Name
                    label_content = opt.ticket.name

                    # Falls ein Kommentar existiert
                    if opt.ticket.comment:
                        label_content = format_html(
                            "{}<br><small class='fw-normal' style='font-size: 0.85em; opacity: 0.8;'>{}</small>",
                            opt.ticket.name,
                            opt.ticket.comment
                        )

                    # --- B) Logik für "Bereits gebucht" vs. "Wählbar" ---
                    if opt.checked:
                        # === BEREITS GEBUCHT ===
                        comment_html = f"<br><small>{opt.ticket.comment}</small>" if opt.ticket.comment else ""

                        html_locked = f"""
                                        <div class="form-check mb-2 touch-friendly-locked" data-event-id="{group.event.id}" data-locked="true">
                                            <input class="form-check-input" type="checkbox" checked disabled>
                                            <label class="form-check-label">
                                                <strong>{opt.ticket.name}</strong>
                                                <span class="badge bg-secondary">Bereits bezahlt</span>
                                                {comment_html} 
                                            </label>
                                        </div>
                                        """
                        self.helper.layout.append(HTML(html_locked))
                    else:
                        # === NOCH FREI ===
                        selectable_choices.append((opt.ticket.ticket_uuid, label_content))

                if selectable_choices:
                    field_name = f"group_{group.event.id}"
                    self.fields[field_name] = forms.MultipleChoiceField(
                        label="",
                        choices=selectable_choices,
                        required=False,
                        widget=forms.CheckboxSelectMultiple
                    )
                    self.helper.layout.append(Field(field_name, wrapper_class="mb-0 touch-friendly-select"))

                # Container schließen
                self.helper.layout.append(HTML('</div></div>'))

        # --- 2. Events ohne Ticket ---
        if no_ticket_events:
            self.helper.layout.append(HTML('<h6 class="fw-bold mt-4 mb-3">Anmeldungen ohne Ticket</h6>'))

            self.helper.layout.append(HTML('<div class="card mb-3 border-0 shadow-sm"><div class="card-body">'))

            nt_choices = []
            has_locked_items = False

            for item in no_ticket_events:
                label = f"{item.event.name} ({item.event.date.strftime('%d.%m.%Y')})"

                if item.checked:
                    # === BEREITS GEBUCHT (Locked) ===
                    has_locked_items = True
                    html_locked = f"""
                    <div class="form-check mb-2 touch-friendly-locked" data-event-id="{item.event.id}" data-locked="true">
                        <input class="form-check-input" type="checkbox" checked disabled>
                        <label class="form-check-label">
                            {label} <span class="badge bg-secondary ms-1">Bereits dabei</span>
                        </label>
                    </div>
                    """
                    self.helper.layout.append(HTML(html_locked))
                else:
                    # === WÄHLBAR ===
                    nt_choices.append((str(item.event.id), label))

            if nt_choices:
                self.fields['no_ticket_events_dynamic'] = forms.MultipleChoiceField(
                    label="",
                    choices=nt_choices,
                    required=False,
                    widget=forms.CheckboxSelectMultiple,
                    help_text=""
                )
                self.helper.layout.append(Field('no_ticket_events_dynamic', wrapper_class="touch-friendly-select"))
            elif not has_locked_items:
                self.helper.layout.append(
                    HTML('<div class="text-muted small text-center">Keine Events verfügbar.</div>'))

            self.helper.layout.append(HTML('</div></div>'))

        # --- 3. & 4. Sticky Footer ---
        price_html = """
            <div id="price-container" class="alert alert-info text-center fw-bold mb-2 shadow-sm" style="display: none;">
                Gesamtpreis: <span id="total-price">0</span> €
                <div id="discount-badge" class="badge bg-success ms-2" style="display:none;">Rabatt aktiv!</div>
                <div id="price-details" class="small fw-normal mt-1 text-muted"></div>
            </div>
            """

        self.helper.layout.append(
            Div(
                Div(
                    HTML(price_html),
                    Div(
                        HTML(
                            f'<a href="{cancel_url}" class="btn btn-outline-secondary id="btn-cancel" px-3 me-2" style="border-radius: 8px;">Abbrechen</a>'),
                        Submit('submit', 'Auswahl speichern', css_class='btn-primary flex-grow-1 fw-bold py-2',
                               style="border-radius: 8px;"),
                        css_class="d-flex"
                    ),
                    css_class="container"
                ),
                css_class="sticky-bottom bg-white border-top py-3 mt-4 start-0 w-100 shadow-lg"
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        all_tickets = []
        for name, value in cleaned_data.items():
            if name.startswith("group_"):
                all_tickets.extend(value)
        cleaned_data['tickets'] = all_tickets

        if 'no_ticket_events_dynamic' in cleaned_data:
            cleaned_data['no_ticket_events'] = cleaned_data['no_ticket_events_dynamic']

        return cleaned_data
