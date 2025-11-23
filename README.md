Table of contents
1.Project overview
2.Repo layout
3.Prerequisites
4.Backend (Django + DRF) — setup & run
5.Web (React + Vite) — setup & run
6.Desktop (PyQt5) — setup & run
7.Sample data (provided)
8.Report generation (WeasyPrint fallback)
9.Useful commands & troubleshooting
10.Known issues / notes for submission

1 — Project overview

A small system to upload CSV equipment parameter data, compute summary statistics and preview / chart data in both a web UI (React/Vite) and a desktop UI (PyQt5). A common Django REST API is used by both clients. Reports (PDF) are created on the backend.

Primary tech:

Backend: Python, Django, Django REST Framework, Pandas

Web client: React + Vite + chart.js

Desktop client: PyQt5 + matplotlib

PDF: ReportLab for a simple fallback; WeasyPrint support included (optional, needs native libs)

2 — Repo layout (important files)
/backend                <- Django backend project
  project/              <- Django project settings
  api/                  <- Django app: views, serializers, models, utils
  manage.py
  requirements.txt

/web                    <- React + Vite web client
  src/
  public/
  package.json
  vite.config.js

/desktop                <- Desktop client (PyQt)
  client.py
  main_window.py
  table_model.py
  api.py, auth.py, request_helper.py (helpers)
  requirements.txt

/samples
  sample_equipment_data.csv
  sample_summary_api_payload.json
  sample_report.pdf (demo)

3 — Prerequisites
Global (install these first)

Python 3.10+ (3.11/3.14 tested by user)

Node 18+ / npm or yarn

On Windows: Git Bash or PowerShell available (examples below use both)

Optional (for nicer HTML PDF via WeasyPrint):

WeasyPrint native dependencies (Pango, Cairo, GObject) — installation differs by OS. If not installed, the server falls back to ReportLab PDF output.

4 — Backend (Django + DRF)
4.1 Create & activate virtual environment

Linux / macOS:

cd backend
python3 -m venv .venv
source .venv/bin/activate


Windows (PowerShell):

cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # or use Activate.bat in cmd


Git Bash (MINGW64):

cd backend
python -m venv .venv
source .venv/Scripts/activate

4.2 Install Python dependencies
pip install -r requirements.txt


If you plan to use WeasyPrint, follow system-specific instructions first (Pango/Cairo). On Windows WeasyPrint requires additional native libraries. If you do not have them, the project will use ReportLab fallback.

4.3 Configure Django defaults (recommended)

Open project/settings.py and ensure:

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


(Helps avoid auto-field warnings.)

4.4 Migrate and create superuser
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

4.5 Import sample dataset (optional)

The repo includes sample CSV and sample summary (in /samples).
To import the sample dataset using the management command:

python manage.py import_sample --username <your_superuser_username>


If the command complains about sample path, ensure the SAMPLE_PATH in api/management/commands/import_sample.py points to your samples/sample_equipment_data.csv. The demo sample path used in development is:

/mnt/data/sample_equipment_data.csv


(If you use Windows MINGW, the relative repo samples/sample_equipment_data.csv will also work.)

4.6 Run the development server
python manage.py runserver 0.0.0.0:8000


API root will be at: http://127.0.0.1:8000/api/

API endpoints (examples)

POST /api-token-auth/ — obtain DRF token (JSON: { username, password })

POST /api/datasets/upload/ — upload CSV (authenticated)

GET /api/datasets/<id>/summary/ — summary & preview (authenticated)

GET /api/datasets/history/ — list last 5 datasets (authenticated)

GET /api/datasets/<id>/report/ — download PDF report (authenticated)

5 — Web (React + Vite)
5.1 Install node deps
cd web
npm install
# or
# yarn

5.2 Environment / baseURL

The web client expects backend at http://localhost:8000. If your backend runs elsewhere, update web/src/api/client.js baseURL.

5.3 Run dev server
npm run dev


Open http://localhost:5173 (Vite default) in the browser.

5.4 Login flow

Open web UI

Use your Django superuser username/password at the login form (it posts to /api-token-auth/)

On success a token is saved to localStorage and attached to subsequent requests.

5.5 Notes about public mock assets

When no backend token or offline, the web client falls back to static files located in web/public/:

web/public/sample_summary_api_payload.json

web/public/sample_report.pdf

web/public/sample_equipment_data.csv

If you want to test purely offline, ensure these files exist in web/public.

