from flask import Flask, jsonify, request, send_from_directory, session, redirect, url_for
from pathlib import Path
from datetime import datetime, timedelta, timezone
import secrets
import sqlite3
import hashlib
import os
from functools import wraps
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent.parent
WEBSITE_DIR = BASE_DIR / "website"
DB_FILE = Path(__file__).resolve().parent / "database.db"
REMOTE_CONFIG_FILE = Path(__file__).resolve().parent / "remote_config.json"

app = Flask(__name__)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False


app.secret_key = os.environ.get("RGB_BOT_SECRET_KEY", "RGB_BOT_V1_LOCAL_SECRET_2026")


@app.before_request
def handle_cors_preflight():
    if request.method == "OPTIONS":
        return ("", 204)


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "")
    if origin == "https://rgbxcheat.github.io":
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Task-Session"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


def get_client_ip():
    cf_ip = request.headers.get("CF-Connecting-IP", "").strip()
    if cf_ip:
        return cf_ip
    return request.remote_addr or ""


ADMIN_PASSWORD = "RGB217642055"

ADMIN_TEMPLATE = Path(__file__).resolve().parent / "admin.html"

SWITCH_FILES_DIR = Path(__file__).resolve().parent / "protected" / "files"
ON_DIR = SWITCH_FILES_DIR / "on"
OFF_DIR = SWITCH_FILES_DIR / "off"

ON_DIR.mkdir(parents=True, exist_ok=True)
OFF_DIR.mkdir(parents=True, exist_ok=True)


def admin_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login"))

        return func(*args, **kwargs)

    return wrapper


def admin_file_info(directory):

    result = []

    for item in sorted(directory.iterdir()):

        if not item.is_file():
            continue

        data = item.read_bytes()

        result.append({
            "name": item.name,
            "path": str(item.relative_to(directory)).replace("\\", "/"),
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest()
        })

    return result



@app.get("/")
def index():
    return send_from_directory(
        WEBSITE_DIR,
        "index.html"
    )


@app.get("/<path:path>")
def website_files(path):

    return send_from_directory(
        WEBSITE_DIR,
        path
    )


@app.get("/api/health")
def health():

    return jsonify({
        "server":"online",
        "system":"RGB BOT V1"
    })



KEY_LIFETIME = timedelta(hours=24)
TASK_SESSION_LIFETIME = timedelta(minutes=15)
TASK_WAIT_SECONDS = 5
TASK_SESSION_COOKIE = "rgb_task_session"

TASK_ORDER = (
    "youtube",
    "youtube_like",
    "whatsapp",
    "telegram",
)


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_ip TEXT,
            bound_ip TEXT,
            device_id TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT UNIQUE NOT NULL,
            key TEXT NOT NULL,
            device_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            last_ip TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            youtube INTEGER NOT NULL DEFAULT 0,
            whatsapp INTEGER NOT NULL DEFAULT 0,
            telegram INTEGER NOT NULL DEFAULT 0,
            youtube_like INTEGER NOT NULL DEFAULT 0,
            used INTEGER NOT NULL DEFAULT 0,
            current_step INTEGER NOT NULL DEFAULT 0,
            task_started_at TEXT
        )
    """)


    try:
        existing_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(task_sessions)"
            )
        }

        if "youtube_like" not in existing_columns:
            conn.execute(
                "ALTER TABLE task_sessions "
                "ADD COLUMN youtube_like INTEGER NOT NULL DEFAULT 0"
            )
            conn.commit()
    except Exception:
        pass

    # Safe migration for existing key databases.
    key_columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(keys)"
        ).fetchall()
    }

    if "created_ip" not in key_columns:
        conn.execute("ALTER TABLE keys ADD COLUMN created_ip TEXT")

    if "bound_ip" not in key_columns:
        conn.execute("ALTER TABLE keys ADD COLUMN bound_ip TEXT")

    if "device_id" not in key_columns:
        conn.execute("ALTER TABLE keys ADD COLUMN device_id TEXT")

    if "visitor_id" not in key_columns:
        conn.execute("ALTER TABLE keys ADD COLUMN visitor_id TEXT")

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_keys_visitor_active
        ON keys(visitor_id, active)
    """)

    # Safe migration for existing databases.
    columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(task_sessions)"
        ).fetchall()
    }

    if "current_step" not in columns:
        conn.execute("""
            ALTER TABLE task_sessions
            ADD COLUMN current_step INTEGER NOT NULL DEFAULT 0
        """)

    if "task_started_at" not in columns:
        conn.execute("""
            ALTER TABLE task_sessions
            ADD COLUMN task_started_at TEXT
        """)

    # Synchronize old sessions with their existing task flags.
    conn.execute("""
        UPDATE task_sessions
        SET current_step =
            CASE
                WHEN youtube = 1
                 AND whatsapp = 1
                 AND telegram = 1 THEN 3

                WHEN youtube = 1
                 AND whatsapp = 1 THEN 2

                WHEN youtube = 1 THEN 1

                ELSE 0
            END
        WHERE current_step = 0
          AND (
              youtube = 1
              OR whatsapp = 1
              OR telegram = 1
          )
    """)

    conn.commit()
    conn.close()


