#!/usr/bin/env python3
"""Emits the seller-console artboards. The chrome (sidebar + topbar) is defined
once here so every screen stays byte-identical; only the page body differs."""
import re, pathlib

OUT = pathlib.Path(__file__).parent

HEAD = '''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap">
  <style>
    body { margin: 0; font-family: "Satoshi", "Plus Jakarta Sans", ui-sans-serif, system-ui, sans-serif; -webkit-font-smoothing: antialiased; color: #0A0A0A; }
    a { color: #C43D00; text-decoration: none; } a:hover { color: #8A2200; }
    h1, h2, h3 { font-family: "Cabinet Grotesk", "Archivo", "Satoshi", ui-sans-serif, sans-serif; margin: 0; letter-spacing: -0.02em; }
    p { margin: 0; }
  </style>
</helmet>
'''
TAIL = '''</x-dc>
</body>
</html>
'''

ICONS = {
 "home": '<path d="M3 9.5 12 3l9 6.5V20a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"></path><path d="M9 22v-8h6v8"></path>',
 "orders": '<path d="M6.5 2 3.5 6v14a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2V6l-3-4Z"></path><path d="M3.5 6h17"></path><path d="M16 10a4 4 0 0 1-8 0"></path>',
 "products": '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"></path><path d="m3.3 7 8.7 5 8.7-5"></path><path d="M12 22V12"></path>',
 "customers": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>',
 "insights": '<path d="M22 7 13.5 15.5 8.5 10.5 2 17"></path><path d="M16 7h6v6"></path>',
 "discounts": '<path d="M12.6 2.6A2 2 0 0 0 11.2 2H4a2 2 0 0 0-2 2v7.2a2 2 0 0 0 .6 1.4l8.7 8.7a2.4 2.4 0 0 0 3.4 0l6.6-6.6a2.4 2.4 0 0 0 0-3.4Z"></path><circle cx="7.5" cy="7.5" r="1.2"></circle>',
 "storefront": '<path d="M4 21V10.5"></path><path d="M20 21V10.5"></path><path d="M2 10.5 4.6 4.4A2 2 0 0 1 6.5 3h11a2 2 0 0 1 1.9 1.4L22 10.5Z"></path><path d="M2 21h20"></path><path d="M9.5 21v-5.5h5V21"></path>',
 "payouts": '<rect x="2" y="5" width="20" height="14" rx="2.5"></rect><path d="M2 10h20"></path>',
 "settings": '<circle cx="12" cy="12" r="3"></circle><path d="M12 2v3"></path><path d="M12 19v3"></path><path d="m4.9 4.9 2.1 2.1"></path><path d="m17 17 2.1 2.1"></path><path d="M2 12h3"></path><path d="M19 12h3"></path><path d="m4.9 19.1 2.1-2.1"></path><path d="m17 7 2.1-2.1"></path>',
}

NAV = [
 ("head", "Run the shop", None, None),
 ("home", "Home", None, None),
 ("orders", "Orders", "3", "urgent"),
 ("products", "Products", "24", "muted"),
 ("customers", "Customers", None, None),
 ("head", "Grow", None, None),
 ("insights", "Insights", None, None),
 ("discounts", "Discounts", None, None),
 ("storefront", "Storefront", None, None),
 ("head", "Money", None, None),
 ("payouts", "Payouts", None, "dot"),
 ("settings", "Settings", None, None),
]

def sidebar(active):
    rows = []
    for key, label, badge, kind in NAV:
        if key == "head":
            rows.append(f'      <div style="padding: {"8px" if label=="Run the shop" else "16px"} 10px 6px 10px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #A3A3A3;">{label}</div>')
            continue
        on = key == active
        bg = "background: #FFF7ED; " if on else ""
        col = "#C43D00" if on else "#525252"
        icol = "#C43D00" if on else "#737373"
        wt = "700" if on else "600"
        extra = ""
        if kind == "urgent":
            extra = f'<span style="background: #FF4F00; color: #FFFFFF; font-size: 10px; font-weight: 800; padding: 2px 7px; border-radius: 999px;">{badge}</span>'
        elif kind == "muted":
            extra = f'<span style="background: #F5F5F5; color: #737373; font-size: 10px; font-weight: 800; padding: 2px 7px; border-radius: 999px;">{badge}</span>'
        elif kind == "dot":
            extra = '<span style="width: 6px; height: 6px; border-radius: 999px; background: #F59E0B;"></span>'
        rows.append(
f'''      <div style="display: flex; align-items: center; gap: 10px; padding: 9px 10px; border-radius: 10px; {bg}color: {col}; font-size: 13px; font-weight: {wt};">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="{icol}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[key]}</svg>
        <span style="flex: 1;">{label}</span>{extra}
      </div>''')
    nav = "\n".join(rows)
    return f'''  <aside style="width: 248px; flex-shrink: 0; background: #FFFFFF; border-right: 1px solid #E5E5E5; display: flex; flex-direction: column;">
    <div style="display: flex; align-items: center; gap: 10px; padding: 16px 16px 15px 16px; border-bottom: 1px solid #F5F5F5;">
      <div style="width: 34px; height: 34px; border-radius: 11px; background: #FF4F00; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M4.2 8h15.6l-1.1 11.1A2 2 0 0 1 16.7 21H7.3a2 2 0 0 1-2-1.9Z"></path><path d="M8.6 8V6.1a3.4 3.4 0 0 1 6.8 0V8"></path></svg>
      </div>
      <div style="min-width: 0; flex: 1;">
        <div style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 14px; font-weight: 800; color: #0A0A0A; letter-spacing: -0.015em; line-height: 1.15;">Asha Handlooms</div>
        <div style="font-size: 11px; color: #A3A3A3; font-weight: 500; line-height: 1.4;">stallwise.in/asha</div>
      </div>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#A3A3A3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m7 15 5 5 5-5"></path><path d="m7 9 5-5 5 5"></path></svg>
    </div>

    <nav style="flex: 1; padding: 12px 10px; display: flex; flex-direction: column; gap: 2px;">
{nav}
    </nav>

    <div style="padding: 12px; border-top: 1px solid #F5F5F5;">
      <div style="border-radius: 14px; background: #0A0A0A; padding: 14px; display: flex; flex-direction: column; gap: 10px;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #A3A3A3;">Free plan</span>
          <span style="font-size: 10px; font-weight: 700; color: #FF7A3D;">10% fee</span>
        </div>
        <p style="font-size: 12px; line-height: 1.45; color: #E5E5E5; font-weight: 500;">You paid <strong style="color:#FFFFFF; font-weight:800;">₹4,120</strong> in commission this month.</p>
        <div style="background: #FF4F00; color: #FFFFFF; font-size: 12px; font-weight: 800; padding: 9px; border-radius: 10px; text-align: center;">Go Pro — keep 100%</div>
      </div>
    </div>
  </aside>'''

def topbar(title, sub, action=None):
    act = action or ''
    return f'''    <header style="height: 64px; flex-shrink: 0; background: #FFFFFF; border-bottom: 1px solid #E5E5E5; display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 0 28px;">
      <div>
        <h1 style="font-size: 18px; font-weight: 800; color: #0A0A0A; line-height: 1.2;">{title}</h1>
        <p style="font-size: 12px; color: #737373; font-weight: 500; margin-top: 2px;">{sub}</p>
      </div>
      <div style="display: flex; align-items: center; gap: 10px;">
        <div style="display: flex; align-items: center; gap: 8px; height: 36px; padding: 0 12px; border: 1px solid #E5E5E5; border-radius: 10px; background: #FAFAFA; width: 220px;">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#A3A3A3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path></svg>
          <span style="font-size: 13px; color: #A3A3A3; font-weight: 500;">Search orders, products…</span>
        </div>{act}
        <div style="position: relative; width: 36px; height: 36px; border: 1px solid #E5E5E5; border-radius: 10px; background: #FFFFFF; display: flex; align-items: center; justify-content: center;">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#525252" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path></svg>
          <span style="position: absolute; top: 6px; right: 7px; width: 7px; height: 7px; border-radius: 999px; background: #FF4F00; border: 1.5px solid #FFFFFF;"></span>
        </div>
        <div style="width: 36px; height: 36px; border-radius: 10px; background: #0A0A0A; color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 800;">AK</div>
      </div>
    </header>'''

def primary(label):
    return f'''
        <div style="display: flex; align-items: center; gap: 7px; height: 36px; padding: 0 14px; border-radius: 10px; background: #FF4F00; color: #FFFFFF; font-size: 13px; font-weight: 800;">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"></path><path d="M12 5v14"></path></svg>{label}
        </div>'''

def page(name, active, title, sub, body, h=1180, action=None):
    doc = (HEAD +
f'''
<div style="width: 1440px; height: {h}px; display: flex; background: #FAFAFA; overflow: hidden;">

{sidebar(active)}

  <div style="flex: 1; min-width: 0; display: flex; flex-direction: column;">

{topbar(title, sub, action)}

    <div style="flex: 1; overflow: hidden; padding: 24px 28px; display: flex; flex-direction: column; gap: 20px;">
{body}
    </div>
  </div>
</div>
''' + TAIL)
    (OUT / f"{name}.dc.html").write_text(doc, encoding="utf-8")
    return len(doc)

