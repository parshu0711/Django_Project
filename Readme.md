# PolarOps: Remote Management Platform for the Indian Antarctic Research Stations

A Django web platform that lets **NCPOR headquarters (Goa)** and the **station teams** at
**Maitri**, **Bharati** and **Dakshin Gangotri** manage station operations remotely from one place:
live weather and power telemetry, automatic alerts, situation reports, crew and medical records,
stores and resupply, equipment maintenance and research projects.

---

## 1. What you need (requirements)

### Software to install

| Requirement | Version | Why |
|---|---|---|
| **Python** | 3.10 or newer (tested on 3.14) | Runs Django |
| **pip** + **venv** | ships with Python | Installs the packages below |
| **Web browser** | any modern browser | The user interface |
| **Internet access** (development) | - | Fonts, icons, Chart.js and Leaflet load from a CDN; map tiles come from Esri (no key needed) |
| PostgreSQL *(optional)* | 14 or newer | Recommended production database (SQLite is used by default) |

You don't need API keys, paid services or Docker.

### Python packages (`requirements.txt`)

| Package | Purpose |
|---|---|
| `Django` 5.2 / 6.0 | Web framework, ORM, admin panel, authentication |
| `djangorestframework` | REST API for sensors, field devices and integrations |
| `python-dotenv` | Reads configuration from the `.env` file |
| `whitenoise` | Serves static files in production |
| `psycopg[binary]` | PostgreSQL driver (only used when `DB_ENGINE=postgres`) |

### Front-end libraries (loaded from CDN, no install)

Chart.js 4 (telemetry charts), Leaflet 1.9 (station map), Phosphor Icons (light) and Google Fonts
(Unbounded, Instrument Sans, JetBrains Mono).

The interface has no CSS framework. It uses a small hand-written "snow paper" design system:

| File | What it holds |
|---|---|
| `static/css/polarops.css` | Design tokens (palette, type), buttons, fields, tags, tables, the app shell, dashboard instruments, motion |
| `static/css/landing.css` | Landing page and login art direction |
| `static/js/globe.js` | The hand-drawn wireframe "ice dome" globe (canvas 2D, no 3D library) |
| `static/js/fx.js` | Text and hover effects: split reveal, decrypt, rotating text, count-up, magnet, tilt |
| `static/js/ui.js` | Dropdown menus, the mobile drawer, dismissible notices, live clocks |
| `static/js/polarops.js` | Chart and map helpers and the dashboard's live polling |

Every animation stops for visitors who prefer reduced motion.

### Station maps: Google Maps (optional)

Set `GOOGLE_MAPS_API_KEY` in `.env` to show the station maps (landing page and dashboard) with Google
satellite imagery. Without a key, or if Google rejects it, the maps fall back to Leaflet with Esri
basemap tiles (satellite, with a switch to a topographic map), which need no key, so the Google key is
never required.

* The key is sent to the browser, which is normal for the Maps JavaScript API. In Google Cloud Console,
  restrict it to your site's HTTP referrers and to the Maps JavaScript API only.
* Markers use Google's `DEMO_MAP_ID`, which is meant for development. For production, create your own
  Map ID and replace it in `static/js/polarops.js`.
* The Esri fallback tiles are free to use with attribution (shown on the map). For a commercial or
  high-traffic deployment, check Esri's terms of use or set up the Google key instead.

### Hardware (for a real deployment)

* **HQ server:** 2 vCPU, 4 GB RAM and 20 GB disk handles several years of 3-hourly telemetry.
* **Each station:** a local gateway PC or Raspberry Pi that collects AWS and power-plant data and
  pushes it to `/api/weather/` and `/api/power/` over the VSAT link. It buffers readings during
  outages and uploads them in bulk later.

---

## 2. Functional requirements covered

