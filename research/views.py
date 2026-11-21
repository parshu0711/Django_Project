from core.mixins import CrudCreateView, CrudDetailView, CrudListView, CrudUpdateView

from .models import FieldLog, Project

PROJECT_FIELDS = [
    "code", "title", "station", "expedition", "discipline", "principal_investigator", "institution",
    "status", "start_date", "end_date", "objectives",
]


class ProjectBase:
    model = Project
    url_base = "research:project"


class ProjectList(ProjectBase, CrudListView):
    title = "Research projects"
    subtitle = "Scientific programmes running at the stations"
    related = ("station", "expedition")
    columns = (
        ("Code", "code"), ("Title", "title"), ("Station", "station"), ("Discipline", "discipline"),
        ("PI", "principal_investigator"), ("Institution", "institution"), ("Status", "status"),
    )
    badge_fields = ("status",)
    search_fields = ("code", "title", "principal_investigator", "institution")
    filter_fields = ("discipline", "status")


class ProjectCreate(ProjectBase, CrudCreateView):
    fields = PROJECT_FIELDS


class ProjectUpdate(ProjectBase, CrudUpdateView):
    fields = PROJECT_FIELDS


class ProjectDetail(ProjectBase, CrudDetailView):
    badge_fields = ("status",)
    related = ({
        "title": "Field logs",
        "attr": "logs",
        "columns": (("Date", "log_date"), ("Location", "location"), ("Activity", "activity"),
                    ("Data collected", "data_collected"), ("Author", "author")),
        "add": ("research:log_create", "project"),
    },)


LOG_FIELDS = ["project", "log_date", "location", "activity", "data_collected"]


class LogBase:
    model = FieldLog
    url_base = "research:log"
    station_field = "project__station"


class LogList(LogBase, CrudListView):
    title = "Field logs"
    subtitle = "Daily records of field work, samples and datasets"
    related = ("project", "project__station", "author")
    columns = (
        ("Log", "__str__"), ("Date", "log_date"), ("Project", "project.title"), ("Station", "project.station"),
        ("Location", "location"), ("Author", "author"),
    )
    search_fields = ("activity", "data_collected", "location", "project__title")


class LogCreate(LogBase, CrudCreateView):
    fields = LOG_FIELDS
    user_field = "author"


class LogUpdate(LogBase, CrudUpdateView):
    fields = LOG_FIELDS


class LogDetail(LogBase, CrudDetailView):
    pass