# ---- shared fragments -------------------------------------------------------
def card(title, right="", body="", pad="16px 20px", grow=False):
    head = ""
    if title:
        head = f'''      <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 20px; border-bottom: 1px solid #F5F5F5;">
        <h2 style="font-size: 14px; font-weight: 800; color: #0A0A0A;">{title}</h2>{right}
      </div>'''
    g = "flex: 1; min-height: 0; " if grow else ""
    return f'''      <section style="background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 16px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); overflow: hidden; {g}display: flex; flex-direction: column;">
{head}
        <div style="padding: {pad}; flex: 1; min-height: 0;">
{body}
        </div>
      </section>'''

def pill(text, bd, bg, fg, dot):
    return (f'<span style="display: inline-flex; align-items: center; gap: 6px; border: 1px solid {bd}; background: {bg}; '
            f'color: {fg}; font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 999px; white-space: nowrap;">'
            f'<span style="width: 6px; height: 6px; border-radius: 999px; background: {dot};"></span>{text}</span>')

PILLS = {
 "placed":    pill("Placed",           "#FDE68A", "#FFFBEB", "#B45309", "#F59E0B"),
 "paid":      pill("Ready to ship",    "#BFDBFE", "#EFF6FF", "#1D4ED8", "#3B82F6"),
 "shipped":   pill("Out for delivery", "#E9D5FF", "#FAF5FF", "#7E22CE", "#A855F7"),
 "delivered": pill("Delivered",        "#A7F3D0", "#ECFDF5", "#047857", "#10B981"),
 "completed": pill("Completed",        "#171717", "#171717", "#FFFFFF", "#34D399"),
 "disputed":  pill("Disputed",         "#FECDD3", "#FFF1F2", "#BE123C", "#F43F5E"),
 "cod":       pill("Cash on delivery", "#FDE68A", "#FFFBEB", "#B45309", "#F59E0B"),
}

LABEL = "font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #A3A3A3;"
TH = "font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #A3A3A3;"

# ============================== ORDERS =======================================
def order_row(oid, when, buyer, city, items, pay, status, total, last=False):
    bb = "" if last else "border-bottom: 1px solid #F5F5F5;"
    return f'''          <div style="display: grid; grid-template-columns: 28px minmax(0,1.15fr) minmax(0,1.3fr) minmax(0,1.5fr) minmax(0,0.9fr) minmax(0,1.25fr) 92px 34px; gap: 14px; align-items: center; padding: 12px 20px; {bb}">
            <div style="width: 16px; height: 16px; border: 1.5px solid #D4D4D4; border-radius: 5px;"></div>
            <div style="min-width: 0;"><div style="font-size: 12.5px; font-weight: 700; color: #0A0A0A;">{oid}</div><div style="font-size: 11px; color: #A3A3A3; font-weight: 500;">{when}</div></div>
            <div style="min-width: 0;"><div style="font-size: 12.5px; font-weight: 600; color: #262626;">{buyer}</div><div style="font-size: 11px; color: #A3A3A3; font-weight: 500;">{city}</div></div>
            <div style="font-size: 12px; color: #525252; font-weight: 500;">{items}</div>
            <div style="font-size: 12px; color: #737373; font-weight: 600;">{pay}</div>
            <div>{PILLS[status]}</div>
            <div style="font-size: 13px; font-weight: 800; color: #0A0A0A; text-align: right;">{total}</div>
            <div style="display: flex; justify-content: flex-end;"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#A3A3A3" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"></path></svg></div>
          </div>'''

ORDER_TABS = ""
for i, (lb, ct) in enumerate([("All", "68"), ("To ship", "3"), ("Out for delivery", "1"), ("Completed", "61"), ("Disputed", "1"), ("Cancelled", "2")]):
    on = i == 1
    ORDER_TABS += f'''<div style="display: flex; align-items: center; gap: 7px; padding: 7px 13px; border-radius: 9px; {"background: #FFFFFF; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.06); " if on else ""}font-size: 12.5px; font-weight: {"800" if on else "600"}; color: {"#0A0A0A" if on else "#737373"};">{lb}<span style="font-size: 10px; font-weight: 800; color: {"#FFFFFF" if on else "#A3A3A3"}; background: {"#FF4F00" if on else "#EFEFEF"}; padding: 1px 6px; border-radius: 999px;">{ct}</span></div>'''

ORDERS_BODY = f'''      <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px;">
        <div style="display: flex; gap: 3px; background: #F0F0F0; border-radius: 11px; padding: 3px;">{ORDER_TABS}</div>
        <div style="display: flex; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 7px; height: 34px; padding: 0 12px; border: 1px solid #E5E5E5; border-radius: 10px; background: #FFFFFF; font-size: 12.5px; font-weight: 600; color: #525252;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#737373" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4.5" width="18" height="17" rx="2.5"></rect><path d="M3 10h18"></path><path d="M8 2.5v4"></path><path d="M16 2.5v4"></path></svg>Last 30 days
          </div>
          <div style="display: flex; align-items: center; gap: 7px; height: 34px; padding: 0 12px; border: 1px solid #E5E5E5; border-radius: 10px; background: #FFFFFF; font-size: 12.5px; font-weight: 600; color: #525252;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#737373" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"></path><path d="m7 10 5 5 5-5"></path><path d="M20 21H4"></path></svg>Export CSV
          </div>
        </div>
      </div>

      <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; background: #0A0A0A; border-radius: 12px; padding: 10px 16px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <span style="font-size: 12.5px; font-weight: 700; color: #FFFFFF;">3 orders selected</span>
          <span style="font-size: 12px; color: #A3A3A3; font-weight: 500;">All are paid and ready to dispatch</span>
        </div>
        <div style="display: flex; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 8px; background: #262626; color: #FFFFFF; font-size: 12px; font-weight: 700;">Print packing slips</div>
          <div style="display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 8px; background: #FF4F00; color: #FFFFFF; font-size: 12px; font-weight: 800;">Mark as shipped</div>
        </div>
      </div>

      <section style="background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 16px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); overflow: hidden; flex: 1; min-height: 0; display: flex; flex-direction: column;">
        <div style="display: grid; grid-template-columns: 28px minmax(0,1.15fr) minmax(0,1.3fr) minmax(0,1.5fr) minmax(0,0.9fr) minmax(0,1.25fr) 92px 34px; gap: 14px; padding: 10px 20px; background: #FAFAFA; border-bottom: 1px solid #F5F5F5;">
          <div style="width: 16px; height: 16px; border: 1.5px solid #FF4F00; background: #FF4F00; border-radius: 5px; display: flex; align-items: center; justify-content: center;"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"></path></svg></div>
          <span style="{TH}">Order</span><span style="{TH}">Buyer</span><span style="{TH}">Items</span><span style="{TH}">Payment</span><span style="{TH}">Status</span><span style="{TH} text-align: right;">Total</span><span></span>
        </div>
        <div style="flex: 1; min-height: 0;">
{order_row("#SW-2418", "Today, 9:14 am", "Meera Nair", "Kochi, KL 682001", "Cotton Runner ×2", "UPI", "paid", "₹1,198")}
{order_row("#SW-2417", "Today, 7:02 am", "Rahul Desai", "Pune, MH 411004", "Indigo Cushion Set", "Card", "shipped", "₹2,450")}
{order_row("#SW-2416", "Yesterday", "Fatima Sheikh", "Hyderabad, TS 500081", "Kora Table Mat ×4", "Cash", "cod", "₹960")}
{order_row("#SW-2415", "Yesterday", "Arjun Menon", "Bengaluru, KA 560095", "Handwoven Throw", "UPI", "completed", "₹3,200")}
{order_row("#SW-2414", "29 Aug", "Priya Raman", "Chennai, TN 600028", "Cotton Runner", "Netbanking", "disputed", "₹599")}
{order_row("#SW-2413", "29 Aug", "Vikram Joshi", "Jaipur, RJ 302015", "Indigo Cushion ×2", "UPI", "completed", "₹4,900")}
{order_row("#SW-2412", "28 Aug", "Ananya Bose", "Kolkata, WB 700019", "Kora Table Mat ×2", "Card", "completed", "₹480")}
{order_row("#SW-2411", "28 Aug", "Imran Qureshi", "Lucknow, UP 226010", "Handwoven Throw ×2", "Cash", "delivered", "₹6,400")}
{order_row("#SW-2410", "27 Aug", "Sneha Pillai", "Kochi, KL 682016", "Cotton Runner ×3", "UPI", "completed", "₹1,797", last=True)}
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 11px 20px; border-top: 1px solid #F5F5F5; background: #FAFAFA;">
          <span style="font-size: 12px; color: #737373; font-weight: 500;">Showing 1–9 of 68 orders</span>
          <div style="display: flex; gap: 6px;">
            <div style="padding: 5px 11px; border: 1px solid #E5E5E5; border-radius: 8px; background: #FFFFFF; font-size: 12px; font-weight: 600; color: #A3A3A3;">Previous</div>
            <div style="padding: 5px 11px; border: 1px solid #E5E5E5; border-radius: 8px; background: #FFFFFF; font-size: 12px; font-weight: 700; color: #262626;">Next</div>
          </div>
        </div>
      </section>'''

