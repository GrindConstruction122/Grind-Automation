"""
Grind Construction Services — Weekly Social Media Automation
Runs every Monday at 9am via Render.com cron job.
Generates 14 posts (7 LinkedIn + 7 Instagram) with captions + images.
Emails a preview to the configured notification email.
"""

import os
import json
import smtplib
import base64
import requests
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from openai import OpenAI

# ============ CONFIGURATION ============
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")

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
        "focus": "Mike's industry POV, credibility, lessons from years in the field",
        "tone": "confident, direct, plain-spoken construction voice",
        "image_style": "editorial portrait of a construction professional on a job site, natural light, documentary style, no corporate stock photo look"
    },
    {
        "id": 2,
        "name": "Scope Review / Red Flags",
        "focus": "Common traps in bid packages contractors miss",
        "tone": "practical warning, no jargon, example-driven",
        "image_style": "close-up of blueprints or bid documents with a red pen marking issues, gritty and real, not staged"
    },
    {
        "id": 3,
        "name": "Ironclad Education",
        "focus": "How Ironclad reviews work, what they catch, why they save money",
        "tone": "explanatory but grounded, not salesy",
        "image_style": "construction documents being reviewed, hands and paperwork, warm industrial lighting"
    },
    {
        "id": 4,
        "name": "Estimating and Bid Strategy",
        "focus": "Pricing tactics, decision frameworks, margin protection",
        "tone": "tactical, actionable, contractor-to-contractor",
        "image_style": "calculator, estimating paperwork, spreadsheet on laptop, realistic workspace"
    },
    {
        "id": 5,
        "name": "AI in Construction",
        "focus": "Practical AI use in bid review and estimating (not hype)",
        "tone": "grounded, skeptical of hype, focused on what actually works",
        "image_style": "laptop on construction site, blending technology with hard-hat environment"
    },
    {
        "id": 6,
        "name": "Case Studies / Wins",
        "focus": "Anonymized stories of bids Ironclad caught issues on",
        "tone": "narrative, specific, lesson-driven",
        "image_style": "completed construction project or job site scene, aspirational but realistic"
    },
    {
        "id": 7,
        "name": "Industry News / Intel",
        "focus": "Material costs, labor trends, regulatory shifts affecting contractors",
        "tone": "informed commentary, practical implications",
        "image_style": "construction materials, supply chain visuals, yards and lumber, documentary"
    },
    {
        "id": 8,
        "name": "Behind the Scenes",
        "focus": "How Ironclad reviews get done, Mike's process, weekly operations",
        "tone": "transparent, personal, process-focused",
        "image_style": "office scene reviewing documents, laptop with coffee, real workspace"
    },
    {
        "id": 9,
        "name": "Myths / Misconceptions",
        "focus": "Debunking bad advice in construction bidding and estimating",
        "tone": "correcting the record, confident, no-nonsense",
        "image_style": "split image or contrast-based composition, clean and graphic"
    },
    {
        "id": 10,
        "name": "Quick Wins / Tactical Tips",
        "focus": "Immediately actionable advice contractors can use today",
        "tone": "punchy, specific, one-clear-takeaway",
        "image_style": "close-up of a specific tool, clipboard, or construction detail, tight crop"
    }
]

# Weekly rotation — 7 pillars per week, rotating each week
WEEK_ROTATIONS = [
    [1, 2, 3, 4, 5, 6, 7],   # Week 1: Mon-Sun
    [8, 9, 10, 1, 2, 3, 4],  # Week 2
    [5, 6, 7, 8, 9, 10, 1],  # Week 3
    [2, 3, 4, 5, 6, 7, 8],   # Week 4
]

# ============ CONTENT GENERATION ============

def generate_linkedin_caption(pillar):
    """Generate a LinkedIn caption for the given pillar."""
    prompt = f"""Write a LinkedIn post for Grind Construction Services, a construction bid review and estimating company run by Mike. The service is called "Ironclad" — it reviews contractor bids before submission to catch scope gaps, pricing errors, and contract red flags.

Content pillar: {pillar['name']}
Focus: {pillar['focus']}
Tone: {pillar['tone']}

Requirements:
- Write in plain construction-industry language. No corporate jargon. No AI-speak.
- 150-220 words max
- Start with a hook (a blunt statement or question)
- Include one specific, concrete example or scenario
- End with one actionable takeaway — no generic "reach out to learn more"
- 3-5 relevant hashtags at the end
- Do NOT use emojis
- Do NOT start with "In the world of..." or "In today's..." or similar filler
- Sound like a contractor talking to other contractors, not a marketing agency

Write only the caption. No commentary."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()


def generate_instagram_caption(pillar, linkedin_caption):
    """Generate a shorter, more casual Instagram caption based on the LinkedIn version."""
    prompt = f"""Take this LinkedIn post and rewrite it as an Instagram caption. Keep the same core message but make it shorter, punchier, and more conversational. Instagram audiences scroll fast.

Original LinkedIn post:
{linkedin_caption}

