/**
 * Site-wide contact details.
 *
 * One place, because the address appears on the contact page, in the footer
 * and in every transactional email (backend/email_service.py keeps its own
 * copy, overridable with SUPPORT_EMAIL).
 */
export const SUPPORT_EMAIL = "help@stallwise.in";

/**
 * Razorpay partner referral link. A seller who signs up through it gets their
 * own Razorpay account — that account is not wired into Stall Wise checkout,
 * which still settles through Route on the platform account.
 */
export const RAZORPAY_SIGNUP_URL = "https://razorpay.me/partners?ref=https://rzp.io/rzp/hsWH7ZRB";
