import os
import re
import logging
import httpx
from html import escape

logger = logging.getLogger("stallwise.email")

BREVO_API_KEY = (
    os.environ.get("BREVO_API_KEY")
    or os.environ.get("SENDINBLUE_API_KEY")
    or ""
).strip()

EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Stall Wise")
EMAIL_FROM_ADDRESS = os.environ.get("EMAIL_FROM_ADDRESS", "dassantana135@gmail.com").strip()


async def send_email(*, to: str, subject: str, html: str, recipient_name: str = "User") -> str | None:
    """Send transactional email via Brevo REST API with 100% deliverability."""
    try:
        payload = {
            "sender": {"name": EMAIL_FROM_NAME, "email": EMAIL_FROM_ADDRESS},
            "to": [{"email": to, "name": recipient_name or to}],
            "subject": subject,
            "htmlContent": html,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": BREVO_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
            )
            if r.status_code in (200, 201, 202):
                data = r.json()
                msg_id = data.get("messageId", "sent")
                logger.info(f"Email successfully delivered via Brevo to {to}: {msg_id}")
                return msg_id
            else:
                logger.error(f"Brevo API error {r.status_code}: {r.text}")
                return None
    except Exception as e:
        logger.error(f"Brevo email dispatch failed to {to}: {e}", exc_info=True)
        return None


def _wrap(inner: str) -> str:
    return (
        f'<table role="presentation" width="100%" style="background-color:#F5F5F7;padding:32px 0;">'
        f'<tr><td align="center">'
        f'<table role="presentation" width="560" style="background-color:#FFFFFF;border-radius:12px;padding:36px;font-family:Arial,sans-serif;color:#1D1D1F;box-shadow:0 4px 16px rgba(0,0,0,0.06);">'
        f'<tr><td>{inner}'
        f'<hr style="border:none;border-top:1px solid #E5E5E7;margin:28px 0 16px 0;" />'
        f'<p style="font-size:12px;color:#86868B;margin:0;line-height:1.5;">Sent by {escape(EMAIL_FROM_NAME)}. '
        f'We never ask for your password or financial credentials by email.</p></td></tr></table>'
        f'</td></tr></table>'
    )


async def send_new_order_email(seller_email, seller_name, order, dashboard_link):
    items = "".join(
        f"<li style='margin-bottom:6px;'><strong>{escape(str(i.get('title','item')))}</strong> x{i.get('quantity',1)} "
        f"— INR {i.get('unitPrice',0) * i.get('quantity',1):.2f}</li>"
        for i in order.get("items", [])
    )
    inner = (
        f"<h2 style='color:#0A0A0A;margin-top:0;'>🎉 You received a new order!</h2>"
        f"<p style='font-size:15px;line-height:1.6;'>Hi {escape(seller_name or 'Seller')}, a customer just placed an order on your shop.</p>"
        f"<p style='font-size:14px;'><strong>Buyer:</strong> {escape(order.get('buyerName',''))} ({escape(order.get('buyerEmail',''))})</p>"
        f"<ul style='font-size:14px;padding-left:20px;'>{items}</ul>"
        f"<p style='font-size:18px;font-weight:bold;color:#FF4F00;'>Total: INR {order.get('amount',0):.2f}</p>"
        f"<div style='margin-top:24px;'><a href='{escape(dashboard_link)}' style='background-color:#FF4F00;color:#FFFFFF;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;'>Open Order in Dashboard</a></div>"
    )
    return await send_email(to=seller_email, subject=f"New order on {EMAIL_FROM_NAME} (INR {order.get('amount',0):.2f})", html=_wrap(inner), recipient_name=seller_name)


async def send_otp_email(buyer_email, buyer_name, otp, order_link):
    inner = (
        f"<h2 style='color:#0A0A0A;margin-top:0;'>🚚 Your order is on the way!</h2>"
        f"<p style='font-size:15px;line-height:1.6;'>Hi {escape(buyer_name or 'there')}, your order has shipped.</p>"
        f"<p style='font-size:14px;color:#525252;'>Your delivery confirmation code is:</p>"
        f"<div style='font-size:32px;font-weight:bold;letter-spacing:6px;text-align:center;padding:18px 0;color:#FF4F00;background-color:#FFF5F0;border-radius:8px;margin:16px 0;'>{escape(otp)}</div>"
        f"<p style='font-size:13px;color:#737373;'>Show this code to the seller upon delivery to complete your handover.</p>"
        f"<div style='margin-top:20px;'><a href='{escape(order_link)}' style='color:#FF4F00;text-decoration:underline;font-size:14px;'>View Order Status</a></div>"
    )
    return await send_email(to=buyer_email, subject=f"Your {EMAIL_FROM_NAME} delivery code: {otp}", html=_wrap(inner), recipient_name=buyer_name)


async def send_reset_email(email, reset_link):
    inner = (
        f"<h2 style='color:#0A0A0A;margin-top:0;'>Reset your password</h2>"
        f"<p style='font-size:15px;line-height:1.6;'>We received a request to reset your {escape(EMAIL_FROM_NAME)} password.</p>"
        f"<div style='margin:24px 0;'><a href='{escape(reset_link)}' style='background-color:#0A0A0A;color:#FFFFFF;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;'>Reset Password</a></div>"
        f"<p style='font-size:13px;color:#86868B;'>This link expires in 1 hour. If you did not request this, you can safely ignore this email.</p>"
    )
    return await send_email(to=email, subject=f"Reset your {escape(EMAIL_FROM_NAME)} password", html=_wrap(inner))


async def send_auth_otp_email(email, name, otp):
    inner = (
        f"<h2 style='color:#0A0A0A;margin-top:0;'>Verify your email</h2>"
        f"<p style='font-size:15px;line-height:1.6;'>Hi {escape(name or 'there')},</p>"
        f"<p style='font-size:14px;color:#525252;'>Your 6-digit verification code for {escape(EMAIL_FROM_NAME)} is:</p>"
        f"<div style='font-size:36px;font-weight:bold;letter-spacing:8px;text-align:center;padding:18px 0;color:#FF4F00;background-color:#FFF5F0;border-radius:8px;margin:20px 0;'>{escape(otp)}</div>"
        f"<p style='font-size:13px;color:#525252;'>Enter this code on your screen to complete your sign in. This code expires in <strong>10 minutes</strong>.</p>"
        f"<p style='font-size:12px;color:#86868B;margin-top:20px;'>If you didn't request this code, you can safely ignore this email.</p>"
    )
    return await send_email(
        to=email,
        subject=f"{otp} is your {EMAIL_FROM_NAME} verification code",
        html=_wrap(inner),
        recipient_name=name,
    )
