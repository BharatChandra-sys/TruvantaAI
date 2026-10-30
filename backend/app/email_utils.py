# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: TruvantaAI – https://github.com/BharatChandra-sys/fake-news-extension
import os
import random
import string
import logging
import requests
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_env_path)

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
FROM_EMAIL    = os.getenv("SMTP_USER", "TruvantaAI2@gmail.com")
FROM_NAME     = "TruvantaAI"

logger = logging.getLogger(__name__)


def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def send_otp_email(to_email: str, otp: str, ip_address: str = None, location: str = None) -> bool:
    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY is not configured.")

    # Format location info
    location_text = ""
    if ip_address or location:
        parts = []
        if ip_address:
            parts.append(ip_address)
        if location:
            parts.append(location)
        location_text = ", ".join(parts)

    # Premium email design matching website aesthetic
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Your verification code</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0b;font-family:-apple-system,'SF Pro Text','SF Pro Display',system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;">

  <!-- Gmail annotation -->
  <div itemscope itemtype="http://schema.org/EmailMessage">
    <div itemprop="potentialAction" itemscope itemtype="http://schema.org/ViewAction">
      <link itemprop="target" href="https://truvantaai.tech"/>
      <meta itemprop="name" content="Code requested"/>
    </div>
    <meta itemprop="description" content="{otp}"/>
  </div>

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0b;padding:72px 24px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

        <!-- Logo with glow -->
        <tr>
          <td align="center" style="padding-bottom:64px;">
            <div style="display:inline-block;position:relative;">
              <img src="https://truvantaai.tech/truvanta-loader.svg" alt="Truvanta" width="120" height="90" style="display:block;position:relative;z-index:1;" />
            </div>
          </td>
        </tr>

        <!-- Code card with gradient border -->
        <tr>
          <td style="padding:0 20px 64px;">
            <div style="background:linear-gradient(180deg, #1f1f23 0%, #17171a 100%);border-radius:20px;padding:56px 48px;border:1px solid rgba(255,197,61,0.12);box-shadow:0 20px 40px -12px rgba(0,0,0,0.3),0 0 0 1px rgba(255,255,255,0.02) inset;">
              <div style="margin-bottom:32px;">
                <p style="margin:0;font-size:12px;font-weight:600;color:#ffc53d;letter-spacing:1.2px;text-transform:uppercase;text-align:center;">
                  Verification Code
                </p>
              </div>
              <div style="text-align:center;font-size:60px;font-weight:700;color:#ededef;letter-spacing:20px;font-family:'SF Mono',Monaco,Consolas,monospace;line-height:1;margin-bottom:40px;text-shadow:0 2px 12px rgba(255,197,61,0.15);">
                {otp}
              </div>
              <div style="padding-top:32px;border-top:1px solid rgba(255,255,255,0.06);">
                <p style="margin:0;font-size:15px;color:#a1a1aa;line-height:1.7;text-align:center;font-weight:400;">
                  Enter this code to reset your password.
                </p>
                <p style="margin:12px 0 0;font-size:14px;color:#6b6b73;text-align:center;">
                  Expires in <span style="color:#ffc53d;font-weight:500;">10 minutes</span>
                </p>
              </div>
            </div>
          </td>
        </tr>

        <!-- Security card -->
        <tr>
          <td style="padding:0 20px 64px;">
            <div style="background:#17171a;border-radius:20px;padding:40px;border:1px solid rgba(255,255,255,0.05);">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding-bottom:24px;">
                    <p style="margin:0;font-size:14px;color:#ededef;line-height:1.7;text-align:center;font-weight:500;">
                       Security Notice
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding-bottom:20px;">
                    <p style="margin:0;font-size:13px;color:#a1a1aa;line-height:1.8;text-align:center;">
                      Never share this code with anyone.<br/>We'll never ask for it by phone, text, or email.
                    </p>
                  </td>
                </tr>
                {f'<tr><td style="padding:24px 0;border-top:1px solid rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.04);"><div style="text-align:center;"><p style="margin:0 0 8px;font-size:11px;color:#6b6b73;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Request Origin</p><p style="margin:0;font-size:13px;color:#a1a1aa;font-family:monospace;">{location_text}</p></div></td></tr>' if location_text else ''}
                <tr>
                  <td style="padding-top:24px;">
                    <p style="margin:0;font-size:12px;color:#6b6b73;line-height:1.6;text-align:center;">
                      Didn't request this code?<br/>
                      <span style="color:#a1a1aa;">You can safely ignore this email.</span>
                    </p>
                  </td>
                </tr>
              </table>
            </div>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td align="center" style="padding-top:16px;">
            <p style="margin:0 0 8px;font-size:12px;color:#6b6b73;letter-spacing:0.4px;">
              <span style="color:#ffc53d;">Truvanta</span> · Fact-checking powered by AI
            </p>
            <p style="margin:0;font-size:11px;color:#6b6b73;">
              © 2026 · <a href="https://truvantaai.tech/privacy" style="color:#6b6b73;text-decoration:none;">Privacy</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>"""

    logger.info("Attempting to send OTP email to %s via Brevo", to_email)
    
    payload = {
        "sender":      {"name": FROM_NAME, "email": FROM_EMAIL},
        "to":          [{"email": to_email}],
        "subject":     f"Your verification code is {otp}",
        "htmlContent": html,
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
            response_data = resp.json()
            message_id = response_data.get("messageId", "unknown")
            logger.info("OTP email sent successfully to %s (messageId: %s)", to_email, message_id)
        except:
            logger.info("OTP email sent successfully to %s", to_email)
        
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error("Network error sending OTP to %s: %s", to_email, str(e))
        raise RuntimeError(f"Failed to send email: {str(e)}")
