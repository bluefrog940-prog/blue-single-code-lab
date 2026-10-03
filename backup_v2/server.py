from flask import Flask, request, jsonify, session, send_from_directory, redirect
import os
import json
import uuid
from datetime import datetime

app = Flask(__name__)

# =========================
# BLUE SINGLE CODE LAB
# =========================

app.secret_key = "BLUE_SINGLE_SECRET_2026_CHANGE_LATER"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
UPLOADS = os.path.join(BASE, "uploads")

os.makedirs(DATA, exist_ok=True)
os.makedirs(UPLOADS, exist_ok=True)


# =========================
# DATABASE FILES
# =========================

FILES = {
    "users": "users.json",
    "codes": "codes.json",
    "comments": "comments.json",
    "likes": "likes.json",
    "issues": "issues.json",
    "discussions": "discussions.json",
    "notifications": "notifications.json",
}


def load(name):
    path = os.path.join(DATA, FILES[name])

    if not os.path.exists(path):
        save(name, [])
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save(name, data):
    path = os.path.join(DATA, FILES[name])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =========================
# AUTH
# =========================

def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    users = load("users")

    for user in users:
        if user.get("id") == user_id:
            return user

    session.clear()
    return None


def user_public(user):
    if not user:
        return None

    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "name": user.get("name", ""),
        "display_name": user.get("display_name", ""),
        "bio": user.get("bio", ""),
        "points": user.get("points", 0),
        "codes": user.get("codes", 0),
        "created_at": user.get("created_at")
    }


def login_required():
    user = get_current_user()

    if not user:
        return None

    return user


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return send_from_directory(BASE, "index.html")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
@app.route("/dashboard.html")
def dashboard():
    return send_from_directory(BASE, "dashboard.html")


# =========================
# UPLOADS
# =========================

@app.route("/uploads/<path:name>")
def uploads(name):
    return send_from_directory(UPLOADS, name)


# =========================
# REGISTER
# =========================

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    name = str(data.get("name", username)).strip()

    if len(username) < 3:
        return jsonify({
            "ok": False,
            "error": "نام کاربری حداقل ۳ حرف باشد"
        }), 400

    if len(password) < 3:
        return jsonify({
            "ok": False,
            "error": "رمز عبور حداقل ۳ کاراکتر باشد"
        }), 400

    users = load("users")

    for user in users:
        if user.get("username", "").lower() == username.lower():
            return jsonify({
                "ok": False,
                "error": "این نام کاربری قبلاً ثبت شده"
            }), 409

    user = {
        "id": uuid.uuid4().hex,
        "username": username,
        "password": password,
        "name": name,
        "display_name": name,
        "bio": "",
        "points": 0,
        "codes": 0,
        "created_at": now()
    }

    users.append(user)
    save("users", users)

    # ورود خودکار بعد از ثبت نام
    session.clear()
    session["user_id"] = user["id"]

    return jsonify({
        "ok": True,
        "user": user_public(user)
    })


# =========================
# LOGIN
# =========================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    users = load("users")

    for user in users:

        if (
            user.get("username", "").lower() == username.lower()
            and user.get("password") == password
        ):

            session.clear()
            session["user_id"] = user["id"]

            return jsonify({
                "ok": True,
                "user": user_public(user)
            })

    return jsonify({
        "ok": False,
        "error": "نام کاربری یا رمز عبور اشتباه است"
    }), 401


# =========================
# LOGOUT
# =========================

@app.route("/api/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "ok": True
    })


# =========================
# CURRENT USER
# =========================

@app.route("/api/me")
def me():

    user = get_current_user()

    if not user:
        return jsonify({
            "ok": False,
            "logged_in": False,
            "user": None
        }), 401

    return jsonify({
        "ok": True,
        "logged_in": True,
        "user": user_public(user),

        # برای سازگاری با داشبورد قدیمی
        "id": user.get("id"),
        "username": user.get("username"),
        "name": user.get("name", ""),
        "display_name": user.get("display_name", ""),
        "bio": user.get("bio", ""),
        "points": user.get("points", 0),
        "codes": user.get("codes", 0)
    })


# =========================
# PROFILE
# =========================

