"""
Grind Construction Services — Weekly Social Media Automation v4
Runs every Monday at 9am Eastern via Render.com cron job.
Generates 14 posts (7 LinkedIn + 7 Instagram) using REAL GRIND JOB PHOTOS.
Emails a preview to the configured notification email.

v4 — Uses Grind's own job site photos. No stock photos. No AI images. 100% authentic.
"""

import os
import io
import glob
import random
import smtplib
import base64
import requests
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

# ============ CONFIGURATION ============
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")

BRAND_WEBSITE = "grindconstructionservices.com"
BRAND_PHONE = "845-415-4609"
BRAND_EMAIL = "mike@grindconstructionservices.com"
LOGO_PATH = "logo.png"
PHOTOS_DIR = "photos"

if not OPENAI_API_KEY:
    raise SystemExit("ERROR: OPENAI_API_KEY environment variable not set")
if not NOTIFY_EMAIL:
    raise SystemExit("ERROR: NOTIFY_EMAIL environment variable not set")

client = OpenAI(api_key=OPENAI_API_KEY)

# ============ CONTENT PILLARS ============
PILLARS = [
    {
        "id": 1,
        "name": "Founder Authority",
        "focus": "Mike's industry POV, credibility, lessons learned from years in the field",
        "tone": "confident, direct, plain-spoken construction voice"
    },
    {
        "id": 2,
        "name": "Scope Review / Red Flags",
        "focus": "Common traps in bid packages that contractors miss before submitting",
        "tone": "practical warning, no jargon, example-driven"
    },
    {
        "id": 3,
        "name": "Ironclad Education",
        "focus": "How Ironclad scope reviews work, what they catch, why they save money",
        "tone": "explanatory but grounded, not salesy"
    },
    {
        "id": 4,
        "name": "Estimating and Bid Strategy",
        "focus": "Pricing tactics, decision frameworks, margin protection before you bid",
        "tone": "tactical, actionable, contractor-to-contractor"
    },
    {
        "id": 5,
        "name": "AI in Construction",
        "focus": "Practical AI use in bid review and estimating — not hype, what actually works",
        "tone": "grounded, skeptical of hype, focused on real applications"
    },
    {
        "id": 6,
        "name": "Case Studies / Wins",
        "focus": "Anonymized real stories of scope issues Ironclad caught before bids went out",
        "tone": "narrative, specific, lesson-driven"
    },
    {
        "id": 7,
        "name": "Industry News / Intel",
        "focus": "Material costs, labor trends, regulatory shifts affecting contractors right now",
        "tone": "informed commentary, practical implications for the field"
    },
    {
        "id": 8,
        "name": "Behind the Scenes",
        "focus": "How Ironclad reviews actually get done, Mike's process, what a review week looks like",
        "tone": "transparent, personal, process-focused"
    },
    {
        "id": 9,
        "name": "Myths / Misconceptions",
        "focus": "Debunking bad advice that circulates in construction bidding and estimating",
        "tone": "correcting the record, confident, no-nonsense"
    },
    {
        "id": 10,
        "name": "Quick Wins / Tactical Tips",
        "focus": "Immediately actionable advice contractors can put to work today",
        "tone": "punchy, specific, one-clear-takeaway"
    }
]

WEEK_ROTATIONS = [
    [1, 2, 3, 4, 5, 6, 7],
    [8, 9, 10, 1, 2, 3, 4],
    [5, 6, 7, 8, 9, 10, 1],
    [2, 3, 4, 5, 6, 7, 8],
]


# ============ PHOTO LIBRARY ============

def get_all_photos():
    """Get all photos from the photos/ directory."""
    exts = ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG", "*.png", "*.PNG"]
    photos = []
    for ext in exts:
        photos.extend(glob.glob(os.path.join(PHOTOS_DIR, ext)))
    return photos


def pick_photo(used_photos):
    """Pick a random photo that hasn't been used this week yet."""
    all_photos = get_all_photos()
    available = [p for p in all_photos if p not in used_photos]

    if not available:
        # If we've used all photos, reset and pick fresh
        available = all_photos

    if not available:
        return None

    return random.choice(available)


# ============ BRANDING ============