# ============================ ORDER DETAIL ===================================
def step(done, title, when, desc, last=False):
    dot = ('<div style="width: 26px; height: 26px; border-radius: 999px; background: #ECFDF5; border: 1.5px solid #A7F3D0; display: flex; align-items: center; justify-content: center; flex-shrink: 0;"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#047857" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"></path></svg></div>'
           if done else
           '<div style="width: 26px; height: 26px; border-radius: 999px; background: #FFFFFF; border: 1.5px dashed #D4D4D4; flex-shrink: 0;"></div>')
    line = "" if last else '<div style="position: absolute; left: 12.5px; top: 26px; bottom: -14px; width: 1.5px; background: #F0F0F0;"></div>'
    return f'''            <div style="position: relative; display: flex; gap: 12px; padding-bottom: {"0" if last else "14px"};">{line}
              {dot}
              <div style="padding-top: 2px;">
                <div style="display: flex; align-items: baseline; gap: 8px;"><span style="font-size: 13px; font-weight: 700; color: {"#0A0A0A" if done else "#A3A3A3"};">{title}</span><span style="font-size: 11px; color: #A3A3A3; font-weight: 500;">{when}</span></div>
                <p style="font-size: 12px; color: #737373; font-weight: 500; margin-top: 2px; line-height: 1.45;">{desc}</p>
              </div>
            </div>'''

def li(name, variant, qty, price):
    return f'''            <div style="display: flex; align-items: center; gap: 12px; padding: 11px 0; border-bottom: 1px solid #F5F5F5;">
              <div style="width: 44px; height: 44px; border-radius: 10px; background: #F5F5F5; border: 1px solid #E5E5E5; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#C4C4C4" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2.5"></rect><circle cx="8.8" cy="8.8" r="1.8"></circle><path d="m21 15.5-4.5-4.5L5 21"></path></svg>
              </div>
              <div style="flex: 1; min-width: 0;">
                <div style="font-size: 13px; font-weight: 700; color: #0A0A0A;">{name}</div>
                <div style="font-size: 11.5px; color: #A3A3A3; font-weight: 500;">{variant}</div>
              </div>
              <div style="font-size: 12px; color: #737373; font-weight: 600;">×{qty}</div>
              <div style="font-size: 13px; font-weight: 800; color: #0A0A0A; width: 68px; text-align: right;">{price}</div>
            </div>'''

DETAIL_BODY = f'''      <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <div style="display: flex; align-items: center; gap: 6px; height: 32px; padding: 0 11px; border: 1px solid #E5E5E5; border-radius: 9px; background: #FFFFFF; font-size: 12.5px; font-weight: 600; color: #525252;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#737373" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"></path></svg>All orders
          </div>
          {PILLS["shipped"]}
          <span style="font-size: 12px; color: #A3A3A3; font-weight: 500;">Placed 30 Aug, 7:02 am · paid by card</span>
        </div>
        <div style="display: flex; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 6px; height: 34px; padding: 0 12px; border: 1px solid #E5E5E5; border-radius: 10px; background: #FFFFFF; font-size: 12.5px; font-weight: 700; color: #525252;">Print slip</div>
          <div style="display: flex; align-items: center; gap: 6px; height: 34px; padding: 0 12px; border: 1px solid #FECDD3; border-radius: 10px; background: #FFF1F2; font-size: 12.5px; font-weight: 700; color: #BE123C;">Refund</div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr); gap: 20px; flex: 1; min-height: 0;">
        <div style="display: flex; flex-direction: column; gap: 20px; min-height: 0;">
{card("Where this order is", '<span style="font-size: 12px; font-weight: 600; color: #A3A3A3;">Auto-completes 3 Sep if no dispute</span>', f"""
{step(True, "Order placed", "30 Aug, 7:02 am", "Rahul paid ₹2,450 by card. Money is held until delivery.")}
{step(True, "Payment confirmed", "30 Aug, 7:02 am", "Razorpay reference pay_Qk28xTn4mLpR91.")}
{step(True, "Dispatched by you", "30 Aug, 4:40 pm", "Delivery code sent to Rahul on +91 98••••4412.")}
{step(False, "Delivered", "Waiting", "Ask Rahul for his 6-digit code and enter it to close this order.")}
{step(False, "Money released", "T+2 after delivery", "₹2,205 settles to HDFC ••4471.", last=True)}
""", pad="16px 20px")}

{card("What they bought", "", f"""
{li("Indigo Cushion Set", "Size: Large · Cover only", 1, "₹2,450")}
          <div style="display: flex; justify-content: space-between; padding: 11px 0 4px 0;"><span style="font-size: 12.5px; color: #737373; font-weight: 500;">Subtotal</span><span style="font-size: 12.5px; font-weight: 700; color: #0A0A0A;">₹2,450</span></div>
          <div style="display: flex; justify-content: space-between; padding: 4px 0;"><span style="font-size: 12.5px; color: #737373; font-weight: 500;">Delivery</span><span style="font-size: 12.5px; font-weight: 700; color: #047857;">Free</span></div>
          <div style="display: flex; justify-content: space-between; padding: 8px 0 0 0; border-top: 1px solid #F5F5F5; margin-top: 6px;"><span style="font-size: 13px; font-weight: 800; color: #0A0A0A;">Buyer paid</span><span style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 17px; font-weight: 900; color: #0A0A0A;">₹2,450</span></div>
""", pad="4px 20px 16px 20px", grow=True)}
        </div>

        <div style="display: flex; flex-direction: column; gap: 20px; min-height: 0;">
          <section style="background: #FFFFFF; border: 1.5px solid #FF4F00; border-radius: 16px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); overflow: hidden;">
            <div style="padding: 14px 20px; background: #FFF7ED; border-bottom: 1px solid #FFD9C2;">
              <h2 style="font-size: 14px; font-weight: 800; color: #8A2200;">Confirm the handover</h2>
              <p style="font-size: 11.5px; color: #A05010; font-weight: 500; margin-top: 2px;">Rahul reads you the code at the door</p>
            </div>
            <div style="padding: 18px 20px; display: flex; flex-direction: column; gap: 14px;">
              <div style="display: flex; gap: 8px;">
                <div style="flex: 1; height: 52px; border: 1.5px solid #E5E5E5; border-radius: 11px; background: #FAFAFA; display: flex; align-items: center; justify-content: center; font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 22px; font-weight: 900; color: #0A0A0A;">4</div>
                <div style="flex: 1; height: 52px; border: 1.5px solid #E5E5E5; border-radius: 11px; background: #FAFAFA; display: flex; align-items: center; justify-content: center; font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 22px; font-weight: 900; color: #0A0A0A;">1</div>
                <div style="flex: 1; height: 52px; border: 1.5px solid #E5E5E5; border-radius: 11px; background: #FAFAFA; display: flex; align-items: center; justify-content: center; font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 22px; font-weight: 900; color: #0A0A0A;">9</div>
                <div style="flex: 1; height: 52px; border: 1.5px solid #FF4F00; border-radius: 11px; background: #FFFFFF; display: flex; align-items: center; justify-content: center;"><div style="width: 1.5px; height: 22px; background: #FF4F00;"></div></div>
                <div style="flex: 1; height: 52px; border: 1.5px solid #E5E5E5; border-radius: 11px; background: #FAFAFA;"></div>
                <div style="flex: 1; height: 52px; border: 1.5px solid #E5E5E5; border-radius: 11px; background: #FAFAFA;"></div>
              </div>
              <div style="background: #FF4F00; color: #FFFFFF; font-size: 13px; font-weight: 800; padding: 11px; border-radius: 11px; text-align: center;">Mark delivered</div>
              <p style="font-size: 11.5px; color: #A3A3A3; font-weight: 500; text-align: center; line-height: 1.45;">3 tries left. Resend the code to Rahul if he cannot find it.</p>
            </div>
          </section>

{card("Buyer", '<span style="font-size: 11px; font-weight: 700; color: #047857; background: #ECFDF5; border: 1px solid #A7F3D0; padding: 2px 8px; border-radius: 999px;">4th order</span>', """
          <div style="display: flex; align-items: center; gap: 11px; padding-bottom: 12px; border-bottom: 1px solid #F5F5F5;">
            <div style="width: 38px; height: 38px; border-radius: 999px; background: #F0F0F0; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 800; color: #525252;">RD</div>
            <div><div style="font-size: 13.5px; font-weight: 700; color: #0A0A0A;">Rahul Desai</div><div style="font-size: 11.5px; color: #A3A3A3; font-weight: 500;">rahul.desai@example.com</div></div>
          </div>
          <div style="padding-top: 12px; display: flex; flex-direction: column; gap: 9px;">
            <div><div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #A3A3A3; margin-bottom: 3px;">Phone</div><div style="font-size: 12.5px; color: #262626; font-weight: 600;">+91 98••••4412</div></div>
            <div><div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #A3A3A3; margin-bottom: 3px;">Deliver to</div><div style="font-size: 12.5px; color: #262626; font-weight: 500; line-height: 1.5;">Flat 302, Sunrise Residency<br>Baner Road, Pune<br>Maharashtra 411045</div></div>
          </div>
""", pad="16px 20px", grow=True)}
        </div>
      </div>'''

