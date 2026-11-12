export type View = "student" | "parent";
export type NavPage = "find" | "cost" | "apply" | "help";
export type Page = NavPage | "login";

const ORDER: Record<View, NavPage[]> = {
  student: ["find", "apply", "cost", "help"],
  parent: ["find", "cost", "help", "apply"],
};
export const pagesFor = (v: View): NavPage[] => ORDER[v];

export const pageFromHash = (): Page => {
  const h = location.hash.replace("#", "");
  return h === "login" || (ORDER.student as string[]).includes(h) ? (h as Page) : "find";
};

export const loadView = (): View => {
  try { return localStorage.getItem("educlear.view") === "parent" ? "parent" : "student"; } catch { return "student"; }
};
export const saveView = (v: View) => { try { localStorage.setItem("educlear.view", v); } catch { /* storage blocked: view lasts for this visit only */ } };