| # | Requirement | Where in the app |
|---|---|---|
| FR1 | Central dashboard showing the live status of every station | **Command dashboard** (`/dashboard/`) |
| FR2 | Weather monitoring: temperature, wind, pressure, humidity, visibility | **Telemetry → Weather** and station charts |
| FR3 | Power and fuel monitoring: diesel generators, solar, wind, load, fuel tank, battery | **Telemetry → Power & fuel** |
| FR4 | Automatic alerts for blizzards, extreme cold, whiteout, low fuel and low battery | `telemetry/alerts.py` creates incidents automatically |
| FR5 | Incident and emergency reporting, with HQ acknowledgement (only HQ can acknowledge) and resolution | **Incidents & alerts** |
| FR6 | Email notification to HQ and the station leader for HIGH/CRITICAL incidents, and when one is escalated | `operations/signals.py` |
| FR7 | Daily situation reports (SITREP) from stations to HQ | **Situation reports** |
| FR8 | Expedition (ISEA) and crew management, including who is on station, on a field trip or in transit | **Members, Expeditions** |
| FR9 | Medical monitoring of expedition members (vitals, fitness for duty); visible only to HQ, station leaders and medical officers | **Medical checks** |
| FR10 | Inventory of fuel, food, medical supplies and spares, with low-stock warnings | **Stock items** |
| FR11 | Audit trail of every stock receipt and issue; stock can't go negative (checked under a row lock and by a database constraint), and the admin can't rewrite movements | **Stock movements** |
| FR12 | Resupply logistics by ship, DROMLAN flight or helicopter | **Shipments** |
| FR13 | Equipment register with service schedule and overdue warnings | **Equipment** |
| FR14 | Maintenance work orders; completing one updates the equipment's service date | **Maintenance** |
| FR15 | Research project and field-log tracking | **Research projects, Field logs** |
| FR16 | Role-based access: HQ sees all stations, station staff see only their own, sensor accounts can only upload telemetry | `core/mixins.py`, `core/api.py`, `core/permissions.py` |
| FR17 | REST API with token authentication for sensors and third-party systems | `/api/` |
| FR18 | CSV export of every list, for reports and offline analysis | **CSV** button on each list |
| FR19 | Full data administration | Django admin at `/admin/` |

### Pages and navigation

* **`/`** is a public landing page. It shows only public facts about the stations (names,
  coordinates, year established), never live operational data.
* **`/accounts/login/`** signs in and goes to the **command dashboard** at `/dashboard/`.
* Inside the app, a top navigation bar groups the modules into menus: Stations, Telemetry, People,
  Logistics, Operations and Science. A bell icon shows the open-incident count, and the account menu
  holds the API link, the admin panel (staff only) and sign-out. On phones the bar collapses into a menu
  button.

### Non-functional requirements

* **Low bandwidth:** pages are server-rendered and light. The dashboard polls one small JSON
  endpoint (`/api/live/`) every 60 s instead of reloading the page.
* **Low bandwidth:** the dashboard stops polling while its browser tab is hidden.
* **Intermittent connectivity:** the API accepts bulk uploads (store-and-forward). Uploads are
  idempotent: a reading already stored for the same station and time is skipped, so a gateway can
  resend its whole buffer after a dropped link. Alert emails are sent after the record is saved, with a
  timeout (`EMAIL_TIMEOUT`), so a mail outage never blocks or hangs data entry. The dashboard keeps the
  last known values when the link drops.
* **Security:** login is required everywhere. Every page and API call is filtered by station, a
  sensor token can only upload readings for its own station (and nothing else), the token endpoint is
  rate limited, CSV exports are protected against spreadsheet formula injection, and CSRF protection is on.
  The app refuses to start without a real `DJANGO_SECRET_KEY` when debug is off, and reports an error if
  demo mode is left on.
* **Duplicate-alert control:** the same automatic alert isn't raised twice within 6 hours, and readings
  older than that (backfilled after an outage) are stored without raising alerts.
* **Portability:** SQLite for development, PostgreSQL for production, switched with one setting.

---

## 3. Architecture

```
 Station AWS / power plant ──► gateway ──(VSAT, Token auth)──► /api/weather/  /api/power/
                                                                     │
                                                       alert rules (telemetry/alerts.py)
                                                                     │
                              HQ & station users ◄── Django web app ─┴─► Incident + email
                                    (browser)          │
                                                   Database
                                           (SQLite / PostgreSQL)
```

| Django app | Models |
|---|---|
| `accounts` | `User` with role (HQ admin, station leader, scientist, engineer, medical, logistics, sensor) and station |
| `stations` | `Station`, `SitRep` |
| `personnel` | `Expedition`, `Member`, `MedicalCheck` |
| `inventory` | `Item`, `StockMovement`, `Shipment` |
| `operations` | `Equipment`, `MaintenanceTask`, `Incident` |
| `telemetry` | `WeatherReading`, `PowerReading`, alert rules |
| `research` | `Project`, `FieldLog` |
| `core` | dashboard, shared CRUD views, template tags, REST API, management commands |

