# Grind Weekly Social Media Automation

Runs every Monday at 9am Eastern. Generates 14 posts (7 LinkedIn + 7 Instagram) with AI-generated images and captions. Emails a preview to the configured address.

## What it does

- Rotates through 10 content pillars across 4 weeks
- Uses DALL·E 3 for images
- Uses GPT-4o for captions
- Sends preview email with embedded images

## Environment variables (set in Render.com)

- `OPENAI_API_KEY` — your OpenAI API key (starts with `sk-`)
- `NOTIFY_EMAIL` — email address for preview delivery
- `SMTP_USER` — Gmail address that sends the preview (e.g. `yourname@gmail.com`)
- `SMTP_PASS` — Gmail app password (not your regular Gmail password)

## Cost estimate

About $2-3/month at 14 posts/week.
