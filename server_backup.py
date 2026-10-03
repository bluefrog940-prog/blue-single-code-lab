from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime
import os
import json
import uuid

app = Flask(__name__)

app.secret_key = "BLUE_SINGLE_CHANGE_THIS_SECRET"

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
UPLOADS = os.path.join(BASE, "uploads")

os.makedirs(DATA, exist_ok=True)
os.makedirs(UPLOADS, exist_ok=True)

USERS = os.path.join(DATA, "users.json")
CODES = os.path.join(DATA, "codes.json")
COMMENTS = os.path.join(DATA, "comments.json")
LIKES = os.path.join(DATA, "likes.json")
ISSUES = os.path.join(DATA, "issues.json")
DISCUSSIONS = os.path.join(DATA, "discussions.json")
NOTIFICATIONS = os.path.join(DATA, "notifications.json")

IMAGE_EXT = {"jpg", "jpeg", "png", "gif", "webp"}
VIDEO_EXT = {"mp4", "webm", "mov", "m4v"}


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load(path, default):
    if not os.path.exists(path):
        save(path, default)
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


def extension(filename):
    if "." not in filename:
        return ""

    return filename.rsplit(".", 1)[1].lower()


def upload_file(file, allowed):
    if not file or not file.filename:
        return ""

    ext = extension(file.filename)

    if ext not in allowed:
        return ""

    filename = secure_filename(file.filename)

    if not filename:
        filename = "file"

    filename = uuid.uuid4().hex + "_" + filename

    path = os.path.join(UPLOADS, filename)

    file.save(path)

    return "/uploads/" + filename


def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    users = load(USERS, [])

    for user in users:
        if user["id"] == user_id:
            return user

    return None


def login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if not current_user():
            return jsonify({
                "ok": False,
                "message": "ابتدا وارد حساب شو."
            }), 401

        return func(*args, **kwargs)

    return wrapper


def add_notification(user_id, message):

    notifications = load(
        NOTIFICATIONS,
        []
    )

    notifications.insert(
        0,
        {
            "id": uuid.uuid4().hex,
            "user_id": user_id,
            "message": message,
            "read": False,
            "created_at": now()
        }
    )

    save(
        NOTIFICATIONS,
        notifications[:500]
    )


# ---------------- HOME ----------------

@app.route("/")
def home():

    return send_from_directory(
        BASE,
        "index.html"
    )


@app.route("/dashboard")
@app.route("/dashboard.html")
def dashboard():

    return send_from_directory(
        BASE,
        "dashboard.html"
    )


@app.route("/uploads/<path:name>")
def uploads(name):

    return send_from_directory(
        UPLOADS,
        name
    )


# ---------------- AUTH ----------------

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json() or {}

    username = str(
        data.get("username", "")
    ).strip()

    password = str(
        data.get("password", "")
    )

    if len(username) < 3:
        return jsonify({
            "ok": False,
            "message": "نام کاربری حداقل ۳ حرف باشد."
        }), 400

    if len(password) < 4:
        return jsonify({
            "ok": False,
            "message": "رمز حداقل ۴ کاراکتر باشد."
        }), 400

    users = load(
        USERS,
        []
    )

    for user in users:

        if user["username"].lower() == username.lower():

            return jsonify({
                "ok": False,
                "message": "این نام کاربری قبلاً ثبت شده."
            }), 400

    user = {
        "id": uuid.uuid4().hex,
        "username": username,
        "password": generate_password_hash(password),
        "display_name": username,
        "bio": "عضو BLUE SINGLE CODE LAB",
        "avatar": "",
        "points": 0,
        "codes_count": 0,
        "created_at": now()
    }

    users.append(user)

    save(
        USERS,
        users
    )

    session["user_id"] = user["id"]

    return jsonify({
        "ok": True,
        "message": "حساب ساخته شد."
    })


