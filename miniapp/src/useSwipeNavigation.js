import { useEffect, useRef } from 'react';

const INTERACTIVE = 'input,textarea,select,button,a,[role="button"],[role="slider"],[role="checkbox"],[role="radio"],details,summary,label,[contenteditable]';
const MIN_HORIZONTAL_PX = 50;

// Returns true if the touch started on or inside an interactive element.
function startsOnInteractive(target) {
  return Boolean(target?.closest?.(INTERACTIVE));
}

/**
 * Attaches horizontal swipe navigation to `elementRef`.
 *
 * @param {React.RefObject} elementRef  - The scrollable container to listen on.
 * @param {string}          activeTab   - Current active tab name.
 * @param {Function}        setActiveTab
 * @param {string[]}        swipeTabs   - Ordered list of swipeable tab names.
 */
export function useSwipeNavigation(elementRef, activeTab, setActiveTab, swipeTabs) {
  // Keep stable refs so the touch handlers don't capture stale state.
  const activeTabRef = useRef(activeTab);
  activeTabRef.current = activeTab;
  const setActiveTabRef = useRef(setActiveTab);
  setActiveTabRef.current = setActiveTab;
  const swipeTabsRef = useRef(swipeTabs);
  swipeTabsRef.current = swipeTabs;

  useEffect(() => {
    const el = elementRef.current;
    if (!el) return;

    let startX = 0;
    let startY = 0;
    let cancelled = false;

    const onTouchStart = (e) => {
      if (startsOnInteractive(e.target)) { cancelled = true; return; }
      const t = e.touches[0];
      startX = t.clientX;
      startY = t.clientY;
      cancelled = false;
    };

    const onTouchMove = (e) => {
      if (cancelled) return;
      const t = e.touches[0];
      const dx = Math.abs(t.clientX - startX);
      const dy = Math.abs(t.clientY - startY);
      // Cancel if vertical scroll is dominant.
      if (dy > dx) cancelled = true;
    };

    const onTouchEnd = (e) => {
      if (cancelled) return;
      const t = e.changedTouches[0];
      const dx = t.clientX - startX;
      const adx = Math.abs(dx);
      const ady = Math.abs(t.clientY - startY);

      if (adx < MIN_HORIZONTAL_PX || adx <= ady) return;

      const tabs = swipeTabsRef.current;
      const current = activeTabRef.current;
      const idx = tabs.indexOf(current);
      if (idx === -1) return; // current tab not in swipe list — do nothing

      const prefersReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

      if (dx < 0 && idx < tabs.length - 1) {
        // Swipe left → next tab
        if (!prefersReduced) triggerHaptic();
        setActiveTabRef.current(tabs[idx + 1]);
      } else if (dx > 0 && idx > 0) {
        // Swipe right → previous tab
        if (!prefersReduced) triggerHaptic();
        setActiveTabRef.current(tabs[idx - 1]);
      }
    };

    el.addEventListener('touchstart', onTouchStart, { passive: true });
    el.addEventListener('touchmove', onTouchMove, { passive: true });
    el.addEventListener('touchend', onTouchEnd, { passive: true });

    return () => {
      el.removeEventListener('touchstart', onTouchStart);
      el.removeEventListener('touchmove', onTouchMove);
      el.removeEventListener('touchend', onTouchEnd);
    };
  }, [elementRef]); // elementRef is stable; tab state is read via refs
}

function triggerHaptic() {
  try {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light');
  } catch {}
}