def apply_branding(image_path):
    """Load a job photo, crop to square, resize to 1080x1080, add branding bar."""
    with open(image_path, "rb") as f:
        raw_bytes = f.read()

    base = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
    W, H = base.size

    # Center crop to square
    if W != H:
        side = min(W, H)
        left = (W - side) // 2
        top = (H - side) // 2
        base = base.crop((left, top, left + side, top + side))
        W, H = base.size

    # Resize to 1080x1080
    target = 1080
    base = base.resize((target, target), Image.LANCZOS)
    W, H = target, target

    bar_height = int(H * 0.11)

    # Dark bar + rust accent line
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([(0, H - bar_height), (W, H)], fill=(14, 14, 14, 240))
    draw.rectangle([(0, H - bar_height - 4), (W, H - bar_height)], fill=(200, 68, 31, 255))

    # Website text on the left
    try:
        font_size = int(bar_height * 0.30)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    text = BRAND_WEBSITE.upper()
    text_x = int(W * 0.04)
    text_y = H - bar_height + int(bar_height * 0.36)
    draw.text((text_x, text_y), text, fill=(244, 241, 234, 255), font=font)

    branded = Image.alpha_composite(base, overlay)

    # Logo in bottom-right
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo_h = int(bar_height * 1.4)
        logo_w = int(logo.width * (logo_h / logo.height))
        max_w = int(W * 0.30)
        if logo_w > max_w:
            logo_w = max_w
            logo_h = int(logo.height * (logo_w / logo.width))
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        pad_right = int(W * 0.025)
        logo_x = W - logo_w - pad_right
        logo_y = H - logo_h - int(bar_height * 0.1)
        branded.paste(logo, (logo_x, logo_y), logo)
    except Exception as e:
        print(f"  Logo overlay skipped: {e}")

    out = io.BytesIO()
    branded.convert("RGB").save(out, format="JPEG", quality=92)
    return out.getvalue()


def caption_signoff():
    return (
        "\n\n—\n"
        "Grind Construction Services\n"
        "Pre-bid scope reviews that protect your margin.\n"
        f"{BRAND_WEBSITE} | {BRAND_PHONE} | {BRAND_EMAIL}"
    )


# ============ CAPTION GENERATION ============

def generate_linkedin_caption(pillar):
    prompt = f"""Write a LinkedIn post for Grind Construction Services, a construction bid review and estimating company run by Mike. The service is called "Ironclad" — it reviews contractor bids before submission to catch scope gaps, pricing errors, and contract red flags.

Content pillar: {pillar['name']}
Focus: {pillar['focus']}
Tone: {pillar['tone']}

Requirements:
- Plain construction-industry language. No corporate jargon. No AI filler phrases.
- 150-220 words max
- Start with a blunt hook (a statement or question that stops a contractor mid-scroll)
- Include one specific, concrete example or scenario
- End with one actionable takeaway — no generic "reach out" or "DM me"
- 3-5 relevant hashtags at the end
- No emojis
- Do NOT start with "In the world of..." or "In today's..." 
- Do NOT include contact info — that gets added separately
- Sound like a contractor talking to other contractors, not a marketing agency

Write only the caption. No commentary or preamble."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.82,
        max_tokens=500
    )
    return response.choices[0].message.content.strip() + caption_signoff()


def generate_instagram_caption(pillar, linkedin_caption):
    clean_linkedin = linkedin_caption.split("\n\n—\n")[0]
    prompt = f"""Rewrite this LinkedIn post as a punchy Instagram caption. Same message, shorter and more conversational.

Original:
{clean_linkedin}

Requirements:
- 80-120 words max
- First line is the hook — make it impossible to scroll past
- Short punchy lines, use line breaks
- Keep the concrete example but tighten it
- One clear takeaway
- 5-8 hashtags at the end
- No emojis
- No AI-speak
- No contact info — added separately

Write only the caption."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.82,
        max_tokens=400
    )
    return response.choices[0].message.content.strip() + caption_signoff()


# ============ WEEK GENERATION ============