@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json() or {}

    username = str(
        data.get("username", "")
    ).strip()

    password = str(
        data.get("password", "")
    )

    users = load(
        USERS,
        []
    )

    for user in users:

        if user["username"].lower() == username.lower():

            if check_password_hash(
                user["password"],
                password
            ):

                session["user_id"] = user["id"]

                return jsonify({
                    "ok": True,
                    "message": "ورود موفق."
                })

            break

    return jsonify({
        "ok": False,
        "message": "نام کاربری یا رمز اشتباه است."
    }), 401


@app.route("/api/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "ok": True
    })


# ---------------- USER ----------------

@app.route("/api/me")
@login_required
def me():

    user = current_user()

    return jsonify({
        "ok": True,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "bio": user["bio"],
            "avatar": user["avatar"],
            "points": user["points"],
            "codes_count": user["codes_count"],
            "created_at": user["created_at"]
        }
    })


@app.route("/api/profile", methods=["POST"])
@login_required
def profile():

    user = current_user()

    display_name = request.form.get(
        "display_name",
        ""
    ).strip()

    bio = request.form.get(
        "bio",
        ""
    ).strip()

    avatar = request.files.get(
        "avatar"
    )

    users = load(
        USERS,
        []
    )

    for item in users:

        if item["id"] == user["id"]:

            if display_name:
                item["display_name"] = display_name

            item["bio"] = bio

            if avatar and avatar.filename:

                avatar_url = upload_file(
                    avatar,
                    IMAGE_EXT
                )

                if not avatar_url:

                    return jsonify({
                        "ok": False,
                        "message": "فرمت عکس مجاز نیست."
                    }), 400

                item["avatar"] = avatar_url

            save(
                USERS,
                users
            )

            return jsonify({
                "ok": True,
                "message": "پروفایل ذخیره شد."
            })

    return jsonify({
        "ok": False,
        "message": "کاربر پیدا نشد."
    }), 404


# ---------------- CODES ----------------

