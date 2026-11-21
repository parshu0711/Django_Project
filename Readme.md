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
| **Internet access** (development) | - | Bootstrap, Chart.js and Leaflet load from a CDN; map tiles come from OpenStreetMap |
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

Bootstrap 5.3 (layout), Bootstrap Icons, Chart.js 4 (telemetry charts), Leaflet 1.9 (station map).

### Station maps: Google Maps (optional)

Set `GOOGLE_MAPS_API_KEY` in `.env` to show the station maps (landing page and dashboard) with Google
satellite imagery. Without a key, or if Google rejects it, the maps fall back to OpenStreetMap through
Leaflet automatically, so the key is never required.

* The key is sent to the browser, which is normal for the Maps JavaScript API. In Google Cloud Console,
  restrict it to your site's HTTP referrers and to the Maps JavaScript API only.
* Markers use Google's `DEMO_MAP_ID`, which is meant for development. For production, create your own
  Map ID and replace it in `static/js/polarops.js`.

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
| FR5 | Incident and emergency reporting, with HQ acknowledgement and resolution | **Incidents & alerts** |
| FR6 | Email notification to HQ and the station leader for HIGH/CRITICAL incidents | `operations/signals.py` |
| FR7 | Daily situation reports (SITREP) from stations to HQ | **Situation reports** |
| FR8 | Expedition (ISEA) and crew management, including who is on station, on a field trip or in transit | **Members, Expeditions** |
| FR9 | Medical monitoring of expedition members (vitals, fitness for duty) | **Medical checks** |
| FR10 | Inventory of fuel, food, medical supplies and spares, with low-stock warnings | **Stock items** |
| FR11 | Audit trail of every stock receipt and issue; stock can't go negative | **Stock movements** |
| FR12 | Resupply logistics by ship, DROMLAN flight or helicopter | **Shipments** |
| FR13 | Equipment register with service schedule and overdue warnings | **Equipment** |
| FR14 | Maintenance work orders; completing one updates the equipment's service date | **Maintenance** |
| FR15 | Research project and field-log tracking | **Research projects, Field logs** |
| FR16 | Role-based access: HQ sees all stations, station staff see only their own | `core/mixins.py`, `core/api.py` |
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
* **Intermittent connectivity:** the API accepts bulk uploads (store-and-forward), alert emails
  never block data entry if mail is down, and the dashboard keeps the last known values when the
  link drops.
* **Security:** login is required everywhere. Every page and API call is filtered by station, a
  sensor token can only write data for its own station, and CSRF protection is on.
* **Duplicate-alert control:** the same automatic alert isn't raised twice within 6 hours.
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
| `accounts` | `User` with role (HQ admin, station leader, scientist, engineer, medical, logistics) and station |
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
cd C:\Users\ASUS\Desktop\Django-Project
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

The suite (103 tests, a few seconds) runs against a throwaway test database, so your demo
data is never touched. It uses a fast password hasher while testing. It covers:

| Area | File |
|---|---|
| Landing page, dashboard, top navigation, every list/form page, CSV export | `core/tests/test_pages.py` |
| Station scoping and HQ-only permissions | `core/tests/test_scoping.py` |
| REST API: tokens, bulk uploads, filters, cross-station protection | `core/tests/test_api.py` |
| Template helpers, `seed_demo`, `simulate_telemetry` | `core/tests/test_tags_and_commands.py` |
| Automatic alert rules and de-duplication | `telemetry/tests.py` |
| Incident emails, maintenance completion, service schedule | `operations/tests.py` |
| Stock movements and the no-negative-stock rule | `inventory/tests.py` |
| Login, logout and user roles | `accounts/tests.py` |
| SITREP, medical and field-log authorship | `stations/tests.py` |

Shared test fixtures live in `core/testing.py`.

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

`seed_demo` also creates the sensor accounts `sensor_maitri` and `sensor_bharati` and prints
their API tokens. Run `python manage.py seed_demo --reset` to reload clean demo data (this
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
| GET, POST | `/api/weather/` | Filters: `?station=MAI&since=2026-11-19T00:00:00Z`. POST accepts one object or a list |
| GET, POST | `/api/power/` | Same filters and bulk upload |
| GET, POST, PATCH | `/api/incidents/` | `?open=1` for unresolved incidents |
| GET | `/api/inventory/` | `?low=1` for low-stock items |

Example sensor upload:

```bash
curl -X POST http://127.0.0.1:8000/api/weather/ \
  -H "Authorization: Token <sensor token>" -H "Content-Type: application/json" \
  -d '[{"station":"BHA","temperature_c":-12.4,"wind_speed_kmh":64,"pressure_hpa":972}]'
```

## 7. Automatic alert rules

Thresholds are set in `.env`:

| Rule | Default | Incident raised |
|---|---|---|
| Wind speed ≥ `ALERT_WIND_KMH` | 100 km/h | Blizzard / high-wind warning (CRITICAL at 1.5× the limit) |
| Temperature ≤ `ALERT_TEMP_C` | −45 °C | Extreme cold warning |
| Visibility < `ALERT_VISIBILITY_KM` | 0.2 km | Whiteout conditions |
| Fuel ≤ `ALERT_FUEL_PCT` | 20 % | Low fuel reserve (CRITICAL at half the limit) |
| Battery ≤ `ALERT_BATTERY_PCT` | 15 % | Battery bank critically low |

---

## 8. Production checklist

* Set `DJANGO_DEBUG=False`, a long random `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS`.
* Make sure `DEMO_MODE` is off (it is when `DJANGO_DEBUG=False`, unless you set it), and delete or
  re-password the demo accounts.
* Use PostgreSQL and run `python manage.py collectstatic`.
* Serve with gunicorn or uvicorn on Linux (waitress on Windows) behind nginx with HTTPS.
* Set the SMTP settings in `.env` so alert emails are actually delivered.
* For stations with very limited bandwidth, host the CDN assets locally under `static/`.

## 9. Possible extensions

Offline-first PWA for station tablets, SMS or Iridium alerts, Celery for scheduled reports,
WebSockets for push updates, satellite-imagery layers on the map, and ML forecasting of fuel
consumption.

> Station names, coordinates and founding years are public information. All people, readings,
> stock levels and incidents in the demo data are fictional.