@app.route("/api/profile", methods=["GET", "POST"])
def profile():

    user = login_required()

    if not user:
        return jsonify({
            "ok": False,
            "error": "ابتدا وارد حساب شوید"
        }), 401

    if request.method == "GET":
        return jsonify({
            "ok": True,
            "user": user_public(user)
        })

    data = request.get_json(silent=True) or {}

    users = load("users")

    for u in users:

        if u.get("id") == user.get("id"):

            if "name" in data:
                u["name"] = str(data["name"]).strip()

            if "display_name" in data:
                u["display_name"] = str(
                    data["display_name"]
                ).strip()

            if "bio" in data:
                u["bio"] = str(data["bio"]).strip()

            save("users", users)

            return jsonify({
                "ok": True,
                "user": user_public(u)
            })

    return jsonify({
        "ok": False,
        "error": "کاربر پیدا نشد"
    }), 404


# =========================
# CODES
# =========================

@app.route("/api/codes", methods=["GET", "POST"])
def codes():

    user = login_required()

    if request.method == "GET":

        all_codes = load("codes")

        return jsonify({
            "ok": True,
            "codes": all_codes
        })

    if not user:
        return jsonify({
            "ok": False,
            "error": "برای ارسال کد باید وارد شوید"
        }), 401

    data = request.form if request.form else (
        request.get_json(silent=True) or {}
    )

    title = str(data.get("title", "")).strip()
    language = str(data.get("language", "Text")).strip()
    description = str(data.get("description", "")).strip()
    code = str(data.get("code", "")).strip()

    if not title:
        return jsonify({
            "ok": False,
            "error": "عنوان کد را وارد کنید"
        }), 400

    if not code:
        return jsonify({
            "ok": False,
            "error": "کد خالی است"
        }), 400

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

    codes_data = load("codes")

    item = {
        "id": uuid.uuid4().hex,
        "title": title,
        "language": language,
        "description": description,
        "code": code,

        "image": image_url,
        "video": video_url,

        "image_url": image_url,
        "video_url": video_url,

        "username": user.get("username"),
        "user_id": user.get("id"),

        "likes": 0,
        "like_count": 0,
        "comments": 0,
        "views": 0,

        "created_at": now()
    }

    codes_data.insert(0, item)
    save("codes", codes_data)

    users = load("users")

    for u in users:
        if u.get("id") == user.get("id"):
            u["points"] = u.get("points", 0) + 10
            u["codes"] = u.get("codes", 0) + 1

    save("users", users)

    return jsonify({
        "ok": True,
        "code": item,
        "message": "+10 امتیاز"
    })


# =========================
# SINGLE CODE
# =========================

@app.route("/api/codes/<code_id>")
def single_code(code_id):

    codes_data = load("codes")

    for code in codes_data:

        if code.get("id") == code_id:

            code["views"] = code.get("views", 0) + 1

            save("codes", codes_data)

            return jsonify({
                "ok": True,
                "code": code
            })

    return jsonify({
        "ok": False,
        "error": "کد پیدا نشد"
    }), 404


# =========================
# LIKE
# =========================

@app.route("/api/codes/<code_id>/like", methods=["POST"])
def like_code(code_id):

    user = login_required()

    if not user:
        return jsonify({
            "ok": False,
            "error": "ابتدا وارد شوید"
        }), 401

    likes = load("likes")

    already = False

    for like in likes:
        if (
            like.get("code_id") == code_id
            and like.get("user_id") == user.get("id")
        ):
            already = True
            break

    codes_data = load("codes")

    target = None

    for code in codes_data:
        if code.get("id") == code_id:
            target = code
            break

    if not target:
        return jsonify({
            "ok": False,
            "error": "کد پیدا نشد"
        }), 404

    if already:

        likes = [
            x for x in likes
            if not (
                x.get("code_id") == code_id
                and x.get("user_id") == user.get("id")
            )
        ]

        target["likes"] = max(0, target.get("likes", 0) - 1)

    else:

        likes.append({
            "id": uuid.uuid4().hex,
            "code_id": code_id,
            "user_id": user.get("id"),
            "created_at": now()
        })

        target["likes"] = target.get("likes", 0) + 1

    target["like_count"] = target["likes"]

    save("likes", likes)
    save("codes", codes_data)

    return jsonify({
        "ok": True,
        "liked": not already,
        "likes": target["likes"]
    })


# =========================
# COMMENTS
# =========================

