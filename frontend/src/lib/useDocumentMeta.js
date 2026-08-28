import { useEffect } from "react";

const SITE = "https://marketo-core-logic.preview.emergentagent.com";

function upsertMeta(selector, attrs) {
  let el = document.head.querySelector(selector);
  if (!el) {
    el = document.createElement(selector.startsWith("link") ? "link" : "meta");
    document.head.appendChild(el);
  }
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  return el;
}

export function useDocumentMeta({ title, description, path = "/", schemaType }) {
  useEffect(() => {
    document.title = title;
    upsertMeta('meta[name="description"]', { name: "description", content: description });
    upsertMeta('meta[property="og:title"]', { property: "og:title", content: title });
    upsertMeta('meta[property="og:description"]', { property: "og:description", content: description });
    upsertMeta('meta[property="og:url"]', { property: "og:url", content: SITE + path });
    upsertMeta('meta[name="twitter:title"]', { name: "twitter:title", content: title });
    upsertMeta('meta[name="twitter:description"]', { name: "twitter:description", content: description });
    upsertMeta('link[rel="canonical"]', { rel: "canonical", href: SITE + path });

    if (!schemaType) return;
    let script = document.head.querySelector('script[data-page-schema="true"]');
    if (!script) {
      script = document.createElement("script");
      script.type = "application/ld+json";
      script.setAttribute("data-page-schema", "true");
      document.head.appendChild(script);
    }
    script.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@type": schemaType,
      name: title,
      description,
      url: SITE + path,
      isPartOf: { "@type": "WebSite", name: "Marketo", url: SITE + "/" },
      publisher: { "@type": "Organization", name: "Marketo", url: SITE + "/" },
    });
    return () => script?.remove();
  }, [title, description, path, schemaType]);
}