@app.route("/api/codes", methods=["POST"])
@login_required
def add_code():

    user = current_user()

    title = request.form.get(
        "title",
        ""
    ).strip()

    language = request.form.get(
        "language",
        "Other"
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    code = request.form.get(
        "code",
        ""
    )

    if not title:

        return jsonify({
            "ok": False,
            "message": "عنوان کد را وارد کن."
        }), 400

    if not code.strip():

        return jsonify({
            "ok": False,
            "message": "کد را وارد کن."
        }), 400

    image = request.files.get(
        "image"
    )

    video = request.files.get(
        "video"
    )

    image_url = ""
    video_url = ""

    if image and image.filename:

        image_url = upload_file(
            image,
            IMAGE_EXT
        )

        if not image_url:

            return jsonify({
                "ok": False,
                "message": "فرمت عکس مجاز نیست."
            }), 400

    if video and video.filename:

        video_url = upload_file(
            video,
            VIDEO_EXT
        )

        if not video_url:

            return jsonify({
                "ok": False,
                "message": "فرمت ویدیو مجاز نیست."
            }), 400

    codes = load(
        CODES,
        []
    )

    users = load(
        USERS,
        []
    )

    new_code = {
        "id": uuid.uuid4().hex,
        "title": title,
        "language": language,
        "description": description,
        "code": code,
        "author": user["username"],
        "author_id": user["id"],
        "image": image_url,
        "video": video_url,
        "points": 10,
        "likes": 0,
        "views": 0,
        "created_at": now()
    }

    codes.insert(
        0,
        new_code
    )

    for item in users:

        if item["id"] == user["id"]:

            item["points"] += 10
            item["codes_count"] += 1

            break

    save(
        CODES,
        codes
    )

    save(
        USERS,
        users
    )

    return jsonify({
        "ok": True,
        "message": "کد ثبت شد! +۱۰ امتیاز",
        "code": new_code
    })


@app.route("/api/codes", methods=["GET"])
def get_codes():

    codes = load(
        CODES,
        []
    )

    query = request.args.get(
        "q",
        ""
    ).strip().lower()

    language = request.args.get(
        "language",
        ""
    ).strip().lower()

    result = []

    for code in codes:

        if query:

            text = (
                code["title"]
                + " "
                + code["description"]
                + " "
                + code["code"]
                + " "
                + code["author"]
            ).lower()

            if query not in text:
                continue

        if language:

            if code["language"].lower() != language:
                continue

        result.append(code)

    return jsonify({
        "ok": True,
        "codes": result
    })


@app.route("/api/codes/<code_id>")
def get_code(code_id):

    codes = load(
        CODES,
        []
    )

    for code in codes:

        if code["id"] == code_id:

            code["views"] += 1

            save(
                CODES,
                codes
            )

            return jsonify({
                "ok": True,
                "code": code
            })

    return jsonify({
        "ok": False,
        "message": "کد پیدا نشد."
    }), 404


# ---------------- LIKES ----------------

@app.route("/api/codes/<code_id>/like", methods=["POST"])
@login_required
def like_code(code_id):

    user = current_user()

    likes = load(
        LIKES,
        []
    )

    exists = any(
        x["code_id"] == code_id
        and x["user_id"] == user["id"]
        for x in likes
    )

    codes = load(
        CODES,
        []
    )

    target = None

    for code in codes:

        if code["id"] == code_id:
            target = code
            break

    if not target:

        return jsonify({
            "ok": False,
            "message": "کد پیدا نشد."
        }), 404

    if exists:

        likes = [
            x for x in likes
            if not (
                x["code_id"] == code_id
                and x["user_id"] == user["id"]
            )
        ]

        target["likes"] = max(
            0,
            target["likes"] - 1
        )

        liked = False

    else:

        likes.append({
            "id": uuid.uuid4().hex,
            "code_id": code_id,
            "user_id": user["id"]
        })

        target["likes"] += 1

        liked = True

        if target["author_id"] != user["id"]:

            add_notification(
                target["author_id"],
                "کدت یک لایک جدید گرفت ❤️"
            )

    save(
        LIKES,
        likes
    )

    save(
        CODES,
        codes
    )

    return jsonify({
        "ok": True,
        "liked": liked,
        "likes": target["likes"]
    })


# ---------------- COMMENTS ----------------

@app.route("/api/codes/<code_id>/comments")
def get_comments(code_id):

    comments = load(
        COMMENTS,
        []
    )

    result = [
        x for x in comments
        if x["code_id"] == code_id
    ]

    return jsonify({
        "ok": True,
        "comments": result
    })


@app.route("/api/codes/<code_id>/comments", methods=["POST"])
@login_required
def add_comment(code_id):

    user = current_user()

    data = request.get_json() or {}

    text = str(
        data.get("text", "")
    ).strip()

    if not text:

        return jsonify({
            "ok": False,
            "message": "متن نظر خالی است."
        }), 400

    comments = load(
        COMMENTS,
        []
    )

    comment = {
        "id": uuid.uuid4().hex,
        "code_id": code_id,
        "user": user["username"],
        "user_id": user["id"],
        "text": text,
        "created_at": now()
    }

    comments.append(comment)

    save(
        COMMENTS,
        comments
    )

    return jsonify({
        "ok": True,
        "comment": comment
    })


# ---------------- RANKING ----------------

@app.route("/api/ranking")
def ranking():

    users = load(
        USERS,
        []
    )

    result = []

    for user in users:

        result.append({
            "username": user["username"],
            "display_name": user["display_name"],
            "points": user["points"],
            "codes_count": user["codes_count"],
            "avatar": user["avatar"]
        })

    result.sort(
        key=lambda x: (
            -x["points"],
            -x["codes_count"],
            x["username"].lower()
        )
    )

    for number, user in enumerate(
        result,
        start=1
    ):
        user["rank"] = number

    return jsonify({
        "ok": True,
        "ranking": result
    })


# ---------------- DISCUSSIONS ----------------

@app.route("/api/discussions")
def get_discussions():

    discussions = load(
        DISCUSSIONS,
        []
    )

    return jsonify({
        "ok": True,
        "discussions": discussions
    })


@app.route("/api/discussions", methods=["POST"])
@login_required
def add_discussion():

    user = current_user()

    data = request.get_json() or {}

    title = str(
        data.get("title", "")
    ).strip()

    text = str(
        data.get("text", "")
    ).strip()

    if not title or not text:

        return jsonify({
            "ok": False,
            "message": "عنوان و متن را وارد کن."
        }), 400

    discussions = load(
        DISCUSSIONS,
        []
    )

    discussion = {
        "id": uuid.uuid4().hex,
        "title": title,
        "text": text,
        "author": user["username"],
        "author_id": user["id"],
        "created_at": now(),
        "replies": 0
    }

    discussions.insert(
        0,
        discussion
    )

    save(
        DISCUSSIONS,
        discussions
    )

    return jsonify({
        "ok": True,
        "discussion": discussion
    })


# ---------------- ISSUES ----------------

@app.route("/api/issues")
@login_required
def get_issues():

    user = current_user()

    issues = load(
        ISSUES,
        []
    )

    result = [
        x for x in issues
        if x["author_id"] == user["id"]
    ]

    return jsonify({
        "ok": True,
        "issues": result
    })


@app.route("/api/issues", methods=["POST"])
@login_required
def add_issue():

    user = current_user()

    data = request.get_json() or {}

    title = str(
        data.get("title", "")
    ).strip()

    text = str(
        data.get("text", "")
    ).strip()

    issue_type = str(
        data.get("type", "Question")
    ).strip()

    if not title or not text:

        return jsonify({
            "ok": False,
            "message": "عنوان و توضیح را وارد کن."
        }), 400

    issues = load(
        ISSUES,
        []
    )

    issue = {
        "id": uuid.uuid4().hex,
        "title": title,
        "text": text,
        "type": issue_type,
        "status": "OPEN",
        "author": user["username"],
        "author_id": user["id"],
        "created_at": now()
    }

    issues.insert(
        0,
        issue
    )

    save(
        ISSUES,
        issues
    )

    return jsonify({
        "ok": True,
        "issue": issue
    })


# ---------------- NOTIFICATIONS ----------------

@app.route("/api/notifications")
@login_required
def notifications():

    user = current_user()

    items = load(
        NOTIFICATIONS,
        []
    )

    result = [
        x for x in items
        if x["user_id"] == user["id"]
    ]

    return jsonify({
        "ok": True,
        "notifications": result[:50]
    })


@app.route("/api/notifications/read", methods=["POST"])
@login_required
def notifications_read():

    user = current_user()

    items = load(
        NOTIFICATIONS,
        []
    )

    for item in items:

        if item["user_id"] == user["id"]:

            item["read"] = True

    save(
        NOTIFICATIONS,
        items
    )

    return jsonify({
        "ok": True
    })


# ---------------- SITE STATS ----------------

@app.route("/api/stats")
def stats():

    users = load(
        USERS,
        []
    )

    codes = load(
        CODES,
        []
    )

    total_points = sum(
        x["points"]
        for x in users
    )

    total_views = sum(
        x["views"]
        for x in codes
    )

    return jsonify({
        "ok": True,
        "users": len(users),
        "codes": len(codes),
        "points": total_points,
        "views": total_views
    })


# ---------------- RUN ----------------

if __name__ == "__main__":

    print("")
    print("========================================")
    print("        BLUE SINGLE CODE LAB")
    print("========================================")
    print("")
    print("SERVER: http://127.0.0.1:8080")
    print("")
    print("Features:")
    print("AUTH / CODES / SEARCH / RANKING")
    print("LIKES / COMMENTS / ISSUES / DISCUSSIONS")
    print("NOTIFICATIONS / PROFILE / MEDIA")
    print("")
    print("========================================")
    print("")

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False
    )
