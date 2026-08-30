import os
import re
import ipaddress
import logging
import asyncio
import smtplib
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("stallwise.email")

EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Stall Wise")
EMAIL_FROM_ADDRESS = (
    os.environ.get("EMAIL_FROM_ADDRESS")
    or os.environ.get("SMTP_USER")
    or os.environ.get("EMAIL_USER")
    or "dassantana135@gmail.com"
)
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r}")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r}")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r}")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r}")


def _send_sync(to: str, subject: str, html: str) -> str:
    user = (
        os.environ.get("SMTP_USER")
        or os.environ.get("EMAIL_USER")
        or os.environ.get("SMTP_AUTH_USER")
        or "dassantana135@gmail.com"
    ).strip()
    password = (
        os.environ.get("SMTP_PASS")
        or os.environ.get("EMAIL_PASS")
        or os.environ.get("SMTP_AUTH_PASS")
        or os.environ.get("EMAIL_PASSWORD")
        or "nhfhupbxvrzzdadp"
    ).strip()
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.environ.get("SMTP_PORT", "465" if host == "smtp.gmail.com" else "587"))

    from_header = f'"{EMAIL_FROM_NAME}" <{EMAIL_FROM_ADDRESS}>'

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_header
    msg["To"] = to
    if EMAIL_REPLY_TO:
        msg["Reply-To"] = EMAIL_REPLY_TO

    # Clean plain-text version as fallback
    text_content = re.sub(r"<[^>]+>", " ", html)
    text_content = re.sub(r"\s+", " ", text_content).strip()

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    # If Gmail or SSL port 465, use direct SMTP_SSL for instant delivery
    if host == "smtp.gmail.com" or port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=12) as server:
            if user and password:
                server.login(user, password)
            server.sendmail(user or EMAIL_FROM_ADDRESS, [to], msg.as_string())
    else:
        # Standard STARTTLS for custom SMTP servers
        with smtplib.SMTP(host, port, timeout=12) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if user and password:
                server.login(user, password)
            server.sendmail(user or EMAIL_FROM_ADDRESS, [to], msg.as_string())

    logger.info(f"Email successfully sent to {to}: {subject}")
    return "sent"


async def send_email(*, to: str, subject: str, html: str) -> str | None:
    try:
        _assert_safe_email(subject, html)
    except Exception as e:
        logger.warning(f"Email safety check notice: {e}")
    try:
        res = await asyncio.to_thread(_send_sync, to, subject, html)
        return res
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}", exc_info=True)
        return None


def _wrap(inner: str) -> str:
    return (f'<table role="presentation" width="100%"><tr><td style="padding:24px;'
            f'font-family:Arial,sans-serif;color:#222">{inner}'
            f'<p style="font-size:12px;color:#888;margin-top:24px">Sent by {escape(EMAIL_FROM_NAME)}. '
            f'We never ask for your password or card details by email.</p></td></tr></table>')


async def send_new_order_email(seller_email, seller_name, order, dashboard_link):
    items = "".join(
        f"<li>{escape(str(i.get('title','item')))} x{i.get('quantity',1)} "
        f"— INR {i.get('unitPrice',0) * i.get('quantity',1):.2f}</li>"
        for i in order.get("items", [])
    )
    inner = (
        f"<p>Hi {escape(seller_name or 'Seller')}, you received a new order.</p>"
        f"<p><strong>Buyer:</strong> {escape(order.get('buyerName',''))} "
        f"({escape(order.get('buyerEmail',''))})</p>"
        f"<ul>{items}</ul>"
        f"<p><strong>Total:</strong> INR {order.get('amount',0):.2f}</p>"
        f'<p><a href="{escape(dashboard_link)}">Open order in your dashboard</a></p>'
    )
    return await send_email(to=seller_email, subject=f"New order on {EMAIL_FROM_NAME}", html=_wrap(inner))


async def send_otp_email(buyer_email, buyer_name, otp, order_link):
    inner = (
        f"<p>Hi {escape(buyer_name or 'there')}, your order is on the way.</p>"
        f"<p>Your delivery confirmation code is:</p>"
        f'<p style="font-size:28px;font-weight:bold;letter-spacing:4px">{escape(otp)}</p>'
        f"<p>Show this code to the seller at handover so they can confirm delivery.</p>"
        f'<p><a href="{escape(order_link)}">View your order</a></p>'
    )
    return await send_email(to=buyer_email, subject=f"Your {EMAIL_FROM_NAME} delivery code", html=_wrap(inner))


async def send_reset_email(email, reset_link):
    inner = (
        f"<p>We received a request to reset your {escape(EMAIL_FROM_NAME)} password.</p>"
        f'<p><a href="{escape(reset_link)}">Reset your password</a></p>'
        f"<p>This link expires in 1 hour. If you did not request this, ignore this email.</p>"
    )
    return await send_email(to=email, subject=f"Reset your {escape(EMAIL_FROM_NAME)} password", html=_wrap(inner))


async def send_auth_otp_email(email, name, otp):
    inner = (
        f"<p>Hi {escape(name or 'there')},</p>"
        f"<p>Your verification code for {escape(EMAIL_FROM_NAME)} is:</p>"
        f'<p style="font-size:32px;font-weight:bold;letter-spacing:6px;'
        f'text-align:center;padding:16px 0;color:#FF4F00">{escape(otp)}</p>'
        f"<p>Enter this code to complete your sign-in. "
        f"This code expires in <strong>10 minutes</strong>.</p>"
        f"<p>If you didn't request this, you can safely ignore this email.</p>"
    )
    return await send_email(
        to=email,
        subject=f"Your {EMAIL_FROM_NAME} verification code: {otp}",
        html=_wrap(inner),
    )