# ============================== PRODUCTS =====================================
def prod(name, price, stock, stock_kind, pays, variants):
    tone = {"ok": ("#047857", "#ECFDF5", "#A7F3D0"), "low": ("#B45309", "#FFFBEB", "#FDE68A"),
            "out": ("#BE123C", "#FFF1F2", "#FECDD3"), "draft": ("#737373", "#F5F5F5", "#E5E5E5")}[stock_kind]
    chips = "".join(
        f'<span style="font-size: 10px; font-weight: 700; color: #525252; background: #F5F5F5; padding: 2px 7px; border-radius: 6px;">{p}</span>'
        for p in pays)
    return f'''          <div style="border: 1px solid #E5E5E5; border-radius: 14px; background: #FFFFFF; overflow: hidden; display: flex; flex-direction: column;">
            <div style="height: 118px; background: #F5F5F5; border-bottom: 1px solid #E5E5E5; display: flex; align-items: center; justify-content: center; position: relative;">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#C4C4C4" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2.5"></rect><circle cx="8.8" cy="8.8" r="1.8"></circle><path d="m21 15.5-4.5-4.5L5 21"></path></svg>
              <span style="position: absolute; top: 9px; left: 9px; font-size: 10px; font-weight: 700; color: {tone[0]}; background: {tone[1]}; border: 1px solid {tone[2]}; padding: 2px 8px; border-radius: 999px;">{stock}</span>
              <div style="position: absolute; top: 7px; right: 7px; width: 26px; height: 26px; border-radius: 8px; background: rgba(255,255,255,0.94); border: 1px solid #E5E5E5; display: flex; align-items: center; justify-content: center;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#525252" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="1.4"></circle><circle cx="12" cy="12" r="1.4"></circle><circle cx="12" cy="19" r="1.4"></circle></svg>
              </div>
            </div>
            <div style="padding: 12px; display: flex; flex-direction: column; gap: 7px; flex: 1;">
              <div style="font-size: 13px; font-weight: 700; color: #0A0A0A; line-height: 1.3; text-wrap: pretty;">{name}</div>
              <div style="display: flex; align-items: baseline; gap: 7px;">
                <span style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 17px; font-weight: 900; color: #0A0A0A;">{price}</span>
                <span style="font-size: 11px; color: #A3A3A3; font-weight: 500;">{variants}</span>
              </div>
              <div style="display: flex; gap: 5px; margin-top: auto; padding-top: 4px;">{chips}</div>
            </div>
          </div>'''

PRODUCTS_BODY = f'''      <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px;">
        <div style="display: flex; gap: 3px; background: #F0F0F0; border-radius: 11px; padding: 3px;">
          <div style="padding: 7px 13px; border-radius: 9px; background: #FFFFFF; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.06); font-size: 12.5px; font-weight: 800; color: #0A0A0A;">All 24</div>
          <div style="padding: 7px 13px; font-size: 12.5px; font-weight: 600; color: #737373;">Live 21</div>
          <div style="padding: 7px 13px; font-size: 12.5px; font-weight: 600; color: #737373;">Drafts 3</div>
          <div style="display: flex; align-items: center; gap: 7px; padding: 7px 13px; font-size: 12.5px; font-weight: 600; color: #B45309;">Low stock<span style="font-size: 10px; font-weight: 800; color: #B45309; background: #FFFBEB; border: 1px solid #FDE68A; padding: 1px 6px; border-radius: 999px;">4</span></div>
        </div>
        <div style="display: flex; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 7px; height: 34px; padding: 0 12px; border: 1px solid #E5E5E5; border-radius: 10px; background: #FFFFFF; font-size: 12.5px; font-weight: 600; color: #525252;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#737373" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5h18"></path><path d="M6.5 12h11"></path><path d="M10 19h4"></path></svg>Sort: Best selling
          </div>
          <div style="display: flex; align-items: center; gap: 7px; height: 34px; padding: 0 12px; border: 1px solid #E5E5E5; border-radius: 10px; background: #FFFFFF; font-size: 12.5px; font-weight: 600; color: #525252;">Bulk edit prices</div>
        </div>
      </div>

      <div style="display: flex; align-items: center; gap: 12px; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 12px; padding: 11px 16px;">
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#B45309" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3"></path><path d="M12 9.5v4"></path><path d="M12 17.2h.01"></path></svg>
        <span style="flex: 1; font-size: 12.5px; font-weight: 600; color: #92400E;">Cotton Table Runner has 2 left and sells about 6 a week. It will run out on Thursday.</span>
        <span style="font-size: 12.5px; font-weight: 800; color: #8A2200;">Restock now</span>
      </div>

      <section style="background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 16px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); overflow: hidden; flex: 1; min-height: 0; display: flex; flex-direction: column;">
        <div style="padding: 16px 20px; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px;">
{prod("Handwoven Cotton Table Runner", "₹599", "2 left", "low", ["UPI", "Cash"], "3 sizes")}
{prod("Indigo Block-Print Cushion Set", "₹2,450", "14 in stock", "ok", ["UPI"], "2 sizes")}
{prod("Kora Cotton Table Mat", "₹240", "38 in stock", "ok", ["UPI", "Cash"], "No variants")}
{prod("Handwoven Wool Throw", "₹3,200", "Out of stock", "out", ["UPI"], "4 colours")}
{prod("Kalamkari Cotton Napkins", "₹480", "Draft", "draft", ["UPI", "Cash"], "Set of 6")}
{prod("Ikat Weave Cushion Cover", "₹890", "9 in stock", "ok", ["UPI", "Cash"], "3 colours")}
{prod("Mangalgiri Cotton Stole", "₹1,150", "3 left", "low", ["UPI"], "5 colours")}
{prod("Jamdani Table Linen Set", "₹4,600", "6 in stock", "ok", ["UPI"], "2 sizes")}
{prod("Chanderi Silk Runner", "₹2,100", "11 in stock", "ok", ["UPI", "Cash"], "No variants")}
{prod("Beige Cotton Placemat", "₹320", "1 left", "low", ["Cash"], "Set of 4")}
        </div>
      </section>'''

# ============================== PAYOUTS ======================================
def payout_row(date, orders, gross, fee, net, state, last=False):
    tone = {"Paid": ("#047857", "#ECFDF5", "#A7F3D0"), "In transit": ("#1D4ED8", "#EFF6FF", "#BFDBFE"),
            "Scheduled": ("#737373", "#F5F5F5", "#E5E5E5")}[state]
    bb = "" if last else "border-bottom: 1px solid #F5F5F5;"
    return f'''          <div style="display: grid; grid-template-columns: minmax(0,1.2fr) 80px minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) 104px; gap: 14px; align-items: center; padding: 12px 20px; {bb}">
            <div style="font-size: 12.5px; font-weight: 700; color: #0A0A0A;">{date}</div>
            <div style="font-size: 12px; color: #737373; font-weight: 600;">{orders}</div>
            <div style="font-size: 12.5px; color: #525252; font-weight: 600; text-align: right;">{gross}</div>
            <div style="font-size: 12.5px; color: #BE123C; font-weight: 600; text-align: right;">{fee}</div>
            <div style="font-size: 13px; color: #0A0A0A; font-weight: 800; text-align: right;">{net}</div>
            <div style="display: flex; justify-content: flex-end;"><span style="font-size: 11px; font-weight: 700; color: {tone[0]}; background: {tone[1]}; border: 1px solid {tone[2]}; padding: 3px 9px; border-radius: 999px;">{state}</span></div>
          </div>'''

