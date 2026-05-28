// ─── Icons ────────────────────────────────────────────────────────────────────
// Specific imports for tree-shaking — only used icons are bundled

import React from 'react';
import {
  Bot, Plug, KeyRound, ShieldCheck, RefreshCw, Search, List,
  X, Repeat2, RotateCcw, Trash2, Settings, Server, LayoutGrid,
  Package, Clock, Send, SkipForward, RefreshCcw, Database,
  Check, Info, Globe, ChevronRight, Wrench, BrainCircuit,
  History, Users, Monitor, CalendarDays,
} from 'lucide-react';

const ICON_MAP = {
  bot:          Bot,
  plug:         Plug,
  key:          KeyRound,
  shield:       ShieldCheck,
  refresh:      RefreshCw,
  search:       Search,
  queue:        List,
  x:            X,
  repeat:       Repeat2,
  reset:        RotateCcw,
  trash:        Trash2,
  settings:     Settings,
  server:       Server,
  cards:        LayoutGrid,
  packs:        Package,
  clock:        Clock,
  send:         Send,
  skip:         SkipForward,
  sync:         RefreshCcw,
  database:     Database,
  result:       Check,
  info:         Info,
  language:     Globe,
  chevron:      ChevronRight,
  wrench:       Wrench,
  ai:           BrainCircuit,
  history:      History,
  destinations: Users,
  app:          Monitor,
  calendar:     CalendarDays,
};

export function Icon({ name, className = '', size = 20 }) {
  const LucideIcon = ICON_MAP[name];
  if (!LucideIcon) return null;
  return <LucideIcon size={size} className={`icon ${className}`.trim()} aria-hidden="true" strokeWidth={1.8} />;
}
