import { useEffect } from "react";

const SITE = "https://stallwise.in";

function upsertMeta(selector, attrs) {
  let el = document.head.querySelector(selector);
  if (!el) {
    el = document.createElement(selector.startsWith("link") ? "link" : "meta");
    document.head.appendChild(el);
  }
  Object.entries(attrs).forEach(([k, v]) => {
    if (v != null) el.setAttribute(k, v);
  });
  return el;
}

export function useDocumentMeta({
  title,
  description,
  path = "/",
  schemaType,
  schemaData,
  image,
  keywords,
}) {
  useEffect(() => {
    if (title) document.title = title;
    const url = `${SITE}${path.startsWith("/") ? path : `/${path}`}`;
    const imgUrl = image || "https://stallwise.in/favicon.ico";

    if (description) {
      upsertMeta('meta[name="description"]', { name: "description", content: description });
      upsertMeta('meta[property="og:description"]', { property: "og:description", content: description });
      upsertMeta('meta[name="twitter:description"]', { name: "twitter:description", content: description });
    }

    if (title) {
      upsertMeta('meta[property="og:title"]', { property: "og:title", content: title });
      upsertMeta('meta[name="twitter:title"]', { name: "twitter:title", content: title });
    }

    upsertMeta('meta[property="og:url"]', { property: "og:url", content: url });
    upsertMeta('meta[property="og:site_name"]', { property: "og:site_name", content: "Stall Wise" });
    upsertMeta('meta[property="og:type"]', { property: "og:type", content: "website" });
    upsertMeta('meta[property="og:image"]', { property: "og:image", content: imgUrl });
    upsertMeta('meta[name="twitter:card"]', { name: "twitter:card", content: "summary_large_image" });
    upsertMeta('meta[name="twitter:image"]', { name: "twitter:image", content: imgUrl });
    upsertMeta('link[rel="canonical"]', { rel: "canonical", href: url });

    if (keywords) {
      upsertMeta('meta[name="keywords"]', { name: "keywords", content: keywords });
    }

    let script = document.head.querySelector('script[data-page-schema="true"]');

    if (schemaData) {
      if (!script) {
        script = document.createElement("script");
        script.type = "application/ld+json";
        script.setAttribute("data-page-schema", "true");
        document.head.appendChild(script);
      }
      script.textContent = JSON.stringify(schemaData);
    } else if (schemaType) {
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
        url,
        isPartOf: { "@type": "WebSite", name: "Stall Wise", url: `${SITE}/` },
        publisher: { "@type": "Organization", name: "Stall Wise", url: `${SITE}/` },
      });
    } else if (script) {
      script.remove();
    }

    return () => {
      // Cleanup custom schema on unmount if needed
    };
  }, [title, description, path, schemaType, schemaData, image, keywords]);
}
