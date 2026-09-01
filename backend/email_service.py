import os
import re
import logging
import httpx
from html import escape
from fastapi import HTTPException

logger = logging.getLogger("stallwise.email")

def _get_clean_brevo_key() -> str:
    raw = (
        os.environ.get("BREVO_API_KEY")
        or os.environ.get("SENDINBLUE_API_KEY")
        or ""
    ).strip()
    if not raw:
        return ""
    # Tolerate 'api xkeysib-...' or extra words pasted around the key.
    for part in raw.split():
        if part.startswith("xkeysib-"):
            return part.strip()
    return raw if raw.startswith("xkeysib-") else ""


EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Stall Wise")
EMAIL_FROM_ADDRESS = os.environ.get("EMAIL_FROM_ADDRESS", "dassantana135@gmail.com").strip()


async def send_email(*, to: str, subject: str, html: str, recipient_name: str = "User") -> str | None:
    """Send transactional email via the Brevo REST API."""
    api_key = _get_clean_brevo_key()
    if not api_key:
        logger.error("BREVO_API_KEY is not configured — email to %s was not sent.", to)
        return None
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
                    "api-key": api_key,
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
                err_msg = f"Brevo API error {r.status_code}: {r.text}"
                logger.error(err_msg)
                raise HTTPException(status_code=500, detail=f"Email delivery failed: {r.text}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Brevo email dispatch failed to {to}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


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


async def send_order_confirmation_email(buyer_email, buyer_name, order, store_name,
                                        order_link, dispatch_days=2):
    """The buyer's receipt.

    Until this existed a buyer paid a shop they had reached from a shared link
    and then heard nothing at all until the parcel shipped — no receipt, no
    order number, no way back to the order. That silence is exactly where a
    first-time buyer decides the site cannot be trusted, and it is the one
    email a marketplace cannot skip.
    """
    paid = (order.get("paymentMethod") or "online") != "cod"
    rows = "".join(
        f"<tr><td style='padding:6px 0;font-size:14px;'>{escape(str(i.get('title','item')))}"
        f"<span style='color:#86868B;'> &times;{i.get('quantity',1)}</span></td>"
        f"<td align='right' style='padding:6px 0;font-size:14px;white-space:nowrap;'>"
        f"₹{i.get('unitPrice',0) * i.get('quantity',1):,.2f}</td></tr>"
        for i in order.get("items", [])
    )
    delivery = float(order.get("deliveryFee") or 0)
    delivery_row = (
        f"<tr><td style='padding:6px 0;font-size:14px;color:#525252;'>Delivery</td>"
        f"<td align='right' style='padding:6px 0;font-size:14px;'>"
        f"{'Free' if delivery <= 0 else f'₹{delivery:,.2f}'}</td></tr>"
    )
    next_step = (
        f"{escape(store_name)} is packing your order and will dispatch it within "
        f"{dispatch_days} working day{'' if dispatch_days == 1 else 's'}. "
        "We'll email you a delivery code when it ships — show that code to the "
        "delivery person to confirm you received it."
    )
    if not paid:
        next_step += " You'll pay in cash when it arrives."

    inner = (
        f"<h2 style='color:#0A0A0A;margin-top:0;'>Thanks for your order</h2>"
        f"<p style='font-size:15px;line-height:1.6;'>Hi {escape(buyer_name or 'there')}, "
        f"{escape(store_name)} has your order.</p>"
        f"<p style='font-size:13px;color:#86868B;margin:0 0 4px 0;'>Order number</p>"
        f"<p style='font-size:15px;font-weight:bold;margin:0 0 20px 0;'>{escape(str(order.get('order_id','')))}</p>"
        f"<table role='presentation' width='100%' style='border-top:1px solid #E5E5E7;"
        f"border-bottom:1px solid #E5E5E7;margin-bottom:12px;'>{rows}{delivery_row}</table>"
        f"<table role='presentation' width='100%'><tr>"
        f"<td style='font-size:16px;font-weight:bold;'>{'Paid' if paid else 'To pay on delivery'}</td>"
        f"<td align='right' style='font-size:18px;font-weight:bold;color:#FF4F00;'>"
        f"₹{float(order.get('amount', 0)):,.2f}</td></tr></table>"
        f"<p style='font-size:14px;line-height:1.6;color:#525252;margin-top:22px;'>{next_step}</p>"
        f"<div style='margin-top:24px;'><a href='{escape(order_link)}' "
        f"style='background-color:#FF4F00;color:#FFFFFF;padding:12px 24px;border-radius:8px;"
        f"text-decoration:none;font-weight:bold;display:inline-block;'>Track your order</a></div>"
        f"<p style='font-size:12px;color:#86868B;margin-top:20px;'>Keep this email — the link above "
        f"is how you check on your order or report a problem.</p>"
    )
    return await send_email(
        to=buyer_email,
        subject=f"Your {escape(store_name)} order is confirmed (₹{float(order.get('amount', 0)):,.2f})",
        html=_wrap(inner), recipient_name=buyer_name)


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


async def send_dispute_email(seller_email, seller_name, order_id, reason, dashboard_link):
    inner = (
        f"<h2 style='color:#0A0A0A;margin-top:0;'>⚠️ A buyer raised a dispute</h2>"
        f"<p style='font-size:15px;line-height:1.6;'>Hi {escape(seller_name or 'Seller')}, order "
        f"<strong>{escape(str(order_id))}</strong> has been disputed within its acceptance window.</p>"
        f"<p style='font-size:14px;color:#525252;'><strong>Reason:</strong> {escape(reason or '')}</p>"
        f"<p style='font-size:13px;color:#737373;'>Reach out to the buyer to resolve it directly.</p>"
        f"<div style='margin-top:24px;'><a href='{escape(dashboard_link)}' style='background-color:#0A0A0A;color:#FFFFFF;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block;'>Open Order</a></div>"
    )
    return await send_email(to=seller_email, subject=f"Dispute raised on {EMAIL_FROM_NAME} order {order_id}",
                            html=_wrap(inner), recipient_name=seller_name)


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
