import { useEffect, useRef, useState } from "react";

/*
 * Shared behaviour for the sticky sub-bars (Experiments sub-nav, Recommendations control bar,
 * Dataset section nav). The bar itself is `position: sticky; top: var(--sticky-top)` in CSS.
 * - "stuck" comes from an IntersectionObserver on a 1 px sentinel placed just above the bar
 *   (no per-frame scroll listener). The observer is rebuilt only on resize, when --sticky-top can change.
 * - The bar's height is published as --subbar-height on <html> (ResizeObserver), so
 *   `scroll-padding-top` keeps anchor jumps and keyboard focus below header + sub-bar.
 */
export function useStickyBar() {
  const bar = useRef(null);
  const sentinel = useRef(null);
  const [stuck, setStuck] = useState(false);

  useEffect(() => {
    const node = bar.current;
    const root = document.documentElement;
    if (!node) return undefined;
    const publish = () => root.style.setProperty("--subbar-height", `${Math.round(node.getBoundingClientRect().height)}px`);
    publish();
    const resize = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(publish);
    resize?.observe(node);
    return () => {
      resize?.disconnect();
      root.style.removeProperty("--subbar-height");
    };
  }, []);

  useEffect(() => {
    const node = bar.current;
    const marker = sentinel.current;
    if (!node || !marker || typeof IntersectionObserver === "undefined") return undefined;
    let observer = null;
    const build = () => {
      observer?.disconnect();
      const top = parseFloat(getComputedStyle(node).top) || 0;
      observer = new IntersectionObserver(([entry]) => {
        setStuck(!entry.isIntersecting && entry.boundingClientRect.top < top + 1);
      }, { rootMargin: `${-Math.ceil(top)}px 0px 0px 0px`, threshold: 0 });
      observer.observe(marker);
    };
    build();
    window.addEventListener("resize", build);
    return () => {
      window.removeEventListener("resize", build);
      observer?.disconnect();
    };
  }, []);

  return { bar, sentinel, stuck };
}

/** True when an element's top is above the sticky line, i.e. its sticky bar is currently stuck. */
export function isPastStickyLine(element) {
  if (!element) return false;
  const top = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--sticky-top")) || 0;
  return element.getBoundingClientRect().top < top;
}
