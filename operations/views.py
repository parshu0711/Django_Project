from core.mixins import CrudCreateView, CrudDetailView, CrudListView, CrudUpdateView

from .models import Equipment, Incident, MaintenanceTask

# ---------------------------------------------------------------- equipment
EQUIPMENT_FIELDS = [
    "station", "name", "kind", "serial_number", "status", "commissioned_on",
    "last_serviced_on", "service_interval_days", "notes",
]


class EquipmentBase:
    model = Equipment
    url_base = "operations:equipment"


class EquipmentList(EquipmentBase, CrudListView):
    title = "Equipment & assets"
    subtitle = "Generators, vehicles, communication and scientific instruments"
    related = ("station",)
    columns = (
        ("Equipment", "name"), ("Station", "station.name"), ("Type", "kind"), ("Status", "status"),
        ("Last serviced", "last_serviced_on"), ("Next service", "next_service_due"), ("Service", "service_state"),
    )
    badge_fields = ("status", "service_state")
    search_fields = ("name", "serial_number", "notes")
    filter_fields = ("kind", "status")


class EquipmentCreate(EquipmentBase, CrudCreateView):
    fields = EQUIPMENT_FIELDS


class EquipmentUpdate(EquipmentBase, CrudUpdateView):
    fields = EQUIPMENT_FIELDS


class EquipmentDetail(EquipmentBase, CrudDetailView):
    badge_fields = ("status",)
    related = ({
        "title": "Maintenance tasks",
        "attr": "tasks",
        "columns": (("Task", "title"), ("Priority", "priority"), ("Status", "status"), ("Due", "due_date"),
                    ("Assigned to", "assigned_to"), ("Completed", "completed_at")),
        "badge_fields": ("priority", "status"),
        "add": ("operations:task_create", "equipment"),
    },)


# -------------------------------------------------------------- maintenance
TASK_FIELDS = ["equipment", "title", "description", "priority", "status", "due_date", "assigned_to"]


class TaskBase:
    model = MaintenanceTask
    url_base = "operations:task"
    station_field = "equipment__station"


class TaskList(TaskBase, CrudListView):
    title = "Maintenance tasks"
    subtitle = "Preventive and breakdown maintenance work orders"
    related = ("equipment", "equipment__station", "assigned_to")
    columns = (
        ("Task", "title"), ("Equipment", "equipment.name"), ("Station", "equipment.station"),
        ("Priority", "priority"), ("Status", "status"), ("Due", "due_date"), ("Assigned to", "assigned_to"),
    )
    badge_fields = ("priority", "status")
    search_fields = ("title", "description", "equipment__name")
    filter_fields = ("priority", "status")


class TaskCreate(TaskBase, CrudCreateView):
    fields = TASK_FIELDS


class TaskUpdate(TaskBase, CrudUpdateView):
    fields = TASK_FIELDS


class TaskDetail(TaskBase, CrudDetailView):
    badge_fields = ("priority", "status")


# ---------------------------------------------------------------- incidents
INCIDENT_FIELDS = [
    "station", "title", "category", "severity", "status", "reported_at", "description", "action_taken",
]


class IncidentBase:
    model = Incident
    url_base = "operations:incident"


class IncidentList(IncidentBase, CrudListView):
    title = "Incidents & alerts"
    subtitle = "Emergencies, failures and automatic sensor alerts"
    related = ("station", "reported_by")
    columns = (
        ("Incident", "title"), ("Station", "station"), ("Category", "category"), ("Severity", "severity"),
        ("Status", "status"), ("Reported", "reported_at"), ("Auto", "auto_generated"), ("Reported by", "reported_by"),
    )
    badge_fields = ("severity", "status")
    search_fields = ("title", "description")
    filter_fields = ("severity", "status", "category")

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.GET.get("open"):
            qs = qs.exclude(status=Incident.Status.RESOLVED)
        return qs


class IncidentCreate(IncidentBase, CrudCreateView):
    fields = INCIDENT_FIELDS
    user_field = "reported_by"
    title = "Report an incident"


class IncidentUpdate(IncidentBase, CrudUpdateView):
    fields = INCIDENT_FIELDS


class IncidentDetail(IncidentBase, CrudDetailView):
    badge_fields = ("severity", "status")
