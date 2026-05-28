// ─── Icons ────────────────────────────────────────────────────────────────────

import React from 'react';

export const ICON_PATHS = {
  bot: <><path d="M12 8V4" /><path d="M9 4h6" /><rect x="5" y="8" width="14" height="11" rx="4" /><path d="M9 13h.01" /><path d="M15 13h.01" /><path d="M10 17h4" /></>,
  plug: <><path d="M8 2v5" /><path d="M16 2v5" /><path d="M7 7h10v4a5 5 0 0 1-10 0Z" /><path d="M12 16v6" /></>,
  key: <><circle cx="7.5" cy="14.5" r="3.5" /><path d="M10 12 21 1" /><path d="M16 6h4v4" /><path d="M14 8h3" /></>,
  shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path d="m9 12 2 2 4-5" /></>,
  refresh: <><path d="M21 12a9 9 0 0 1-15.2 6.5" /><path d="M3 12A9 9 0 0 1 18.2 5.5" /><path d="M18 2v4h4" /><path d="M6 22v-4H2" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></>,
  queue: <><path d="M4 6h16" /><path d="M4 12h16" /><path d="M4 18h10" /></>,
  x: <><path d="M18 6 6 18" /><path d="m6 6 12 12" /></>,
  repeat: <><path d="m17 2 4 4-4 4" /><path d="M3 11V9a3 3 0 0 1 3-3h15" /><path d="m7 22-4-4 4-4" /><path d="M21 13v2a3 3 0 0 1-3 3H3" /></>,
  reset: <><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 3v6h6" /></>,
  trash: <><path d="M3 6h18" /><path d="M8 6V4h8v2" /><path d="M19 6l-1 15H6L5 6" /><path d="M10 11v6" /><path d="M14 11v6" /></>,
  settings: <><path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.7 1.7 0 0 0 9 4.7a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8 1.7 1.7 0 0 0 1.5 1h.2a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.4 1Z" /></>,
  server: <><rect x="3" y="4" width="18" height="6" rx="2" /><rect x="3" y="14" width="18" height="6" rx="2" /><path d="M7 7h.01" /><path d="M7 17h.01" /></>,
  cards: <><rect x="7" y="3" width="10" height="14" rx="2" /><path d="M5 7 3.7 18.1a2 2 0 0 0 1.8 2.2l8.9 1" /><path d="M10 7h4" /><path d="M10 11h4" /></>,
  packs: <><path d="m21 8-9-5-9 5 9 5 9-5Z" /><path d="M3 8v8l9 5 9-5V8" /><path d="M12 13v8" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  send: <><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></>,
  skip: <><path d="m5 4 8 8-8 8Z" /><path d="M19 5v14" /></>,
  sync: <><path d="M17 2v5h5" /><path d="M7 22v-5H2" /><path d="M20 11a8 8 0 0 0-13.5-5.8L2 9" /><path d="M4 13a8 8 0 0 0 13.5 5.8L22 15" /></>,
  database: <><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" /><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3" /></>,
  result: <path d="M20 6 9 17l-5-5" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 8h.01" /></>,
  language: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18" /><path d="M12 3a13.5 13.5 0 0 1 0 18" /><path d="M12 3a13.5 13.5 0 0 0 0 18" /></>,
  chevron: <path d="m9 18 6-6-6-6" />,
  wrench: <><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" /></>,
  ai: <><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 0 2h-1v1a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-1H1a1 1 0 0 1 0-2h1a7 7 0 0 1 7-7h1V5.73A2 2 0 0 1 10 4a2 2 0 0 1 2-2M7.5 13a4.5 4.5 0 0 0 0 9h9a4.5 4.5 0 0 0 0-9h-9M9 16.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3M15 16.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3" /></>,
};

export function Icon({ name, className = '' }) {
  return (
    <svg className={`icon ${className}`.trim()} aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {ICON_PATHS[name]}
    </svg>
  );
}
