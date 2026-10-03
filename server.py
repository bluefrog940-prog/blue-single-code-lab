from flask import Flask, request, jsonify, send_from_directory, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import uuid
import secrets
from datetime import datetime, timedelta

app = Flask(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
UPLOADS = os.path.join(BASE, "uploads")

os.makedirs(DATA, exist_ok=True)
os.makedirs(UPLOADS, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

DB = {
    "users": "users.json",
    "codes": "codes.json",
    "comments": "comments.json",
    "likes": "likes.json",
    "discussions": "discussions.json",
    "issues": "issues.json",
    "notifications": "notifications.json",
    "tokens": "tokens.json",
}

def path(name):
    return os.path.join(DATA, DB[name])

def load(name):
    p = path(name)
    if not os.path.exists(p):
        save(name, [])
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save(name, value):
    with open(path(name), "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def public_user(u):
    if not u:
        return None

    return {
        "id": u.get("id"),
        "username": u.get("username"),
        "name": u.get("name", ""),
        "bio": u.get("bio", ""),
        "avatar": u.get("avatar", ""),
        "points": u.get("points", 0),
        "xp": u.get("xp", 0),
        "level": u.get("level", 1),
        "codes": u.get("codes", 0),
        "likes": u.get("likes", 0),
        "created_at": u.get("created_at"),
    }

def find_user(user_id):
    for u in load("users"):
        if u.get("id") == user_id:
            return u
    return None

def token_user():
    token = request.cookies.get("blue_token")

    if not token:
        return None

    tokens = load("tokens")

    for t in tokens:
        if t.get("token") == token:
            if t.get("expires", "") < now():
                continue
            return find_user(t.get("user_id"))

    return None

def current_user():
    return token_user()

def require_user():
    return current_user()

def level_from_xp(xp):
    return max(1, (int(xp) // 100) + 1)

def add_xp(user_id, amount):
    users = load("users")

    for u in users:
        if u.get("id") == user_id:
            u["xp"] = u.get("xp", 0) + amount
            u["points"] = u.get("points", 0) + amount
            u["level"] = level_from_xp(u["xp"])

    save("users", users)

def notify(user_id, text):
    items = load("notifications")

    items.insert(0, {
        "id": uuid.uuid4().hex,
        "user_id": user_id,
        "text": text,
        "read": False,
        "created_at": now()
    })

    save("notifications", items)

@app.route("/")
def home():
    return send_from_directory(BASE, "index.html")

@app.route("/dashboard")
@app.route("/dashboard.html")
def dashboard():
    return send_from_directory(BASE, "dashboard.html")

@app.route("/uploads/<path:name>")
def upload(name):
    return send_from_directory(UPLOADS, name)

# =========================
# REGISTER
# =========================

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if len(username) < 3:
        return jsonify({"ok": False, "error": "نام کاربری حداقل ۳ حرف باشد"}), 400

    if len(password) < 6:
        return jsonify({"ok": False, "error": "رمز عبور حداقل ۶ کاراکتر باشد"}), 400

    users = load("users")

    for u in users:
        if u.get("username", "").lower() == username.lower():
            return jsonify({"ok": False, "error": "این نام کاربری قبلاً ثبت شده"}), 409

    user = {
        "id": uuid.uuid4().hex,
        "name": name or username,
        "username": username,
        "password": generate_password_hash(password),
        "bio": "",
        "avatar": "",
        "points": 0,
        "xp": 0,
        "level": 1,
        "codes": 0,
        "likes": 0,
        "created_at": now()
    }

    users.append(user)
    save("users", users)

    return create_login(user)

# =========================
# LOGIN
# =========================

def create_login(user):
    token = secrets.token_urlsafe(48)

    tokens = load("tokens")

    tokens = [
        x for x in tokens
        if x.get("expires", "") >= now()
    ]

    tokens.append({
        "token": token,
        "user_id": user["id"],
        "created_at": now(),
        "expires": (datetime.now() + timedelta(days=3650)).strftime("%Y-%m-%d %H:%M:%S")
    })

    save("tokens", tokens)

    response = make_response(jsonify({
        "ok": True,
        "user": public_user(user)
    }))

    response.set_cookie(
        "blue_token",
        token,
        max_age=60 * 60 * 24 * 3650,
        httponly=True,
        samesite="Lax"
    )

    return response

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    for u in load("users"):
        if u.get("username", "").lower() == username.lower():

            stored = u.get("password", "")

            valid = False

            try:
                valid = check_password_hash(stored, password)
            except Exception:
                valid = stored == password

            if valid:
                return create_login(u)

            break

    return jsonify({
        "ok": False,
        "error": "نام کاربری یا رمز عبور اشتباه است"
    }), 401

# =========================
# AUTO LOGIN
# =========================

@app.route("/api/me")
def me():
    u = current_user()

    if not u:
        return jsonify({
            "ok": False,
            "logged_in": False,
            "user": None
        }), 401

    return jsonify({
        "ok": True,
        "logged_in": True,
        "user": public_user(u)
    })

@app.route("/api/logout", methods=["POST"])
def logout():
    token = request.cookies.get("blue_token")

    if token:
        tokens = [
            x for x in load("tokens")
            if x.get("token") != token
        ]
        save("tokens", tokens)

    response = make_response(jsonify({"ok": True}))
    response.delete_cookie("blue_token")
    return response

# =========================
# PROFILE
# =========================

@app.route("/api/profile", methods=["GET", "POST"])
def profile():
    u = require_user()

    if not u:
        return jsonify({"ok": False, "error": "ابتدا وارد شوید"}), 401

    if request.method == "GET":
        return jsonify({
            "ok": True,
            "user": public_user(u)
        })

    data = request.get_json(silent=True) or {}
    users = load("users")

    for user in users:
        if user.get("id") == u.get("id"):

            if "name" in data:
                user["name"] = str(data["name"]).strip()

            if "bio" in data:
                user["bio"] = str(data["bio"]).strip()

            if "avatar" in data:
                user["avatar"] = str(data["avatar"]).strip()

            save("users", users)

            return jsonify({
                "ok": True,
                "user": public_user(user)
            })

    return jsonify({"ok": False, "error": "کاربر پیدا نشد"}), 404

# =========================
# CODES
# =========================

@app.route("/api/codes", methods=["GET", "POST"])
def codes():

    if request.method == "GET":
        return jsonify({
            "ok": True,
            "codes": load("codes")
        })

    u = require_user()

    if not u:
        return jsonify({"ok": False, "error": "ابتدا وارد شوید"}), 401

    data = request.form

    title = str(data.get("title", "")).strip()
    language = str(data.get("language", "Other")).strip()
    description = str(data.get("description", "")).strip()
    code_text = str(data.get("code", "")).strip()

    if not title:
        return jsonify({"ok": False, "error": "عنوان کد را وارد کن"}), 400

    if not code_text:
        return jsonify({"ok": False, "error": "کد خالی است"}), 400

    image_url = ""
    video_url = ""

    image = request.files.get("image")
    video = request.files.get("video")

    if image and image.filename:
        filename = uuid.uuid4().hex + "_" + image.filename
        image.save(os.path.join(UPLOADS, filename))
        image_url = "/uploads/" + filename

    if video and video.filename:
        filename = uuid.uuid4().hex + "_" + video.filename
        video.save(os.path.join(UPLOADS, filename))
        video_url = "/uploads/" + filename

    item = {
        "id": uuid.uuid4().hex,
        "title": title,
        "language": language,
        "description": description,
        "code": code_text,
        "image": image_url,
        "video": video_url,
        "username": u["username"],
        "user_id": u["id"],
        "likes": 0,
        "comments": 0,
        "views": 0,
        "created_at": now()
    }

    items = load("codes")
    items.insert(0, item)
    save("codes", items)

    users = load("users")

    for user in users:
        if user.get("id") == u["id"]:
            user["codes"] = user.get("codes", 0) + 1

    save("users", users)

    add_xp(u["id"], 10)

    return jsonify({
        "ok": True,
        "code": item,
        "message": "+10 XP"
    })

@app.route("/api/codes/<code_id>")
def one_code(code_id):
    items = load("codes")

    for item in items:
        if item.get("id") == code_id:
            item["views"] = item.get("views", 0) + 1
            save("codes", items)

            return jsonify({
                "ok": True,
                "code": item
            })

    return jsonify({"ok": False, "error": "کد پیدا نشد"}), 404

# =========================
# LIKE
# =========================

@app.route("/api/codes/<code_id>/like", methods=["POST"])
def like(code_id):
    u = require_user()

    if not u:
        return jsonify({"ok": False, "error": "ابتدا وارد شوید"}), 401

    likes = load("likes")
    codes_data = load("codes")

    target = None

    for code in codes_data:
        if code.get("id") == code_id:
            target = code
            break

    if not target:
        return jsonify({"ok": False, "error": "کد پیدا نشد"}), 404

    exists = any(
        x.get("code_id") == code_id and
        x.get("user_id") == u["id"]
        for x in likes
    )

    if exists:
        likes = [
            x for x in likes
            if not (
                x.get("code_id") == code_id and
                x.get("user_id") == u["id"]
            )
        ]

        target["likes"] = max(0, target.get("likes", 0) - 1)
        liked = False

    else:
        likes.append({
            "id": uuid.uuid4().hex,
            "code_id": code_id,
            "user_id": u["id"],
            "created_at": now()
        })

        target["likes"] = target.get("likes", 0) + 1
        liked = True

        owner = target.get("user_id")

        if owner and owner != u["id"]:
            notify(
                owner,
                "❤️ @" + u["username"] + " کد شما را لایک کرد"
            )

            add_xp(owner, 2)

    save("likes", likes)
    save("codes", codes_data)

    return jsonify({
        "ok": True,
        "liked": liked,
        "likes": target["likes"]
    })

# =========================
# COMMENTS
# =========================

@app.route("/api/codes/<code_id>/comments", methods=["GET", "POST"])
def comments(code_id):

    if request.method == "GET":

        result = [
            x for x in load("comments")
            if x.get("code_id") == code_id
        ]

        return jsonify({
            "ok": True,
            "comments": result
        })

    u = require_user()

    if not u:
        return jsonify({"ok": False, "error": "ابتدا وارد شوید"}), 401

    data = request.get_json(silent=True) or {}

    text = str(
        data.get("text", data.get("body", ""))
    ).strip()

    if not text:
        return jsonify({"ok": False, "error": "کامنت خالی است"}), 400

    item = {
        "id": uuid.uuid4().hex,
        "code_id": code_id,
        "user_id": u["id"],
        "username": u["username"],
        "text": text,
        "created_at": now()
    }

    comments_data = load("comments")
    comments_data.append(item)
    save("comments", comments_data)

    codes_data = load("codes")

    for code in codes_data:
        if code.get("id") == code_id:
            code["comments"] = code.get("comments", 0) + 1

            if code.get("user_id") != u["id"]:
                notify(
                    code.get("user_id"),
                    "💬 @" + u["username"] + " روی کد شما کامنت گذاشت"
                )

            break

    save("codes", codes_data)

    add_xp(u["id"], 1)

    return jsonify({
        "ok": True,
        "comment": item
    })

# =========================
# RANKING
# =========================

@app.route("/api/ranking")
def ranking():

    users = load("users")

    users.sort(
        key=lambda x: x.get("points", 0),
        reverse=True
    )

    result = []

    for i, u in enumerate(users, 1):
        result.append({
            "rank": i,
            "username": u.get("username"),
            "name": u.get("name"),
            "level": u.get("level", 1),
            "xp": u.get("xp", 0),
            "points": u.get("points", 0),
            "codes": u.get("codes", 0),
            "likes": u.get("likes", 0)
        })

    return jsonify({
        "ok": True,
        "ranking": result
    })

# =========================
# DISCUSSION
# =========================

@app.route("/api/discussions", methods=["GET", "POST"])
def discussions():

    if request.method == "GET":
        return jsonify({
            "ok": True,
            "discussions": load("discussions")
        })

    u = require_user()

    if not u:
        return jsonify({"ok": False, "error": "ابتدا وارد شوید"}), 401

    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    body = str(data.get("body", "")).strip()

    if not title or not body:
        return jsonify({"ok": False, "error": "عنوان و متن را وارد کن"}), 400

    item = {
        "id": uuid.uuid4().hex,
        "title": title,
        "body": body,
        "username": u["username"],
        "user_id": u["id"],
        "created_at": now()
    }

    items = load("discussions")
    items.insert(0, item)
    save("discussions", items)

    add_xp(u["id"], 5)

    return jsonify({
        "ok": True,
        "discussion": item
    })

# =========================
# ISSUES
# =========================

@app.route("/api/issues", methods=["GET", "POST"])
def issues():

    if request.method == "GET":
        return jsonify({
            "ok": True,
            "issues": load("issues")
        })

    u = require_user()

    if not u:
        return jsonify({"ok": False, "error": "ابتدا وارد شوید"}), 401

    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    body = str(data.get("body", "")).strip()

    if not title or not body:
        return jsonify({"ok": False, "error": "عنوان و متن را وارد کن"}), 400

    item = {
        "id": uuid.uuid4().hex,
        "title": title,
        "body": body,
        "username": u["username"],
        "user_id": u["id"],
        "status": "open",
        "created_at": now()
    }

    items = load("issues")
    items.insert(0, item)
    save("issues", items)

    add_xp(u["id"], 5)

    return jsonify({
        "ok": True,
        "issue": item
    })

# =========================
# NOTIFICATIONS
# =========================

@app.route("/api/notifications")
def notifications():

    u = require_user()

    if not u:
        return jsonify({"ok": False, "error": "ابتدا وارد شوید"}), 401

    result = [
        x for x in load("notifications")
        if x.get("user_id") == u["id"]
    ]

    return jsonify({
        "ok": True,
        "notifications": result
    })

@app.route("/api/notifications/read", methods=["POST"])
def read_notifications():

    u = require_user()

    if not u:
        return jsonify({"ok": False, "error": "ابتدا وارد شوید"}), 401

    items = load("notifications")

    for item in items:
        if item.get("user_id") == u["id"]:
            item["read"] = True

    save("notifications", items)

    return jsonify({"ok": True})

# =========================
# SEARCH
# =========================

@app.route("/api/search")
def search():

    q = request.args.get("q", "").strip().lower()

    if not q:
        return jsonify({
            "ok": True,
            "results": []
        })

    results = []

    for code in load("codes"):

        text = (
            str(code.get("title", "")) + " " +
            str(code.get("description", "")) + " " +
            str(code.get("language", "")) + " " +
            str(code.get("username", ""))
        ).lower()

        if q in text:
            results.append(code)

    return jsonify({
        "ok": True,
        "results": results
    })

# =========================
# STATS
# =========================

@app.route("/api/stats")
def stats():

    users = load("users")
    codes_data = load("codes")

    points = sum(
        x.get("points", 0)
        for x in users
    )

    views = sum(
        x.get("views", 0)
        for x in codes_data
    )

    return jsonify({
        "ok": True,
        "users": len(users),
        "codes": len(codes_data),
        "points": points,
        "views": views
    })

# =========================
# RUN
# =========================

if __name__ == "__main__":

    print()
    print("==========================================")
    print("       BLUE SINGLE CODE LAB v2")
    print("==========================================")
    print()
    print("AUTH       : ONLINE")
    print("PERSISTENT : ON")
    print("XP SYSTEM  : ON")
    print("RANKING    : ON")
    print("CODES      : ON")
    print("COMMENTS   : ON")
    print("LIKES      : ON")
    print("DISCUSSION : ON")
    print("ISSUES     : ON")
    print("SEARCH     : ON")
    print("NOTIFY     : ON")
    print()
    print("SERVER: http://127.0.0.1:8080")
    print()
    print("==========================================")

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
