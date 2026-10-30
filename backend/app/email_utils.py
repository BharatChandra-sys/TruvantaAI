# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: TruvantaAI – https://github.com/BharatChandra-sys/fake-news-extension
import os
import secrets
import string
import logging
import html as html_lib
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_env_path)

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
FROM_EMAIL    = os.getenv("SMTP_USER", "TruvantaAI2@gmail.com")
FROM_NAME     = "TruvantaAI"
BRAND_NAME    = "Truvanta"
SITE_URL      = os.getenv("SITE_URL", "https://truvantaai.tech").rstrip("/")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "contact@gari.live")
SUPPORT_URL   = os.getenv("SUPPORT_URL", "https://bharatchandra.me/")
GITHUB_URL    = "https://github.com/BharatChandra-sys/TruvantaAI"

# Mirrors the website theme tokens (factcheckai-website/app/globals.css).
C_CANVAS = "#0a0a0b"
C_RAISED = "#111113"
C_PANEL  = "#17171a"
C_LINE   = "#232327"
C_FG     = "#ededef"
C_FG2    = "#a1a1aa"
C_FG3    = "#6b6b73"
C_ACCENT = "#ffc53d"

FONT_STACK = "Geist,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO_STACK = "'Geist Mono','SF Mono',SFMono-Regular,Menlo,Consolas,'Courier New',monospace"

logger = logging.getLogger(__name__)


def generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))


def _footer_col(title: str, links: list) -> str:
    items = "".join(
        f'<tr><td style="padding:0 0 10px;font-size:13px;line-height:1.4;">'
        f'<a href="{href}" style="color:{C_FG3};text-decoration:none;">{label}</a></td></tr>'
        for label, href in links
    )
    return (
        f'<td valign="top" width="33%" style="padding:0 8px 0 0;">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0">'
        f'<tr><td style="padding:0 0 12px;font-size:13px;line-height:1.4;font-weight:500;color:{C_FG};">{title}</td></tr>'
        f'{items}</table></td>'
    )


def _wordmark(height: int = 22) -> str:
    # Flat logo mark rendered from the site's <Mark /> SVG (public/email/mark.png, 40:31).
    width = round(height * 40 / 31)
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
        f'<td style="vertical-align:middle;padding-right:10px;">'
        f'<img src="{SITE_URL}/email/mark.png" width="{width}" height="{height}" alt="" style="display:block;border:0;">'
        f'</td>'
        f'<td style="vertical-align:middle;font-size:16px;font-weight:600;color:{C_FG};letter-spacing:-0.02em;">{BRAND_NAME}</td>'
        f'</tr></table>'
    )


def _otp_html(otp: str, details_rows: str, year: int) -> str:
    # Table layout + inline styles so it renders the same in Gmail, Outlook and Apple Mail.
    # Structure mirrors the website: wordmark header, centred hero, raised footer with link columns.
    footer_cols = (
        _footer_col("Product", [("How it works", f"{SITE_URL}/#how-it-works"), ("Install", f"{SITE_URL}/install"), ("GitHub", GITHUB_URL)])
        + _footer_col("Help", [("Support", SUPPORT_URL), ("FAQ", f"{SITE_URL}/#faq")])
        + _footer_col("Legal", [("Privacy", f"{SITE_URL}/privacy"), ("Terms", f"{SITE_URL}/terms")])
    )
    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="dark">
  <meta name="supported-color-schemes" content="dark">
  <title>Your {BRAND_NAME} verification code</title>
  <link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400&display=swap" rel="stylesheet">
  <!--[if mso]><style>body,table,td,p,a{{font-family:Arial,Helvetica,sans-serif !important;}}</style><![endif]-->
