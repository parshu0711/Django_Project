"""
Load realistic demo data:  python manage.py seed_demo  [--reset]

Station names, locations and founding years are public facts; all people,
readings, stock levels and incidents are fictional demo data.
"""
import math
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from rest_framework.authtoken.models import Token

from inventory.models import Item, Shipment, StockMovement
from operations.models import Equipment, Incident, MaintenanceTask
from personnel.models import Expedition, MedicalCheck, Member
from research.models import FieldLog, Project
from stations.models import SitRep, Station
from telemetry.models import PowerReading, WeatherReading

DEMO_PASSWORD = "Antarctica@2026"

DEMO_USERS = [
    # username, first, last, role, station code, superuser
    ("hq_admin", "Anita", "Rao", "HQ_ADMIN", None, True),
    ("maitri_leader", "Rajesh", "Kumar", "STATION_LEADER", "MAI", False),
    ("bharati_leader", "Sunita", "Nair", "STATION_LEADER", "BHA", False),
    ("maitri_doctor", "Arjun", "Mehta", "MEDICAL", "MAI", False),
    ("bharati_engineer", "Vikram", "Singh", "ENGINEER", "BHA", False),
    ("maitri_scientist", "Priya", "Sharma", "SCIENTIST", "MAI", False),
]
SENSOR_USERS = [("sensor_maitri", "MAI"), ("sensor_bharati", "BHA")]

STATIONS = [
    dict(
        name="Maitri", code="MAI", status=Station.Status.ACTIVE,
        region="Schirmacher Oasis, Dronning Maud Land",
        latitude=Decimal("-70.766667"), longitude=Decimal("11.733333"), established=1989,
        capacity_winter=25, capacity_summer=65, communications="VSAT (primary), INMARSAT, HF radio",
        description="India's second permanent research station, on the ice-free Schirmacher Oasis about "
                    "100 km from the coast. Year-round programmes in meteorology, glaciology, geology, "
                    "biology and human physiology.",
    ),
    dict(
        name="Bharati", code="BHA", status=Station.Status.ACTIVE,
        region="Larsemann Hills, Prydz Bay",
        latitude=Decimal("-69.408889"), longitude=Decimal("76.187222"), established=2012,
        capacity_winter=25, capacity_summer=72, communications="VSAT satellite link, INMARSAT, HF radio",
        description="India's third and most modern research station, built from shipping-container modules "
                    "on the Larsemann Hills coast. Focus on oceanography, geology, ionosphere and satellite "
                    "data reception.",
    ),
    dict(
        name="Dakshin Gangotri", code="DKG", status=Station.Status.INACTIVE,
        region="Princess Astrid Coast, Dronning Maud Land",
        latitude=Decimal("-70.083333"), longitude=Decimal("12.000000"), established=1983,
        capacity_winter=0, capacity_summer=0, communications="",
        description="India's first Antarctic base, built in 1983. It was buried in ice and decommissioned in "
                    "1990, and has since served as a supply base and transit camp.",
    ),
]

CREW = {
    "MAI": [
        ("Rajesh Kumar", "Station Leader", "NCPOR"),
        ("Dr Arjun Mehta", "Medical Officer", "Armed Forces Medical Services"),
        ("Dr Priya Sharma", "Glaciologist", "NCPOR"),
        ("Amit Verma", "Meteorologist", "IMD"),
        ("Sandeep Yadav", "Electrical Engineer", "NCPOR"),
        ("Harpreet Gill", "Mechanical Engineer", "NCPOR"),
        ("Kavita Joshi", "Geologist", "GSI"),
        ("Naik Ravi Thapa", "Communications Operator", "Indian Army"),
        ("Hav. Manoj Pillai", "Cook / Stores", "Indian Army"),
        ("Dr Neha Kulkarni", "Biologist", "NCPOR"),
        ("Rohit Bansal", "Vehicle Mechanic", "NCPOR"),
    ],
    "BHA": [
        ("Sunita Nair", "Station Leader", "NCPOR"),
        ("Dr Farhan Qureshi", "Medical Officer", "Armed Forces Medical Services"),
        ("Vikram Singh", "Electrical Engineer", "NCPOR"),
        ("Deepa Iyer", "Oceanographer", "NCPOR"),
        ("Arvind Reddy", "Space Physicist", "IIG Mumbai"),
        ("Suresh Patil", "Satellite Ground Station Engineer", "NRSC"),
        ("Meera Das", "Meteorologist", "IMD"),
        ("Naik Gurdeep Singh", "Communications Operator", "Indian Army"),
        ("Hav. Prakash Rawat", "Cook / Stores", "Indian Army"),
        ("Anil Chauhan", "Mechanical Engineer", "NCPOR"),
    ],
}