---

## 4. Setup (Windows PowerShell)

```powershell
cd <project folder>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env            # optional: edit settings
python manage.py migrate
python manage.py seed_demo        # loads demo stations, crew, stores, telemetry ...
python manage.py runserver
```

Open http://127.0.0.1:8000 for the landing page, or go straight to http://127.0.0.1:8000/dashboard/.
On macOS or Linux, activate with `source .venv/bin/activate`.

### Running the tests

```powershell
python manage.py test
```

The suite (154 tests, a few seconds) runs against a throwaway test database, so your demo
data is never touched. It uses a fast password hasher while testing. It covers:

| Area | File |
|---|---|
| Landing page, dashboard, top navigation, every list/form page, CSV export | `core/tests/test_pages.py` |
| Station scoping, HQ-only permissions and medical confidentiality | `core/tests/test_scoping.py` |
| REST API: tokens, idempotent bulk uploads, filters, sensor-only access, cross-station protection | `core/tests/test_api.py` |
| Template helpers, `seed_demo`, `simulate_telemetry`, system checks | `core/tests/test_tags_and_commands.py` |
| Automatic alert rules, de-duplication, backfilled readings, one reading per station and time | `telemetry/tests.py` |
| Incident emails and escalation, HQ-only acknowledgement, maintenance completion, service schedule | `operations/tests.py` |
| Stock movements, the no-negative-stock rule and the read-only admin audit trail | `inventory/tests.py` |
| Login, logout and user roles | `accounts/tests.py` |
| SITREP, medical and field-log authorship | `stations/tests.py` |

Shared test fixtures live in `core/testing.py`.

For development, `pip install -r requirements-dev.txt` adds `ruff` (lint: `ruff check .`) and
`coverage`. GitHub Actions (`.github/workflows/ci.yml`) runs the lint, `manage.py check`, a
migrations check and the tests on Python 3.10 and 3.12 for every push and pull request.

### Demo logins

Every demo account uses the password **`Antarctica@2026`**.

| Username | Role | Sees |
|---|---|---|
| `hq_admin` | HQ administrator (superuser, admin panel) | All stations |
| `maitri_leader` | Station leader | Maitri only |
| `bharati_leader` | Station leader | Bharati only |
| `maitri_doctor` | Medical officer | Maitri only |
| `bharati_engineer` | Engineer | Bharati only |
| `maitri_scientist` | Scientist | Maitri only |

#### Switching roles quickly (demo mode)

To explore the site as different roles without typing passwords:

* **Login page:** under the form, *Or try a demo account* signs you in with one click.
* **Inside the app:** open your name at the top right. *Switch demo account* lists every demo role
  (HQ admin, station leaders, medical officer, engineer, scientist), and a click switches straight to it.
  Your current account has a tick.

This only works for the six seeded demo accounts above, and only while `DEMO_MODE` is on. It defaults
to the value of `DJANGO_DEBUG`. **Set `DEMO_MODE=False` (or `DJANGO_DEBUG=False`) on any real deployment**,
otherwise anyone who can reach the site could sign in as the HQ administrator.

`seed_demo` also creates the sensor accounts `sensor_maitri` and `sensor_bharati` (role *Sensor*:
no password, no web access, API uploads only) and prints their API tokens. Run `python manage.py seed_demo --reset` to reload clean demo data (this
generates new tokens).

### Simulating a live sensor feed

```powershell
python manage.py simulate_telemetry --interval 30      # new readings every 30 s
python manage.py simulate_telemetry --storm MAI        # force a blizzard at Maitri -> automatic alert
```

Keep the dashboard open: values refresh every minute, and alert emails print in the
`runserver` terminal because the console email backend is the default.

---

## 5. Using PostgreSQL instead of SQLite

1. Create a database: `createdb polarops` (or use pgAdmin).
2. In `.env` set:
   ```
   DB_ENGINE=postgres
   DB_NAME=polarops
   DB_USER=postgres
   DB_PASSWORD=<your password>
   DB_HOST=localhost
   DB_PORT=5432
   ```
