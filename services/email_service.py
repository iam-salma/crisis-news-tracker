import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional
from core.config import settings
from core.logging_config import logger


def send_smtp_email(to_email: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Dispatches an email via SMTP (supports SSL port 465 and STARTTLS port 587)."""
    if not settings.EMAIL_USER or not settings.EMAIL_PASSWORD:
        logger.warning(
            "SMTP email skipped: EMAIL_USER or EMAIL_PASSWORD environment variables are not set. "
            "Configure them in your .env or Render dashboard to enable email delivery."
        )
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.PROJECT_NAME} <{settings.EMAIL_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        if settings.EMAIL_PORT == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.EMAIL_SERVER, settings.EMAIL_PORT, context=context, timeout=15) as server:
                server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
                server.sendmail(settings.EMAIL_USER, to_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.EMAIL_SERVER, settings.EMAIL_PORT, timeout=15) as server:
                server.ehlo()
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
                server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
                server.sendmail(settings.EMAIL_USER, to_email, msg.as_string())

        logger.info("Successfully delivered email '%s' to %s", subject, to_email)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False


def send_welcome_newsletter_email(recipient_email: str) -> None:
    """Sends a subscription welcome confirmation with verified humanitarian resources."""
    subject = "CrisisAid - Subscription Confirmed: Real-Time Crisis Briefings"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
      <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #b91c1c 0%, #dc2626 100%); padding: 32px 24px; text-align: center;">
          <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">CrisisAid</h1>
          <p style="color: #fecaca; margin: 6px 0 0; font-size: 14px;">Frontline Humanitarian Intelligence & Disaster Radar</p>
        </div>
        <div style="padding: 32px 24px;">
          <h2 style="font-size: 18px; margin-top: 0; color: #0f172a;">Welcome to the CrisisAid Alert Network</h2>
          <p style="font-size: 15px; line-height: 1.6; color: #475569;">
            Your email address (<strong>{recipient_email}</strong>) has been registered to receive live humanitarian briefs, active emergency radar updates, and verified relief corridors.
          </p>
          <div style="background: #f1f5f9; border-radius: 8px; padding: 16px; margin: 24px 0;">
            <h3 style="font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 10px; color: #64748b;">Direct Aid Partners (Zero Intermediary Fees)</h3>
            <ul style="margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.8; color: #334155;">
              <li><strong>ICRC</strong> — International Committee of the Red Cross</li>
              <li><strong>UNHCR</strong> — UN Refugee Agency Emergency Aid</li>
              <li><strong>WFP</strong> — UN World Food Programme</li>
              <li><strong>MSF</strong> — Doctors Without Borders</li>
            </ul>
          </div>
          <p style="font-size: 13px; color: #94a3b8; line-height: 1.5; margin-bottom: 0;">
            You received this email because you subscribed on <a href="https://crisisaid.onrender.com" style="color: #dc2626;">CrisisAid</a>.
          </p>
        </div>
      </div>
    </body>
    </html>
    """
    text_body = (
        "Welcome to CrisisAid Humanitarian Alert Network!\n\n"
        f"Your email ({recipient_email}) has been registered to receive live crisis briefs.\n"
        "Explore real-time crisis hotspots at: https://crisisaid.onrender.com"
    )
    send_smtp_email(recipient_email, subject, html_body, text_body)


def send_contact_email(name: str, email: str, message: str) -> None:
    """Dispatches contact form submission to site administrator."""
    if not settings.EMAIL_USER:
        return
    subject = f"CrisisAid Contact Form Submission from {name}"
    body = f"Sender Name: {name}\nSender Email: {email}\n\nMessage:\n{message}"
    send_smtp_email(settings.EMAIL_USER, subject, f"<pre style='font-family:sans-serif;'>{body}</pre>", body)


def broadcast_crisis_newsletter(subscribers: List[str], articles: List[dict]) -> int:
    """Sends a curated crisis briefing digest to all active subscribers."""
    if not subscribers or not articles or not settings.EMAIL_USER:
        return 0

    subject = f"CrisisAid Humanitarian Briefing: Top Global Situation Reports"
    
    cards_html = ""
    for art in articles[:5]:
        title = art.get("title", "Disaster Alert")
        desc = art.get("description", "")
        url = art.get("url", "#")
        cards_html += f"""
        <div style="margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #e2e8f0;">
          <h3 style="font-size: 16px; margin: 0 0 6px;"><a href="{url}" style="color: #b91c1c; text-decoration: none;">{title}</a></h3>
          <p style="font-size: 14px; line-height: 1.5; color: #475569; margin: 0 0 8px;">{desc}</p>
          <a href="{url}" style="font-size: 13px; font-weight: 600; color: #dc2626;">Read Verified Report &rarr;</a>
        </div>
        """

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
      <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;">
        <div style="background: #b91c1c; padding: 24px; text-align: center;">
          <h1 style="color: #ffffff; margin: 0; font-size: 22px;">CrisisAid Daily Intelligence Briefing</h1>
        </div>
        <div style="padding: 24px;">
          {cards_html}
        </div>
      </div>
    </body>
    </html>
    """

    dispatched = 0
    for sub_email in subscribers:
        if send_smtp_email(sub_email, subject, html_body):
            dispatched += 1
    return dispatched