def create_key(visitor_id=None):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    while True:
        parts = [
            "".join(secrets.choice(alphabet) for _ in range(4))
            for _ in range(3)
        ]

        key = "RGB1-" + "-".join(parts)

        now = datetime.now(timezone.utc)
        expires = now + KEY_LIFETIME
        created_ip = get_client_ip()

        try:
            conn = get_db()
            conn.execute(
                """
                INSERT INTO keys
                (key, created_at, expires_at, active, created_ip, visitor_id)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                (
                    key,
                    now.isoformat(),
                    expires.isoformat(),
                    created_ip,
                    visitor_id
                )
            )
            conn.commit()
            conn.close()
            return key, expires

        except sqlite3.IntegrityError:
            conn.close()


def lookup_active_key(key):
    conn = get_db()

    row = conn.execute(
        """
        SELECT
            key,
            created_at,
            expires_at,
            active,
            created_ip,
            bound_ip,
            device_id,
            visitor_id
        FROM keys
        WHERE key = ?
        """,
        (key,)
    ).fetchone()

    conn.close()

    if row is None:
        return None, "INVALID_KEY"

    if row["active"] != 1:
        return None, "KEY_DISABLED"

    try:
        expires = datetime.fromisoformat(row["expires_at"])
    except Exception:
        return None, "KEY_INVALID_DATE"

    if datetime.now(timezone.utc) >= expires:
        return None, "KEY_EXPIRED"

    return row, None


def get_task_session():
    session_id = (
        request.headers.get("X-Task-Session", "").strip()
        or request.cookies.get(TASK_SESSION_COOKIE, "").strip()
    )

    if not session_id:
        return None, "TASK_SESSION_REQUIRED"

    conn = get_db()

    row = conn.execute(
        """
        SELECT *
        FROM task_sessions
        WHERE id = ?
        """,
        (session_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return None, "TASK_SESSION_INVALID"

    try:
        expires = datetime.fromisoformat(row["expires_at"])
    except Exception:
        return None, "TASK_SESSION_INVALID_DATE"

    if datetime.now(timezone.utc) >= expires:
        return None, "TASK_SESSION_EXPIRED"

    if row["used"] != 0:
        return None, "TASK_SESSION_USED"

    return row, None


def task_state(row):
    step = int(row["current_step"] or 0)

    if step < 0:
        step = 0

    if step > len(TASK_ORDER):
        step = len(TASK_ORDER)

    current_task = (
        TASK_ORDER[step]
        if step < len(TASK_ORDER)
        else None
    )

    tasks = {}

    for task_name in TASK_ORDER:
        try:
            tasks[task_name] = bool(row[task_name])
        except Exception:
            tasks[task_name] = False

    started_at = row["task_started_at"]
    waiting_seconds = 0

    if started_at:
        try:
            started = datetime.fromisoformat(started_at)

            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)

            elapsed = (
                datetime.now(timezone.utc) - started
            ).total_seconds()

            waiting_seconds = max(
                0,
                TASK_WAIT_SECONDS - int(elapsed)
            )

        except Exception:
            waiting_seconds = TASK_WAIT_SECONDS

    return {
        "step": step,
        "completed": step,
        "total": len(TASK_ORDER),
        "current_task": current_task,
        "tasks": tasks,
        "waiting": bool(started_at),
        "waiting_seconds": waiting_seconds,
    }


@app.post("/api/tasks/start")
def start_tasks():

    # Reuse a valid existing session so page reload
    # does not reset progress.
    existing, existing_error = get_task_session()

    if existing is not None:
        return jsonify({
            "success": True,
            "existing": True,
            "session_id": existing["id"],
            "expires_at": existing["expires_at"],
            **task_state(existing)
        })

    now = datetime.now(timezone.utc)
    expires = now + TASK_SESSION_LIFETIME
    session_id = secrets.token_urlsafe(32)

    conn = get_db()

    conn.execute(
        """
        INSERT INTO task_sessions
        (
            id,
            created_at,
            expires_at,
            youtube,
            whatsapp,
            telegram,
            youtube_like,
            used,
            current_step,
            task_started_at
        )
        VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, NULL)
        """,
        (
            session_id,
            now.isoformat(),
            expires.isoformat()
        )
    )

    conn.commit()

    row = conn.execute(
        """
        SELECT *
        FROM task_sessions
        WHERE id = ?
        """,
        (session_id,)
    ).fetchone()

    conn.close()

    response = jsonify({
        "success": True,
        "existing": False,
        "session_id": session_id,
        "expires_at": expires.isoformat(),
        **task_state(row)
    })

    response.set_cookie(
        TASK_SESSION_COOKIE,
        session_id,
        max_age=int(TASK_SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=False,
        samesite="Lax",
        path="/"
    )

    return response


@app.post("/api/tasks/open")
def open_task():

    row, error = get_task_session()

    if error:
        return jsonify({
            "success": False,
            "error": error
        }), 403

    data = request.get_json(silent=True) or {}
    task = str(data.get("task", "")).strip().lower()

    if task not in TASK_ORDER:
        return jsonify({
            "success": False,
            "error": "INVALID_TASK"
        }), 400

    step = int(row["current_step"])

    if step >= len(TASK_ORDER):
        return jsonify({
            "success": False,
            "error": "ALL_TASKS_COMPLETED",
            **task_state(row)
        }), 409

    expected = TASK_ORDER[step]

    if task != expected:
        return jsonify({
            "success": False,
            "error": "INVALID_TASK_ORDER",
            "expected": expected,
            **task_state(row)
        }), 409

    # If this task is already running, do not reset
    # its timer by pressing the button again.
    if row["task_started_at"]:
        return jsonify({
            "success": True,
            "already_started": True,
            **task_state(row)
        })

    now = datetime.now(timezone.utc)

    conn = get_db()

    conn.execute(
        """
        UPDATE task_sessions
        SET task_started_at = ?
        WHERE id = ?
          AND current_step = ?
          AND task_started_at IS NULL
          AND used = 0
        """,
        (
            now.isoformat(),
            row["id"],
            step
        )
    )

    conn.commit()

    updated = conn.execute(
        """
        SELECT *
        FROM task_sessions
        WHERE id = ?
        """,
        (row["id"],)
    ).fetchone()

    conn.close()

    return jsonify({
        "success": True,
        "task": task,
        "wait_seconds": TASK_WAIT_SECONDS,
        **task_state(updated)
    })


@app.post("/api/tasks/complete")
def complete_task():

    row, error = get_task_session()

    if error:
        return jsonify({
            "success": False,
            "error": error
        }), 403

    data = request.get_json(silent=True) or {}
    task = str(data.get("task", "")).strip().lower()

    if task not in TASK_ORDER:
        return jsonify({
            "success": False,
            "error": "INVALID_TASK"
        }), 400

    step = int(row["current_step"])

    if step >= len(TASK_ORDER):
        return jsonify({
            "success": False,
            "error": "ALL_TASKS_COMPLETED",
            **task_state(row)
        }), 409

    expected = TASK_ORDER[step]

    if task != expected:
        return jsonify({
            "success": False,
            "error": "INVALID_TASK_ORDER",
            "expected": expected,
            **task_state(row)
        }), 409

    if not row["task_started_at"]:
        return jsonify({
            "success": False,
            "error": "TASK_NOT_STARTED",
            **task_state(row)
        }), 409

    try:
        started = datetime.fromisoformat(
            row["task_started_at"]
        )
    except Exception:
        return jsonify({
            "success": False,
            "error": "TASK_TIMER_INVALID"
        }), 500

    elapsed = (
        datetime.now(timezone.utc) - started
    ).total_seconds()

    if elapsed < TASK_WAIT_SECONDS:
        remaining = max(
            1,
            int(TASK_WAIT_SECONDS - elapsed)
        )

        return jsonify({
            "success": False,
            "error": "TASK_WAIT_NOT_FINISHED",
            "remaining_seconds": remaining,
            **task_state(row)
        }), 429

    next_step = step + 1

    conn = get_db()

    # Atomic step transition.
    # This prevents two simultaneous requests from
    # completing the same step twice.
    result = conn.execute(
        f"""
        UPDATE task_sessions
        SET
            {task} = 1,
            current_step = ?,
            task_started_at = NULL
        WHERE id = ?
          AND current_step = ?
          AND task_started_at = ?
          AND used = 0
        """,
        (
            next_step,
            row["id"],
            step,
            row["task_started_at"]
        )
    )

    conn.commit()

    updated = conn.execute(
        """
        SELECT *
        FROM task_sessions
        WHERE id = ?
        """,
        (row["id"],)
    ).fetchone()

    conn.close()

    if result.rowcount != 1:
        return jsonify({
            "success": False,
            "error": "TASK_STATE_CHANGED",
            **task_state(updated)
        }), 409

    return jsonify({
        "success": True,
        "task": task,
        "completed": next_step == len(TASK_ORDER),
        **task_state(updated)
    })


@app.get("/api/tasks/status")
def task_status():

    row, error = get_task_session()

    if error:
        return jsonify({
            "success": False,
            "error": error
        }), 403

    return jsonify({
        "success": True,
        **task_state(row)
    })


@app.post("/api/get-key")
def get_key():
    """
    Return the existing active key for this browser visitor.
    Generate a new 24-hour key only when none exists or the old one expired.
    """

    try:
        data = request.get_json(silent=True) or {}
        visitor_id = str(data.get("visitor_id", "")).strip()

        if not visitor_id or len(visitor_id) > 128:
            return jsonify({
                "success": False,
                "error": "VISITOR_ID_REQUIRED"
            }), 400

        conn = get_db()
        row = conn.execute("""
            SELECT key, expires_at
            FROM keys
            WHERE visitor_id = ?
              AND active = 1
            ORDER BY id DESC
            LIMIT 1
        """, (visitor_id,)).fetchone()

        now = datetime.now(timezone.utc)

        if row:
            expires = datetime.fromisoformat(row["expires_at"])

            if expires > now:
                conn.close()
                return jsonify({
                    "success": True,
                    "key": row["key"],
                    "expires_at": expires.isoformat()
                })

            conn.execute(
                "UPDATE keys SET active = 0 WHERE visitor_id = ?",
                (visitor_id,)
            )
            conn.commit()

        key, expires = create_key(visitor_id)

        conn.close()

        return jsonify({
            "success": True,
            "key": key,
            "expires_at": expires.isoformat()
        })

    except Exception:
        app.logger.exception("GET KEY ERROR")

        return jsonify({
            "success": False,
            "error": "KEY_GENERATION_FAILED"
        }), 500

def create_app_session(key, device_id, expires_at):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)

    conn = get_db()
    conn.execute(
        "UPDATE app_sessions SET active = 0 WHERE key = ? AND device_id = ? AND active = 1",
        (key, device_id)
    )
    conn.execute(
        """
        INSERT INTO app_sessions
        (token_hash, key, device_id, created_at, expires_at, active, last_ip)
        VALUES (?, ?, ?, ?, ?, 1, ?)
        """,
        (token_hash, key, device_id, now.isoformat(), expires_at, get_client_ip())
    )
    conn.commit()
    conn.close()
    return token


def lookup_app_session(token):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = get_db()
    row = conn.execute(
        """
        SELECT token_hash, key, device_id, created_at, expires_at, active, last_ip
        FROM app_sessions
        WHERE token_hash = ?
        """,
        (token_hash,)
    ).fetchone()

    if row is None:
        conn.close()
        return None, "INVALID_SESSION"

    if row["active"] != 1:
        conn.close()
        return None, "SESSION_DISABLED"

    try:
        expires = datetime.fromisoformat(row["expires_at"])
    except Exception:
        conn.close()
        return None, "SESSION_INVALID_DATE"

    if expires <= datetime.now(timezone.utc):
        conn.execute(
            "UPDATE app_sessions SET active = 0 WHERE token_hash = ?",
            (token_hash,)
        )
        conn.commit()
        conn.close()
        return None, "SESSION_EXPIRED"

    conn.execute(
        "UPDATE app_sessions SET last_ip = ? WHERE token_hash = ?",
        (get_client_ip(), token_hash)
    )
    conn.commit()
    conn.close()
    return row, None


@app.post("/api/verify-key")
def verify_key():
    data = request.get_json(silent=True) or {}

    entered_key = str(data.get("key", "")).strip().upper()
    device_id = str(data.get("device_id", "")).strip()
    client_ip = get_client_ip()

    if not entered_key:
        return jsonify({
            "valid": False,
            "error": "KEY_REQUIRED"
        }), 400

    if not device_id:
        return jsonify({
            "valid": False,
            "error": "DEVICE_ID_REQUIRED"
        }), 400

    row, error = lookup_active_key(entered_key)

    if error:
        return jsonify({
            "valid": False,
            "error": error
        })

    conn = get_db()

    if row["device_id"]:
        if row["device_id"] != device_id:
            conn.close()
            return jsonify({
                "valid": False,
                "error": "KEY_ALREADY_BOUND_TO_ANOTHER_DEVICE"
            })

        conn.execute(
            """
            UPDATE keys
            SET bound_ip = ?
            WHERE key = ?
            """,
            (client_ip, entered_key)
        )
    else:
        conn.execute(
            """
            UPDATE keys
            SET device_id = ?, bound_ip = ?
            WHERE key = ?
            """,
            (device_id, client_ip, entered_key)
        )

    conn.commit()
    conn.close()

    session_token = create_app_session(
        row["key"],
        device_id,
        row["expires_at"]
    )

    return jsonify({
        "valid": True,
        "key": row["key"],
        "expires_at": row["expires_at"],
        "session_token": session_token
    })

SWITCH_FILES_DIR = Path(__file__).resolve().parent / "protected" / "files"


def authenticate_switch_key():
    data = request.get_json(silent=True) or {}
    session_token = str(data.get("session_token", "")).strip()

    if session_token:
        row, error = lookup_app_session(session_token)
        if error:
            return None, jsonify({
                "success": False,
                "error": error
            }), 403
        return row, None, None

    entered_key = str(data.get("key", "")).strip().upper()
    device_id = str(data.get("device_id", "")).strip()
    client_ip = get_client_ip()

    if not entered_key:
        return None, jsonify({
            "success": False,
            "error": "KEY_REQUIRED"
        }), 400

    if not device_id:
        return None, jsonify({
            "success": False,
            "error": "DEVICE_ID_REQUIRED"
        }), 400

    row, error = lookup_active_key(entered_key)

    if error:
        return None, jsonify({
            "success": False,
            "error": error
        }), 403

    if not row["device_id"]:
        return None, jsonify({
            "success": False,
            "error": "KEY_NOT_BOUND"
        }), 403

    if row["device_id"] != device_id:
        return None, jsonify({
            "success": False,
            "error": "KEY_ALREADY_BOUND_TO_ANOTHER_DEVICE"
        }), 403

    conn = get_db()
    conn.execute(
        "UPDATE keys SET bound_ip = ? WHERE key = ?",
        (client_ip, entered_key)
    )
    conn.commit()
    conn.close()

    return row, None, None



def read_switch_files(folder_name):
    folder = SWITCH_FILES_DIR / folder_name

    if not folder.exists() or not folder.is_dir():
        return []

    files = []

    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue

        relative = path.relative_to(folder)

        # منع أي ملف/مسار غير طبيعي
        if ".." in relative.parts:
            continue

        content = path.read_bytes()

        import base64
        import hashlib

        files.append({
            "name": relative.as_posix(),
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "content_base64": base64.b64encode(content).decode("ascii")
        })

    return files


@app.post("/api/switch/on")
def switch_on():

    row, error_response, status = authenticate_switch_key()

    if error_response:
        return error_response, status

    files = read_switch_files("on")

    return jsonify({
        "success": True,
        "mode": "on",
        "files": files
    })


@app.post("/api/switch/off")
def switch_off():

    row, error_response, status = authenticate_switch_key()

    if error_response:
        return error_response, status

    files = read_switch_files("off")

    return jsonify({
        "success": True,
        "mode": "off",
        "files": files
    })



@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if session.get("admin_authenticated"):
        return redirect(url_for("admin_panel"))

    error = ""

    if request.method == "POST":

        password = str(request.form.get("password", ""))

        if secrets.compare_digest(password, ADMIN_PASSWORD):
            session["admin_authenticated"] = True
            return redirect(url_for("admin_panel"))

        error = "INVALID PASSWORD"

    return send_from_directory(
        Path(__file__).resolve().parent,
        "admin.html"
    )


@app.get("/api/admin/config")
@admin_required
def admin_config():
    import json

    try:
        with open(REMOTE_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        return jsonify({
            "success": True,
            "config": config
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.post("/api/admin/config")
@admin_required
def admin_save_config():
    import json

    data = request.get_json(silent=True) or {}

    try:
        with open(REMOTE_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        if "app_code" in data:
            config["app_code"] = str(data["app_code"]).strip()

        if "app_version" in data:
            config["app_version"] = int(data["app_version"])

        if "force_update" in data:
            config["force_update"] = bool(data["force_update"])

        if "update_url" in data:
            config["update_url"] = str(data["update_url"]).strip()

        if "update_message" in data:
            config["update_message"] = str(data["update_message"])

        with open(REMOTE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            f.write("\n")

        return jsonify({
            "success": True,
            "message": "CONFIG SAVED",
            "config": config
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.get("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(url_for("admin_login"))


@app.get("/admin")
@admin_required
def admin_panel():

    return send_from_directory(
        Path(__file__).resolve().parent,
        "admin.html"
    )


@app.get("/api/admin/files")
@admin_required
def admin_files():

    return jsonify({
        "success": True,
        "on": admin_file_info(ON_DIR),
        "off": admin_file_info(OFF_DIR),
        "security": admin_file_info(SECURITY_DIR),
        "fix_error": admin_file_info(FIX_ERROR_DIR)
    })


@app.post("/api/admin/upload")
@admin_required
def admin_upload():

    mode = str(request.form.get("mode", "")).lower()

    directories = {
        "on": ON_DIR,
        "off": OFF_DIR,
        "security": SECURITY_DIR,
        "fix_error": FIX_ERROR_DIR
    }

    if mode not in directories:
        return jsonify({
            "success": False,
            "error": "INVALID_MODE"
        }), 400

    uploaded = request.files.get("file")

    if uploaded is None or not uploaded.filename:
        return jsonify({
            "success": False,
            "error": "FILE_REQUIRED"
        }), 400

    filename = secure_filename(uploaded.filename)

    if not filename:
        return jsonify({
            "success": False,
            "error": "INVALID_FILENAME"
        }), 400

    if filename in (".", "..") or "/" in filename or "\\" in filename:
        return jsonify({
            "success": False,
            "error": "INVALID_FILENAME"
        }), 400

    relative_path = str(request.form.get("path", "")).strip()

    if not relative_path:
        return jsonify({
            "success": False,
            "error": "PATH_REQUIRED"
        }), 400

    relative_path = relative_path.replace("\\", "/").strip("/")

    parts = [
        part for part in relative_path.split("/")
        if part not in ("", ".")
    ]

    if any(part == ".." for part in parts):
        return jsonify({
            "success": False,
            "error": "INVALID_PATH"
        }), 400

    while parts and parts[0] in (
        "server",
        "protected",
        "files",
        "on",
        "off"
    ):
        parts.pop(0)

    if not parts:
        parts = [filename]

    if parts[-1] != filename:
        parts.append(filename)

    destination = directories[mode].joinpath(*parts)

    base = directories[mode].resolve()
    resolved = destination.resolve()

    if resolved != base and base not in resolved.parents:
        return jsonify({
            "success": False,
            "error": "INVALID_PATH"
        }), 400

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    uploaded.save(destination)

    return jsonify({
        "success": True,
        "mode": mode,
        "name": filename,
        "path": str(
            destination.relative_to(base)
        ).replace("\\", "/"),
        "size": destination.stat().st_size,
        "sha256": hashlib.sha256(
            destination.read_bytes()
        ).hexdigest()
    })



@app.post("/api/admin/upload-folder")
@admin_required
def admin_upload_folder():

    import os

    mode = str(request.form.get("mode", "")).lower()

    directories = {
        "on": ON_DIR,
        "off": OFF_DIR
    }

    if mode not in directories:
        return jsonify({
            "success": False,
            "error": "INVALID_MODE"
        }), 400

    base_path = str(
        request.form.get("path", "")
    ).strip()

    if not base_path:
        return jsonify({
            "success": False,
            "error": "PATH_REQUIRED"
        }), 400

    base_path = base_path.replace("\\\\", "/").strip("/")

    parts = [
        x for x in base_path.split("/")
        if x not in ("", ".")
    ]

    if any(x == ".." for x in parts):
        return jsonify({
            "success": False,
            "error": "INVALID_PATH"
        }), 400

    while parts and parts[0] in (
        "server",
        "protected",
        "files",
        "on",
        "off"
    ):
        parts.pop(0)

    destination_root = directories[mode].joinpath(*parts)

    root = directories[mode].resolve()
    resolved_root = destination_root.resolve()

    if resolved_root != root and root not in resolved_root.parents:
        return jsonify({
            "success": False,
            "error": "INVALID_PATH"
        }), 400

    destination_root.mkdir(
        parents=True,
        exist_ok=True
    )

    uploaded_files = request.files.getlist("files")

    if not uploaded_files:
        uploaded_files = request.files.getlist("file")

    if not uploaded_files:
        return jsonify({
            "success": False,
            "error": "FILES_REQUIRED"
        }), 400

    results = []

    for uploaded in uploaded_files:

        original = uploaded.filename or ""

        original = original.replace("\\\\", "/")

        relative_parts = [
            x for x in original.split("/")
            if x not in ("", ".")
        ]

        if any(x == ".." for x in relative_parts):
            return jsonify({
                "success": False,
                "error": "INVALID_FILE_PATH"
            }), 400

        if not relative_parts:
            continue

        safe_name = secure_filename(
            relative_parts[-1]
        )

        if not safe_name:
            return jsonify({
                "success": False,
                "error": "INVALID_FILENAME"
            }), 400

        relative_parts[-1] = safe_name

        destination = destination_root.joinpath(
            *relative_parts
        )

        resolved = destination.resolve()

        if resolved != root and root not in resolved.parents:
            return jsonify({
                "success": False,
                "error": "INVALID_PATH"
            }), 400

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        uploaded.save(destination)

        content = destination.read_bytes()

        results.append({
            "path": str(
                destination.relative_to(root)
            ).replace("\\\\", "/"),
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest()
        })

    return jsonify({
        "success": True,
        "mode": mode,
        "files": results
    })

@app.post("/api/admin/delete")
@admin_required
def admin_delete():

    mode = str(request.form.get("mode", "")).lower()
    filename = secure_filename(
        str(request.form.get("filename", ""))
    )

    directories = {
        "on": ON_DIR,
        "off": OFF_DIR,
        "security": SECURITY_DIR,
        "fix_error": FIX_ERROR_DIR
    }

    if mode not in directories:
        return jsonify({
            "success": False,
            "error": "INVALID_MODE"
        }), 400

    if not filename:
        return jsonify({
            "success": False,
            "error": "INVALID_FILENAME"
        }), 400

    target = directories[mode] / filename

    if not target.exists() or not target.is_file():
        return jsonify({
            "success": False,
            "error": "FILE_NOT_FOUND"
        }), 404

    target.unlink()

    return jsonify({
        "success": True,
        "mode": mode,
        "name": filename
    })


@app.get("/api/config")
def remote_config():

    try:
        import json

        with open(REMOTE_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        return jsonify(config)

    except Exception:
        return jsonify({
            "version": 1,
            "app": "RGB BOT V1",
            "buttons": {
                "get_key": {
                    "enabled": False,
                    "action": "get_key"
                },
                "switch": {
                    "enabled": False,
                    "on": {
                        "enabled": False,
                        "action": "switch_on"
                    },
                    "off": {
                        "enabled": False,
                        "action": "switch_off"
                    }
                }
            }
        }), 500


if __name__ == "__main__":

    init_db()

    print("================================")
    print(" RGB BOT V1 WEBSITE + API")
    print(" STATUS : ONLINE")
    print(" PORT   : 5000")
    print("================================")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
