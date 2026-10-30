import os
import sqlite3
import hashlib
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "riragia.db"
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="Riragia Social Hub", page_icon="🌍", layout="wide")

# ----------------------------- Database ------------------------------------
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            faculty TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            profile_picture TEXT DEFAULT '',
            role TEXT DEFAULT 'user',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            caption TEXT DEFAULT '',
            media_path TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            price TEXT DEFAULT '',
            contact TEXT DEFAULT '',
            image_path TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            admin_note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placement TEXT NOT NULL,
            headline TEXT NOT NULL,
            body TEXT DEFAULT '',
            sponsor TEXT DEFAULT '',
            active INTEGER DEFAULT 1
        );
        """)
        # Demo sponsored content. Replace these with real approved ad campaigns later.
        count = con.execute("SELECT COUNT(*) FROM ads").fetchone()[0]
        if count == 0:
            con.executemany(
                "INSERT INTO ads (placement, headline, body, sponsor) VALUES (?, ?, ?, ?)",
                [
                    ("feed", "Sponsored • Campus opportunity", "Promote a service, event or opportunity to the Riragia community.", "Riragia Partners"),
                    ("reels", "Sponsored • Discover something new", "A short sponsored video slot can appear between community reels.", "Riragia Partners"),
                ],
            )
        # Create a demo admin only when no admin exists.
        admin = con.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
        if not admin:
            con.execute(
                """INSERT OR IGNORE INTO users
                (username,password_hash,full_name,faculty,bio,role,created_at)
                VALUES (?,?,?,?,?,?,?)""",
                ("admin", password_hash("ChangeMe123!"), "Riragia Admin",
                 "Administration", "Platform administrator", "admin", now())
            )

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def password_hash(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def save_upload(uploaded, prefix):
    if uploaded is None:
        return ""
    suffix = Path(uploaded.name).suffix.lower()
    allowed = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov"}
    if suffix not in allowed:
        st.error("Unsupported file type. Use JPG, PNG, WEBP, GIF, MP4 or MOV.")
        return ""
    name = f"{prefix}_{uuid.uuid4().hex}{suffix}"
    target = UPLOAD_DIR / name
    target.write_bytes(uploaded.getbuffer())
    return str(target.relative_to(APP_DIR))

def media(path, caption=""):
    if not path:
        return
    full = APP_DIR / path
    if not full.exists():
        st.caption("Media file is missing.")
        return
    ext = full.suffix.lower()
    if ext in {".mp4", ".mov"}:
        st.video(str(full))
    else:
        st.image(str(full), caption=caption, use_container_width=True)

def user_by_id(user_id):
    with db() as con:
        return con.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

def get_ads(placement):
    with db() as con:
        return con.execute(
            "SELECT * FROM ads WHERE placement=? AND active=1 ORDER BY id", (placement,)
        ).fetchall()

def show_ad(placement):
    ads = get_ads(placement)
    if ads:
        ad = ads[0]
        with st.container(border=True):
            st.caption("📣 SPONSORED")
            st.markdown(f"**{ad['headline']}**")
            st.write(ad["body"])
            st.caption(f"Advertiser: {ad['sponsor']}")

def require_login():
    if not st.session_state.get("user_id"):
        st.info("Please log in or create an account to use Riragia Social Hub.")
        return False
    return True

init_db()

# ----------------------------- Sidebar / Auth ------------------------------
with st.sidebar:
    st.markdown("# 🌍 Riragia")
    st.caption("Social Hub")
    if st.session_state.get("user_id"):
        current = user_by_id(st.session_state.user_id)
        if current:
            st.write(f"Signed in as **{current['full_name']}**")
            st.caption(f"@{current['username']} · {current['role']}")
        if st.button("Log out", use_container_width=True):
            for key in ("user_id", "page", "profile_target"):
                st.session_state.pop(key, None)
            st.rerun()
    else:
        auth_tab = st.radio("Account", ["Log in", "Create account"])
        if auth_tab == "Log in":
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", use_container_width=True)
            if submitted:
                with db() as con:
                    row = con.execute(
                        "SELECT * FROM users WHERE username=? AND password_hash=?",
                        (username.strip(), password_hash(password))
                    ).fetchone()
                if row:
                    st.session_state.user_id = row["id"]
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")
        else:
            with st.form("register_form"):
                full_name = st.text_input("Full name")
                username = st.text_input("Choose a username")
                faculty = st.text_input("Faculty")
                password = st.text_input("Password", type="password")
                confirm = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Create account", use_container_width=True)
            if submitted:
                if not full_name.strip() or not username.strip() or not password:
                    st.error("Please complete your name, username and password.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                elif len(password) < 8:
                    st.error("Use a password with at least 8 characters.")
                else:
                    try:
                        with db() as con:
                            con.execute(
                                """INSERT INTO users
                                (username,password_hash,full_name,faculty,created_at)
                                VALUES (?,?,?,?,?)""",
                                (username.strip(), password_hash(password), full_name.strip(),
                                 faculty.strip(), now())
                            )
                        st.success("Account created. You can now log in.")
                    except sqlite3.IntegrityError:
                        st.error("That username is already taken.")

if not st.session_state.get("user_id"):
    st.title("🌍 Riragia Social Hub")
    st.subheader("Your campus. Your community. Your marketplace.")
    st.write("Connect with friends, share posts and reels, message people, and discover community listings.")
    st.info("Create an account in the sidebar to get started.")
    st.markdown("**First-run admin demo account**")
    st.code("Username: admin\nPassword: ChangeMe123!")
    st.warning("Change the demo admin password before using this app beyond local testing.")
    st.stop()

me = user_by_id(st.session_state.user_id)
is_admin = me["role"] == "admin"

# Navigation
pages = ["Feeds", "Reels", "Messages", "Marketplace", "Profile"]
if is_admin:
    pages.append("Admin")
with st.sidebar:
    st.divider()
    page = st.radio("Navigate", pages, key="navigation")
st.title("🌍 Riragia Social Hub")
st.caption("Connect • Share • Discover")

# -------------------------------- Feeds -------------------------------------
if page == "Feeds":
    st.header("📰 Feeds")
    with st.expander("＋ Create a post", expanded=False):
        with st.form("create_post"):
            caption = st.text_area("What's happening?")
            upload = st.file_uploader("Add a photo or video", type=["png","jpg","jpeg","webp","gif","mp4","mov"], key="feed_upload")
            submitted = st.form_submit_button("Publish post")
        if submitted:
            path = save_upload(upload, "post")
            with db() as con:
                con.execute(
                    "INSERT INTO posts(user_id,kind,caption,media_path,created_at) VALUES (?,?,?,?,?)",
                    (me["id"], "post", caption, path, now())
                )
            st.success("Your post has been published.")
            st.rerun()

    with db() as con:
        posts = con.execute("""
            SELECT posts.*, users.full_name, users.username, users.faculty
            FROM posts JOIN users ON users.id=posts.user_id
            WHERE posts.kind='post' ORDER BY posts.id DESC
        """).fetchall()
    if not posts:
        st.info("No posts yet. Be the first to share something.")
    for i, post in enumerate(posts):
        if i == 2:
            show_ad("feed")
        with st.container(border=True):
            st.markdown(f"**{post['full_name']}**  ·  @{post['username']}")
            st.caption(f"{post['faculty'] or 'Riragia community'} · {post['created_at']}")
            if post["caption"]:
                st.write(post["caption"])
            media(post["media_path"])
    if len(posts) < 3:
        show_ad("feed")

# -------------------------------- Reels -------------------------------------
elif page == "Reels":
    st.header("🎬 Reels")
    st.write("Short videos from friends and creators in the Riragia community.")
    with st.expander("＋ Upload a reel"):
        with st.form("create_reel"):
            caption = st.text_area("Caption", key="reel_caption")
            upload = st.file_uploader("Choose a video", type=["mp4","mov"], key="reel_upload")
            submitted = st.form_submit_button("Publish reel")
        if submitted:
            if upload is None:
                st.error("Please select a video.")
            else:
                path = save_upload(upload, "reel")
                with db() as con:
                    con.execute(
                        "INSERT INTO posts(user_id,kind,caption,media_path,created_at) VALUES (?,?,?,?,?)",
                        (me["id"], "reel", caption, path, now())
                    )
                st.success("Your reel has been published.")
                st.rerun()
    with db() as con:
        reels = con.execute("""
            SELECT posts.*, users.full_name, users.username
            FROM posts JOIN users ON users.id=posts.user_id
            WHERE posts.kind='reel' ORDER BY posts.id DESC
        """).fetchall()
    if not reels:
        st.info("No reels yet. Upload the first community reel.")
    for i, reel in enumerate(reels):
        if i == 2:
            show_ad("reels")
        with st.container(border=True):
            st.markdown(f"**{reel['full_name']}** · @{reel['username']}")
            if reel["caption"]:
                st.write(reel["caption"])
            media(reel["media_path"])
            st.caption(reel["created_at"])
    if len(reels) < 3:
        show_ad("reels")

# -------------------------------- Messages ----------------------------------
elif page == "Messages":
    st.header("✉️ Messages")
    with db() as con:
        people = con.execute("SELECT id,full_name,username FROM users WHERE id != ? ORDER BY full_name", (me["id"],)).fetchall()
    if not people:
        st.info("Other users will appear here after they create accounts.")
    else:
        choices = {f"{p['full_name']} (@{p['username']})": p["id"] for p in people}
        selected_label = st.selectbox("Conversation", list(choices.keys()))
        other_id = choices[selected_label]
        with db() as con:
            msgs = con.execute("""
                SELECT messages.*, s.full_name AS sender_name
                FROM messages JOIN users s ON s.id=messages.sender_id
                WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
                ORDER BY messages.id
            """, (me["id"], other_id, other_id, me["id"])).fetchall()
        for msg in msgs:
            prefix = "You" if msg["sender_id"] == me["id"] else msg["sender_name"]
            st.markdown(f"**{prefix}** · {msg['created_at']}")
            st.write(msg["body"])
            st.divider()
        with st.form("send_message", clear_on_submit=True):
            body = st.text_input("Write a message")
            sent = st.form_submit_button("Send")
        if sent and body.strip():
            with db() as con:
                con.execute(
                    "INSERT INTO messages(sender_id,receiver_id,body,created_at) VALUES (?,?,?,?)",
                    (me["id"], other_id, body.strip(), now())
                )
            st.rerun()

# ------------------------------- Marketplace -------------------------------
elif page == "Marketplace":
    st.header("🛍️ Marketplace")
    st.write("Listings are reviewed by Riragia administrators before they become public.")
    with st.expander("＋ Submit a product for approval"):
        with st.form("submit_product"):
            title = st.text_input("Product name")
            description = st.text_area("Description")
            price = st.text_input("Price (e.g. KSh 2,500)")
            contact = st.text_input("Contact (phone, email or username)")
            image_file = st.file_uploader("Product photo", type=["png","jpg","jpeg","webp"], key="product_image")
            submitted = st.form_submit_button("Submit for admin review")
        if submitted:
            if not title.strip() or not description.strip() or not contact.strip():
                st.error("Product name, description and contact are required.")
            else:
                path = save_upload(image_file, "product")
                with db() as con:
                    con.execute("""
                        INSERT INTO products(user_id,title,description,price,contact,image_path,status,created_at)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (me["id"], title.strip(), description.strip(), price.strip(),
                          contact.strip(), path, "pending", now()))
                st.success("Submitted. It will appear publicly after admin approval.")
                st.rerun()
    with db() as con:
        products = con.execute("""
            SELECT products.*, users.full_name, users.username
            FROM products JOIN users ON users.id=products.user_id
            WHERE products.status='approved' ORDER BY products.id DESC
        """).fetchall()
    st.subheader("Approved products")
    if not products:
        st.info("No approved products yet.")
    for product in products:
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                media(product["image_path"])
            with c2:
                st.markdown(f"**{product['title']}**")
                st.write(product["description"])
                if product["price"]:
                    st.markdown(f"**Price:** {product['price']}")
                st.caption(f"Seller: {product['full_name']} · @{product['username']}")
                st.write(f"**Contact seller:** {product['contact']}")
    with db() as con:
        mine = con.execute("SELECT * FROM products WHERE user_id=? ORDER BY id DESC", (me["id"],)).fetchall()
    if mine:
        st.subheader("Your submissions")
        for item in mine:
            st.write(f"**{item['title']}** — {item['status'].title()}")
            if item["admin_note"]:
                st.caption(f"Admin note: {item['admin_note']}")