PAYOUTS_BODY = f'''      <div style="display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr) minmax(0, 1fr); gap: 20px;">
        <section style="background: #0A0A0A; border-radius: 16px; padding: 20px; display: flex; flex-direction: column; gap: 12px;">
          <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #A3A3A3;">Arriving Thursday</span>
          <div style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 40px; font-weight: 900; color: #FFFFFF; letter-spacing: -0.03em; line-height: 1;">₹8,640</div>
          <div style="display: flex; align-items: center; gap: 8px; padding-top: 2px;">
            <div style="width: 26px; height: 18px; border-radius: 4px; background: #262626; display: flex; align-items: center; justify-content: center;"><span style="font-size: 8px; font-weight: 800; color: #FFFFFF;">HDFC</span></div>
            <span style="font-size: 12.5px; color: #E5E5E5; font-weight: 600;">•••• 4471</span>
            <span style="font-size: 11px; font-weight: 700; color: #34D399; background: rgba(52,211,153,0.13); padding: 2px 8px; border-radius: 999px;">Verified</span>
          </div>
          <p style="font-size: 11.5px; color: #A3A3A3; font-weight: 500; line-height: 1.5; margin-top: auto;">Buyers pay Razorpay, which routes your share straight to this account two days after each delivery is confirmed.</p>
        </section>

        <section style="background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 16px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); padding: 20px; display: flex; flex-direction: column; gap: 14px;">
          <span style="{LABEL}">Held until delivery</span>
          <div style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 30px; font-weight: 900; color: #0A0A0A; letter-spacing: -0.025em; line-height: 1;">₹3,648</div>
          <div style="display: flex; flex-direction: column; gap: 9px; margin-top: auto;">
            <div style="display: flex; justify-content: space-between;"><span style="font-size: 12px; color: #737373; font-weight: 500;">3 orders to ship</span><span style="font-size: 12px; font-weight: 700; color: #0A0A0A;">₹2,205</span></div>
            <div style="display: flex; justify-content: space-between;"><span style="font-size: 12px; color: #737373; font-weight: 500;">1 out for delivery</span><span style="font-size: 12px; font-weight: 700; color: #0A0A0A;">₹1,443</span></div>
            <div style="display: flex; justify-content: space-between; padding-top: 9px; border-top: 1px solid #F5F5F5;"><span style="font-size: 12px; color: #737373; font-weight: 500;">1 disputed — on hold</span><span style="font-size: 12px; font-weight: 700; color: #BE123C;">₹599</span></div>
          </div>
        </section>

        <section style="background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 16px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); padding: 20px; display: flex; flex-direction: column; gap: 14px;">
          <span style="{LABEL}">Cash you collected</span>
          <div style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 30px; font-weight: 900; color: #0A0A0A; letter-spacing: -0.025em; line-height: 1;">₹1,920</div>
          <p style="font-size: 12px; color: #737373; font-weight: 500; line-height: 1.5;">You already hold this money. Nothing settles to your bank for cash-on-delivery orders.</p>
          <div style="display: flex; justify-content: space-between; padding-top: 12px; border-top: 1px solid #F5F5F5; margin-top: auto;"><span style="font-size: 12px; color: #737373; font-weight: 500;">Commission owed on it</span><span style="font-size: 12px; font-weight: 700; color: #BE123C;">₹192</span></div>
        </section>
      </div>

      <section style="background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 16px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); overflow: hidden; flex: 1; min-height: 0; display: flex; flex-direction: column;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 20px; border-bottom: 1px solid #F5F5F5;">
          <div><h2 style="font-size: 14px; font-weight: 800; color: #0A0A0A;">Payout history</h2><p style="font-size: 11px; color: #A3A3A3; font-weight: 500; margin-top: 1px;">Every settlement Razorpay has sent to your account</p></div>
          <div style="display: flex; align-items: center; gap: 7px; height: 32px; padding: 0 12px; border: 1px solid #E5E5E5; border-radius: 9px; font-size: 12.5px; font-weight: 600; color: #525252;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#737373" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"></path><path d="m7 10 5 5 5-5"></path><path d="M20 21H4"></path></svg>Download statement
          </div>
        </div>
        <div style="display: grid; grid-template-columns: minmax(0,1.2fr) 80px minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) 104px; gap: 14px; padding: 10px 20px; background: #FAFAFA; border-bottom: 1px solid #F5F5F5;">
          <span style="{TH}">Settlement date</span><span style="{TH}">Orders</span><span style="{TH} text-align: right;">Collected</span><span style="{TH} text-align: right;">Commission</span><span style="{TH} text-align: right;">Paid to you</span><span></span>
        </div>
        <div style="flex: 1; min-height: 0;">
{payout_row("2 Sep 2026", "4", "₹9,600", "−₹960", "₹8,640", "Scheduled")}
{payout_row("28 Aug 2026", "6", "₹12,400", "−₹1,240", "₹11,160", "In transit")}
{payout_row("24 Aug 2026", "5", "₹8,900", "−₹890", "₹8,010", "Paid")}
{payout_row("20 Aug 2026", "7", "₹14,200", "−₹1,420", "₹12,780", "Paid")}
{payout_row("16 Aug 2026", "3", "₹5,100", "−₹510", "₹4,590", "Paid")}
{payout_row("12 Aug 2026", "6", "₹11,800", "−₹1,180", "₹10,620", "Paid", last=True)}
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 20px; border-top: 1px solid #F5F5F5; background: #FFF7ED;">
          <span style="font-size: 12.5px; color: #8A2200; font-weight: 600;">You have paid ₹6,200 in commission over 31 settlements. Pro would have cost ₹499 a month.</span>
          <span style="font-size: 12.5px; font-weight: 800; color: #8A2200;">Compare plans</span>
        </div>
      </section>'''

# ============================== INSIGHTS =====================================
def hbar(label, value, pct, shade):
    return f'''            <div style="display: flex; flex-direction: column; gap: 6px;">
              <div style="display: flex; justify-content: space-between; align-items: baseline;"><span style="font-size: 12.5px; font-weight: 700; color: #0A0A0A;">{label}</span><span style="font-size: 12.5px; font-weight: 700; color: #525252;">{value}</span></div>
              <div style="height: 9px; background: #F5F5F5; border-radius: 5px; overflow: hidden;"><div style="width: {pct}%; height: 9px; background: {shade}; border-radius: 5px;"></div></div>
            </div>'''

