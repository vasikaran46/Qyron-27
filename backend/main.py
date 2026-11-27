from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routers import admin, auth_routes, participant, registration_wizard

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"


def _frontend_file(filename: str) -> Path:
    """Finds HTML file in frontend/ directory, with fallback to project root."""
    f_path = FRONTEND_DIR / filename
    if f_path.exists():
        return f_path
    return ROOT / filename


app = FastAPI(title="QYRON'27 API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().allowed_origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(auth_routes.router)
app.include_router(participant.router)
app.include_router(admin.router)
app.include_router(registration_wizard.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "qyron27"}


@app.get("/api/event")
def event_details():
    return {
        "name": "QYRON'27", "timezone": "Asia/Kolkata",
        "team_size": {"minimum": 2, "maximum": 4},
        "fees_inr": {"registration_per_team": 150, "shortlisted_per_member": 350},
        "registration_deadline": "2027-01-20T23:59:00+05:30",
        "proposal_deadline": "2027-01-25T23:59:00+05:30",
        "shortlist_announcement": "2027-02-01T18:00:00+05:30", "shortlist_limit": 20,
        "shortlisted_fee_deadline": "2027-02-07", "event_dates": ["2027-02-12", "2027-02-13"],
        "submission": {"formats": ["ppt", "pptx", "pdf"], "max_size_mb": 10},
    }


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(_frontend_file("index.html"))


@app.get("/portal", include_in_schema=False)
@app.get("/portal.html", include_in_schema=False)
def portal_page():
    return FileResponse(_frontend_file("portal.html"))


@app.get("/login", include_in_schema=False)
@app.get("/login.html", include_in_schema=False)
def login_page():
    return FileResponse(_frontend_file("login.html"))


@app.get("/register", include_in_schema=False)
@app.get("/register.html", include_in_schema=False)
def register_page():
    return FileResponse(_frontend_file("register.html"))


@app.get("/participant", include_in_schema=False)
@app.get("/participant.html", include_in_schema=False)
def participant_page():
    return FileResponse(_frontend_file("participant.html"))


@app.get("/admin", include_in_schema=False)
@app.get("/admin.html", include_in_schema=False)
def admin_page():
    return FileResponse(_frontend_file("admin.html"))


@app.get("/confirmation", include_in_schema=False)
@app.get("/confirmation.html", include_in_schema=False)
@app.get("/confirmation/{team_code}", include_in_schema=False)
def confirmation_page(team_code: str = ""):
    return FileResponse(_frontend_file("confirmation.html"))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    fav = ROOT / "favicon.ico"
    if not fav.exists():
        fav = ROOT / "assets" / "favicon-32x32.png"
    return FileResponse(fav, media_type="image/x-icon")


@app.get("/main.js", include_in_schema=False)
def frontend_script():
    js_file = ROOT / "js" / "main.js"
    if not js_file.exists():
        js_file = ROOT / "main.js"
    return FileResponse(js_file, media_type="text/javascript")


@app.get("/portal.css", include_in_schema=False)
def portal_styles():
    css_file = ROOT / "css" / "portal.css"
    if not css_file.exists():
        css_file = ROOT / "portal.css"
    return FileResponse(css_file, media_type="text/css")


uploads_dir = ROOT / "uploads"
try:
    uploads_dir.mkdir(parents=True, exist_ok=True)
except OSError:
    pass

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")
app.mount("/css", StaticFiles(directory=ROOT / "css"), name="css")
app.mount("/js", StaticFiles(directory=ROOT / "js"), name="js")
app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