3. Run `python manage.py migrate` and then `python manage.py seed_demo`.

---

## 6. REST API

Authenticate with a session (when logged in through the browser) or a token header:
`Authorization: Token <key>`. Get a token with `POST /api/auth/token/` using
`{"username": "...", "password": "..."}`, or run `python manage.py drf_create_token <username>`.

| Method | Endpoint | Notes |
|---|---|---|
| GET | `/api/live/` | Latest weather, power and open-incident count per station |
| GET | `/api/stations/` | Stations visible to the user |
| GET, POST | `/api/weather/` | Filters: `?station=MAI&since=2026-11-19T00:00:00Z` (an invalid `since` is a 400). POST accepts one object or a list |
| GET, POST | `/api/power/` | Same filters and bulk upload |
| GET, POST, PATCH | `/api/incidents/` | `?open=1` for unresolved incidents. Only HQ can set `status` to `ACKNOWLEDGED` |
| GET | `/api/inventory/` | `?low=1` for low-stock items |

Example sensor upload:

```bash
curl -X POST http://127.0.0.1:8000/api/weather/ \
  -H "Authorization: Token <sensor token>" -H "Content-Type: application/json" \
  -d '[{"station":"BHA","recorded_at":"2026-11-20T06:00:00Z","temperature_c":-12.4,"wind_speed_kmh":64,"pressure_hpa":972}]'
```

A list upload answers `201` with `{"created": n, "skipped": m, "results": [...]}`. Readings whose
station and `recorded_at` are already stored are skipped, so always send `recorded_at` from the gateway
and resend the whole buffer after a failed upload. Station codes are case-insensitive.

Sensor accounts (role *Sensor*) can only `POST` to `/api/weather/` and `/api/power/`; every other
endpoint answers 403. `POST /api/auth/token/` is limited to `API_RATE_TOKEN` (default 10/min) per
client, and every user to `API_RATE_USER` (default 600/min).

## 7. Automatic alert rules

Thresholds are set in `.env`:

| Rule | Default | Incident raised |
|---|---|---|
| Wind speed ≥ `ALERT_WIND_KMH` | 100 km/h | Blizzard / high-wind warning (CRITICAL at 1.5× the limit) |
| Temperature ≤ `ALERT_TEMP_C` | −45 °C | Extreme cold warning |
| Visibility < `ALERT_VISIBILITY_KM` | 0.2 km | Whiteout conditions |
| Fuel ≤ `ALERT_FUEL_PCT` | 20 % | Low fuel reserve (CRITICAL at half the limit) |
| Battery ≤ `ALERT_BATTERY_PCT` | 15 % | Battery bank critically low |

The dashboard and station charts draw these same thresholds as dashed lines. Readings recorded more than
6 hours ago (a backlog uploaded after an outage) are stored but don't raise alerts.

---

## 8. Production checklist

* Set `DJANGO_DEBUG=False`, a long random `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` (plus
  `DJANGO_CSRF_TRUSTED_ORIGINS` for your HTTPS origin). The app won't start with the placeholder key.
* Make sure `DEMO_MODE` is off (it is when `DJANGO_DEBUG=False`, unless you set it; `manage.py check`
  reports `polarops.E001` otherwise), and delete or re-password the demo accounts.
* Run `python manage.py check --deploy` and fix what it reports.
* Use PostgreSQL and run `python manage.py collectstatic`.
* Serve with gunicorn on Linux (waitress on Windows; both are listed, commented out, in
  `requirements.txt`) behind nginx with HTTPS. Set `BEHIND_HTTPS_PROXY=True` when nginx terminates TLS,
  and raise `SECURE_HSTS_SECONDS` once HTTPS works.
* Set the SMTP settings in `.env` so alert emails are actually delivered, and set `LOG_FILE` to keep a log.
* For stations with very limited bandwidth, host the CDN assets locally under `static/`.

## 9. Possible extensions

Offline-first PWA for station tablets, SMS or Iridium alerts, Celery for scheduled reports,
WebSockets for push updates, satellite-imagery layers on the map, and ML forecasting of fuel
consumption.

> Station names, coordinates and founding years are public information. All people, readings,
> stock levels and incidents in the demo data are fictional.