INSIGHTS_BODY = f'''      <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px;">
        <div style="display: flex; gap: 3px; background: #F0F0F0; border-radius: 11px; padding: 3px;">
          <div style="padding: 7px 14px; font-size: 12.5px; font-weight: 600; color: #737373;">7 days</div>
          <div style="padding: 7px 14px; border-radius: 9px; background: #FFFFFF; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.06); font-size: 12.5px; font-weight: 800; color: #0A0A0A;">30 days</div>
          <div style="padding: 7px 14px; font-size: 12.5px; font-weight: 600; color: #737373;">3 months</div>
          <div style="padding: 7px 14px; font-size: 12.5px; font-weight: 600; color: #737373;">This year</div>
        </div>
        <span style="font-size: 12px; color: #A3A3A3; font-weight: 500;">Compared with 1–31 July</span>
      </div>

      <section style="background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 16px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); overflow: hidden;">
        <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-bottom: 1px solid #F5F5F5;">
          <div style="padding: 16px 20px; border-right: 1px solid #F5F5F5;"><span style="{LABEL}">Revenue</span><div style="display: flex; align-items: baseline; gap: 8px; margin-top: 5px;"><span style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 26px; font-weight: 900; color: #0A0A0A; letter-spacing: -0.02em;">₹41,200</span><span style="font-size: 12px; font-weight: 700; color: #047857;">+18%</span></div></div>
          <div style="padding: 16px 20px; border-right: 1px solid #F5F5F5;"><span style="{LABEL}">Orders</span><div style="display: flex; align-items: baseline; gap: 8px; margin-top: 5px;"><span style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 26px; font-weight: 900; color: #0A0A0A; letter-spacing: -0.02em;">68</span><span style="font-size: 12px; font-weight: 700; color: #047857;">+19%</span></div></div>
          <div style="padding: 16px 20px; border-right: 1px solid #F5F5F5;"><span style="{LABEL}">Repeat buyers</span><div style="display: flex; align-items: baseline; gap: 8px; margin-top: 5px;"><span style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 26px; font-weight: 900; color: #0A0A0A; letter-spacing: -0.02em;">31%</span><span style="font-size: 12px; font-weight: 700; color: #047857;">+6pt</span></div></div>
          <div style="padding: 16px 20px;"><span style="{LABEL}">Disputes</span><div style="display: flex; align-items: baseline; gap: 8px; margin-top: 5px;"><span style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 26px; font-weight: 900; color: #0A0A0A; letter-spacing: -0.02em;">1.5%</span><span style="font-size: 12px; font-weight: 700; color: #BE123C;">+0.4pt</span></div></div>
        </div>
        <div style="padding: 20px 24px 14px 24px;">
          <h2 style="font-size: 14px; font-weight: 800; color: #0A0A0A; margin-bottom: 2px;">Revenue per day</h2>
          <p style="font-size: 11.5px; color: #A3A3A3; font-weight: 500; margin-bottom: 14px;">Paid and completed orders, August 2026</p>
          <svg width="100%" height="230" viewBox="0 0 1080 230" preserveAspectRatio="none" style="display: block; overflow: visible;">
            <line x1="44" y1="10" x2="1080" y2="10" stroke="#F5F5F5" stroke-width="1"></line>
            <line x1="44" y1="64" x2="1080" y2="64" stroke="#F5F5F5" stroke-width="1"></line>
            <line x1="44" y1="118" x2="1080" y2="118" stroke="#F5F5F5" stroke-width="1"></line>
            <line x1="44" y1="172" x2="1080" y2="172" stroke="#F5F5F5" stroke-width="1"></line>
            <line x1="44" y1="222" x2="1080" y2="222" stroke="#E5E5E5" stroke-width="1"></line>
            <text x="38" y="14" text-anchor="end" font-size="10" font-weight="600" fill="#A3A3A3">12k</text>
            <text x="38" y="68" text-anchor="end" font-size="10" font-weight="600" fill="#A3A3A3">9k</text>
            <text x="38" y="122" text-anchor="end" font-size="10" font-weight="600" fill="#A3A3A3">6k</text>
            <text x="38" y="176" text-anchor="end" font-size="10" font-weight="600" fill="#A3A3A3">3k</text>
            <text x="38" y="226" text-anchor="end" font-size="10" font-weight="600" fill="#A3A3A3">0</text>
            <path d="M64 186 L98 174 L132 190 L166 158 L200 166 L234 140 L268 150 L302 120 L336 132 L370 104 L404 118 L438 88 L472 100 L506 74 L540 96 L574 66 L608 82 L642 58 L676 72 L710 46 L744 64 L778 40 L812 56 L846 34 L880 50 L914 28 L948 44 L982 22 L1016 38 L1050 16 L1050 222 L64 222 Z" fill="#FF4F00" fill-opacity="0.07"></path>
            <path d="M64 186 L98 174 L132 190 L166 158 L200 166 L234 140 L268 150 L302 120 L336 132 L370 104 L404 118 L438 88 L472 100 L506 74 L540 96 L574 66 L608 82 L642 58 L676 72 L710 46 L744 64 L778 40 L812 56 L846 34 L880 50 L914 28 L948 44 L982 22 L1016 38 L1050 16" fill="none" stroke="#FF4F00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
            <circle cx="1050" cy="16" r="4.5" fill="#FF4F00" stroke="#FFFFFF" stroke-width="2"></circle>
          </svg>
          <div style="display: flex; justify-content: space-between; padding: 8px 0 0 44px;">
            <span style="font-size: 10px; font-weight: 600; color: #A3A3A3;">1 Aug</span><span style="font-size: 10px; font-weight: 600; color: #A3A3A3;">8 Aug</span><span style="font-size: 10px; font-weight: 600; color: #A3A3A3;">15 Aug</span><span style="font-size: 10px; font-weight: 600; color: #A3A3A3;">23 Aug</span><span style="font-size: 10px; font-weight: 700; color: #525252;">31 Aug · ₹11,600</span>
          </div>
        </div>
      </section>

      <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; flex: 1; min-height: 0;">
{card("Best sellers", '<span style="font-size: 11px; font-weight: 600; color: #A3A3A3;">by revenue</span>', f"""
          <div style="display: flex; flex-direction: column; gap: 14px;">
{hbar("Cotton Table Runner", "₹14,376", 100, "#FF4F00")}
{hbar("Indigo Cushion Set", "₹9,800", 68, "#FF7A3D")}
{hbar("Handwoven Throw", "₹6,400", 45, "#FFA478")}
{hbar("Kora Table Mat", "₹3,840", 27, "#FFC9AC")}
{hbar("Chanderi Silk Runner", "₹2,100", 15, "#FFE0CF")}
          </div>
""", pad="18px 20px", grow=True)}

{card("How buyers pay", '<span style="font-size: 11px; font-weight: 600; color: #A3A3A3;">68 orders</span>', f"""
          <div style="display: flex; flex-direction: column; gap: 14px;">
{hbar("UPI", "41 orders", 100, "#FF4F00")}
{hbar("Cards", "13 orders", 32, "#FF7A3D")}
{hbar("Cash on delivery", "9 orders", 22, "#FFA478")}
{hbar("Netbanking", "5 orders", 12, "#FFC9AC")}
          </div>
          <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid #F5F5F5;">
            <p style="font-size: 12px; color: #737373; font-weight: 500; line-height: 1.5;">Cash orders take <strong style="color:#0A0A0A; font-weight:700;">4 days longer</strong> to close on average, because the money never passes through Razorpay.</p>
          </div>
""", pad="18px 20px", grow=True)}

{card("Where your buyers are", '<span style="font-size: 11px; font-weight: 600; color: #A3A3A3;">top cities</span>', f"""
          <div style="display: flex; flex-direction: column; gap: 14px;">
{hbar("Bengaluru", "18 orders", 100, "#FF4F00")}
{hbar("Kochi", "14 orders", 78, "#FF7A3D")}
{hbar("Pune", "11 orders", 61, "#FFA478")}
{hbar("Hyderabad", "9 orders", 50, "#FFC9AC")}
{hbar("Chennai", "7 orders", 39, "#FFE0CF")}
          </div>
          <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid #F5F5F5;">
            <p style="font-size: 12px; color: #737373; font-weight: 500; line-height: 1.5;">South India is <strong style="color:#0A0A0A; font-weight:700;">71%</strong> of your orders. Free delivery above ₹1,500 could lift the rest.</p>
          </div>
""", pad="18px 20px", grow=True)}
      </div>'''

# ============================== SETTINGS =====================================
def field(label, value, hint="", w="100%"):
    h = f'<div style="font-size: 11px; color: #A3A3A3; font-weight: 500; margin-top: 5px;">{hint}</div>' if hint else ""
    return f'''            <div style="width: {w};">
              <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #525252; margin-bottom: 6px;">{label}</div>
              <div style="height: 40px; border: 1px solid #E5E5E5; border-radius: 12px; background: #FFFFFF; display: flex; align-items: center; padding: 0 14px; font-size: 13.5px; color: #0A0A0A; font-weight: 500;">{value}</div>{h}
            </div>'''

def toggle(on, title, desc):
    knob = ('<div style="width: 40px; height: 23px; border-radius: 999px; background: #FF4F00; display: flex; align-items: center; justify-content: flex-end; padding: 0 2.5px; flex-shrink: 0;"><div style="width: 18px; height: 18px; border-radius: 999px; background: #FFFFFF;"></div></div>'
            if on else
            '<div style="width: 40px; height: 23px; border-radius: 999px; background: #E5E5E5; display: flex; align-items: center; padding: 0 2.5px; flex-shrink: 0;"><div style="width: 18px; height: 18px; border-radius: 999px; background: #FFFFFF;"></div></div>')
    return f'''            <div style="display: flex; align-items: flex-start; gap: 14px; padding: 13px 0; border-bottom: 1px solid #F5F5F5;">
              <div style="flex: 1;"><div style="font-size: 13px; font-weight: 700; color: #0A0A0A;">{title}</div><div style="font-size: 12px; color: #737373; font-weight: 500; margin-top: 2px; line-height: 1.45;">{desc}</div></div>
              {knob}
            </div>'''

SET_NAV = ""
for i, s in enumerate(["Shop profile", "Payments & bank", "Delivery", "Tax & invoicing", "Notifications", "Your account", "Close shop"]):
    on = i == 0
    danger = i == 6
    SET_NAV += f'''        <div style="padding: 9px 12px; border-radius: 10px; {"background: #FFF7ED; " if on else ""}font-size: 13px; font-weight: {"700" if on else "600"}; color: {"#C43D00" if on else ("#BE123C" if danger else "#525252")};">{s}</div>'''