# -------------------------------- Profile -----------------------------------
elif page == "Profile":
    st.header("👤 Profile")
    with st.form("edit_profile"):
        full_name = st.text_input("Name", value=me["full_name"])
        faculty = st.text_input("Faculty", value=me["faculty"])
        bio = st.text_area("About you", value=me["bio"])
        picture = st.file_uploader("Update profile picture", type=["png","jpg","jpeg","webp"], key="profile_pic")
        saved = st.form_submit_button("Save profile")
    if saved:
        pic_path = save_upload(picture, "profile") if picture else me["profile_picture"]
        with db() as con:
            con.execute(
                "UPDATE users SET full_name=?,faculty=?,bio=?,profile_picture=? WHERE id=?",
                (full_name.strip(), faculty.strip(), bio.strip(), pic_path, me["id"])
            )
        st.success("Profile updated.")
        st.rerun()
    me = user_by_id(st.session_state.user_id)
    left, right = st.columns([1, 3])
    with left:
        if me["profile_picture"]:
            media(me["profile_picture"])
        else:
            st.markdown("### 🙂")
    with right:
        st.subheader(me["full_name"])
        st.write(f"**Faculty:** {me['faculty'] or 'Not added'}")
        st.write(me["bio"])
        st.caption(f"@{me['username']}")
    st.divider()
    st.subheader("Your posts and reels")
    with db() as con:
        mine = con.execute("SELECT * FROM posts WHERE user_id=? ORDER BY id DESC", (me["id"],)).fetchall()
    if not mine:
        st.info("Your posts and reels will appear here.")
    for item in mine:
        with st.container(border=True):
            st.caption(f"{item['kind'].title()} · {item['created_at']}")
            st.write(item["caption"])
            media(item["media_path"])

