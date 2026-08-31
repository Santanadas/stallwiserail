import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";

function loadRazorpay() {
  return new Promise((res) => {
    if (window.Razorpay) return res(true);
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => res(true);
    s.onerror = () => res(false);
    document.body.appendChild(s);
  });
}

/**
 * Places the order and, for online payments, drives the Razorpay checkout and
 * server-side signature verification. Shared by the shop page and each product
 * page so both can check out without duplicating the flow.
 */
export function useCheckout({ storeSlug, storeName, cart, cartTotal, payMethod, clear }) {
  const navigate = useNavigate();
  const [placing, setPlacing] = useState(false);
  const [err, setErr] = useState("");

  const checkout = async (buyer) => {
    setErr("");
    setPlacing(true);
    const email = (buyer.buyerEmail || "").trim();
    try {
      const { data } = await api.post("/orders", {
        storeSlug,
        buyerName: (buyer.buyerName || "").trim(),
        buyerEmail: email,
        buyerPhone: (buyer.buyerPhone || "").replace(/\D/g, ""),
        paymentMethod: payMethod,
        items: cart.map((c) => ({
          productId: c.productId,
          quantity: c.quantity,
          optionSelections: c.optionSelections,
        })),
      });

      const orderId = data.orderId;
      const goToOrder = () => {
        clear?.();
        navigate(`/order/${orderId}?email=${encodeURIComponent(email)}`);
      };

      // Cash on delivery: nothing to charge now.
      if (payMethod === "cod" || !data.razorpayOrderId) {
        goToOrder();
        return;
      }

      const ok = await loadRazorpay();
      if (!ok || !window.Razorpay) {
        setErr("Could not load the payment window. Your order was saved — open it to pay.");
        goToOrder();
        return;
      }

      const rzp = new window.Razorpay({
        key: data.razorpayKeyId,
        order_id: data.razorpayOrderId,
        amount: Math.round((data.amount || cartTotal) * 100),
        currency: "INR",
        name: storeName || "Stall Wise",
        description: `Order ${orderId}`,
        prefill: {
          name: (buyer.buyerName || "").trim(),
          email,
          contact: (buyer.buyerPhone || "").replace(/\D/g, ""),
        },
        theme: { color: "#FF4F00" },
        modal: { ondismiss: () => { setPlacing(false); goToOrder(); } },
        handler: async (res) => {
          try {
            await api.post(`/orders/${orderId}/verify-payment`, {
              razorpay_order_id: res.razorpay_order_id,
              razorpay_payment_id: res.razorpay_payment_id,
              razorpay_signature: res.razorpay_signature,
            });
          } catch {
            // Payment went through at Razorpay; the webhook reconciles it.
          } finally {
            goToOrder();
          }
        },
      });
      rzp.on("payment.failed", (r) => {
        setErr(r.error?.description || "Payment failed. Your order was saved — open it to try again.");
        setPlacing(false);
      });
      rzp.open();
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail));
      setPlacing(false);
    }
  };

  return { checkout, placing, err, setErr };
}