SETTINGS_BODY = f'''      <div style="display: grid; grid-template-columns: 208px minmax(0, 1fr); gap: 24px; flex: 1; min-height: 0;">
        <nav style="display: flex; flex-direction: column; gap: 2px;">
{SET_NAV}
        </nav>

        <div style="display: flex; flex-direction: column; gap: 20px; min-height: 0;">
{card("Shop profile", '<span style="font-size: 12px; font-weight: 700; color: #A3A3A3;">Buyers see this</span>', f"""
          <div style="display: flex; gap: 20px; align-items: flex-start;">
            <div style="display: flex; flex-direction: column; gap: 8px; align-items: center;">
              <div style="width: 88px; height: 88px; border-radius: 20px; background: #F5F5F5; border: 1px solid #E5E5E5; display: flex; align-items: center; justify-content: center;">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#C4C4C4" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2.5"></rect><circle cx="8.8" cy="8.8" r="1.8"></circle><path d="m21 15.5-4.5-4.5L5 21"></path></svg>
              </div>
              <span style="font-size: 11.5px; font-weight: 700; color: #C43D00;">Change logo</span>
            </div>
            <div style="flex: 1; display: flex; flex-direction: column; gap: 14px;">
              <div style="display: flex; gap: 14px;">
{field("Shop name", "Asha Handlooms")}
{field("Shop address", "stallwise.in/asha", "Changing this breaks links you have already shared.")}
              </div>
              <div>
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #525252; margin-bottom: 6px;">About the shop</div>
                <div style="min-height: 62px; border: 1px solid #E5E5E5; border-radius: 12px; background: #FFFFFF; padding: 11px 14px; font-size: 13.5px; color: #0A0A0A; font-weight: 500; line-height: 1.55;">Handwoven cotton and khadi home linen from Chendamangalam, Kerala. Every piece is made on a pit loom by one of six weavers we work with.</div>
              </div>
            </div>
          </div>
""", pad="18px 20px")}

{card("Delivery", "", f"""
          <div style="display: flex; gap: 14px; margin-bottom: 4px;">
{field("Delivery charge", "₹60", "", "33%")}
{field("Free delivery above", "₹1,500", "", "33%")}
{field("Usual dispatch time", "2 working days", "", "34%")}
          </div>
{toggle(True, "Offer cash on delivery", "Buyers pay you in cash at the door. You keep the money, and commission is billed separately.")}
{toggle(False, "Ship outside Kerala", "Turn this on once you have a courier account for the rest of India.")}
""", pad="18px 20px")}

{card("Tax & invoicing", '<span style="font-size: 11px; font-weight: 700; color: #B45309; background: #FFFBEB; border: 1px solid #FDE68A; padding: 2px 8px; border-radius: 999px;">Needs your GSTIN</span>', f"""
          <div style="display: flex; gap: 14px;">
{field("GSTIN", "Not added yet", "Required once your turnover crosses ₹40 lakh.", "50%")}
{field("HSN code for handloom", "5702", "", "50%")}
          </div>
""", pad="18px 20px")}

{card("Notifications", "", f"""
{toggle(True, "Email me when an order comes in", "Sent to asha@example.com the moment a buyer pays.")}
{toggle(True, "Daily summary at 8 pm", "One message with the day's orders, cash collected and anything left to ship.")}
{toggle(False, "Weekly insights digest", "Best sellers, repeat buyers and what ran out of stock.")}
""", pad="18px 20px", grow=True)}
        </div>
      </div>'''

# ============================== MOBILE =======================================
def mobile(name, body, title, h=844):
    tabs = ""
    for i, (k, lb) in enumerate([("home", "Home"), ("orders", "Orders"), ("products", "Products"), ("insights", "Insights"), ("settings", "More")]):
        on = i == (0 if name == "MobileHome" else 1)
        c = "#FF4F00" if on else "#A3A3A3"
        tabs += f'''        <div style="flex: 1; height: 56px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;">
          <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[k]}</svg>
          <span style="font-size: 10px; font-weight: {"800" if on else "600"}; color: {c};">{lb}</span>
        </div>'''
    doc = HEAD + f'''
<div style="width: 390px; height: {h}px; display: flex; flex-direction: column; background: #FAFAFA; overflow: hidden;">
  <header style="flex-shrink: 0; background: #FFFFFF; border-bottom: 1px solid #E5E5E5; padding: 14px 18px; display: flex; align-items: center; justify-content: space-between; gap: 12px;">
{title}
  </header>
  <div style="flex: 1; overflow: hidden; padding: 16px 18px; display: flex; flex-direction: column; gap: 14px;">
{body}
  </div>
  <nav style="flex-shrink: 0; background: #FFFFFF; border-top: 1px solid #E5E5E5; display: flex; padding-bottom: 6px;">
{tabs}
  </nav>
</div>
''' + TAIL
    (OUT / f"{name}.dc.html").write_text(doc, encoding="utf-8")
    return len(doc)

M_TITLE_HOME = '''    <div style="display: flex; align-items: center; gap: 10px;">
      <div style="width: 34px; height: 34px; border-radius: 11px; background: #FF4F00; display: flex; align-items: center; justify-content: center;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M4.2 8h15.6l-1.1 11.1A2 2 0 0 1 16.7 21H7.3a2 2 0 0 1-2-1.9Z"></path><path d="M8.6 8V6.1a3.4 3.4 0 0 1 6.8 0V8"></path></svg>
      </div>
      <div><div style="font-size: 15px; font-weight: 800; color: #0A0A0A; font-family: 'Cabinet Grotesk','Archivo',sans-serif; line-height: 1.15;">Asha Handlooms</div><div style="font-size: 11px; color: #A3A3A3; font-weight: 500;">stallwise.in/asha</div></div>
    </div>
    <div style="position: relative; width: 40px; height: 40px; border: 1px solid #E5E5E5; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
      <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#525252" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path></svg>
      <span style="position: absolute; top: 7px; right: 8px; width: 8px; height: 8px; border-radius: 999px; background: #FF4F00; border: 1.5px solid #FFFFFF;"></span>
    </div>'''

M_TITLE_ORDER = '''    <div style="display: flex; align-items: center; gap: 12px;">
      <div style="width: 40px; height: 40px; border: 1px solid #E5E5E5; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#525252" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"></path></svg>
      </div>
      <div><div style="font-size: 15px; font-weight: 800; color: #0A0A0A; font-family: 'Cabinet Grotesk','Archivo',sans-serif; line-height: 1.15;">#SW-2417</div><div style="font-size: 11px; color: #A3A3A3; font-weight: 500;">Rahul Desai · Pune</div></div>
    </div>
    ''' + PILLS["shipped"]

def m_task(color, bg, bd, tag, headline, sub, cta):
    return f'''      <div style="background: #FFFFFF; border: 1px solid {bd}; border-radius: 14px; padding: 14px; display: flex; align-items: center; gap: 13px;">
        <div style="width: 44px; height: 44px; border-radius: 12px; background: {bg}; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">{tag}</svg>
        </div>
        <div style="flex: 1; min-width: 0;">
          <div style="font-size: 14px; font-weight: 800; color: #0A0A0A; line-height: 1.25;">{headline}</div>
          <div style="font-size: 12px; color: #737373; font-weight: 500; margin-top: 2px;">{sub}</div>
        </div>
        <div style="font-size: 12px; font-weight: 800; color: {color}; white-space: nowrap;">{cta}</div>
      </div>'''

MHOME_BODY = f'''      <div style="background: #0A0A0A; border-radius: 16px; padding: 18px; display: flex; flex-direction: column; gap: 6px;">
        <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #A3A3A3;">Arriving Thursday</span>
        <div style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 34px; font-weight: 900; color: #FFFFFF; letter-spacing: -0.03em; line-height: 1;">₹8,640</div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 6px;">
          <span style="font-size: 12px; color: #A3A3A3; font-weight: 500;">HDFC ••4471 · ₹3,648 still held</span>
          <span style="font-size: 12px; font-weight: 700; color: #FF7A3D;">Details</span>
        </div>
      </div>

      <div style="display: flex; flex-direction: column; gap: 9px;">
        <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #A3A3A3;">Needs you today</div>
{m_task("#FF4F00", "#FFF7ED", "#FFD9C2", '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h1.5"></path><path d="M9 18h5"></path><path d="M18.5 18H21a1 1 0 0 0 1-1v-3.6a1 1 0 0 0-.2-.6l-3-3.8a1 1 0 0 0-.8-.4H14"></path><circle cx="6.5" cy="18" r="2"></circle><circle cx="16.5" cy="18" r="2"></circle>', "3 orders to ship", "Oldest waiting 2 days", "Open")}
{m_task("#7E22CE", "#FAF5FF", "#E9D5FF", '<rect x="4" y="10.5" width="16" height="11" rx="2.5"></rect><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"></path>', "1 delivery to close", "Enter Rahul's code", "Enter")}
{m_task("#B45309", "#FFFBEB", "#FDE68A", '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3"></path><path d="M12 9.5v4"></path><path d="M12 17.2h.01"></path>', "4 running low", "Two are best sellers", "Restock")}
      </div>

      <div style="display: flex; gap: 10px;">
        <div style="flex: 1; height: 48px; border-radius: 13px; background: #FF4F00; color: #FFFFFF; display: flex; align-items: center; justify-content: center; gap: 7px; font-size: 13.5px; font-weight: 800;">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"></path><path d="M12 5v14"></path></svg>Add product
        </div>
        <div style="flex: 1; height: 48px; border-radius: 13px; border: 1px solid #E5E5E5; background: #FFFFFF; color: #262626; display: flex; align-items: center; justify-content: center; gap: 7px; font-size: 13.5px; font-weight: 800;">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#262626" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7"></path><path d="m8 7 4-4 4 4"></path><path d="M12 3v13"></path></svg>Share shop
        </div>
      </div>

      <div style="display: flex; gap: 10px;">
        <div style="flex: 1; background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 14px; padding: 13px;">
          <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #A3A3A3;">Today</div>
          <div style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 22px; font-weight: 900; color: #0A0A0A; margin-top: 4px; line-height: 1;">₹2,158</div>
          <div style="font-size: 11px; color: #047857; font-weight: 700; margin-top: 4px;">3 orders</div>
        </div>
        <div style="flex: 1; background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 14px; padding: 13px;">
          <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #A3A3A3;">This month</div>
          <div style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 22px; font-weight: 900; color: #0A0A0A; margin-top: 4px; line-height: 1;">₹41,200</div>
          <div style="font-size: 11px; color: #047857; font-weight: 700; margin-top: 4px;">+18% on July</div>
        </div>
      </div>

      <div style="background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 14px; overflow: hidden; flex: 1; min-height: 0;">
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid #F5F5F5;">
          <span style="font-size: 13px; font-weight: 800; color: #0A0A0A;">Latest orders</span>
          <span style="font-size: 12px; font-weight: 700; color: #C43D00;">All 68</span>
        </div>
        <div style="display: flex; align-items: center; gap: 11px; padding: 11px 14px; border-bottom: 1px solid #F5F5F5;">
          <div style="flex: 1; min-width: 0;"><div style="font-size: 13px; font-weight: 700; color: #0A0A0A;">Meera Nair</div><div style="font-size: 11px; color: #A3A3A3; font-weight: 500;">Cotton Runner ×2 · 2h ago</div></div>
          <div style="font-size: 13px; font-weight: 800; color: #0A0A0A;">₹1,198</div>
        </div>
        <div style="display: flex; align-items: center; gap: 11px; padding: 11px 14px; border-bottom: 1px solid #F5F5F5;">
          <div style="flex: 1; min-width: 0;"><div style="font-size: 13px; font-weight: 700; color: #0A0A0A;">Rahul Desai</div><div style="font-size: 11px; color: #A3A3A3; font-weight: 500;">Indigo Cushion Set · 5h ago</div></div>
          <div style="font-size: 13px; font-weight: 800; color: #0A0A0A;">₹2,450</div>
        </div>
        <div style="display: flex; align-items: center; gap: 11px; padding: 11px 14px;">
          <div style="flex: 1; min-width: 0;"><div style="font-size: 13px; font-weight: 700; color: #0A0A0A;">Fatima Sheikh</div><div style="font-size: 11px; color: #A3A3A3; font-weight: 500;">Kora Table Mat ×4 · 1d ago</div></div>
          <div style="font-size: 13px; font-weight: 800; color: #0A0A0A;">₹960</div>
        </div>
      </div>'''