</head>
<body style="margin:0;padding:0;background:{C_CANVAS};-webkit-text-size-adjust:100%;-webkit-font-smoothing:antialiased;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:{C_CANVAS};font-size:1px;line-height:1px;">
    Your {BRAND_NAME} code is {otp}. It expires in 10 minutes.&#8204;&nbsp;&#8204;&nbsp;&#8204;&nbsp;&#8204;&nbsp;&#8204;&nbsp;&#8204;&nbsp;
  </div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{C_CANVAS}" style="background:{C_CANVAS};font-family:{FONT_STACK};">

    <!-- Header -->
    <tr><td align="center" style="padding:0 20px;">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:560px;">
        <tr><td style="padding:24px 0;border-bottom:1px solid {C_LINE};">{_wordmark()}</td></tr>
      </table>
    </td></tr>

    <!-- Hero -->
    <tr><td align="center" style="padding:0 20px;">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:560px;">
        <tr>
          <td align="center" style="padding:72px 0 0;font-size:36px;line-height:1.08;font-weight:600;color:{C_FG};letter-spacing:-0.035em;">
            Reset your password
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:16px 12px 0;font-size:17px;line-height:1.5;color:{C_FG2};letter-spacing:-0.006em;">
            Enter this code in {BRAND_NAME} to set a new password.
          </td>
        </tr>

        <tr>
          <td align="center" style="padding:44px 0 0;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td align="center" bgcolor="{C_RAISED}" style="background:{C_RAISED};border-radius:16px;padding:28px 40px 28px 52px;font-family:{FONT_STACK};font-size:40px;line-height:1;font-weight:700;letter-spacing:12px;font-variant-numeric:tabular-nums;color:{C_FG};">
                  {otp}
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:20px 0 0;font-size:13px;line-height:1.4;color:{C_FG3};">
            <span style="color:{C_ACCENT};">&#9679;</span>&nbsp; Expires in 10 minutes &middot; Single use
          </td>
        </tr>
{details_rows}
        <tr>
          <td align="center" style="padding:56px 12px 72px;font-size:13px;line-height:1.6;color:{C_FG3};">
            Didn't request this? You can safely ignore this email &mdash; your password won't change.<br>
            {BRAND_NAME} will never ask you to share this code.
          </td>
        </tr>
      </table>
    </td></tr>

    <!-- Footer -->
    <tr><td align="center" bgcolor="{C_RAISED}" style="background:{C_RAISED};border-top:1px solid {C_LINE};padding:0 20px;">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:560px;">
        <tr>
          <td style="padding:44px 0 0;">{_wordmark()}</td>
        </tr>
        <tr>
          <td style="padding:12px 0 36px;font-size:13px;line-height:1.4;color:{C_FG3};">Fact-checking that shows its sources.</td>
        </tr>
        <tr>
          <td style="padding:0 0 26px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>{footer_cols}</tr></table>
          </td>
        </tr>
        <tr>
          <td style="padding:22px 0 32px;border-top:1px solid {C_LINE};font-size:13px;line-height:1.5;color:{C_FG3};">
            &copy; {year} {BRAND_NAME} &middot; You're receiving this because a password reset was requested for this address.
          </td>
        </tr>
      </table>
    </td></tr>

  </table>
</body>
</html>"""


def _otp_text(otp: str, details_text: str, year: int) -> str:
    return f"""Your {BRAND_NAME} verification code

Enter this code in {BRAND_NAME} to set a new password.

    {otp}

Expires in 10 minutes. Single use.
{details_text}
Didn't request this? You can safely ignore this email - your password won't change.
{BRAND_NAME} will never ask you to share this code.

--
Support: {SUPPORT_URL}
Terms:   {SITE_URL}/terms
Privacy: {SITE_URL}/privacy

(c) {year} {BRAND_NAME}
"""


def send_otp_email(to_email: str, otp: str, ip_address: str = None, location: str = None) -> bool:
    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY is not configured.")

    # Only show request details we actually have — "Unknown" rows look broken.
    details = [(label, value) for label, value in (("Location", location), ("IP", ip_address)) if value]
    details_rows = ""
    details_text = ""
    if details:
        cells = "".join(
            f'<tr><td style="padding:2px 16px 2px 0;font-size:12px;color:{C_FG3};">{label}</td>'
            f'<td style="padding:2px 0;font-family:{MONO_STACK};font-size:12px;color:{C_FG2};">{html_lib.escape(value)}</td></tr>'
            for label, value in details
        )
        details_rows = f"""        <tr>
          <td align="center" style="padding:16px 0 0;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0">{cells}</table>
          </td>
        </tr>
"""
        details_text = "\n" + "".join(f"{label}: {value}\n" for label, value in details)

    year = datetime.now(timezone.utc).year

    logger.info("Attempting to send OTP email to %s via Brevo", to_email)

    payload = {
        "sender":      {"name": FROM_NAME, "email": FROM_EMAIL},
        "to":          [{"email": to_email}],
        "replyTo":     {"email": SUPPORT_EMAIL, "name": f"{BRAND_NAME} Support"},
        "subject":     f"{otp} is your {BRAND_NAME} verification code",
        "htmlContent": _otp_html(otp, details_rows, year),
        "textContent": _otp_text(otp, details_text, year),
        "tags":        ["password-reset"],
    }

    try:
        resp = requests.post(
            BREVO_API_URL,
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )

        logger.info("Brevo API response: status=%d", resp.status_code)

        if resp.status_code not in (200, 201):
            logger.error("Brevo API error %d: %s", resp.status_code, resp.text)
            raise RuntimeError(f"Brevo API error {resp.status_code}: {resp.text}")

        try:
            message_id = resp.json().get("messageId", "unknown")
            logger.info("OTP email sent successfully to %s (messageId: %s)", to_email, message_id)
        except ValueError:
            logger.info("OTP email sent successfully to %s", to_email)

        return True

    except requests.exceptions.RequestException as e:
        logger.error("Network error sending OTP to %s: %s", to_email, str(e))
        raise RuntimeError(f"Failed to send email: {str(e)}")