# -------------------------------- Admin -------------------------------------
elif page == "Admin":
    st.header("🛡️ Admin dashboard")
    st.warning("Review each listing carefully. Approval here means the admin has checked the listing; it is not a guarantee of product quality or seller identity.")
    with db() as con:
        pending = con.execute("""
            SELECT products.*, users.full_name, users.username
            FROM products JOIN users ON users.id=products.user_id
            WHERE products.status='pending' ORDER BY products.id
        """).fetchall()
    st.subheader(f"Pending product approvals ({len(pending)})")
    if not pending:
        st.success("No products are waiting for review.")
    for item in pending:
        with st.container(border=True):
            st.markdown(f"**{item['title']}** — submitted by {item['full_name']} (@{item['username']})")
            media(item["image_path"])
            st.write(item["description"])
            st.write(f"Price: {item['price'] or 'Not provided'}")
            st.write(f"Seller contact: {item['contact']}")
            with st.form(f"review_{item['id']}"):
                note = st.text_input("Admin note (optional)", key=f"note_{item['id']}")
                c1, c2 = st.columns(2)
                approve = c1.form_submit_button("Approve listing", use_container_width=True)
                reject = c2.form_submit_button("Reject listing", use_container_width=True)
            if approve or reject:
                status = "approved" if approve else "rejected"
                with db() as con:
                    con.execute(
                        "UPDATE products SET status=?,admin_note=? WHERE id=?",
                        (status, note.strip(), item["id"])
                    )
                st.success(f"Listing {status}.")
                st.rerun()

    st.divider()
    st.subheader("Manage sponsored placements")
    with db() as con:
        ads = con.execute("SELECT * FROM ads ORDER BY id").fetchall()
    for ad in ads:
        with st.container(border=True):
            st.write(f"**{ad['placement'].title()} ad:** {ad['headline']}")
            st.caption(f"{ad['sponsor']} · {'Active' if ad['active'] else 'Paused'}")
            if st.button("Pause ad" if ad["active"] else "Activate ad", key=f"toggle_ad_{ad['id']}"):
                with db() as con:
                    con.execute("UPDATE ads SET active=? WHERE id=?", (0 if ad["active"] else 1, ad["id"]))
                st.rerun()
    with st.form("new_ad"):
        st.write("Add a sponsored placement")
        placement = st.selectbox("Placement", ["feed", "reels"])
        headline = st.text_input("Headline")
        ad_body = st.text_area("Ad description")
        sponsor = st.text_input("Advertiser")
        add_ad = st.form_submit_button("Add ad")
    if add_ad:
        if headline.strip():
            with db() as con:
                con.execute(
                    "INSERT INTO ads(placement,headline,body,sponsor) VALUES (?,?,?,?)",
                    (placement, headline.strip(), ad_body.strip(), sponsor.strip())
                )
            st.success("Ad added.")
            st.rerun()
        else:
            st.error("Enter an ad headline.")

st.sidebar.divider()
st.sidebar.caption("Riragia Social Hub · First version")