ITEMS = [
    # name, category, unit, quantity, minimum, location
    ("Arctic-grade diesel (SKA)", "FUEL", "litres", 412000, 150000, "Tank farm"),
    ("Aviation turbine fuel", "FUEL", "litres", 38000, 20000, "Helipad fuel store"),
    ("Engine lubricant oil", "FUEL", "litres", 1800, 600, "Garage"),
    ("Rice", "FOOD", "kg", 3200, 1500, "Dry store A"),
    ("Wheat flour (atta)", "FOOD", "kg", 2900, 1500, "Dry store A"),
    ("Pulses (dal)", "FOOD", "kg", 1100, 600, "Dry store A"),
    ("Frozen vegetables", "FOOD", "kg", 950, 800, "Cold store"),
    ("Fresh eggs", "FOOD", "dozen", 120, 150, "Cold store"),
    ("Medical oxygen cylinders", "MEDICAL", "cylinders", 14, 10, "Medical bay"),
    ("Broad-spectrum antibiotics", "MEDICAL", "courses", 60, 40, "Medical bay"),
    ("Trauma / first-aid kits", "MEDICAL", "kits", 22, 12, "Medical bay"),
    ("Generator fuel filter sets", "SPARES", "sets", 6, 8, "Workshop"),
    ("Snow-cat track pads", "SPARES", "units", 40, 24, "Garage"),
    ("VSAT LNB spare", "SPARES", "units", 2, 1, "Comms room"),
    ("Liquid nitrogen", "SCIENTIFIC", "litres", 240, 100, "Lab store"),
    ("Sample bags & vials", "SCIENTIFIC", "packs", 75, 30, "Lab store"),
    ("Polar survival bags", "SAFETY", "units", 30, 25, "Field store"),
    ("Fire extinguisher refills", "SAFETY", "units", 18, 12, "Safety store"),
]

EQUIPMENT = [
    # name, kind, status, days since service, interval
    ("DG set #1 (250 kVA)", "GENERATOR", "OPERATIONAL", 20, 60),
    ("DG set #2 (250 kVA)", "GENERATOR", "MAINTENANCE", 75, 60),
    ("DG set #3 standby (125 kVA)", "GENERATOR", "STANDBY", 40, 90),
    ("Solar PV array (30 kW)", "RENEWABLE", "OPERATIONAL", 100, 180),
    ("Wind turbine (10 kW)", "RENEWABLE", "OPERATIONAL", 130, 120),
    ("PistenBully snow-cat #1", "VEHICLE", "OPERATIONAL", 30, 90),
    ("Hagglunds BV206", "VEHICLE", "FAULTY", 160, 90),
    ("VSAT terminal", "COMMS", "OPERATIONAL", 45, 180),
    ("HF radio set", "COMMS", "OPERATIONAL", 60, 180),
    ("Central heating boiler", "HVAC", "OPERATIONAL", 25, 30),
    ("RO / snow-melt water plant", "WATER", "OPERATIONAL", 12, 30),
    ("Automatic weather station", "SCIENTIFIC", "OPERATIONAL", 50, 120),
]