def get_week_number():
    today = datetime.now()
    return min((today.day - 1) // 7 + 1, 4)


def generate_week():
    week_num = get_week_number()
    rotation = WEEK_ROTATIONS[week_num - 1]
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())

    posts = []
    used_photos = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    all_photos = get_all_photos()
    print(f"Photo library: {len(all_photos)} photos available")

    for i, pillar_id in enumerate(rotation):
        pillar = next(p for p in PILLARS if p["id"] == pillar_id)
        day_name = days[i]
        post_date = (monday + timedelta(days=i)).strftime("%Y-%m-%d")

        print(f"[{day_name}] Pillar: {pillar['name']}")

        # Captions
        linkedin_caption = generate_linkedin_caption(pillar)
        instagram_caption = generate_instagram_caption(pillar, linkedin_caption)

        # Pick a real Grind photo
        photo_path = pick_photo(used_photos)
        if not photo_path:
            print(f"  WARNING: No photos found in {PHOTOS_DIR}/ folder")
            continue

        used_photos.append(photo_path)
        photo_filename = os.path.basename(photo_path)
        print(f"  Using photo: {photo_filename}")

        # Apply branding
        branded_bytes = apply_branding(photo_path)
        image_b64 = base64.b64encode(branded_bytes).decode("utf-8")

        posts.append({
            "day": day_name,
            "date": post_date,
            "pillar": pillar["name"],
            "linkedin_caption": linkedin_caption,
            "instagram_caption": instagram_caption,
            "image_b64": image_b64,
            "photo_file": photo_filename
        })

    return posts


# ============ EMAIL PREVIEW ============

def build_email_html(posts):
    rows = ""
    for p in posts:
        rows += f"""
        <div style="margin-bottom:48px;padding:24px;border:2px solid #0e0e0e;background:#f4f1ea;">
          <div style="font-family:monospace;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#c8441f;margin-bottom:8px;">
            {p['day']} — {p['date']} — {p['pillar']}
          </div>
          <img src="cid:img_{p['day']}" style="width:100%;max-width:500px;display:block;margin-bottom:8px;border:1px solid #0e0e0e;">
          <div style="font-family:monospace;font-size:10px;color:#6b6b6b;margin-bottom:16px;">
            Grind job photo: {p['photo_file']}
          </div>
          <div style="margin-bottom:20px;">
            <div style="font-weight:bold;font-size:12px;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">LinkedIn</div>
            <div style="white-space:pre-wrap;font-size:14px;line-height:1.6;">{p['linkedin_caption']}</div>
          </div>
          <div>
            <div style="font-weight:bold;font-size:12px;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">Instagram</div>
            <div style="white-space:pre-wrap;font-size:14px;line-height:1.6;">{p['instagram_caption']}</div>
          </div>
        </div>
        """

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f1ea;padding:24px;">
      <div style="max-width:700px;margin:0 auto;">
        <h1 style="font-size:32px;text-transform:uppercase;letter-spacing:-1px;">Grind Weekly Preview</h1>
        <p style="font-family:monospace;font-size:12px;color:#6b6b6b;border-bottom:2px solid #0e0e0e;padding-bottom:16px;margin-bottom:32px;">
          WEEK OF {posts[0]['date']} // {len(posts) * 2} POSTS // LINKEDIN + INSTAGRAM // YOUR PHOTOS
        </p>
        {rows}
        <p style="font-family:monospace;font-size:11px;color:#6b6b6b;border-top:2px solid #0e0e0e;padding-top:16px;margin-top:40px;">
          Reply "approve" to use as-is. Note any posts to swap and I'll regenerate next run.
          Add new job photos to the photos/ folder in GitHub anytime — they'll appear automatically.
        </p>
      </div>
    </body></html>
    """
    return html


def send_email(posts):
    if not (SMTP_USER and SMTP_PASS):
        print("WARNING: SMTP credentials not set — skipping email.")
        return

    msg = MIMEMultipart("related")
    msg["Subject"] = f"Grind Weekly Preview — {posts[0]['date']}"
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL

    html = build_email_html(posts)
    msg.attach(MIMEText(html, "html"))

    for p in posts:
        img_bytes = base64.b64decode(p["image_b64"])
        img = MIMEImage(img_bytes)
        img.add_header("Content-ID", f"<img_{p['day']}>")
        msg.attach(img)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

    print(f"Email sent to {NOTIFY_EMAIL}")


# ============ MAIN ============

if __name__ == "__main__":
    print(f"[{datetime.now()}] Starting Grind automation v4 (your job photos)...")
    posts = generate_week()
    print(f"Generated {len(posts)} posts.")
    send_email(posts)
    print(f"[{datetime.now()}] Done.")
