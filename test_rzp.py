import razorpay
import json

kid = "rzp_live_TVs3r96Uvj8B1S"
ksec = "xM9IugMkJB74bdDbH7UWh3Zi"

try:
    client = razorpay.Client(auth=(kid, ksec))
    order = client.order.create({
        "amount": 19900,
        "currency": "INR",
        "payment_capture": 1,
        "notes": {
            "type": "platform_subscription",
            "userId": "test",
            "interval": "monthly",
            "tier": "Premium",
        },
    })
    print(json.dumps(order, indent=2))
except Exception as e:
    print("Error:", str(e))
