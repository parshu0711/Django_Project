"""
Reusable class-based views. Every list/form/detail page in the platform is
built from these, so station scoping (HQ sees all stations, station staff see
only their own) is enforced in one place.
"""
import csv

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.db.models import Q
from django.http import HttpResponse
from django.urls import NoReverseMatch, reverse
from django.utils.text import capfirst, slugify
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from stations.models import Station

from .templatetags.polar_tags import format_value, resolve


def model_has_field(model, name):
    try:
        model._meta.get_field(name)
        return True
    except FieldDoesNotExist:
        return False


def style_form(form):
    """Apply Bootstrap classes and HTML5 date pickers to every field."""
    for field in form.fields.values():
        if isinstance(field, forms.DateTimeField):
            field.widget = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
            field.widget.is_required = field.required
        elif isinstance(field, forms.DateField):
            field.widget = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
            field.widget.is_required = field.required
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            css = "form-check-input"
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            css = "form-select"
        else:
            css = "form-control"
        widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()
        if isinstance(widget, forms.Textarea):
            widget.attrs["rows"] = 3


class StationScopedMixin(LoginRequiredMixin):
    station_field = "station"   # lookup path from the model to Station; None = not station specific
    url_base = None             # e.g. "operations:incident" -> incident_list / _create / _detail / _edit
    hq_only_write = False       # only HQ may create / edit
    title = ""

    def scope(self, qs):
        user = self.request.user
        if user.is_hq or not self.station_field:
            return qs
        if not user.station_id:
            return qs.none()
        return qs.filter(**{self.station_field: user.station_id})

    def can_write(self):
        return not self.hq_only_write or self.request.user.is_hq

    def url_name(self, suffix):
        name = f"{self.url_base}_{suffix}"
        for args in ((), (0,)):
            try:
                reverse(name, args=args)
                return name
            except NoReverseMatch:
                continue
        return None


class CrudListView(StationScopedMixin, ListView):
    template_name = "core/list.html"
    paginate_by = 25
    columns = ()            # (label, accessor) pairs; accessor may be dotted: "equipment.station"
    badge_fields = ()       # accessors rendered as coloured status pills
    search_fields = ()
    filter_fields = ()      # model fields with choices, shown as dropdown filters
    related = ()            # select_related paths
    show_station_filter = True
    subtitle = ""

    def get_queryset(self):
        qs = self.scope(super().get_queryset())
        if self.related:
            qs = qs.select_related(*self.related)
        params = self.request.GET
        q = params.get("q", "").strip()
        if q and self.search_fields:
            cond = Q()
            for f in self.search_fields:
                cond |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(cond)
        station = params.get("station", "")
        if station.isdigit() and self.station_field and self.request.user.is_hq:
            qs = qs.filter(**{self.station_field: station})
        for name in self.filter_fields:
            value = params.get(name)
            if value:
                qs = qs.filter(**{name: value})
        return qs

    def get_filters(self):
        filters = []
        for name in self.filter_fields:
            field = self.model._meta.get_field(name)
            filters.append({
                "name": name,
                "label": capfirst(field.verbose_name),
                "choices": field.choices,
                "current": self.request.GET.get(name, ""),
            })
        return filters

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        writable = self.can_write()
        ctx.update(
            title=self.title or capfirst(self.model._meta.verbose_name_plural),
            subtitle=self.subtitle,
            columns=self.columns,
            badge_fields=self.badge_fields,
            filters=self.get_filters(),
            search_enabled=bool(self.search_fields),
            q=self.request.GET.get("q", ""),
            stations=Station.objects.all() if (user.is_hq and self.station_field and self.show_station_filter) else None,
            current_station=self.request.GET.get("station", ""),
            create_name=self.url_name("create") if writable else None,
            edit_name=self.url_name("edit") if writable else None,
            detail_name=self.url_name("detail"),
            total=ctx["paginator"].count if ctx.get("paginator") else len(ctx["object_list"]),
        )
        return ctx

    def render_to_response(self, context, **kwargs):
        if self.request.GET.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{slugify(context["title"])}.csv"'
            writer = csv.writer(response)
            writer.writerow([label for label, _ in self.columns])
            for obj in self.object_list:
                writer.writerow([format_value(resolve(obj, acc)[0]) for _, acc in self.columns])
            return response
        return super().render_to_response(context, **kwargs)


class CrudFormMixin(StationScopedMixin, SuccessMessageMixin):
    template_name = "core/form.html"
    user_field = None   # model FK set to request.user on create, e.g. "reported_by"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not self.can_write():
            raise PermissionDenied("Only HQ administrators can change this record.")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        if not user.is_hq and user.station_id:
            initial.setdefault("station", user.station_id)
        for key, value in self.request.GET.items():   # e.g. ?equipment=4 pre-selects the equipment
            if key in (self.fields or ()):
                initial[key] = value
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        style_form(form)
        self.scope_form(form)
        return form

    def scope_form(self, form):
        """Station staff can only pick records belonging to their own station."""
        user = self.request.user
        if user.is_hq:
            return
        for field in form.fields.values():
            if not isinstance(field, forms.ModelChoiceField):
                continue
            model = field.queryset.model
            if model is Station:
                field.queryset = field.queryset.filter(pk=user.station_id)
            elif model_has_field(model, "station"):
                field.queryset = field.queryset.filter(station_id=user.station_id)

    def form_valid(self, form):
        if self.user_field and form.instance._state.adding and not getattr(form.instance, f"{self.user_field}_id"):
            setattr(form.instance, self.user_field, self.request.user)
        return super().form_valid(form)

    def get_success_message(self, cleaned_data):
        return f"{capfirst(self.model._meta.verbose_name)} “{self.object}” saved."

    def get_success_url(self):
        detail = self.url_name("detail")
        if detail:
            return reverse(detail, args=[self.object.pk])
        return reverse(self.url_name("list"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        list_name = self.url_name("list")
        ctx["list_url"] = reverse(list_name) if list_name else None
        ctx["verbose_name"] = self.model._meta.verbose_name
        return ctx


class CrudCreateView(CrudFormMixin, CreateView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = self.title or f"New {self.model._meta.verbose_name}"
        return ctx


class CrudUpdateView(CrudFormMixin, UpdateView):
    def get_queryset(self):
        return self.scope(super().get_queryset())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Edit {self.object}"
        return ctx


class CrudDetailView(StationScopedMixin, DetailView):
    template_name = "core/detail.html"
    badge_fields = ()
    exclude_fields = ()
    related = ()   # dicts: {"title", "attr", "columns", "badge_fields", "add": ("url name", "fk param")}

    def get_queryset(self):
        return self.scope(super().get_queryset())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = self.object
        blocks = []
        for spec in self.related:
            add_url = None
            if spec.get("add") and self.request.user.is_authenticated:
                name, param = spec["add"]
                add_url = f"{reverse(name)}?{param}={obj.pk}"
            blocks.append({
                "title": spec["title"],
                "columns": spec["columns"],
                "badge_fields": spec.get("badge_fields", ()),
                "rows": getattr(obj, spec["attr"]).all()[: spec.get("limit", 25)],
                "add_url": add_url,
            })
        list_name = self.url_name("list")
        ctx.update(
            title=str(obj),
            verbose_name=self.model._meta.verbose_name,
            badge_fields=self.badge_fields,
            exclude_fields=self.exclude_fields,
            related_blocks=blocks,
            edit_name=self.url_name("edit") if self.can_write() else None,
            list_url=reverse(list_name) if list_name else None,
        )
        return ctx