Requirements:
- 80-120 words max
- Hook in the first line (it's the only part most people will read)
- Break into short punchy lines with line breaks
- Keep the same concrete example but condense it
- One clear takeaway
- 5-8 hashtags at the end (mix broad + niche construction tags)
- No emojis
- No AI-speak

Write only the caption. No commentary."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=400
    )
    return response.choices[0].message.content.strip()


def generate_image(pillar):
    """Generate a DALL·E 3 image for the pillar. Returns URL."""
    prompt = f"""Professional documentary-style photograph for a construction industry social media post.

Subject: {pillar['image_style']}
Theme: {pillar['focus']}

Style requirements:
- Realistic, editorial, documentary photography
- Natural lighting, not studio-lit
- Gritty authenticity — real job sites, real workers, real paperwork
- No text, no logos, no watermarks
- No obviously AI-generated aesthetic (avoid overly clean, shiny, or futuristic looks)
- Color palette: earth tones, warm industrial, natural
- Composition: leaves room for overlay text if needed

Avoid: stock photo aesthetics, corporate clipart vibes, cartoon styles, overly polished studio shots."""

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )
    return response.data[0].url


def download_image(url):
    """Download image bytes from URL."""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


# ============ WEEK GENERATION ============

def get_week_number():
    """Return 1-4 based on current week of month."""
    today = datetime.now()
    # Week of month based on day
    week = (today.day - 1) // 7 + 1
    return min(week, 4)


def generate_week():
    """Generate all 14 posts for the week (7 days x 2 posts)."""
    week_num = get_week_number()
    rotation = WEEK_ROTATIONS[week_num - 1]
    today = datetime.now()
    # Find Monday of this week
    monday = today - timedelta(days=today.weekday())

    posts = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for i, pillar_id in enumerate(rotation):
        pillar = next(p for p in PILLARS if p["id"] == pillar_id)
        day_name = days[i]
        post_date = (monday + timedelta(days=i)).strftime("%Y-%m-%d")

        print(f"[{day_name}] Generating pillar: {pillar['name']}...")

        # Generate captions
        linkedin_caption = generate_linkedin_caption(pillar)
        instagram_caption = generate_instagram_caption(pillar, linkedin_caption)

        # Generate image
        image_url = generate_image(pillar)
        image_bytes = download_image(image_url)
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        posts.append({
            "day": day_name,
            "date": post_date,
            "pillar": pillar["name"],
            "linkedin_caption": linkedin_caption,
            "instagram_caption": instagram_caption,
            "image_b64": image_b64
        })

    return posts


# ============ EMAIL PREVIEW ============

def build_email_html(posts):
    """Build the HTML preview email."""
    rows = ""
    for p in posts:
        rows += f"""
        <div style="margin-bottom:48px;padding:24px;border:2px solid #0e0e0e;background:#f4f1ea;">
          <div style="font-family:monospace;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#c8441f;margin-bottom:8px;">
            {p['day']} — {p['date']} — {p['pillar']}
          </div>
          <img src="cid:img_{p['day']}" style="width:100%;max-width:500px;display:block;margin-bottom:16px;border:1px solid #0e0e0e;">
          <div style="margin-bottom:20px;">
            <div style="font-weight:bold;font-size:12px;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">LinkedIn</div>
            <div style="white-space:pre-wrap;font-size:14px;line-height:1.5;">{p['linkedin_caption']}</div>
          </div>
          <div>
            <div style="font-weight:bold;font-size:12px;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">Instagram</div>
            <div style="white-space:pre-wrap;font-size:14px;line-height:1.5;">{p['instagram_caption']}</div>
          </div>
        </div>
        """

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f1ea;padding:24px;">
      <div style="max-width:700px;margin:0 auto;">
        <h1 style="font-size:32px;text-transform:uppercase;letter-spacing:-1px;">Grind Weekly Preview</h1>
        <p style="font-family:monospace;font-size:12px;color:#6b6b6b;border-bottom:2px solid #0e0e0e;padding-bottom:16px;margin-bottom:32px;">
          WEEK OF {posts[0]['date']} // 14 POSTS // LINKEDIN + INSTAGRAM
        </p>
        {rows}
        <p style="font-family:monospace;font-size:11px;color:#6b6b6b;border-top:2px solid #0e0e0e;padding-top:16px;margin-top:40px;">
          Reply to this email with "approve" to use as-is, or note which posts to regenerate.
        </p>
      </div>
    </body></html>
    """
    return html


def send_email(posts):
    """Send preview email with all images embedded."""
    if not (SMTP_USER and SMTP_PASS):
        print("WARNING: SMTP credentials not set — skipping email. Posts saved to output.json instead.")
        with open("output.json", "w") as f:
            # Strip image bytes from saved version to keep file small
            saved = [{k: v for k, v in p.items() if k != "image_b64"} for p in posts]
            json.dump(saved, f, indent=2)
        return

    msg = MIMEMultipart("related")
    msg["Subject"] = f"Grind Weekly Preview — {posts[0]['date']}"
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL

    html = build_email_html(posts)
    msg.attach(MIMEText(html, "html"))

    # Attach images
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
    print(f"[{datetime.now()}] Starting Grind weekly automation...")
    posts = generate_week()
    print(f"Generated {len(posts)} posts.")
    send_email(posts)
    print(f"[{datetime.now()}] Done.")
