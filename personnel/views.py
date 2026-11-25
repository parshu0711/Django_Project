from accounts.models import User
from core.mixins import CrudCreateView, CrudDetailView, CrudListView, CrudUpdateView

from .models import Expedition, MedicalCheck, Member

# ------------------------------------------------------------------- members
MEMBER_FIELDS = [
    "full_name", "station", "expedition", "designation", "organisation", "team", "status",
    "blood_group", "emergency_contact", "arrival_date", "departure_date", "user",
]


class MemberBase:
    model = Member
    url_base = "personnel:member"


class MemberList(MemberBase, CrudListView):
    title = "Expedition members"
    subtitle = "Who is where - on station, on a field trip or in transit"
    related = ("station", "expedition")
    columns = (
        ("Name", "full_name"), ("Station", "station"), ("Expedition", "expedition"), ("Designation", "designation"),
        ("Organisation", "organisation"), ("Team", "team"), ("Status", "status"), ("Blood", "blood_group"),
    )
    badge_fields = ("status",)
    search_fields = ("full_name", "designation", "organisation")
    filter_fields = ("status", "team")


class MemberCreate(MemberBase, CrudCreateView):
    fields = MEMBER_FIELDS


class MemberUpdate(MemberBase, CrudUpdateView):
    fields = MEMBER_FIELDS


class MemberDetail(MemberBase, CrudDetailView):
    badge_fields = ("status",)
    related = ({
        "title": "Medical checks",
        "attr": "medical_checks",
        "columns": (("Date", "checked_on"), ("BP", "blood_pressure"), ("Pulse", "pulse"), ("SpO2 %", "spo2"),
                    ("Weight", "weight_kg"), ("Fit for duty", "fit_for_duty")),
        "add": ("personnel:medical_create", "member"),
    },)

    def get_related(self):
        # medical checks are confidential: only HQ, station leaders and medical officers see them
        return self.related if self.request.user.can_view_medical else ()


# --------------------------------------------------------------- expeditions
EXPEDITION_FIELDS = ["code", "name", "start_date", "end_date", "leader", "notes"]


class ExpeditionBase:
    model = Expedition
    url_base = "personnel:expedition"
    station_field = None
    hq_only_write = True


class ExpeditionList(ExpeditionBase, CrudListView):
    title = "Expeditions"
    subtitle = "Indian Scientific Expeditions to Antarctica (ISEA)"
    columns = (("Code", "code"), ("Name", "name"), ("Start", "start_date"), ("End", "end_date"), ("Leader", "leader"))
    search_fields = ("code", "name", "leader")


class ExpeditionCreate(ExpeditionBase, CrudCreateView):
    fields = EXPEDITION_FIELDS


class ExpeditionUpdate(ExpeditionBase, CrudUpdateView):
    fields = EXPEDITION_FIELDS


class ExpeditionDetail(ExpeditionBase, CrudDetailView):
    related = ({
        "title": "Members",
        "attr": "members",
        "columns": (("Name", "full_name"), ("Station", "station"), ("Designation", "designation"),
                    ("Team", "team"), ("Status", "status")),
        "badge_fields": ("status",),
        "limit": 100,
    },)


# ------------------------------------------------------------ medical checks
MEDICAL_FIELDS = [
    "member", "checked_on", "bp_systolic", "bp_diastolic", "pulse", "spo2",
    "temperature_c", "weight_kg", "fit_for_duty", "notes",
]


class MedicalBase:
    model = MedicalCheck
    url_base = "personnel:medical"
    station_field = "member__station"
    allowed_roles = {User.Role.MEDICAL, User.Role.STATION_LEADER}   # keep in step with User.can_view_medical


class MedicalList(MedicalBase, CrudListView):
    title = "Medical checks"
    subtitle = "Routine health monitoring of expedition members"
    related = ("member", "member__station", "examiner")
    columns = (
        ("Member", "member"), ("Station", "member.station"), ("Date", "checked_on"), ("BP", "blood_pressure"),
        ("Pulse", "pulse"), ("SpO2 %", "spo2"), ("Temp °C", "temperature_c"), ("Fit for duty", "fit_for_duty"),
        ("Examiner", "examiner"),
    )
    search_fields = ("member__full_name", "notes")
    filter_fields = ("fit_for_duty",)


class MedicalCreate(MedicalBase, CrudCreateView):
    fields = MEDICAL_FIELDS
    user_field = "examiner"


class MedicalUpdate(MedicalBase, CrudUpdateView):
    fields = MEDICAL_FIELDS


class MedicalDetail(MedicalBase, CrudDetailView):
    pass
