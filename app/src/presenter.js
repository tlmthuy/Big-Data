import { createContext, useContext } from "react";

const KEY = "tv4-presenter";

/** ?present=1 turns presenter mode on (?present=0 off); otherwise the last choice is remembered. */
export function readPresenter(search = typeof window === "undefined" ? "" : window.location.search, storage = safeStorage()) {
  const param = new URLSearchParams(search).get("present");
  if (param === "1" || param === "true") return true;
  if (param === "0" || param === "false") return false;
  try {
    return storage?.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export function savePresenter(on, storage = safeStorage()) {
  try {
    storage?.setItem(KEY, on ? "1" : "0");
  } catch {
    /* Storage is optional. */
  }
}

function safeStorage() {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

export const PresenterContext = createContext(false);
export const usePresenter = () => useContext(PresenterContext);