6 — Desktop (PyQt5)
6.1 Create & activate a Python virtual environment (desktop)

You may reuse the backend venv or create separate one:

cd desktop
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

6.2 Run the desktop app
python client.py

Desktop quick flow

Login (mock or real backend). If using real backend, the desktop auth and request_helper will send token in headers.

Click Load sample CSV or Choose CSV.

Click Upload (to backend) to upload and compute summary.

Click Generate / Open Report — desktop resolves dataset numeric id (via summary fields or history) and downloads PDF from /api/datasets/<id>/report/.

6.3 Important

If the desktop cannot determine a numeric dataset id from the loaded summary, it will auto-upload the currently loaded CSV to backend, obtain the id, then download the report.

If you use the desktop purely in mock/offline mode, adjust desktop/client.py mock helpers.

7 — Sample data (paths)

Samples included in the repository are located in /samples. On some test environments a global path was used. Useful sample paths used in development:

Sample CSV (repo): samples/sample_equipment_data.csv

Sample summary JSON: samples/sample_summary_api_payload.json

(Dev full path used in some scripts) /mnt/data/sample_equipment_data.csv — if scripts reference this absolute path, update them to samples/ relative path in your environment.

If you want every part to use the same sample path, update the small constant in:

backend/api/management/commands/import_sample.py

desktop/client.py (SAMPLE_CSV_PATH / SAMPLE_SUMMARY_JSON)

web/public/* if serving purely static demos

8 — Report generation (WeasyPrint & fallback)

The backend ships two modes:

WeasyPrint (preferred, HTML → PDF) — produces high-quality, styled PDF. Requires native libs: Pango, Cairo, GObject, libffi; platform-specific installation needed.

ReportLab fallback — light-weight, pure-Python fallback used when WeasyPrint's native deps are missing.

If you want WeasyPrint:

Install native libs (see WeasyPrint docs):

Linux (Debian/Ubuntu): apt install libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi7 (names vary)

Windows: follow official instructions (MSYS2 / GTK builds)

Mac: brew install pango cairo gdk-pixbuf

Then pip install weasyprint inside your venv.

If WeasyPrint cannot import native libs, the backend will log the warning and use the ReportLab generator (already present). The ReportLab generator creates a simple, valid PDF.

Where to change the HTML template (for WeasyPrint):

Add backend/templates/reports/report.html and CSS under backend/static/reports/. Then update api/report_view.py to call WeasyPrint with that template.

9 — Useful commands & troubleshooting
Run all components locally

Start backend:

cd backend
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000


Start web:

cd web
npm run dev


Start desktop:

cd desktop
source .venv/Scripts/activate
python client.py

Common issues & fixes

ModuleNotFoundError: No module named 'django'
Activate the venv with .venv/Scripts/activate (Windows) or .venv/bin/activate (Unix) and re-run pip install -r requirements.txt.

Django warnings about AutoField
Set DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField" in project/settings.py and re-run migrations.

WeasyPrint OSError (libgobject, libpango)
Install native dependencies or accept ReportLab fallback.

Web 404 when requesting /api/datasets/<filename>/report/
That route expects a numeric ID. The web/desktop clients include logic to resolve filename → numeric id via the /api/datasets/history/ endpoint. If resolution fails, check history endpoint data or upload the CSV first.

Desktop: QPaintDevice: Cannot destroy paint device that is being painted or segmentation fault
This typically occurs if GUI objects are manipulated from non-main threads. The desktop code contains thread helpers — do not call GUI widget methods from worker threads. Use run_in_thread style helpers that signal back onto main thread.

Debugging tips

Check backend logs (console) for stack traces.

Confirm your token is set in web (localStorage token) or desktop (saved token in auth.py).

Use curl -u <username>:<password> http://127.0.0.1:8000/api/datasets/history/ to inspect history payload.

10 — Known issues / notes (for submission)

WeasyPrint: native libs not bundled — if evaluator can't install native deps, backend will fallback to ReportLab. Mention this in your submission notes.

Sample path normalization: some scripts used absolute /mnt/data/.... For portability, update them to use samples/ relative path in repo before final submission.

Auth: token-based DRF authentication is used. Unauthenticated requests show 401. For demonstration you can create a superuser and use credentials to log in.

Database: project uses SQLite by default (dev). For production use a proper RDBMS.

Tests: basic tests not included by default — add tests for summary compute and API behaviors if required by evaluators.
