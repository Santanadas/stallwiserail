import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Store, Package, ArrowRight } from "lucide-react";
import api from "@/lib/api";
import { fileUrl } from "@/components/ImageUpload";
import SiteFooter from "@/components/SiteFooter";
import { useDocumentMeta } from "@/lib/useDocumentMeta";

function initials(name) {
  return (name || "S").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

export default function Shops() {
  const [data, setData] = useState({ shops: [], total: 0, page: 1, pages: 1 });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data: d } = await api.get(`/shops?page=${page}&limit=24`);
      setData(d);
    } catch {
      setData({ shops: [], total: 0, page: 1, pages: 1 });
    } finally {
      setLoading(false);
    }
  }, [page]);
  useEffect(() => { load(); }, [load]);

  useDocumentMeta({
    title: "Browse Shops on Stall Wise | Independent Indian Sellers",
    description:
      "Discover independent shops on Stall Wise — handmade goods, small-batch food, crafts and more. Pay the seller directly by UPI, card or cash on delivery.",
    path: "/shops",
  });

  return (
    <div className="mk min-h-screen bg-[#FAFAFA] text-[#0A0A0A]">
      <header className="border-b-2 border-[#0A0A0A] bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3.5 sm:px-6 md:px-8">
          <Link to="/" className="mk-head text-lg font-black tracking-tighter sm:text-xl">
            STALL WISE<span className="text-[#FF4F00]">.</span>
          </Link>
          <Link
            to="/register"
            className="inline-flex items-center gap-1.5 border-2 border-[#0A0A0A] bg-[#0A0A0A] px-4 py-2 text-xs font-bold text-white transition-transform hover:-translate-y-0.5 hover:bg-[#FF4F00]"
          >
            Open your shop <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6 md:px-8 md:py-14">
        <h1 className="mk-head text-4xl font-black leading-tight tracking-tighter sm:text-5xl">
          Browse shops
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#525252] sm:text-base">
          Every shop here is run by an independent seller. When you buy, your money goes straight to
          them — Stall Wise never holds it. Pay by UPI, card, netbanking or cash on delivery where
          the seller offers it.
        </p>

        {loading ? (
          <p className="mt-10 text-sm text-[#525252]">Loading shops…</p>
        ) : data.shops.length === 0 ? (
          <div className="mt-10 border-2 border-[#0A0A0A] bg-white p-10 text-center">
            <Store className="mx-auto h-9 w-9 text-neutral-300" />
            <p className="mt-3 text-sm text-[#525252]">No shops are listed yet.</p>
            <Link
              to="/register"
              className="mt-5 inline-flex items-center gap-2 border-2 border-[#0A0A0A] bg-[#0A0A0A] px-5 py-2.5 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 hover:bg-[#FF4F00]"
            >
              Be the first <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        ) : (
          <>
            <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {data.shops.map((s) => (
                <Link
                  key={s.slug}
                  to={`/${s.slug}`}
                  data-testid={`shop-card-${s.slug}`}
                  className="group flex flex-col border-2 border-[#0A0A0A] bg-white p-5 transition-transform hover:-translate-y-1 hover:shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-[#0A0A0A] bg-[#FF4F00]">
                      {s.avatar ? (
                        <img src={fileUrl(s.avatar)} alt="" className="h-full w-full object-cover" loading="lazy" />
                      ) : (
                        <span className="mk-head text-sm font-black text-white">{initials(s.name)}</span>
                      )}
                    </div>
                    <div className="min-w-0">
                      <h2 className="mk-head truncate text-lg font-black tracking-tight">{s.name}</h2>
                      <p className="truncate font-mono text-xs text-[#525252]">stallwise.in/{s.slug}</p>
                    </div>
                  </div>
                  {s.bio && <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-[#525252]">{s.bio}</p>}
                  <span className="mt-4 inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#525252]">
                    <Package className="h-3.5 w-3.5" />
                    {s.productCount} product{s.productCount === 1 ? "" : "s"}
                  </span>
                </Link>
              ))}
            </div>

            {data.pages > 1 && (
              <div className="mt-10 flex items-center justify-between border-t-2 border-[#0A0A0A] pt-5">
                <span className="text-xs font-bold uppercase tracking-widest text-[#525252]">
                  Page {data.page} of {data.pages}
                </span>
                <div className="flex gap-2">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="border-2 border-[#0A0A0A] bg-white px-4 py-2 text-xs font-bold disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <button
                    disabled={page >= data.pages}
                    onClick={() => setPage((p) => p + 1)}
                    className="border-2 border-[#0A0A0A] bg-white px-4 py-2 text-xs font-bold disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      <SiteFooter />
    </div>
  );
}
