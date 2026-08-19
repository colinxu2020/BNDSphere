import { useEffect, useState } from "react";

/**
 * Whether the user has asked for reduced motion, kept in sync if they change it.
 *
 * Reading `matchMedia(...).matches` once inside an effect is the common shortcut,
 * but it never updates: a user who turns the setting on while the page is open
 * keeps the animation. This subscribes, so the answer stays true.
 *
 * Framer Motion's own animations are handled globally by
 * `<MotionConfig reducedMotion="user">` in App.tsx. This hook is for motion we
 * drive ourselves — currently the 展板 carousel's auto-advance.
 */
export function usePrefersReducedMotion() {
  const [prefersReduced, setPrefersReduced] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setPrefersReduced(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  return prefersReduced;
}
