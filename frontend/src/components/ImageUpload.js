import { useRef, useState } from "react";
import { Upload, Loader2, X } from "lucide-react";
import api, { API, formatApiError } from "@/lib/api";

export const fileUrl = (path) => (path ? `${API}/files/${path}` : null);

export default function ImageUpload({
  value,
  onChange,
  kind = "product",
  shape = "square",
  label = "Upload image",
  testId = "image-upload",
}) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const handle = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setErr("");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const { data } = await api.post(`/uploads/image?kind=${kind}`, fd);
      onChange(data.path);
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const round = shape === "round";

  return (
    <div className="flex items-center gap-4" data-testid={testId}>
      <div
        className={`relative flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden border-2 border-[#0A0A0A] bg-[#FAFAFA] ${
          round ? "rounded-full" : ""
        }`}
      >
        {value ? (
          <img src={fileUrl(value)} alt="Preview" className="h-full w-full object-cover" data-testid={`${testId}-preview`} />
        ) : (
          <Upload className="h-6 w-6 text-neutral-400" />
        )}
        {busy && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70">
            <Loader2 className="h-5 w-5 animate-spin text-[#FF4F00]" />
          </div>
        )}
      </div>
      <div>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp"
          onChange={handle}
          className="hidden"
          data-testid={`${testId}-input`}
        />
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
            data-testid={`${testId}-btn`}
            className="inline-flex items-center gap-2 border-2 border-[#0A0A0A] bg-white px-3 py-2 text-xs font-bold uppercase tracking-wider transition-transform hover:-translate-y-0.5 hover:shadow-[3px_3px_0px_0px_rgba(10,10,10,1)] disabled:opacity-60"
          >
            <Upload className="h-3.5 w-3.5" /> {value ? "Replace" : label}
          </button>
          {value && (
            <button
              type="button"
              onClick={() => onChange(null)}
              data-testid={`${testId}-clear`}
              aria-label="Remove image"
              className="inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-[#8A2200] transition-colors hover:text-[#FF4F00]"
            >
              <X className="h-3.5 w-3.5" /> Remove
            </button>
          )}
        </div>
        <p className="mt-1.5 text-xs text-neutral-500">PNG, JPG, GIF or WEBP · up to 5MB</p>
        {err && <p className="mt-1 text-xs font-medium text-[#8A2200]" data-testid={`${testId}-error`}>{err}</p>}
      </div>
    </div>
  );
}
