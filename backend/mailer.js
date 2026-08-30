const nodemailer = require("nodemailer");
const path = require("path");
// Suppress any dotenv console banners
process.env.DOTENV_CONFIG_QUIET = "true";
require("dotenv").config({ path: path.join(__dirname, ".env"), quiet: true });

async function getTransporter() {
  const host = process.env.SMTP_HOST;
  const port = parseInt(process.env.SMTP_PORT || "587", 10);
  const user = process.env.SMTP_USER || process.env.EMAIL_USER || process.env.SMTP_AUTH_USER;
  const pass = process.env.SMTP_PASS || process.env.EMAIL_PASS || process.env.SMTP_AUTH_PASS || process.env.EMAIL_PASSWORD;
  const service = process.env.SMTP_SERVICE;
  const secure = process.env.SMTP_SECURE === "true" || port === 465;

  // Auto-detect Gmail accounts for highest deliverability and zero connection timeouts
  if ((service === "gmail" || (host && host.includes("gmail")) || (user && user.includes("@gmail.com"))) && user && pass) {
    return nodemailer.createTransport({
      service: "gmail",
      auth: { user, pass },
    });
  }

  if (host && user && pass) {
    return nodemailer.createTransport({
      host,
      port,
      secure,
      auth: { user, pass },
      connectionTimeout: 10000,
      greetingTimeout: 10000,
      socketTimeout: 10000,
      tls: {
        rejectUnauthorized: process.env.SMTP_REJECT_UNAUTHORIZED !== "false",
      },
    });
  }

  if (host) {
    return nodemailer.createTransport({
      host,
      port,
      secure,
      connectionTimeout: 8000,
      greetingTimeout: 8000,
      socketTimeout: 8000,
    });
  }

  // Development Fallback: Use Ethereal test account or jsonTransport
  try {
    const testAccount = await nodemailer.createTestAccount();
    return nodemailer.createTransport({
      host: "smtp.ethereal.email",
      port: 587,
      secure: false,
      auth: {
        user: testAccount.user,
        pass: testAccount.pass,
      },
    });
  } catch (err) {
    return nodemailer.createTransport({
      jsonTransport: true,
    });
  }
}

async function sendMail(payload) {
  const { to, subject, html, text, fromName, fromEmail, replyTo } = payload;

  const defaultFromName = process.env.EMAIL_FROM_NAME || "Stall Wise";
  const defaultFromEmail = process.env.EMAIL_FROM_ADDRESS || process.env.SMTP_USER || "noreply@stallwise.in";
  
  const from = process.env.EMAIL_FROM || `"${fromName || defaultFromName}" <${fromEmail || defaultFromEmail}>`;
  const reply = replyTo || process.env.EMAIL_REPLY_TO;

  const transporter = await getTransporter();

  const mailOptions = {
    from,
    to,
    subject,
    html,
    text: text || html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim(),
  };

  if (reply) {
    mailOptions.replyTo = reply;
  }

  const info = await transporter.sendMail(mailOptions);
  const previewUrl = nodemailer.getTestMessageUrl(info);

  return {
    ok: true,
    messageId: info.messageId,
    previewUrl: previewUrl || null,
  };
}

async function main() {
  let input = "";
  process.stdin.setEncoding("utf8");

  for await (const chunk of process.stdin) {
    input += chunk;
  }

  if (!input.trim()) {
    console.error(JSON.stringify({ ok: false, error: "Empty input payload" }));
    process.exit(1);
  }

  try {
    const payload = JSON.parse(input);
    const result = await sendMail(payload);
    console.log(JSON.stringify(result));
  } catch (err) {
    console.error(JSON.stringify({ ok: false, error: err.message || String(err) }));
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { sendMail, getTransporter };