PROJECTS = {
    "MAI": [
        ("MAI-GL-01", "Mass balance of the Dronning Maud Land ice sheet margin", "GLACIOLOGY",
         "Dr Priya Sharma", "NCPOR, Goa"),
        ("MAI-AT-02", "Ozone, UV and aerosol monitoring at Maitri", "ATMOSPHERIC", "Amit Verma",
         "India Meteorological Department"),
        ("MAI-BI-03", "Lichen and moss biodiversity of Schirmacher Oasis lakes", "BIOLOGY",
         "Dr Neha Kulkarni", "NCPOR, Goa"),
        ("MAI-HP-04", "Physiological and psychological adaptation during winter-over", "HUMAN",
         "Dr Arjun Mehta", "Defence Institute of Physiology & Allied Sciences"),
    ],
    "BHA": [
        ("BHA-OC-01", "Coastal ocean dynamics and sea-ice of Prydz Bay", "OCEANOGRAPHY", "Deepa Iyer",
         "NCPOR, Goa"),
        ("BHA-SP-02", "Polar ionosphere and geomagnetic observatory", "SPACE", "Arvind Reddy",
         "Indian Institute of Geomagnetism"),
        ("BHA-GE-03", "GPS geodesy and crustal deformation of the Larsemann Hills", "GEOLOGY",
         "Sunita Nair", "Geological Survey of India"),
    ],
}


