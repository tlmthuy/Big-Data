import React, { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { t } from "./i18n.js";

export const VIEWS = () => [
  { id: "recommendation", label: t("recommendations") },
  { id: "dataset", label: t("dataset") },
  { id: "experiments", label: t("experiments_e1_e5") },
];

/** Plain link navigation styled as a segmented control. The current view carries aria-current="page". */
export function MainNav({ tab }) {
  return <nav className="segmented tabs" aria-label={t("views_2")}>
    {VIEWS().map(({ id, label }) => (
      <a key={id} href={`#${id}`} aria-current={tab === id ? "page" : undefined}>{label}</a>
    ))}
  </nav>;
}

export function LanguageSwitch({ language, onChoose }) {
  return <div className="segmented segmented-small language-switch" role="group" aria-label={t("language")}>
    {["en", "vi"].map((code) => <button type="button" key={code}
      aria-pressed={language === code} onClick={() => onChoose(code)}>{code.toUpperCase()}</button>)}
  </div>;
}

export function PresenterToggle({ on, onToggle }) {
  return <button type="button" className="presenter-toggle" aria-pressed={on} onClick={() => onToggle(!on)}>
    <span className="switch" aria-hidden="true" />{t("presenter_mode")}
  </button>;
}

/**
 * A small button that opens a glass popover. Keyboard and touch accessible:
 * Enter/Space or tap opens, Esc or a click outside closes and returns focus to the button.
 */
export function Popover({ label, buttonText, className = "", children, align = "start" }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef(null);
  const button = useRef(null);
  const panel = useRef(null);
  const [shift, setShift] = useState(0);
  // Keep the open popover inside the viewport (e.g. 375 px phones): shift it sideways if needed.
  useLayoutEffect(() => {
    if (!open || !panel.current) { setShift(0); return; }
    panel.current.style.transform = "";
    const rect = panel.current.getBoundingClientRect();
    const margin = 8, right = document.documentElement.clientWidth - margin;
    setShift(rect.right > right ? right - rect.right : rect.left < margin ? margin - rect.left : 0);
  }, [open]);
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        setOpen(false);
        button.current?.focus();
      }
    };
    const onPointer = (event) => { if (!root.current?.contains(event.target)) setOpen(false); };
    document.addEventListener("keydown", onKey, true);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey, true);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);
  return <span className={`popover-root ${className}`} ref={root}>
    <button type="button" ref={button} className="popover-button" aria-expanded={open} aria-controls={id}
      aria-label={label} onClick={() => setOpen((value) => !value)}>{buttonText}</button>
    <span id={id} ref={panel} role="dialog" aria-label={label} className={`popover glass popover-${align}`} hidden={!open}
      style={shift ? { transform: `translateX(${shift}px)` } : undefined}>{children}</span>
  </span>;
}

/** The one "About the demo" disclosure, in the header. */
export function AboutDemo() {
  return <Popover label={t("demo_intro")} buttonText={t("about_short")} className="about" align="end">
    <strong>{t("demo_intro")}</strong>
    <span className="popover-text">{t("about_demo_body")}</span>
    <span className="popover-text">{t("about_demo_tabs")}</span>
  </Popover>;
}
