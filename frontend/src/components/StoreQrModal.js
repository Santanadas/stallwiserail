import { useState, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X, QrCode, Download, Copy, Check, ExternalLink, Sparkles } from "lucide-react";

export default function StoreQrModal({ isOpen, onClose, storeName, storeSlug }) {
  const [copied, setCopied] = useState(false);
  const qrRef = useRef(null);
  const storeUrl = `https://stallwise.in/${storeSlug}`;
  // Generate high-resolution QR URL via Google Chart API or SVG QR
  const qrImageUrl = `https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=${encodeURIComponent(storeUrl)}&margin=15&color=0a0a0a&bgcolor=ffffff`;

  const copyUrl = async () => {
    try {
      await navigator.clipboard.writeText(storeUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const downloadQr = async () => {
    try {
      const res = await fetch(qrImageUrl);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${storeSlug || "stallwise"}-store-qr.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      window.open(qrImageUrl, "_blank");
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="relative w-full max-w-md overflow-hidden rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl z-10"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-neutral-100 pb-4">
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#FF4F00]/10 text-[#FF4F00]">
                <QrCode className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-bold text-[#0A0A0A] text-base">Storefront QR Code</h3>
                <p className="text-xs text-neutral-500">Scan to visit your live store</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* QR Container */}
          <div className="my-6 flex flex-col items-center justify-center">
            <div
              ref={qrRef}
              className="group relative flex flex-col items-center rounded-2xl border-2 border-neutral-900 bg-white p-6 shadow-[6px_6px_0px_0px_rgba(10,10,10,1)] transition-transform hover:scale-[1.02]"
            >
              {/* Store Pill Top */}
              <div className="mb-3 flex items-center gap-1.5 rounded-full bg-neutral-100 px-3 py-1 text-xs font-bold text-neutral-800">
                <Sparkles className="h-3.5 w-3.5 text-[#FF4F00]" />
                <span>{storeName || "My Store"}</span>
              </div>

              {/* QR Image */}
              <div className="relative h-48 w-48 overflow-hidden rounded-xl bg-white p-2 border border-neutral-100 shadow-inner">
                <img
                  src={qrImageUrl}
                  alt={`QR Code for ${storeName}`}
                  className="h-full w-full object-contain"
                />
              </div>

              {/* URL Pill Bottom */}
              <p className="mt-3 font-mono text-[11px] font-bold text-neutral-600">
                stallwise.in/{storeSlug}
              </p>
            </div>

            <p className="mt-3 text-center text-xs text-neutral-500 max-w-xs">
              Print this code on thank-you cards, product tags, shipping boxes, or share in your Instagram bio.
            </p>
          </div>

          {/* Actions */}
          <div className="grid grid-cols-2 gap-3 pt-2">
            <button
              onClick={downloadQr}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-neutral-900 bg-neutral-900 px-4 py-2.5 text-xs font-bold text-white shadow-sm transition-all hover:bg-[#FF4F00] hover:border-[#FF4F00]"
            >
              <Download className="h-4 w-4" />
              Download PNG
            </button>

            <button
              onClick={copyUrl}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-xs font-bold text-neutral-800 shadow-sm transition-all hover:bg-neutral-100 hover:border-neutral-300"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 text-[#10B981]" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  Copy Link
                </>
              )}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