class Command(BaseCommand):
    help = "Load realistic demo data for the Indian Antarctic research stations."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo data before loading")

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        if reset:
            self._reset()
        elif Station.objects.exists():
            self.stdout.write(self.style.WARNING("Data already present - run with --reset to reload the demo."))
            return

        random.seed(45)
        self.now = timezone.now().replace(minute=0, second=0, microsecond=0)
        self.today = timezone.localdate()

        stations = {s["code"]: Station.objects.create(**s) for s in STATIONS}
        users = self._users(stations)
        expeditions = self._expeditions()
        members = self._members(stations, expeditions, users)
        self._medical(members, users)
        self._inventory(stations, users)
        self._equipment(stations, users)
        self._projects(stations, expeditions, users)
        self._sitreps(stations, members, users)
        self._incidents(stations, users)
        self._telemetry(stations)

        self.stdout.write(self.style.SUCCESS("\nDemo data loaded."))
        self.stdout.write(f"All demo accounts use the password: {DEMO_PASSWORD}")
        for username, *_ in DEMO_USERS:
            self.stdout.write(f"  - {username}")
        self.stdout.write("\nSensor API tokens (Authorization: Token <key>):")
        for username, _ in SENSOR_USERS:
            token = Token.objects.get(user__username=username)
            self.stdout.write(f"  - {username}: {token.key}")

    # ------------------------------------------------------------------
    def _reset(self):
        User = get_user_model()
        Member.objects.all().delete()
        Station.objects.all().delete()          # cascades to most station data
        Expedition.objects.all().delete()
        names = [u[0] for u in DEMO_USERS] + [u[0] for u in SENSOR_USERS]
        User.objects.filter(username__in=names).delete()
        self.stdout.write("Existing demo data removed.")

    def _users(self, stations):
        User = get_user_model()
        users = {}
        for username, first, last, role, code, superuser in DEMO_USERS:
            user = User(
                username=username, first_name=first, last_name=last, role=role,
                station=stations.get(code), email=f"{username}@example.org",
                is_staff=superuser, is_superuser=superuser,
            )
            user.set_password(DEMO_PASSWORD)
            user.save()
            users[username] = user
        for username, code in SENSOR_USERS:
            sensor = User(username=username, first_name="AWS gateway", last_name=stations[code].name,
                          role=User.Role.SENSOR, station=stations[code])
            sensor.set_unusable_password()
            sensor.save()
            Token.objects.create(user=sensor)
        return users

    def _expeditions(self):
        return {
            "ISEA-45": Expedition.objects.create(
                code="ISEA-45", name="45th Indian Scientific Expedition to Antarctica",
                start_date=date(2025, 11, 10), end_date=date(2027, 3, 15), leader="Dr S. Menon",
                notes="Wintering teams at Maitri and Bharati; summer team returned in March 2026.",
            ),
            "ISEA-46": Expedition.objects.create(
                code="ISEA-46", name="46th Indian Scientific Expedition to Antarctica",
                start_date=date(2026, 11, 1), leader="Dr K. Bhattacharya",
                notes="Summer team arriving via DROMLAN flights and chartered ice-class vessel.",
            ),
        }

    def _members(self, stations, expeditions, users):
        links = {"Rajesh Kumar": "maitri_leader", "Sunita Nair": "bharati_leader", "Dr Arjun Mehta": "maitri_doctor",
                 "Vikram Singh": "bharati_engineer", "Dr Priya Sharma": "maitri_scientist"}
        blood = [b for b, _ in Member.BloodGroup.choices]
        members = []
        for code, crew in CREW.items():
            for i, (name, designation, org) in enumerate(crew):
                status = Member.Status.ON_STATION
                if i in (4, 6) and code == "MAI":
                    status = Member.Status.ON_FIELD
                members.append(Member.objects.create(
                    full_name=name, station=stations[code], expedition=expeditions["ISEA-45"],
                    user=users.get(links.get(name)), designation=designation, organisation=org,
                    team=Member.Team.WINTER, status=status, blood_group=random.choice(blood),
                    emergency_contact=f"Family contact via NCPOR Goa · +91 832 252 {5000 + i:04d}",
                    arrival_date=date(2025, 12, 2) if code == "MAI" else date(2025, 12, 18),
                ))
        # summer team of ISEA-46 on its way
        for name, designation, org, code in [
            ("Dr Ananya Ghosh", "Glaciologist", "IISc Bengaluru", "MAI"),
            ("Karan Malhotra", "Drilling Engineer", "NCPOR", "MAI"),
            ("Dr Lakshmi Menon", "Marine Biologist", "CMLRE Kochi", "BHA"),
        ]:
            members.append(Member.objects.create(
                full_name=name, station=stations[code], expedition=expeditions["ISEA-46"], designation=designation,
                organisation=org, team=Member.Team.SUMMER, status=Member.Status.IN_TRANSIT,
                blood_group=random.choice(blood), arrival_date=self.today + timedelta(days=9),
            ))
        return members

    def _medical(self, members, users):
        examiner = users["maitri_doctor"]
        for m in members:
            if m.status == Member.Status.IN_TRANSIT:
                continue
            for weeks in (5, 1):
                fit = not (m.full_name == "Rohit Bansal" and weeks == 1)
                MedicalCheck.objects.create(
                    member=m, checked_on=self.today - timedelta(weeks=weeks),
                    examiner=examiner if m.station.code == "MAI" else None,
                    bp_systolic=random.randint(112, 134), bp_diastolic=random.randint(72, 88),
                    pulse=random.randint(62, 84), spo2=random.randint(94, 99),
                    temperature_c=Decimal(str(round(random.uniform(36.4, 37.1), 1))),
                    weight_kg=Decimal(str(round(random.uniform(58, 88), 1))),
                    fit_for_duty=fit,
                    notes="Mild frostbite on left hand fingers, light duty for 5 days." if not fit else "",
                )

    def _inventory(self, stations, users):
        for code, factor in (("MAI", 1.0), ("BHA", 1.2)):
            st = stations[code]
            for name, cat, unit, qty, minimum, location in ITEMS:
                q = qty * factor
                if code == "MAI" and name == "Medical oxygen cylinders":
                    q = 9
                if code == "BHA" and name == "Frozen vegetables":
                    q = 610
                item = Item.objects.create(
                    station=st, name=name, category=cat, unit=unit,
                    quantity=Decimal(str(round(q))), min_threshold=Decimal(str(minimum)), storage_location=location,
                )
                if cat in ("FOOD", "FUEL"):
                    by = users["maitri_leader"] if code == "MAI" else users["bharati_leader"]
                    for days in (6, 3, 1):
                        StockMovement.objects.create(
                            item=item, kind=StockMovement.Kind.OUT,
                            quantity=Decimal(str(round(float(item.quantity) * 0.004, 2))),
                            note="Daily consumption", performed_by=by,
                            created_at=self.now - timedelta(days=days),
                        )
                        item.refresh_from_db()

        Shipment.objects.create(
            reference="SHP-46-01", station=stations["MAI"], mode=Shipment.Mode.SHIP,
            carrier="Chartered ice-class cargo vessel", origin="Cape Town",
            departure_date=self.today - timedelta(days=6), eta=self.today + timedelta(days=12),
            status=Shipment.Status.IN_TRANSIT, weight_tonnes=Decimal("1450"),
            cargo_summary="Arctic-grade diesel (900 kL), frozen and dry rations, construction material, "
                          "generator spares, scientific equipment for ISEA-46.",
        )
        Shipment.objects.create(
            reference="AIR-46-03", station=stations["MAI"], mode=Shipment.Mode.AIR,
            carrier="DROMLAN intercontinental flight", origin="Cape Town",
            departure_date=self.today + timedelta(days=8), eta=self.today + timedelta(days=9),
            status=Shipment.Status.PLANNED, weight_tonnes=Decimal("3.2"),
            cargo_summary="ISEA-46 summer team (12 members), medical oxygen, fresh food, mail.",
        )
        Shipment.objects.create(
            reference="SHP-46-02", station=stations["BHA"], mode=Shipment.Mode.SHIP,
            carrier="Chartered ice-class cargo vessel", origin="Cape Town",
            departure_date=self.today - timedelta(days=2), eta=self.today + timedelta(days=24),
            status=Shipment.Status.DELAYED, weight_tonnes=Decimal("980"),
            cargo_summary="Fuel, rations, replacement wind turbine blades. Delayed by heavy pack ice in Prydz Bay.",
        )
        Shipment.objects.create(
            reference="SHP-45-04", station=stations["BHA"], mode=Shipment.Mode.HELI,
            carrier="Ship-borne helicopter", origin="Vessel anchorage",
            departure_date=date(2026, 2, 20), eta=date(2026, 2, 21), status=Shipment.Status.DELIVERED,
            weight_tonnes=Decimal("12.5"), cargo_summary="End-of-season resupply for the wintering team.",
        )

    def _equipment(self, stations, users):
        for code in ("MAI", "BHA"):
            st = stations[code]
            for name, kind, status, since, interval in EQUIPMENT:
                if code == "BHA" and name.startswith("Hagglunds"):
                    status = "OPERATIONAL"
                eq = Equipment.objects.create(
                    station=st, name=name, kind=kind, status=status,
                    serial_number=f"{code}-{kind[:3]}-{random.randint(1000, 9999)}",
                    commissioned_on=date(2012 if code == "BHA" else 2010, 3, 1),
                    last_serviced_on=self.today - timedelta(days=since), service_interval_days=interval,
                )
                engineer = users["bharati_engineer"] if code == "BHA" else users["maitri_leader"]
                if status == "MAINTENANCE":
                    MaintenanceTask.objects.create(
                        equipment=eq, title="Replace turbocharger and coolant pump", priority="HIGH",
                        status="IN_PROGRESS", due_date=self.today + timedelta(days=2), assigned_to=engineer,
                        description="Overheating observed during peak load. Spares drawn from workshop.",
                    )
                if status == "FAULTY":
                    MaintenanceTask.objects.create(
                        equipment=eq, title="Diagnose transmission failure", priority="MEDIUM",
                        status="OPEN", due_date=self.today + timedelta(days=10), assigned_to=engineer,
                        description="Vehicle will not engage gear. Spare gearbox requested on SHP-46-01.",
                    )
                if kind == "HVAC":
                    MaintenanceTask.objects.create(
                        equipment=eq, title="Monthly burner cleaning", priority="LOW", status="OPEN",
                        due_date=self.today + timedelta(days=5), assigned_to=engineer,
                    )
                if kind == "WATER":
                    MaintenanceTask.objects.create(
                        equipment=eq, title="Replace RO membranes", priority="MEDIUM", status="DONE",
                        due_date=self.today - timedelta(days=12), assigned_to=engineer,
                    )

    def _projects(self, stations, expeditions, users):
        for code, projects in PROJECTS.items():
            for pcode, title, discipline, pi, inst in projects:
                project = Project.objects.create(
                    code=pcode, title=title, station=stations[code], expedition=expeditions["ISEA-45"],
                    discipline=discipline, principal_investigator=pi, institution=inst,
                    status=Project.Status.ACTIVE, start_date=date(2025, 12, 15),
                    objectives="Continue the long-term observation series and transmit summary data to "
                               "NCPOR HQ weekly over the satellite link.",
                )
                for days, activity, loc in [
                    (6, "Routine observations and instrument calibration.", "Station lab"),
                    (2, "Field sampling trip with snow-cat support; all members returned safely.", "Field site 3"),
                ]:
                    FieldLog.objects.create(
                        project=project, log_date=self.today - timedelta(days=days), location=loc,
                        activity=activity, data_collected="Raw data backed up to station NAS and queued for upload.",
                        author=users["maitri_scientist"] if code == "MAI" else users["bharati_leader"],
                    )

    def _sitreps(self, stations, members, users):
        crew = {code: sum(1 for m in members if m.station.code == code and m.status != Member.Status.IN_TRANSIT)
                for code in ("MAI", "BHA")}
        for code, leader in (("MAI", "maitri_leader"), ("BHA", "bharati_leader")):
            for days in range(6, -1, -1):
                status = SitRep.Status.GREEN
                issues = ""
                if code == "MAI" and days <= 2:
                    status = SitRep.Status.AMBER
                    issues = "DG set #2 under repair; station running on DG #1 and renewables."
                if code == "BHA" and days == 0:
                    status = SitRep.Status.AMBER
                    issues = "High winds since early morning; all outdoor work suspended."
                SitRep.objects.create(
                    station=stations[code], report_date=self.today - timedelta(days=days), overall_status=status,
                    personnel_on_station=crew[code],
                    weather_summary=random.choice(["Clear, light winds", "Overcast, moderate winds",
                                                   "Snow showers", "Partly cloudy"]),
                    activities="Routine station upkeep, scientific observations as per schedule, "
                               "daily radio check with HQ completed.",
                    issues=issues,
                    requests_to_hq="Confirm ETA of SHP-46-01." if days == 0 else "",
                    author=users[leader],
                )

    def _incidents(self, stations, users):
        rows = [
            ("MAI", "DG set #2 overheating", "EQUIPMENT", "HIGH", "ACKNOWLEDGED", 2,
             "Coolant temperature alarm on DG set #2 during peak load. Generator shut down, load moved to DG #1."),
            ("MAI", "Minor frostbite during field trip", "MEDICAL", "MEDIUM", "RESOLVED", 7,
             "Vehicle mechanic reported numbness in fingers after a 6 h field trip. Treated at the medical bay."),
            ("MAI", "VSAT link outage (4 h)", "COMMS", "MEDIUM", "RESOLVED", 4,
             "Satellite link lost due to snow on the dish. Cleared and realigned; HF radio used meanwhile."),
            ("BHA", "Small diesel leak near tank farm", "ENVIRONMENT", "HIGH", "OPEN", 1,
             "Approximately 20 litres leaked from a flange joint. Spill kit deployed, contaminated snow being "
             "collected for return to India as per the Madrid Protocol."),
            ("BHA", "Sea-ice crack on the jetty route", "SAFETY", "MEDIUM", "OPEN", 3,
             "New crack observed on the sea-ice route to the jetty. Route closed until survey completed."),
        ]
        objs = []
        for code, title, cat, sev, status, days, desc in rows:
            reported = self.now - timedelta(days=days, hours=3)
            objs.append(Incident(
                station=stations[code], title=title, category=cat, severity=sev, status=status, description=desc,
                reported_at=reported, resolved_at=reported + timedelta(hours=6) if status == "RESOLVED" else None,
                reported_by=users["maitri_leader"] if code == "MAI" else users["bharati_leader"],
                action_taken="Situation handled by station team." if status == "RESOLVED" else "",
            ))
        Incident.objects.bulk_create(objs)   # bulk_create: no alert emails for historical records

    def _telemetry(self, stations):
        profiles = {
            "MAI": dict(temp=-7.5, wind=22, fuel=48.0, lon=11.7),
            "BHA": dict(temp=-4.5, wind=28, fuel=71.0, lon=76.2),
        }
        for code, prof in profiles.items():
            st = stations[code]
            weather, power = [], []
            wind = prof["wind"]
            fuel = prof["fuel"] + 7 * 8 * 0.18
            t = self.now - timedelta(days=7)
            while t < self.now:
                solar_hour = (t.hour + prof["lon"] / 15) % 24
                diurnal = math.cos((solar_hour - 14) / 24 * 2 * math.pi)
                wind = max(3.0, min(95.0, wind + 0.3 * (prof["wind"] - wind) + random.gauss(0, 7)))
                temp = prof["temp"] + 3 * diurnal + random.gauss(0, 1.0) - (wind - prof["wind"]) * 0.05
                weather.append(WeatherReading(
                    station=st, recorded_at=t, temperature_c=round(temp, 1), wind_speed_kmh=round(wind, 1),
                    wind_direction_deg=random.choice([90, 110, 120, 135, 150]),
                    pressure_hpa=round(984 + random.gauss(0, 3) - (wind - prof["wind"]) * 0.25, 1),
                    humidity_pct=round(random.uniform(35, 70), 1),
                    visibility_km=round(max(0.5, 20 - wind / 5 + random.gauss(0, 2)), 1),
                ))
                solar = max(0.0, 22 * math.cos((solar_hour - 12) / 24 * 2 * math.pi) + random.gauss(0, 1.5))
                wind_kw = min(10.0, wind * 0.22)
                load = 82 + random.gauss(0, 4) + (8 if 7 <= solar_hour <= 21 else 0)
                gen = max(25.0, load - solar - wind_kw)
                fuel -= 0.18 + random.gauss(0, 0.02)
                power.append(PowerReading(
                    station=st, recorded_at=t, generator_kw=round(gen, 1), solar_kw=round(solar, 1),
                    wind_kw=round(wind_kw, 1), load_kw=round(load, 1), fuel_level_pct=round(fuel, 1),
                    battery_pct=round(random.uniform(62, 94), 1),
                ))
                t += timedelta(hours=3)
            WeatherReading.objects.bulk_create(weather)
            PowerReading.objects.bulk_create(power)

        # latest live readings go through normal save() so alert rules run:
        # Bharati is hit by a blizzard right now -> automatic CRITICAL/HIGH incident + email to HQ
        WeatherReading.objects.create(
            station=stations["BHA"], recorded_at=self.now, temperature_c=-11.8, wind_speed_kmh=118.0,
            wind_direction_deg=120, pressure_hpa=968.4, humidity_pct=88, visibility_km=0.4,
        )
        PowerReading.objects.create(
            station=stations["BHA"], recorded_at=self.now, generator_kw=78.0, solar_kw=2.1, wind_kw=0.0,
            load_kw=80.1, fuel_level_pct=70.6, battery_pct=71,
        )
        WeatherReading.objects.create(
            station=stations["MAI"], recorded_at=self.now, temperature_c=-6.4, wind_speed_kmh=24.0,
            wind_direction_deg=135, pressure_hpa=986.1, humidity_pct=48, visibility_km=18,
        )
        PowerReading.objects.create(
            station=stations["MAI"], recorded_at=self.now, generator_kw=58.0, solar_kw=17.5, wind_kw=5.3,
            load_kw=80.8, fuel_level_pct=47.7, battery_pct=88,
        )