MORDER_BODY = '''      <div style="background: #FFFFFF; border: 1.5px solid #FF4F00; border-radius: 16px; overflow: hidden;">
        <div style="padding: 14px 16px; background: #FFF7ED; border-bottom: 1px solid #FFD9C2;">
          <div style="font-size: 15px; font-weight: 800; color: #8A2200; font-family: 'Cabinet Grotesk','Archivo',sans-serif;">Confirm the handover</div>
          <div style="font-size: 12px; color: #A05010; font-weight: 500; margin-top: 2px;">Ask Rahul to read out his 6-digit code</div>
        </div>
        <div style="padding: 18px 16px; display: flex; flex-direction: column; gap: 14px;">
          <div style="display: flex; gap: 7px;">
            <div style="flex: 1; height: 56px; border: 1.5px solid #E5E5E5; border-radius: 12px; background: #FAFAFA; display: flex; align-items: center; justify-content: center; font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 24px; font-weight: 900; color: #0A0A0A;">4</div>
            <div style="flex: 1; height: 56px; border: 1.5px solid #E5E5E5; border-radius: 12px; background: #FAFAFA; display: flex; align-items: center; justify-content: center; font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 24px; font-weight: 900; color: #0A0A0A;">1</div>
            <div style="flex: 1; height: 56px; border: 1.5px solid #E5E5E5; border-radius: 12px; background: #FAFAFA; display: flex; align-items: center; justify-content: center; font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 24px; font-weight: 900; color: #0A0A0A;">9</div>
            <div style="flex: 1; height: 56px; border: 1.5px solid #FF4F00; border-radius: 12px; background: #FFFFFF; display: flex; align-items: center; justify-content: center;"><div style="width: 1.5px; height: 24px; background: #FF4F00;"></div></div>
            <div style="flex: 1; height: 56px; border: 1.5px solid #E5E5E5; border-radius: 12px; background: #FAFAFA;"></div>
            <div style="flex: 1; height: 56px; border: 1.5px solid #E5E5E5; border-radius: 12px; background: #FAFAFA;"></div>
          </div>
          <div style="height: 52px; background: #FF4F00; color: #FFFFFF; font-size: 15px; font-weight: 800; border-radius: 13px; display: flex; align-items: center; justify-content: center;">Mark delivered</div>
          <div style="display: flex; align-items: center; justify-content: center; gap: 6px;">
            <span style="font-size: 12px; color: #A3A3A3; font-weight: 500;">3 tries left ·</span>
            <span style="font-size: 12px; font-weight: 700; color: #C43D00;">Resend code</span>
          </div>
        </div>
      </div>

      <div style="background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 14px; padding: 14px; display: flex; flex-direction: column; gap: 12px;">
        <div style="display: flex; align-items: center; gap: 11px;">
          <div style="width: 40px; height: 40px; border-radius: 999px; background: #F0F0F0; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 800; color: #525252;">RD</div>
          <div style="flex: 1;"><div style="font-size: 14px; font-weight: 700; color: #0A0A0A;">Rahul Desai</div><div style="font-size: 11.5px; color: #A3A3A3; font-weight: 500;">4th order from you</div></div>
          <div style="width: 40px; height: 40px; border-radius: 12px; border: 1px solid #E5E5E5; display: flex; align-items: center; justify-content: center;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#525252" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 15.5v2.6a1.4 1.4 0 0 1-1.6 1.4 14 14 0 0 1-6.1-2.2 13.8 13.8 0 0 1-4.2-4.2A14 14 0 0 1 .4 7a1.4 1.4 0 0 1 1.4-1.6h2.6a1.4 1.4 0 0 1 1.4 1.2c.1.7.3 1.4.5 2a1.4 1.4 0 0 1-.3 1.5l-1.1 1.1a11 11 0 0 0 4.2 4.2l1.1-1.1a1.4 1.4 0 0 1 1.5-.3c.6.2 1.3.4 2 .5a1.4 1.4 0 0 1 1.2 1.4Z"></path></svg>
          </div>
        </div>
        <div style="padding-top: 12px; border-top: 1px solid #F5F5F5;">
          <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #A3A3A3; margin-bottom: 4px;">Deliver to</div>
          <div style="font-size: 13px; color: #262626; font-weight: 500; line-height: 1.55;">Flat 302, Sunrise Residency<br>Baner Road, Pune, Maharashtra 411045</div>
        </div>
      </div>

      <div style="background: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 14px; padding: 14px; flex: 1; min-height: 0;">
        <div style="display: flex; align-items: center; gap: 12px; padding-bottom: 12px; border-bottom: 1px solid #F5F5F5;">
          <div style="width: 46px; height: 46px; border-radius: 11px; background: #F5F5F5; border: 1px solid #E5E5E5; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#C4C4C4" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2.5"></rect><circle cx="8.8" cy="8.8" r="1.8"></circle><path d="m21 15.5-4.5-4.5L5 21"></path></svg>
          </div>
          <div style="flex: 1; min-width: 0;"><div style="font-size: 13.5px; font-weight: 700; color: #0A0A0A;">Indigo Cushion Set</div><div style="font-size: 11.5px; color: #A3A3A3; font-weight: 500;">Large · Cover only · ×1</div></div>
          <div style="font-size: 14px; font-weight: 800; color: #0A0A0A;">₹2,450</div>
        </div>
        <div style="display: flex; justify-content: space-between; padding-top: 12px;">
          <span style="font-size: 13px; font-weight: 700; color: #0A0A0A;">You receive</span>
          <div style="text-align: right;">
            <div style="font-family: 'Cabinet Grotesk','Archivo',sans-serif; font-size: 19px; font-weight: 900; color: #0A0A0A; line-height: 1;">₹2,205</div>
            <div style="font-size: 11px; color: #A3A3A3; font-weight: 500; margin-top: 3px;">after ₹245 commission</div>
          </div>
        </div>
      </div>'''

# ============================== EMIT =========================================
sizes = {}
sizes["Orders"] = page("Orders", "orders", "Orders", "3 paid orders are waiting to be packed", ORDERS_BODY)
sizes["OrderDetail"] = page("OrderDetail", "orders", "Order #SW-2417", "Rahul Desai · Pune · out for delivery since yesterday", DETAIL_BODY)
sizes["Products"] = page("Products", "products", "Products", "24 listings · 21 live, 3 drafts", PRODUCTS_BODY, action=primary("Add product"))
sizes["Payouts"] = page("Payouts", "payouts", "Payouts", "Where your money is right now", PAYOUTS_BODY)
sizes["Insights"] = page("Insights", "insights", "Insights", "What is selling, and to whom", INSIGHTS_BODY)
sizes["Settings"] = page("Settings", "settings", "Settings", "Shop details, delivery, tax and alerts", SETTINGS_BODY, h=1240)
sizes["MobileHome"] = mobile("MobileHome", MHOME_BODY, M_TITLE_HOME)
sizes["MobileOrder"] = mobile("MobileOrder", MORDER_BODY, M_TITLE_ORDER)

for k, v in sorted(sizes.items()):
    print(f"  {k:14s} {v:>7,} bytes")