@app.route("/api/codes/<code_id>/comments", methods=["GET", "POST"])
def comments(code_id):

    if request.method == "GET":

        all_comments = load("comments")

        result = [
            c for c in all_comments
            if c.get("code_id") == code_id
        ]

        return jsonify({
            "ok": True,
            "comments": result
        })

    user = login_required()

    if not user:
        return jsonify({
            "ok": False,
            "error": "ابتدا وارد شوید"
        }), 401

    data = request.get_json(silent=True) or {}

    text = str(
        data.get("text", data.get("body", ""))
    ).strip()

    if not text:
        return jsonify({
            "ok": False,
            "error": "کامنت خالی است"
        }), 400

    all_comments = load("comments")

    comment = {
        "id": uuid.uuid4().hex,
        "code_id": code_id,
        "user_id": user.get("id"),
        "username": user.get("username"),
        "text": text,
        "body": text,
        "created_at": now()
    }

    all_comments.append(comment)
    save("comments", all_comments)

    return jsonify({
        "ok": True,
        "comment": comment
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

    for index, user in enumerate(users, 1):

        result.append({
            "rank": index,
            "username": user.get("username"),
            "name": user.get("name", ""),
            "points": user.get("points", 0),
            "codes": user.get("codes", 0)
        })

    return jsonify({
        "ok": True,
        "ranking": result
    })


# =========================
# DISCUSSIONS
# =========================

@app.route("/api/discussions", methods=["GET", "POST"])
def discussions():

    if request.method == "GET":

        return jsonify({
            "ok": True,
            "discussions": load("discussions")
        })

    user = login_required()

    if not user:
        return jsonify({
            "ok": False,
            "error": "ابتدا وارد شوید"
        }), 401

    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    body = str(data.get("body", "")).strip()

    if not title or not body:
        return jsonify({
            "ok": False,
            "error": "عنوان و متن را وارد کنید"
        }), 400

    discussions_data = load("discussions")

    item = {
        "id": uuid.uuid4().hex,
        "title": title,
        "body": body,
        "username": user.get("username"),
        "user_id": user.get("id"),
        "created_at": now()
    }

    discussions_data.insert(0, item)
    save("discussions", discussions_data)

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

    user = login_required()

    if not user:
        return jsonify({
            "ok": False,
            "error": "ابتدا وارد شوید"
        }), 401

    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    body = str(data.get("body", "")).strip()

    if not title or not body:
        return jsonify({
            "ok": False,
            "error": "عنوان و متن را وارد کنید"
        }), 400

    issues_data = load("issues")

    item = {
        "id": uuid.uuid4().hex,
        "title": title,
        "body": body,
        "username": user.get("username"),
        "user_id": user.get("id"),
        "status": "open",
        "created_at": now()
    }

    issues_data.insert(0, item)
    save("issues", issues_data)

    return jsonify({
        "ok": True,
        "issue": item
    })


# =========================
# NOTIFICATIONS
# =========================

@app.route("/api/notifications")
def notifications():

    user = login_required()

    if not user:
        return jsonify({
            "ok": False,
            "error": "ابتدا وارد شوید"
        }), 401

    all_notifications = load("notifications")

    result = [
        n for n in all_notifications
        if n.get("user_id") == user.get("id")
    ]

    return jsonify({
        "ok": True,
        "notifications": result
    })


@app.route("/api/notifications/read", methods=["POST"])
def notifications_read():

    user = login_required()

    if not user:
        return jsonify({
            "ok": False,
            "error": "ابتدا وارد شوید"
        }), 401

    all_notifications = load("notifications")

    for n in all_notifications:

        if n.get("user_id") == user.get("id"):
            n["read"] = True

    save("notifications", all_notifications)

    return jsonify({
        "ok": True
    })


# =========================
# STATS
# =========================

@app.route("/api/stats")
def stats():

    users = load("users")
    codes_data = load("codes")

    total_points = sum(
        u.get("points", 0)
        for u in users
    )

    total_views = sum(
        c.get("views", 0)
        for c in codes_data
    )

    return jsonify({
        "ok": True,

        "users": len(users),
        "codes": len(codes_data),
        "points": total_points,
        "total_points": total_points,
        "views": total_views,
        "total_views": total_views
    })


# =========================
# RUN
# =========================

if __name__ == "__main__":

    print()
    print("========================================")
    print("        BLUE SINGLE CODE LAB")
    print("========================================")
    print()
    print("SERVER: http://127.0.0.1:8080")
    print()
    print("AUTH / CODES / SEARCH / RANKING")
    print("LIKES / COMMENTS / ISSUES / DISCUSSIONS")
    print("NOTIFICATIONS / PROFILE / MEDIA")
    print()
    print("========================================")
    print()

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
