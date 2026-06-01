// ─── App ──────────────────────────────────────────────────────────────────────

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { tg, initData, tgUser, haptic, tgShowPopup } from './telegram.js';
import { getBotPhotoUrl, getApiBase, apiFetch } from './api.js';
import { WEEKDAYS, ALL_CARD_TYPES, deriveCycles, TIMEZONES, I18N, resolveError, readLangStorage, writeLangStorage, getInitialLanguage } from './i18n.js';
import { AI_TONES, AI_PROVIDERS, AI_MODELS, _providerOfModel, DEFAULT_SETTINGS, normalizeSettings, settingsPatchPayload, isValidTimeValue, validateTimes, settingsEqual, DELAY_OPTIONS, formatDelay } from './settings.js';
import { Icon } from './icons.jsx';
import { useSwipeNavigation } from './useSwipeNavigation.js';
import {
  Spinner, LoadingRow, Badge, Notice, Section, Row, MenuRow, DangerRow, ResultRow,
  ToggleRow, InputRow, StackedInputRow, ChatIdInputRow, SelectRow, StackedSelectRow,
  DayScheduleRow, CommandRow, CardResult,
  LoadingGate, NoTelegramGate, AuthErrorGate, UnauthorizedGate, ApiNotConfiguredGate,
} from './components.jsx';

export default function App() {
  const [language, setLanguage] = useState(getInitialLanguage);
  const copy = I18N[language];

  const [authState, setAuthState] = useState('loading');
  const [me, setMe] = useState(null);
  const [botInfo, setBotInfo] = useState(null);
  const [sysStatus, setSysStatus] = useState(null);
  const [overview, setOverview] = useState(null);
  const [commands, setCommands] = useState([]);

  // Settings state: current (edited) and saved (last confirmed from server)
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [savedSettings, setSavedSettings] = useState(DEFAULT_SETTINGS);
  const [pendingTime, setPendingTime] = useState(DEFAULT_SETTINGS.daily_post_times[0]);

  const [result, setResult] = useState(null);
  const [settingsResult, setSettingsResult] = useState(null);
  const [cardCode, setCardCode] = useState('');
  const [cardQuery, setCardQuery] = useState('');
  const [cardResults, setCardResults] = useState([]);
  const [targetChatId, setTargetChatId] = useState('');
  const [activeTab, setActiveTab] = useState('home');
  const [activeDayCode, setActiveDayCode] = useState(null);
  const [packs, setPacks] = useState([]);
  const [packsLoading, setPacksLoading] = useState(false);
  const [packsError, setPacksError] = useState(false);

  const [aiProviders, setAiProviders] = useState([]);
  const [botRuntime, setBotRuntime] = useState(null);

  // Admins state
  const [admins, setAdmins] = useState([]);
  const [adminsLoading, setAdminsLoading] = useState(false);
  const [adminsError, setAdminsError] = useState(null);
  const [adminUserId, setAdminUserId] = useState('');
  const [adminName, setAdminName] = useState('');
  const [adminRole, setAdminRole] = useState('admin');
  const [addingAdmin, setAddingAdmin] = useState(false);
  const [addAdminResult, setAddAdminResult] = useState(null);

  // Destinations manage state
  const [destList, setDestList] = useState([]);
  const [destLoading, setDestLoading] = useState(false);
  const [destError, setDestError] = useState(null);
  const [pendingDests, setPendingDests] = useState([]);
  const [pendingThreadId, setPendingThreadId] = useState({});
  const [acceptingPending, setAcceptingPending] = useState(null);
  const [destChatId, setDestChatId] = useState('');
  const [destTitle, setDestTitle] = useState('');
  const [destThread, setDestThread] = useState('');
  const [addingDest, setAddingDest] = useState(false);
  const [addDestResult, setAddDestResult] = useState(null);
  const [testingDest, setTestingDest] = useState(null);
  const [destActionResult, setDestActionResult] = useState(null); // { id, ok, text } — inline feedback per destination row
  const [resolvingDest, setResolvingDest] = useState(false);
  const destResolveTimer = useRef(null);

  const [commandsError, setCommandsError] = useState(null);
  const [historySourceFilter, setHistorySourceFilter] = useState('all');

  const [loadingCmd, setLoadingCmd] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [loadingOverview, setLoadingOverview] = useState(false);
  const [loadingCommands, setLoadingCommands] = useState(false);
  const [loadingSettings, setLoadingSettings] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [searchingCards, setSearchingCards] = useState(false);
  const [cancellingCommand, setCancellingCommand] = useState(null);

  const searchTimerRef = useRef(null);
  const [historyItems, setHistoryItems] = useState([]);
  const [historyLoadingState, setHistoryLoadingState] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [historyDate, setHistoryDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [historyHasMore, setHistoryHasMore] = useState(false);
  const [allDaysMode, setAllDaysMode] = useState(false);
  const [savedAllDaysMode, setSavedAllDaysMode] = useState(false);

  const apiConfigured = Boolean(getApiBase());
  const isAdmin = me?.admin === true;
  const actionsDisabled = !isAdmin || !apiConfigured || loadingCmd !== null;
  const settingsDirty = !settingsEqual(settings, savedSettings) || allDaysMode !== savedAllDaysMode;
  // Ref necessária: closures async (ex: MainButton handler) capturam o valor no momento de criação.
  // Ler o estado diretamente retornaria o valor antigo; a ref sempre reflete o valor atual.
  const settingsDirtyRef = useRef(false);
  settingsDirtyRef.current = settingsDirty;

  // Enable closing confirmation when settings are dirty to prevent accidental data loss
  useEffect(() => {
    const app = tg();
    if (!app) return;
    if (settingsDirty) app.enableClosingConfirmation?.();
    else app.disableClosingConfirmation?.();
  }, [settingsDirty]);
  // Ref keeps the latest saveSettings for the MainButton handler (stale closure guard)
  const saveSettingsRef = useRef(null);

  // ── Telegram setup ──────────────────────────────────────────────────────────
  useEffect(() => {
    const app = tg();
    if (!app) return;
    app.ready?.();
    if (['android', 'ios'].includes(app.platform)) app.expand?.();
    try { app.setHeaderColor?.('secondary_bg_color'); } catch {}
    try { app.setBackgroundColor?.('bg_color'); } catch {}
    try { app.setBottomBarColor?.('secondary_bg_color'); } catch {}

    const applyColors = () => {
      try { app.setHeaderColor?.('secondary_bg_color'); } catch {}
      try { app.setBackgroundColor?.('bg_color'); } catch {}
      try { app.setBottomBarColor?.('secondary_bg_color'); } catch {}
    };
    const mobileOnlyPlatforms = ['android', 'ios'];
    const onViewportChanged = ({ isStateStable }) => {
      if (isStateStable && mobileOnlyPlatforms.includes(app.platform)) app.expand?.();
    };

    app.onEvent?.('themeChanged', applyColors);
    app.onEvent?.('viewportChanged', onViewportChanged);

    // Fullscreen: request on mobile only (Bot API 8.0+), exit on desktop.
    if (app.isVersionAtLeast?.('8.0')) {
      try {
        if (mobileOnlyPlatforms.includes(app.platform)) app.requestFullscreen?.();
        else app.exitFullscreen?.();
      } catch {}
    }
    const onFullscreenFailed = ({ error } = {}) => {
      if (error === 'UNSUPPORTED') { try { app.exitFullscreen?.(); } catch {} }
    };
    const onFullscreenChanged = () => {};
    app.onEvent?.('fullscreenFailed', onFullscreenFailed);
    app.onEvent?.('fullscreenChanged', onFullscreenChanged);

    // SettingsButton in Telegram header → jump to settings tab
    try {
      const sb = app.SettingsButton;
      if (sb) {
        sb.show?.();
        sb.onClick?.(() => setActiveTab('settings'));
      }
    } catch {}

    return () => {
      app.offEvent?.('themeChanged', applyColors);
      app.offEvent?.('viewportChanged', onViewportChanged);
      app.offEvent?.('fullscreenFailed', onFullscreenFailed);
      app.offEvent?.('fullscreenChanged', onFullscreenChanged);
    };
  }, []);

  // ── Refresh when user returns to app (Telegram activated/deactivated events) ─
  useEffect(() => {
    const app = tg();
    if (!app) return;
    const onActivated = () => { fetchOverview(); fetchCommands(); };
    app.onEvent?.('activated', onActivated);
    return () => app.offEvent?.('activated', onActivated);
  }, []);

  // ── MainButton: shows "Save" when settings are dirty ───────────────────────
  useEffect(() => {
    const app = tg();
    const btn = app?.MainButton;
    if (!btn) return;

    if ((activeTab === 'settings' || activeTab === 'day_detail' || activeTab === 'ai' || activeTab === 'database' || activeTab === 'schedule') && settingsDirty && !savingSettings) {
      btn.setText(copy.saveSettings);
      btn.show?.();
      // Use ref so handler always calls the latest saveSettings regardless of re-renders
      const handler = () => saveSettingsRef.current?.();
      btn.onClick?.(handler);
      return () => { btn.offClick?.(handler); btn.hide?.(); };
    } else {
      btn.hide?.();
    }
  }, [activeTab, settingsDirty, savingSettings, copy.saveSettings]);

  // ── Swipe navigation ────────────────────────────────────────────────────────
  // Ordered list of top-level tabs reachable by horizontal swipe.
  // Excluded: database, maintenance, app_settings (system/destructive/admin)
  // and all nested sub-screens (day_detail, schedule, ai, admins).
  const SWIPE_TABS = ['home', 'post', 'history', 'queue', 'settings', 'destinations', 'health'];

  // ── Move focus to the first heading on tab change (screen-reader awareness) ──
  const contentRef = useRef(null);
  const swipeRef = useSwipeNavigation(activeTab, setActiveTab, SWIPE_TABS);
  // Merge refs: keep contentRef for focus management, register node for swipe.
  const setContentRef = useCallback((node) => { contentRef.current = node; swipeRef(node); }, [swipeRef]);
  const didMountRef = useRef(false);
  useEffect(() => {
    if (!didMountRef.current) { didMountRef.current = true; return; }
    const el = contentRef.current;
    if (!el) return;
    const heading = el.querySelector('h2, .section-header-standalone');
    if (heading) {
      heading.setAttribute('tabindex', '-1');
      try { heading.focus({ preventScroll: false }); } catch {}
    }
  }, [activeTab]);

  // ── BackButton ──────────────────────────────────────────────────────────────
  const PARENT_TAB = { day_detail: 'settings', ai: 'settings', app_settings: 'home', database: 'home', schedule: 'settings', admins: 'app_settings', destinations: 'home', maintenance: 'home', queue: 'home', history: 'home', health: 'home' };
  useEffect(() => {
    const btn = tg()?.BackButton;
    if (!btn) return;
    const goBack = () => setActiveTab(PARENT_TAB[activeTab] || 'home');
    if (activeTab === 'home') {
      btn.hide?.();
    } else {
      btn.show?.();
      btn.onClick?.(goBack);
    }
    return () => btn.offClick?.(goBack);
  }, [activeTab]);

  // ── Load packs when entering day_detail tab ─────────────────────────────────
  useEffect(() => {
    if (activeTab === 'day_detail' && packs.length === 0 && !packsLoading) {
      setPacksLoading(true);
      setPacksError(false);
      apiFetch('/packs').then(({ ok, json }) => {
        if (ok && Array.isArray(json.packs)) setPacks(json.packs);
        else setPacksError(true);
      }).catch(() => setPacksError(true)).finally(() => setPacksLoading(false));
    }
  }, [activeTab]);

  // ── CloudStorage language sync ──────────────────────────────────────────────
  useEffect(() => { readLangStorage((lang) => setLanguage(lang)); }, []);

  // ── Auth gate ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!tg() || !initData()) { setAuthState('no_telegram'); return; }
    if (!apiConfigured) { setAuthState('api_not_configured'); return; }

    apiFetch('/me').then(({ ok, json }) => {
      if (ok && json?.admin === true) {
        setMe(json);
        setAuthState('ready');
        fetchStatus();
        fetchOverview();
        fetchCommands();
        fetchBotInfo();
        fetchAiProviders();
        fetchBotRuntime();
      } else {
        const msg = copy.errors.unauthorized?.[0] || 'Access denied.';
        const app = tg();
        if (app?.showAlert) app.showAlert(msg, () => app.close?.());
        else app?.close?.();
        setAuthState('unauthorized');
      }
    }).catch(() => setAuthState('auth_error'));
  }, []);

  // ── Auto-load settings when entering settings or ai tab ────────────────────
  useEffect(() => {
    if ((activeTab === 'settings' || activeTab === 'ai' || activeTab === 'database' || activeTab === 'schedule') && !settingsDirty) fetchSettings();
    if (activeTab === 'database') { fetchOverview(); fetchStatus(); }
  }, [activeTab]);

  // ── Auto-load history when entering history tab ─────────────────────────────
  useEffect(() => {
    if (activeTab === 'history') fetchHistoryItems(historyDate, 0);
    if (activeTab === 'app_settings') fetchAdmins();
    if (activeTab === 'health') fetchBotRuntime();
    // Load on entry regardless of how the tab is reached (tap or swipe).
    if (activeTab === 'destinations') { fetchDestinations(); fetchPendingDestinations(); }
  }, [activeTab]);

  // ── API calls ───────────────────────────────────────────────────────────────

  async function fetchBotInfo() {
    if (!apiConfigured) return;
    try { const { ok, json } = await apiFetch('/bot-info'); if (ok) setBotInfo(json); }
    catch {}
  }

  async function fetchStatus() {
    if (!apiConfigured) return;
    setLoadingStatus(true);
    try { const { json } = await apiFetch('/status'); setSysStatus(json); }
    catch { setSysStatus({ ok: false }); }
    finally { setLoadingStatus(false); }
  }

  async function fetchOverview() {
    if (!apiConfigured) return;
    setLoadingOverview(true);
    try {
      const { ok, status, json } = await apiFetch('/overview');
      if (ok) { setOverview(json); if (json.settings && !settingsDirtyRef.current) applySettings(json.settings); }
      else setResult({ ok: false, ...resolveError(json.error, `HTTP ${status}`, copy, json) });
    } catch { setResult({ ok: false, friendly: copy.networkError, detail: '' }); }
    finally { setLoadingOverview(false); }
  }

  async function fetchCommands() {
    if (!apiConfigured) return;
    setLoadingCommands(true);
    setCommandsError(null);
    try {
      const { ok, status, json } = await apiFetch('/commands');
      if (ok) {
        const STATUS_ORDER = { pending: 0, retrying: 1, processing: 2, executed: 3, failed: 4, cancelled: 5 };
        const sorted = (json.commands || []).slice().sort((a, b) => (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9));
        setCommands(sorted);
      } else {
        setCommandsError(json.error || `HTTP ${status}`);
      }
    } catch { setCommandsError('network_error'); }
    finally { setLoadingCommands(false); }
  }

  async function fetchSettings() {
    if (!apiConfigured) return;
    setLoadingSettings(true);
    setSettingsResult(null);
    try {
      const { ok, status, json } = await apiFetch('/settings');
      if (ok) { if (!settingsDirtyRef.current) applySettings(json.settings); }
      else setSettingsResult({ ok: false, ...resolveError(json.error, `HTTP ${status}`, copy, json) });
    } catch { setSettingsResult({ ok: false, friendly: copy.networkError, detail: '' }); }
    finally { setLoadingSettings(false); }
  }

  async function saveSettings() {
    const times = settings.daily_post_times;
    if (!validateTimes(times)) { haptic('notification', 'error'); setSettingsResult({ ok: false, friendly: copy.invalidTime, detail: '' }); return; }
    if (!settings.timezone.trim()) { haptic('notification', 'error'); setSettingsResult({ ok: false, friendly: copy.timezoneRequired, detail: '' }); return; }

    setSavingSettings(true);
    tg()?.MainButton?.showProgress?.(false);
    try {
      const body = settingsPatchPayload(settings, times);
      const { ok, status, json } = await apiFetch('/settings', {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!ok) {
        haptic('notification', 'error');
        const errInfo = resolveError(json.error, `HTTP ${status}`, copy, json);
        setSettingsResult({ ok: false, ...errInfo, detail: json.error || errInfo.detail || `HTTP ${status}` });
      } else {
        haptic('notification', 'success');
        applySettings(json.settings);
        setSettingsResult({ ok: true, friendly: copy.settingsSaved, detail: '' });
      }
    } catch {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: copy.networkError, detail: '' });
    } finally {
      setSavingSettings(false);
      tg()?.MainButton?.hideProgress?.();
    }
  }
  saveSettingsRef.current = saveSettings;

  async function saveSingleSetting(key, value) {
    try {
      const { ok } = await apiFetch('/settings', {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ [key]: value }),
      });
      if (ok) {
        haptic('notification', 'success');
        // Keep saved baseline in sync so this immediate save doesn't surface a spurious "unsaved changes" state
        setSavedSettings((cur) => ({ ...cur, [key]: value }));
      } else {
        haptic('notification', 'error');
      }
    } catch {
      haptic('notification', 'error');
    }
  }

  async function cancelCommand(command) {
    const confirmed = await tgShowPopup({
      title: copy.cancelCommand,
      message: copy.confirmCancel(command.command_type),
      buttons: [
        { id: 'confirm', type: 'destructive', text: copy.popupConfirm },
        { id: 'cancel', type: 'cancel', text: copy.popupCancel },
      ],
    });
    if (confirmed !== 'confirm') return;

    setCancellingCommand(command.id);
    try {
      const { ok, status, json } = await apiFetch(`/commands/${command.id}`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ status: 'cancelled' }),
      });
      if (!ok) { haptic('notification', 'error'); setResult({ ok: false, ...resolveError(json.error, `HTTP ${status}`, copy, json) }); }
      else { haptic('notification', 'success'); setResult({ ok: true, friendly: copy.commandCancelled, detail: '' }); fetchCommands(); fetchOverview(); }
    } catch { haptic('notification', 'error'); setResult({ ok: false, friendly: copy.networkError, detail: '' }); }
    finally { setCancellingCommand(null); }
  }

  const enqueue = useCallback(async (command_type, payload = {}) => {
    if (loadingCmd) return;
    haptic('impact', 'light');
    setLoadingCmd(command_type);
    try {
      const { ok, status, json } = await apiFetch('/bot-command', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ command_type, payload, target_chat_id: targetChatId || null }),
      });
      if (!ok) {
        haptic('notification', 'error');
        setResult({ ok: false, command_type, ...resolveError(json.error, `HTTP ${status}`, copy, json) });
      } else {
        haptic('notification', 'success');
        setResult({ ok: true, command_type: json.command?.command_type || command_type, friendly: copy.commandQueued, detail: '' });
        // After a card action, clear the current selection so the next action starts clean
        if (['post_now', 'repost_card', 'skip_card'].includes(command_type)) {
          setCardCode('');
          setCardQuery('');
          setCardResults([]);
        }
        fetchStatus(); fetchCommands(); fetchOverview();
      }
    } catch { haptic('notification', 'error'); setResult({ ok: false, command_type, friendly: copy.networkError, detail: '' }); }
    finally { setLoadingCmd(null); }
  }, [loadingCmd, targetChatId, copy]);

  async function confirmEnqueue(message, command_type, payload = {}) {
    const confirmed = await tgShowPopup({
      message,
      buttons: [
        { id: 'confirm', type: 'default', text: copy.popupConfirm },
        { id: 'cancel', type: 'cancel', text: copy.popupCancel },
      ],
    });
    if (confirmed === 'confirm') enqueue(command_type, payload);
  }

  function applySettings(next) {
    const n = normalizeSettings(next);
    setSettings(n);
    setSavedSettings(n);
    const allSelected = WEEKDAYS.every((d) => n.daily_post_days.includes(d.code));
    setAllDaysMode(allSelected);
    setSavedAllDaysMode(allSelected);
    // Sync miniapp UI language from the server-side ai_language setting
    const uiLang = n.ai_language === 'en-US' ? 'en' : 'pt';
    setLanguage(uiLang);
    writeLangStorage(uiLang);
  }

  function updateSetting(key, value) {
    haptic('selection');
    setSettings((cur) => ({ ...cur, [key]: value }));
  }

  // ── Day config helpers ──────────────────────────────────────────────────────

  function getDayConfig(dayCode) {
    return settings.day_config[dayCode] || { packs: [], types: [] };
  }

  function getTimesForDay(dayCode) {
    if (dayCode === 'all') return settings.daily_post_times;
    const cfg = getDayConfig(dayCode);
    return Array.isArray(cfg.times) && cfg.times.length ? cfg.times : settings.daily_post_times;
  }

  function updateDayConfig(dayCode, updater) {
    const baseConfig = (cfg) => ({ packs: [], types: [], ...(cfg || {}) });
    setSettings((cur) => ({
      ...cur,
      day_config: {
        ...cur.day_config,
        [dayCode]: updater(baseConfig(cur.day_config[dayCode])),
      },
    }));
  }

  function addTimeForDay(dayCode) {
    if (!isValidTimeValue(pendingTime)) return;
    haptic('selection');
    if (dayCode === 'all') {
      setSettings((cur) => ({
        ...cur,
        daily_post_times: [...new Set([...cur.daily_post_times, pendingTime])].sort(),
      }));
      return;
    }
    updateDayConfig(dayCode, (cfg) => {
      const base = Array.isArray(cfg.times) && cfg.times.length ? cfg.times : settings.daily_post_times;
      return { ...cfg, times: [...new Set([...base, pendingTime])].sort() };
    });
  }

  function removeTimeForDay(dayCode, time) {
    haptic('selection');
    if (dayCode === 'all') {
      setSettings((cur) => {
        const next = cur.daily_post_times.filter((t) => t !== time);
        return { ...cur, daily_post_times: next.length ? next : cur.daily_post_times };
      });
      return;
    }
    updateDayConfig(dayCode, (cfg) => {
      const base = Array.isArray(cfg.times) && cfg.times.length ? cfg.times : settings.daily_post_times;
      return { ...cfg, times: base.filter((t) => t !== time) };
    });
  }

  function isCycleSelectedForDay(dayCode, cyclePos) {
    const { packs: dp } = getDayConfig(dayCode);
    const cyclePacks = packs.filter((p) => p.cycle_position === cyclePos).map((p) => p.code);
    if (!cyclePacks.length) return false;
    return dp.length === 0 || cyclePacks.every((pc) => dp.includes(pc));
  }

  function isTypeSelectedForDay(dayCode, typeCode) {
    const { types: dt } = getDayConfig(dayCode);
    return dt.length === 0 || dt.includes(typeCode);
  }

  function setAllWeekdays(enabled) {
    haptic('selection');
    setAllDaysMode(enabled);
    setSettings((cur) => ({ ...cur, daily_post_days: enabled ? WEEKDAYS.map((d) => d.code) : cur.daily_post_days }));
  }

  function applyDaysPreset(codes) {
    haptic('selection');
    setAllDaysMode(false);
    setSettings((cur) => ({ ...cur, daily_post_days: codes }));
  }

  function areAllCyclesSelectedForDay(dayCode) {
    const { packs: dp } = getDayConfig(dayCode);
    return dp.length === 0 || (packs.length > 0 && packs.every((p) => dp.includes(p.code)));
  }

  function areAllTypesSelectedForDay(dayCode) {
    const { types: dt } = getDayConfig(dayCode);
    return dt.length === 0 || ALL_CARD_TYPES.every((t) => dt.includes(t.code));
  }

  function setAllCyclesForDay(dayCode, enabled) {
    haptic('selection');
    // enabled=true → [] (all packs allowed); enabled=false → explicit list of all packs (then user unticks individually)
    updateDayConfig(dayCode, (cfg) => ({ ...cfg, packs: enabled ? [] : packs.map((p) => p.code) }));
  }

  function setAllTypesForDay(dayCode, enabled) {
    haptic('selection');
    updateDayConfig(dayCode, (cfg) => ({
      ...cfg,
      types: enabled ? [] : ALL_CARD_TYPES.map((t) => t.code),
    }));
  }

  function toggleCycleForDay(dayCode, cyclePos) {
    haptic('selection');
    const cyclePacks = packs.filter((p) => p.cycle_position === cyclePos).map((p) => p.code);
    updateDayConfig(dayCode, (cfg) => {
      const dp = cfg.packs;
      const allSelected = dp.length === 0 || cyclePacks.every((pc) => dp.includes(pc));
      let nextPacks;
      if (allSelected) {
        const base = dp.length === 0 ? packs.map((p) => p.code) : dp;
        nextPacks = base.filter((pc) => !cyclePacks.includes(pc));
      } else {
        const base = dp.length === 0 ? packs.map((p) => p.code) : dp;
        nextPacks = [...new Set([...base, ...cyclePacks])];
        if (nextPacks.length === packs.length) nextPacks = [];
      }
      return { ...cfg, packs: nextPacks };
    });
  }

  function toggleTypeForDay(dayCode, typeCode) {
    haptic('selection');
    updateDayConfig(dayCode, (cfg) => {
      const dt = cfg.types;
      let nextTypes;
      if (dt.length === 0) {
        nextTypes = ALL_CARD_TYPES.map((t) => t.code).filter((c) => c !== typeCode);
      } else if (dt.includes(typeCode)) {
        nextTypes = dt.filter((c) => c !== typeCode);
        if (nextTypes.length === 0 || nextTypes.length === ALL_CARD_TYPES.length) nextTypes = [];
      } else {
        nextTypes = [...dt, typeCode];
        if (nextTypes.length === ALL_CARD_TYPES.length) nextTypes = [];
      }
      return { ...cfg, types: nextTypes };
    });
  }

  function dayConfigSummary(dayCode, copy) {
    const { packs: dp, types: dt } = getDayConfig(dayCode);
    const cycles = deriveCycles(packs);
    const activeCycles = dp.length === 0 ? 0 : cycles.filter((c) =>
      packs.filter((p) => p.cycle_position === c.position).some((p) => dp.includes(p.code))
    ).length;
    const parts = [];
    if (dp.length > 0 && activeCycles > 0) parts.push(copy.cyclesSelected(activeCycles));
    if (dt.length > 0) parts.push(copy.typesSelected(dt.length));
    return parts.length ? parts.join(' · ') : copy.noCycleConfig;
  }

  function handleSearchChange(e) {
    const val = e.target.value;
    setCardQuery(val);
    clearTimeout(searchTimerRef.current);
    // <2 chars gera resultados demais (todos que contêm "a"); 500ms de debounce evita chamada a cada tecla
    if (val.trim().length < 2) { setCardResults([]); return; }
    searchTimerRef.current = setTimeout(() => doSearchCards(val.trim()), 500);
  }

  async function doSearchCards(query) {
    if (!apiConfigured) return;
    setSearchingCards(true);
    try {
      const { ok, status, json } = await apiFetch(`/cards?q=${encodeURIComponent(query)}`);
      if (ok) setCardResults(json.cards || []);
      else setResult({ ok: false, ...resolveError(json.error, `HTTP ${status}`, copy, json) });
    } catch { setResult({ ok: false, friendly: copy.networkError, detail: '' }); }
    finally { setSearchingCards(false); }
  }

  async function fetchHistoryItems(date, offset, sourceOverride) {
    if (!apiConfigured) return;
    setHistoryLoadingState(true);
    setHistoryError(null);
    const effectiveSource = sourceOverride !== undefined ? sourceOverride : historySourceFilter;
    const params = new URLSearchParams({ limit: '30', offset: String(offset) });
    if (date) params.set('date', date);
    if (effectiveSource && effectiveSource !== 'all') params.set('source', effectiveSource);
    try {
      const { ok, status, json } = await apiFetch(`/history?${params.toString()}`);
      if (ok) {
        const items = json.history || [];
        if (offset === 0) setHistoryItems(items);
        else setHistoryItems((prev) => [...prev, ...items]);
        setHistoryHasMore(items.length === 30);
      } else {
        setHistoryError(json?.error || `HTTP ${status}`);
      }
    } catch {
      setHistoryError('network_error');
    }
    finally { setHistoryLoadingState(false); }
  }

  async function fetchAiProviders() {
    if (!apiConfigured) return;
    try {
      const { ok, json } = await apiFetch('/ai-models');
      if (ok && Array.isArray(json.providers) && json.providers.length) setAiProviders(json.providers);
    } catch {}
  }

  async function fetchBotRuntime() {
    if (!apiConfigured) return;
    try {
      const { ok, json } = await apiFetch('/bot-runtime');
      if (ok) setBotRuntime(json);
    } catch {}
  }

  async function fetchAdmins() {
    if (!apiConfigured) return;
    setAdminsLoading(true);
    setAdminsError(null);
    try {
      const { ok, json } = await apiFetch('/admins');
      if (ok) setAdmins(json.admins || []);
      else setAdminsError(json.error || 'admins_fetch_failed');
    } catch { setAdminsError('network_error'); }
    finally { setAdminsLoading(false); }
  }

  async function addAdmin() {
    const idDigits = adminUserId.replace(/[^0-9]/g, '');
    if (!idDigits) { haptic('notification', 'error'); setAddAdminResult({ ok: false, friendly: copy.adminInvalidId }); return; }
    setAddingAdmin(true);
    setAddAdminResult(null);
    try {
      const { ok, status, json } = await apiFetch('/admins', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ telegram_user_id: Number(idDigits), name: adminName, role: adminRole }),
      });
      if (ok) {
        haptic('notification', 'success');
        setAddAdminResult({ ok: true, friendly: copy.success });
        setAdminUserId('');
        setAdminName('');
        setAdminRole('admin');
        fetchAdmins();
      } else {
        haptic('notification', 'error');
        setAddAdminResult({ ok: false, ...resolveError(json.error, copy.unknownError, copy, json) });
      }
    } catch { haptic('notification', 'error'); setAddAdminResult({ ok: false, friendly: copy.networkError }); }
    finally { setAddingAdmin(false); }
  }

  async function removeAdmin(targetId) {
    try {
      const { ok, json } = await apiFetch(`/admins/${targetId}`, { method: 'DELETE' });
      if (ok) { haptic('notification', 'success'); fetchAdmins(); }
      else {
        haptic('notification', 'error');
        setAdminsError(json.error || 'admin_remove_failed');
      }
    } catch { haptic('notification', 'error'); setAdminsError('network_error'); }
  }

  async function fetchPendingDestinations() {
    if (!apiConfigured) return;
    try {
      const { ok, json } = await apiFetch('/destinations/pending');
      if (ok) setPendingDests(json.pending || []);
    } catch {}
  }

  async function acceptPending(pending) {
    setAcceptingPending(pending.id);
    try {
      const threadId = pendingThreadId[pending.id] || '';
      const body = threadId ? { message_thread_id: Number(threadId) } : {};
      const { ok, json } = await apiFetch(`/destinations/pending/${pending.id}/accept`, {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
      });
      if (ok) {
        haptic('notification', 'success');
        setPendingDests(p => p.filter(d => d.id !== pending.id));
        fetchDestinations();
      } else {
        haptic('notification', 'error');
        setAddDestResult({ ok: false, friendly: json?.error || copy.error });
      }
    } catch { haptic('notification', 'error'); }
    finally { setAcceptingPending(null); }
  }

  async function dismissPending(pendingId) {
    try {
      await apiFetch(`/destinations/pending/${pendingId}`, { method: 'DELETE' });
      setPendingDests(p => p.filter(d => d.id !== pendingId));
      haptic('selection');
    } catch {}
  }

  async function fetchDestinations() {
    if (!apiConfigured) return;
    setDestLoading(true);
    setDestError(null);
    setDestActionResult(null);
    try {
      const { ok, json } = await apiFetch('/destinations');
      if (ok) setDestList(json.destinations || []);
      else setDestError(json.error || 'destinations_fetch_failed');
    } catch { setDestError('network_error'); }
    finally { setDestLoading(false); }
  }

  async function addDestination() {
    const chatIdDigits = destChatId.replace(/[^0-9]/g, '');
    if (!chatIdDigits) { haptic('notification', 'error'); setAddDestResult({ ok: false, friendly: copy.destinationInvalidChatId }); return; }
    if (destThread && !/^\d+$/.test(destThread.trim())) { haptic('notification', 'error'); setAddDestResult({ ok: false, friendly: copy.destinationInvalidThreadId }); return; }
    const finalChatId = `-${chatIdDigits}`;
    setAddingDest(true);
    setAddDestResult(null);
    try {
      const { ok, status, json } = await apiFetch('/destinations', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ chat_id: finalChatId, title: destTitle, message_thread_id: destThread ? Number(destThread) : null }),
      });
      if (ok) {
        haptic('notification', 'success');
        setAddDestResult({ ok: true, friendly: copy.success });
        setDestChatId('');
        setDestTitle('');
        setDestThread('');
        fetchDestinations();
      } else {
        haptic('notification', 'error');
        setAddDestResult({ ok: false, ...resolveError(json.error, copy.unknownError, copy, json) });
      }
    } catch { haptic('notification', 'error'); setAddDestResult({ ok: false, friendly: copy.networkError }); }
    finally { setAddingDest(false); }
  }

  async function testDestination(destId) {
    setTestingDest(destId);
    setDestActionResult(null);
    try {
      const { ok, json } = await apiFetch(`/destinations/${destId}/test`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ language }),
      });
      if (ok) { haptic('notification', 'success'); setDestActionResult({ id: destId, ok: true, text: copy.destinationTestOk }); }
      else { haptic('notification', 'error'); setDestActionResult({ id: destId, ok: false, text: [copy.destinationTestFailed, json?.detail || json?.error].filter(Boolean).join(' — ') }); }
    } catch { haptic('notification', 'error'); setDestActionResult({ id: destId, ok: false, text: copy.networkError }); }
    finally { setTestingDest(null); }
  }

  async function removeDestination(destId) {
    try {
      const { ok } = await apiFetch(`/destinations/${destId}`, { method: 'DELETE' });
      if (ok) { haptic('notification', 'success'); fetchDestinations(); }
      else { haptic('notification', 'error'); }
    } catch { haptic('notification', 'error'); }
  }

  function handleDestChatIdChange(digits) {
    setDestChatId(digits);
    clearTimeout(destResolveTimer.current);
    if (!digits || digits.replace(/[^0-9]/g, '').length < 6) return;
    destResolveTimer.current = setTimeout(async () => {
      const chatId = `-${digits.replace(/[^0-9]/g, '')}`;
      setResolvingDest(true);
      try {
        const { ok, json } = await apiFetch(`/destinations/resolve?chat_id=${encodeURIComponent(chatId)}`);
        if (ok && json.name && !destTitle) {
          setDestTitle(json.name);
          haptic('selection');
        }
      } catch {}
      finally { setResolvingDest(false); }
    }, 800);
  }

  function formatHeartbeatAge(secondsAgo, c) {
    if (secondsAgo === null) return '-';
    if (secondsAgo < 60) return c.secondsAgo(secondsAgo);
    return c.minutesAgo(Math.floor(secondsAgo / 60));
  }

  function postedDailyQueueItems() {
    const actual = savedSettings || settings;
    const timezone = actual.timezone || 'UTC';
    return (overview?.recent_posts || []).filter((post) => post.source === 'scheduled' && post.created_at).map((post) => {
      const postDate = new Intl.DateTimeFormat('sv-SE', {
        timeZone: timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).format(new Date(post.created_at));
      return {
        id: `daily-post-${post.id || post.created_at}`,
        command_type: 'daily_post',
        status: 'executed',
        caption: [post.card_name || post.card_code, postDate].filter(Boolean).join(' · '),
        created_at: post.created_at,
      };
    });
  }

  // ── Derived ─────────────────────────────────────────────────────────────────

  const workerValue = loadingStatus ? '…' : sysStatus?.ok ? copy.online : copy.offline;
  const workerTone = sysStatus?.ok ? 'ok' : 'err';
  const cardsValue = loadingOverview ? '…' : (overview?.counts?.cards ?? sysStatus?.total_cards ?? '-');
  const queueValue = loadingOverview ? '…' : (overview?.counts?.pending_commands ?? 0);
  const targetChats = overview?.target_chats?.filter((c) => c.enabled !== false) || [];

  // ── Auth gate ───────────────────────────────────────────────────────────────

  if (authState === 'loading') return <LoadingGate />;
  if (authState === 'unauthorized') return <UnauthorizedGate copy={copy} />;
  if (authState === 'api_not_configured') return <ApiNotConfiguredGate copy={copy} />;
  if (authState === 'no_telegram') return <NoTelegramGate copy={copy} />;
  if (authState === 'auth_error') return <AuthErrorGate copy={copy} />;

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="app" ref={setContentRef}>

      {/* Header */}
      <header className="app-header">
        <div className="avatar">
          {(botInfo?.photo_url || getBotPhotoUrl())
            ? <img src={botInfo?.photo_url || getBotPhotoUrl()} alt={botInfo?.name || 'Bot'} className="avatar-img" />
            : <Icon name="bot" />}
        </div>
        <div className="header-title">{botInfo?.name || '…'}</div>
        {botInfo?.username && <div className="header-subtitle">@{botInfo.username}</div>}
        {(botInfo?.short_description || botInfo?.description) && (
          <div className="header-description">{botInfo.short_description || botInfo.description}</div>
        )}
      </header>

      {!apiConfigured && <Notice tone="err">{copy.workerNotConfigured}</Notice>}

      {settingsDirty && ['settings', 'schedule', 'ai', 'database', 'day_detail'].includes(activeTab) && (
        <Notice tone="warn">{copy.unsavedChanges}</Notice>
      )}

      {/* ── HOME ── */}
      {activeTab === 'home' && (
        <>
          <div className="overview-panel">
            <div
              className="overview-stat overview-stat-action"
              onClick={() => setActiveTab('health')}
              role="button"
              tabIndex={0}
              aria-label={copy.health}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActiveTab('health'); } }}
            >
              <span className={`overview-dot ${sysStatus?.ok ? 'ok' : 'err'}`} />
              <span className="overview-stat-label">{loadingStatus ? '…' : workerValue}</span>
            </div>
            <div className="overview-divider" />
            <div
              className="overview-stat overview-stat-action"
              onClick={() => setActiveTab('database')}
              role="button"
              tabIndex={0}
              aria-label={copy.databaseTab}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActiveTab('database'); } }}
            >
              <Icon name="cards" />
              <span className="overview-stat-label">{cardsValue}</span>
            </div>
            <div className="overview-divider" />
            <div
              className="overview-stat overview-stat-action"
              onClick={() => setActiveTab('queue')}
              role="button"
              tabIndex={0}
              aria-label={copy.queue}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setActiveTab('queue'); } }}
            >
              <Icon name="queue" />
              <span className="overview-stat-label">{queueValue > 0 ? String(queueValue) : '0'}</span>
              {queueValue > 0 && <span className="overview-badge">{copy.pending}</span>}
            </div>
          </div>

          <Section title={copy.actionsTitle}>
            <Row icon="send"    label={copy.postCard}   onClick={() => setActiveTab('post')} />
            <Row icon="history" label={copy.historyTab} onClick={() => setActiveTab('history')} />
            <Row icon="queue" label={copy.queue} value={queueValue > 0 ? String(queueValue) : null} badgeTone={queueValue > 0 ? 'warn' : ''} onClick={() => setActiveTab('queue')} />
          </Section>

          <Section title={copy.configTitle}>
            <Row icon="settings"     label={copy.postingConfig}          onClick={() => setActiveTab('settings')} />
            <Row icon="destinations" label={copy.destinationsManageTab}  onClick={() => setActiveTab('destinations')} />
            <Row icon="app"          label={copy.appTab}                 onClick={() => { setActiveTab('app_settings'); fetchAdmins(); }} />
          </Section>

          <Section title={copy.systemTitle}>
            <Row icon="database" label={copy.databaseTab}  onClick={() => setActiveTab('database')} />
            <Row icon="server"   label={copy.health}       onClick={() => setActiveTab('health')} value={workerValue} badgeTone={workerTone} />
            <Row icon="wrench"   label={copy.maintenance}  onClick={() => setActiveTab('maintenance')} />
          </Section>
        </>
      )}

      {/* ── POST CARD ── */}
      {activeTab === 'post' && (
        <>
          <Section title={copy.postCard} footer={copy.postCardManualCaption}>
            <div className="row search-row">
              <Icon name="search" />
              <input
                className="search-input"
                type="search"
                value={cardQuery}
                onChange={handleSearchChange}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); clearTimeout(searchTimerRef.current); const q = cardQuery.trim(); if (q.length >= 2) doSearchCards(q); } }}
                placeholder={copy.searchPlaceholder}
                aria-label={copy.searchCard || copy.searchPlaceholder}
                inputMode="text"
              />
              {searchingCards && <Spinner />}
            </div>

            {!searchingCards && cardQuery.trim().length >= 2 && cardResults.length === 0 && (
              <Row icon="info" label={copy.searchNotFound} />
            )}
            {cardResults.length > 0 && cardResults.map((card) => (
              <CardResult
                key={card.code}
                card={card}
                selected={cardCode === card.code}
                onSelect={(sel) => {
                  setCardCode(sel.code);
                  setCardQuery(`${sel.code} – ${sel.name || sel.real_name}`);
                  setCardResults([]);
                  haptic('impact', 'light');
                }}
              />
            ))}
          </Section>

          {targetChats.length > 0 ? (
            <Section title={copy.destination}>
              <SelectRow label={copy.destination} value={targetChatId} onChange={setTargetChatId}>
                <option value="">{copy.defaultChat}</option>
                {targetChats.map((chat) => (
                  <option key={chat.chat_id} value={chat.chat_id}>{chat.title || chat.chat_id}</option>
                ))}
              </SelectRow>
            </Section>
          ) : (
            <Section>
              <Row icon="info" label={copy.noDestinationsInPost} />
              <Row icon="destinations" label={copy.goToDestinations} onClick={() => setActiveTab('destinations')} />
            </Section>
          )}

          <Section footer={!cardCode ? copy.automaticChoice : undefined}>
            <MenuRow
              icon="send"
              accent
              label={copy.postNow}
              value={cardCode || undefined}
              loading={loadingCmd === 'post_now'}
              disabled={actionsDisabled}
              onClick={() => confirmEnqueue(copy.confirmPostNow(cardCode), 'post_now', cardCode ? { card_code: cardCode } : {})}
            />
            <MenuRow
              icon="repeat"
              label={copy.repostCard}
              value={cardCode || undefined}
              loading={loadingCmd === 'repost_card'}
              disabled={actionsDisabled || !cardCode}
              onClick={() => confirmEnqueue(copy.confirmRepost(cardCode), 'repost_card', { card_code: cardCode })}
            />
            <MenuRow
              icon="skip"
              label={copy.skipCard}
              value={cardCode || undefined}
              loading={loadingCmd === 'skip_card'}
              disabled={actionsDisabled || !cardCode}
              onClick={() => confirmEnqueue(copy.confirmSkip(cardCode), 'skip_card', { card_code: cardCode })}
            />
          </Section>

          {result && <Section><ResultRow result={result} copy={copy} /></Section>}
        </>
      )}

      {/* ── SETTINGS ── */}
      {activeTab === 'settings' && (
        <>
          {/* Daily post */}
          <Section title={copy.dailyPost}>
            <ToggleRow label={copy.automaticPosting} checked={settings.daily_post_enabled} onChange={(v) => updateSetting('daily_post_enabled', v)} />
            {settings.daily_post_enabled && (
              <SelectRow label={copy.timezoneLabel} value={settings.timezone} onChange={(v) => updateSetting('timezone', v)}>
                {TIMEZONES.map((tz) => (
                  <option key={tz.value} value={tz.value}>{tz.label}</option>
                ))}
              </SelectRow>
            )}
          </Section>

          {/* No destinations warning */}
          {targetChats.length === 0 && (
            <Section>
              <Row icon="info" label={copy.noDestinationsWarning} badgeTone="warn" />
              <Row icon="destinations" label={copy.goToDestinations} onClick={() => setActiveTab('destinations')} />
            </Section>
          )}

          <Section title={copy.scheduleTab}>
            <Row icon="calendar" label={copy.scheduleTab} onClick={() => setActiveTab('schedule')} />
          </Section>

          <Section title={copy.aiTab}>
            <Row icon="ai" label={copy.aiTab} onClick={() => setActiveTab('ai')} />
          </Section>

          {settingsResult && <Section><ResultRow result={settingsResult} copy={copy} /></Section>}

        </>
      )}

      {/* ── DATABASE ── */}
      {activeTab === 'database' && (() => {
        const lang = language === 'pt' ? 'pt' : 'en';
        const syncDate = overview?.last_sync || sysStatus?.last_sync;
        const daysSinceSync = syncDate ? (Date.now() - new Date(syncDate).getTime()) / 86400000 : null;
        const isStale = daysSinceSync === null || daysSinceSync > 7;
        return (
          <>
            <Section title={copy.syncArkhamDB}>
              <MenuRow icon="sync"    label={copy.syncArkhamDB} loading={loadingCmd === 'sync_arkhamdb'} disabled={actionsDisabled} onClick={() => confirmEnqueue(copy.confirmSync, 'sync_arkhamdb', { sync_faq: false })} />
              <MenuRow icon="refresh" label={copy.refreshStatus} loading={loadingOverview || loadingStatus} disabled={!apiConfigured} onClick={() => { fetchOverview(); fetchStatus(); }} />
            </Section>

            <Section title={copy.databaseStatus}>
              <Row icon="clock" label={copy.lastSyncAt} value={syncDate ? new Date(syncDate).toLocaleString(copy.locale) : copy.neverSynced} mono={!!syncDate} badgeTone={isStale ? 'warn' : 'ok'} />
              <Row icon="cards" label={copy.cards}      value={loadingOverview ? '…' : (overview?.counts?.cards ?? sysStatus?.total_cards ?? '-')} />
              <Row icon="packs" label={copy.packs}      value={loadingOverview ? '…' : (overview?.counts?.packs ?? sysStatus?.total_packs ?? '-')} />
            </Section>

            <Section title={copy.syncSchedule}>
              <ToggleRow
                label={copy.syncScheduleEnabled}
                checked={settings.sync_schedule_enabled}
                onChange={(v) => updateSetting('sync_schedule_enabled', v)}
              />
            </Section>

            {settings.sync_schedule_enabled && (
              <>
                <Section title={copy.syncScheduleTime}>
                  <div className="time-add-row">
                    <span className="row-label">{copy.syncScheduleTime}</span>
                    <input
                      className="time-add-input"
                      type="time"
                      value={settings.sync_schedule_time}
                      onChange={(e) => updateSetting('sync_schedule_time', e.target.value.slice(0, 5))}
                    />
                  </div>
                </Section>
                <Section title={copy.syncScheduleDays}>
                  {WEEKDAYS.map((day) => (
                    <ToggleRow
                      key={day.code}
                      label={day[lang]}
                      checked={settings.sync_schedule_days.includes(day.code)}
                      onChange={(checked) => {
                        const next = checked
                          ? [...new Set([...settings.sync_schedule_days, day.code])]
                          : settings.sync_schedule_days.filter((d) => d !== day.code);
                        updateSetting('sync_schedule_days', next.length ? next : [day.code]);
                      }}
                    />
                  ))}
                </Section>
              </>
            )}

            {settingsResult && <Section><ResultRow result={settingsResult} copy={copy} /></Section>}

            {result && <Section><ResultRow result={result} copy={copy} /></Section>}
          </>
        );
      })()}

      {activeTab === 'maintenance' && (
        <>
          <Section title={copy.resetCycle}>
            <DangerRow icon="reset" label={copy.resetCycle} loading={loadingCmd === 'reset_cycle'} disabled={actionsDisabled} onClick={() => confirmEnqueue(copy.confirmReset, 'reset_cycle')} />
          </Section>

          {result && <Section><ResultRow result={result} copy={copy} /></Section>}
        </>
      )}

      {/* ── SCHEDULE ── */}
      {activeTab === 'schedule' && (() => {
        const lang = language === 'pt' ? 'pt' : 'en';
        const allEnabled = allDaysMode;
        return (
          <>
            <Section title={copy.cardFilter}>
              <ToggleRow label={copy.includeSpoilers} checked={settings.include_spoilers} onChange={(v) => updateSetting('include_spoilers', v)} />
            </Section>
            <Section title={copy.weeklySchedule} footer={copy.weeklyScheduleHint}>
              <DayScheduleRow
                label={copy.allWeekdays}
                subtitle={dayConfigSummary('all', copy)}
                enabled={allEnabled}
                onToggle={setAllWeekdays}
                onConfigure={() => { setActiveDayCode('all'); setActiveTab('day_detail'); }}
                configureLabel={copy.configureDay}
              />
            </Section>
            <Section title={copy.dailySchedule}>
              {!allEnabled && (
                <div className="preset-row">
                  <button type="button" className="source-filter-btn" onClick={() => applyDaysPreset(['mon', 'tue', 'wed', 'thu', 'fri'])}>{copy.presetWeekdays}</button>
                  <button type="button" className="source-filter-btn" onClick={() => applyDaysPreset(['sat', 'sun'])}>{copy.presetWeekend}</button>
                </div>
              )}
              {WEEKDAYS.map((day) => {
                const enabled = settings.daily_post_days.includes(day.code);
                return (
                  <DayScheduleRow
                    key={day.code}
                    label={day[lang]}
                    subtitle={enabled ? dayConfigSummary(day.code, copy) : undefined}
                    enabled={enabled}
                    onToggle={(v) => {
                      setSettings((cur) => {
                        const next = v
                          ? [...cur.daily_post_days, day.code]
                          : cur.daily_post_days.filter((d) => d !== day.code);
                        return { ...cur, daily_post_days: [...new Set(next)] };
                      });
                      haptic('selection');
                    }}
                    onConfigure={() => { setActiveDayCode(day.code); setActiveTab('day_detail'); }}
                    disabled={allEnabled}
                    configureLabel={copy.configureDay}
                  />
                );
              })}
            </Section>

            {settingsResult && <Section><ResultRow result={settingsResult} copy={copy} /></Section>}
          </>
        );
      })()}

      {/* ── QUEUE ── */}
      {activeTab === 'queue' && (() => {
        const pendingCount = commands.filter((c) => ['pending', 'retrying'].includes(c.status)).length;
        const totalCount = commands.length;
        const summaryFooter = !loadingCommands && !commandsError && totalCount > 0 ? copy.queueStatusSummary(pendingCount, totalCount) : undefined;
        return (
          <>
            <Section title={copy.commandQueue} footer={summaryFooter}>
              <MenuRow icon="refresh" label={copy.refreshQueue} loading={loadingCommands} disabled={!apiConfigured} onClick={fetchCommands} />
              {commandsError && <Row icon="info" label={copy.commandsFetchError} value="err" badgeTone="err" />}
              {!commandsError && commands.length === 0 && !loadingCommands && <Row icon="queue" label={copy.noRecentCommands} />}
              {commands.map((cmd) => (
                <CommandRow key={cmd.id} command={cmd} onCancel={cancelCommand} loading={cancellingCommand === cmd.id} copy={copy} />
              ))}
            </Section>
            {pendingCount > 0 && (
              <Section title={copy.clearQueue}>
                <DangerRow icon="trash" label={copy.clearQueue} loading={loadingCmd === 'clear_queue'} disabled={actionsDisabled} onClick={() => confirmEnqueue(copy.confirmClear, 'clear_queue')} />
              </Section>
            )}
            {result && <Section><ResultRow result={result} copy={copy} /></Section>}
          </>
        );
      })()}

      {/* ── DAY DETAIL ── */}
      {activeTab === 'day_detail' && activeDayCode && (() => {
        const lang = language === 'pt' ? 'pt' : 'en';
        const dayLabel = activeDayCode === 'all'
          ? copy.configureAllWeekdays
          : WEEKDAYS.find((d) => d.code === activeDayCode)?.[lang] || activeDayCode;
        const cycles = deriveCycles(packs);
        return (
          <>
            <header className="section-header-standalone">{dayLabel}</header>

            {settingsResult && <Section><ResultRow result={settingsResult} copy={copy} /></Section>}

            <Section title={copy.postTimes}>
              {getTimesForDay(activeDayCode).map((t) => (
                <div key={t} className="time-add-row">
                  <span className="row-label">{t}</span>
                  <button
                    type="button"
                    className="icon-btn danger"
                    aria-label={copy.removeTime}
                    onClick={() => removeTimeForDay(activeDayCode, t)}
                  ><Icon name="x" /></button>
                </div>
              ))}
              <div className="time-add-row">
                <span className="row-label">{copy.addTime}</span>
                <input
                  className="time-add-input"
                  type="time"
                  value={pendingTime}
                  onChange={(e) => setPendingTime(e.target.value.slice(0, 5))}
                />
                <button
                  type="button"
                  className="icon-btn"
                  aria-label={copy.addTime}
                  onClick={() => addTimeForDay(activeDayCode)}
                >+</button>
              </div>
            </Section>

            {/* Cycles */}
            <Section title={copy.cyclesToday}>
              {packsLoading && <LoadingRow label={copy.loadingPacks} />}
              {packsError && !packsLoading && <Row icon="info" label={copy.packsFailed} />}
              {!packsLoading && !packsError && (
                <ToggleRow
                  label={copy.allCycles}
                  checked={areAllCyclesSelectedForDay(activeDayCode)}
                  onChange={(v) => setAllCyclesForDay(activeDayCode, v)}
                />
              )}
              {!packsLoading && !packsError && cycles.map((cycle) => (
                <ToggleRow
                  key={cycle.position}
                  label={cycle.name}
                  checked={isCycleSelectedForDay(activeDayCode, cycle.position)}
                  onChange={() => toggleCycleForDay(activeDayCode, cycle.position)}
                />
              ))}
            </Section>

            {/* Card types */}
            <Section title={copy.typesToday}>
              <ToggleRow
                label={copy.allTypes}
                checked={areAllTypesSelectedForDay(activeDayCode)}
                onChange={(v) => setAllTypesForDay(activeDayCode, v)}
              />
              {ALL_CARD_TYPES.map((type) => (
                <ToggleRow
                  key={type.code}
                  label={type[lang]}
                  checked={isTypeSelectedForDay(activeDayCode, type.code)}
                  onChange={() => toggleTypeForDay(activeDayCode, type.code)}
                />
              ))}
            </Section>

          </>
        );
      })()}

      {/* ── HISTORY ── */}
      {activeTab === 'history' && (
        <>
          <Section title={copy.historyTitle}>
            <div className="history-source-filter">
              {[['all', copy.sourceAll], ['scheduled', copy.sourceScheduled], ['manual', copy.sourceManual]].map(([val, label]) => (
                <button
                  key={val}
                  type="button"
                  className={`source-filter-btn${historySourceFilter === val ? ' active' : ''}`}
                  onClick={() => { haptic('selection'); setHistorySourceFilter(val); fetchHistoryItems(historyDate, 0, val); }}
                >{label}</button>
              ))}
            </div>
            <div className="history-toolbar">
              <div className="history-date-wrap">
                <Icon name="clock" />
                <input
                  className="history-date-input"
                  type="date"
                  value={historyDate}
                  onChange={(e) => { setHistoryDate(e.target.value); fetchHistoryItems(e.target.value, 0); }}
                />
                {historyDate && (
                  <button className="history-clear-btn" type="button" onClick={() => { setHistoryDate(''); fetchHistoryItems('', 0); }} aria-label={copy.clearFilter}>
                    <Icon name="x" />
                  </button>
                )}
              </div>
              <button className="history-refresh-btn" type="button" onClick={() => fetchHistoryItems(historyDate, 0)} disabled={!apiConfigured} aria-label={copy.refreshQueue}>
                {historyLoadingState ? <Spinner /> : <Icon name="refresh" />}
              </button>
            </div>
          </Section>

          {(() => {
            const filteredItems = historyItems;
            return (
              <Section footer={!historyLoadingState && !historyError ? copy.postsOnDate(filteredItems.length, historyDate) : undefined}>
                {historyError && <Row icon="info" label={copy.error} value="err" badgeTone="err" caption={resolveError(historyError, copy.unknownError, copy).friendly} />}
                {historyLoadingState && filteredItems.length === 0 && !historyError && (
                  <LoadingRow label={copy.loading} />
                )}
                {!historyLoadingState && !historyError && filteredItems.length === 0 && (
                  <Row icon="cards" label={copy.noHistory} />
                )}
                {filteredItems.map((post) => {
                  const friendlyStatus = copy.postStatusLabels[post.status] || post.status;
                  const STATUS_TONE = { POSTED_FRONT_SUCCESS: 'ok', POSTED_BACK: 'ok', FAILED_DOWNLOAD: 'err', FAILED_SEND: 'err', CYCLE_RESET: '' };
                  const tone = STATUS_TONE[post.status] ?? (post.status?.startsWith('POSTED') ? 'ok' : post.status?.startsWith('FAIL') ? 'err' : '');
                  const srcTone = post.source === 'scheduled' ? 'ok' : 'warn';
                  const srcLabel = post.source === 'scheduled' ? copy.scheduledPost : post.source === 'manual' ? copy.manualPost : null;
                  const arkhamUrl = post.card_code ? `https://arkhamdb.com/card/${post.card_code}` : null;
                  const timeStr = post.created_at ? new Date(post.created_at).toLocaleTimeString(copy.locale, { hour: '2-digit', minute: '2-digit' }) : null;
                  return (
                    <div key={post.id} className="history-item">
                      <div className="history-item-main">
                        {arkhamUrl ? (
                          <a className="history-item-name row-link" href={arkhamUrl} target="_blank" rel="noopener noreferrer">
                            {post.card_name || post.card_code}
                          </a>
                        ) : (
                          <span className="history-item-name">{post.card_name || post.card_code}</span>
                        )}
                        <div className="history-item-footer">
                          <span className="history-item-meta">{[post.card_code, timeStr].filter(Boolean).join(' · ')}</span>
                          <div className="history-item-badges">
                            {srcLabel && <Badge tone={srcTone}>{srcLabel}</Badge>}
                            <Badge tone={tone}>{friendlyStatus}</Badge>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
                {historyHasMore && (
                  <MenuRow icon="refresh" label={copy.loadMore} loading={historyLoadingState} disabled={!apiConfigured} onClick={() => fetchHistoryItems(historyDate, historyItems.length)} />
                )}
              </Section>
            );
          })()}
        </>
      )}

      {/* ── AI ── */}
      {activeTab === 'ai' && (() => {
        const lang = language === 'pt' ? 'pt' : 'en';
        return (
          <>
            <Section title={copy.aiSection} footer={copy.aiTabCaption}>
              <ToggleRow label={copy.aiEnabled} checked={settings.ai_enabled} onChange={(v) => updateSetting('ai_enabled', v)} />
              {settings.ai_enabled && <>
                <ToggleRow label={copy.aiAutoOnly} checked={settings.ai_auto_only} onChange={(v) => updateSetting('ai_auto_only', v)} />
                {settings.ai_auto_only && <p className="section-note">{copy.aiAutoOnlyCaption}</p>}
              </>}
            </Section>

            {settings.ai_enabled && (
              <>
                <Section title={copy.aiTone}>
                  <SelectRow label={copy.aiTone} value={settings.ai_tone} onChange={(v) => updateSetting('ai_tone', v)}>
                    {AI_TONES.map((t) => (
                      <option key={t.value} value={t.value}>{t[lang]}</option>
                    ))}
                  </SelectRow>
                </Section>

                <Section title={copy.aiCreativity}>
                  <SelectRow label={copy.aiCreativity} value={settings.ai_creativity} onChange={(v) => updateSetting('ai_creativity', v)}>
                    <option value="conservative">{copy.aiCreativityConservative}</option>
                    <option value="default">{copy.aiCreativityDefault}</option>
                    <option value="creative">{copy.aiCreativityCreative}</option>
                  </SelectRow>
                </Section>

                <Section title={copy.aiProvider}>
                  {(() => {
                    const effectiveProviders = aiProviders.length > 0 ? aiProviders : AI_PROVIDERS;
                    const currentProvider = _providerOfModel(settings.ai_model);
                    const providerModels = effectiveProviders.find((p) => p.value === currentProvider)?.models ?? [];
                    return (<>
                      <StackedSelectRow label={copy.aiProvider} value={currentProvider} onChange={(providerValue) => {
                        const firstModel = effectiveProviders.find((p) => p.value === providerValue)?.models[0]?.value;
                        if (firstModel) updateSetting('ai_model', firstModel);
                      }}>
                        {effectiveProviders.map((p) => (
                          <option key={p.value} value={p.value}>{lang === 'pt' ? p.labelPt : p.labelEn}</option>
                        ))}
                      </StackedSelectRow>
                      <StackedSelectRow label={copy.aiModel} value={settings.ai_model} onChange={(v) => updateSetting('ai_model', v)}>
                        {providerModels.map((m) => (
                          <option key={m.value} value={m.value}>{m.label}</option>
                        ))}
                      </StackedSelectRow>
                    </>);
                  })()}
                </Section>

                <Section title={copy.aiPreMessageTitle}>
                  <ToggleRow label={copy.aiPreMessage} checked={settings.ai_pre_message_enabled} onChange={(v) => updateSetting('ai_pre_message_enabled', v)} />
                  {settings.ai_pre_message_enabled && (
                    <SelectRow label={copy.aiPreMessageDelay} value={String(settings.ai_pre_message_delay_seconds)} onChange={(v) => updateSetting('ai_pre_message_delay_seconds', Number(v))}>
                      {DELAY_OPTIONS.map((v) => <option key={v} value={v}>{formatDelay(v, lang)}</option>)}
                    </SelectRow>
                  )}
                </Section>

                <Section title={copy.aiPostQuestionTitle}>
                  <ToggleRow label={copy.aiPostQuestion} checked={settings.ai_post_question_enabled} onChange={(v) => updateSetting('ai_post_question_enabled', v)} />
                  {settings.ai_post_question_enabled && (
                    <SelectRow label={copy.aiPostQuestionDelay} value={String(settings.ai_post_question_delay_seconds)} onChange={(v) => updateSetting('ai_post_question_delay_seconds', Number(v))}>
                      {DELAY_OPTIONS.map((v) => <option key={v} value={v}>{formatDelay(v, lang)}</option>)}
                    </SelectRow>
                  )}
                </Section>

              </>
            )}

            {settingsResult && <Section><ResultRow result={settingsResult} copy={copy} /></Section>}
          </>
        );
      })()}


      {/* ── DESTINATIONS MANAGE ── */}
      {activeTab === 'destinations' && (
        <>
          {pendingDests.length > 0 && (
            <Section title={copy.pendingDestinationsTitle} footer={copy.pendingDestinationCaption}>
              {pendingDests.map(p => (
                <div key={p.id} className="pending-row">
                  <div className="pending-row-head">
                    <span className="row-label">{p.chat_title}</span>
                    <span className="row-caption">
                      {p.chat_id}{p.chat_username ? ` · @${p.chat_username}` : ''}
                    </span>
                  </div>
                  <div className="stacked-input-row" style={{ padding: 0 }}>
                    <input
                      className="block-input"
                      inputMode="numeric"
                      placeholder={copy.pendingThreadHint}
                      value={pendingThreadId[p.id] || ''}
                      onChange={e => setPendingThreadId(t => ({ ...t, [p.id]: e.target.value.replace(/[^0-9]/g, '') }))}
                      autoComplete="off"
                    />
                  </div>
                  <div className="pending-actions">
                    <button
                      type="button"
                      className="pending-action-btn confirm"
                      disabled={acceptingPending === p.id}
                      onClick={() => acceptPending(p)}
                    >
                      {acceptingPending === p.id ? <Spinner /> : <><Icon name="result" /><span className="row-label">{copy.pendingAccept}</span></>}
                    </button>
                    <button
                      type="button"
                      className="pending-action-btn dismiss"
                      disabled={acceptingPending === p.id}
                      onClick={() => dismissPending(p.id)}
                    >
                      <Icon name="x" /><span className="row-label">{copy.pendingDismiss}</span>
                    </button>
                  </div>
                </div>
              ))}
            </Section>
          )}

          <Section title={copy.destinationsManageTab}>
            <MenuRow icon="refresh" label={copy.refreshQueue} loading={destLoading} disabled={!apiConfigured} onClick={() => { fetchDestinations(); fetchPendingDestinations(); }} />
            {destError && <Row icon="info" label={copy.error} value="err" badgeTone="err" caption={resolveError(destError, copy.unknownError, copy).friendly} />}
            {!destLoading && !destError && destList.length === 0 && <Row icon="info" label={copy.noDestinations} />}
            {destList.map((dest) => {
              const fb = destActionResult && destActionResult.id === dest.id ? destActionResult : null;
              return (
                <div key={dest.id} className="row manage-row">
                  <div className="row-main">
                    <span className="row-label">{dest.title || dest.chat_id}</span>
                    <span className={`row-caption${fb ? (fb.ok ? ' ok' : ' err') : ''}`}>
                      {fb ? fb.text : `${dest.chat_id}${dest.message_thread_id ? ` · thread ${dest.message_thread_id}` : ''}`}
                    </span>
                  </div>
                  <div className="manage-row-actions">
                    <button
                      type="button"
                      className="icon-btn"
                      disabled={testingDest === dest.id}
                      onClick={() => testDestination(dest.id)}
                      aria-label={copy.testDestination}
                    >{testingDest === dest.id ? <Spinner /> : <Icon name="send" />}</button>
                    <button
                      type="button"
                      className="icon-btn danger"
                      onClick={async () => {
                        const confirmed = await tgShowPopup({
                          message: copy.confirmRemoveDestination(dest.title),
                          buttons: [
                            { id: 'confirm', type: 'destructive', text: copy.popupConfirm },
                            { id: 'cancel', type: 'cancel', text: copy.popupCancel },
                          ],
                        });
                        if (confirmed === 'confirm') removeDestination(dest.id);
                      }}
                      aria-label={copy.removeDestination}
                    ><Icon name="x" /></button>
                  </div>
                </div>
              );
            })}
          </Section>

          <Section title={copy.addDestination}>
            <ChatIdInputRow label={copy.destinationChatIdLabel} value={destChatId} onChange={handleDestChatIdChange} placeholder="100123456789" loading={resolvingDest} />
            <StackedInputRow label={copy.destinationTitleLabel} value={destTitle} onChange={setDestTitle} placeholder={copy.destinationTitlePlaceholder} />
            <StackedInputRow label={copy.destinationThreadLabel} value={destThread} onChange={setDestThread} placeholder={copy.destinationThreadPlaceholder} inputMode="numeric" invalid={!!destThread && !/^\d+$/.test(destThread.trim())} />
            <MenuRow icon="send" accent label={copy.addDestination} loading={addingDest} disabled={!apiConfigured || !destChatId.trim()} onClick={addDestination} />
            {addDestResult && <ResultRow result={addDestResult} copy={copy} />}
          </Section>
        </>
      )}

      {/* ── APP SETTINGS ── */}
      {activeTab === 'app_settings' && (
        <>
          <Section title={copy.chooseLanguage}>
            <SelectRow
              label={copy.chooseLanguage}
              value={language}
              onChange={(v) => {
                const aiLang = v === 'en' ? 'en-US' : 'pt-BR';
                setLanguage(v);
                writeLangStorage(v);
                updateSetting('ai_language', aiLang);
                saveSingleSetting('ai_language', aiLang);
              }}
            >
              <option value="pt">{copy.portuguese}</option>
              <option value="en">{copy.englishLang}</option>
            </SelectRow>
          </Section>

          {me?.role === 'owner' && (
            <>
              <Section title={copy.adminsTitle}>
                <MenuRow icon="refresh" label={copy.refreshQueue} loading={adminsLoading} disabled={!apiConfigured} onClick={fetchAdmins} />
                {adminsError && <Row icon="info" label={copy.error} value="err" badgeTone="err" caption={resolveError(adminsError, copy.unknownError, copy).friendly} />}
                {!adminsLoading && !adminsError && admins.length === 0 && <Row icon="info" label={copy.noAdmins} />}
                {admins.map((admin) => (
                  <div key={admin.telegram_user_id} className="row manage-row">
                    <div className="row-main">
                      <span className="row-label">{admin.name || String(admin.telegram_user_id)}</span>
                      <span className="row-caption">{admin.telegram_user_id}{admin.added_by_name ? ` · ${copy.adminAddedBy} ${admin.added_by_name}` : ''}</span>
                    </div>
                    <div className="manage-row-actions">
                      <Badge tone={admin.role === 'owner' ? 'ok' : admin.role === 'admin' ? 'warn' : ''}>{admin.role}</Badge>
                      {!(admin.telegram_user_id === me?.user?.id && admin.role === 'owner') && (
                        <button
                          type="button"
                          className="icon-btn danger"
                          onClick={async () => {
                            const confirmed = await tgShowPopup({
                              message: copy.confirmRemoveAdmin(admin.name || String(admin.telegram_user_id)),
                              buttons: [
                                { id: 'confirm', type: 'destructive', text: copy.popupConfirm },
                                { id: 'cancel', type: 'cancel', text: copy.popupCancel },
                              ],
                            });
                            if (confirmed === 'confirm') removeAdmin(admin.telegram_user_id);
                          }}
                          aria-label={copy.removeAdmin}
                        ><Icon name="x" /></button>
                      )}
                    </div>
                  </div>
                ))}
              </Section>
              <Section title={copy.addAdmin}>
                <StackedInputRow label={copy.adminUserIdLabel} value={adminUserId} onChange={setAdminUserId} placeholder={copy.adminUserIdPlaceholder} inputMode="numeric" invalid={!!adminUserId && !/^\d+$/.test(adminUserId.trim())} />
                <StackedInputRow label={copy.adminNameLabel} value={adminName} onChange={setAdminName} placeholder={copy.adminNamePlaceholder} />
                <SelectRow label={copy.adminRoleLabel} value={adminRole} onChange={setAdminRole}>
                  <option value="admin">{copy.adminRoleAdmin}</option>
                  <option value="viewer">{copy.adminRoleViewer}</option>
                </SelectRow>
                <MenuRow icon="shield" accent label={copy.addAdmin} loading={addingAdmin} disabled={!apiConfigured || !adminUserId.trim()} onClick={addAdmin} />
                {addAdminResult && <ResultRow result={addAdminResult} copy={copy} />}
              </Section>
            </>
          )}
        </>
      )}

      {/* ── HEALTH ── */}
      {activeTab === 'health' && (
        <>
          <Section title={copy.botRuntime}>
            {botRuntime ? (
              <>
                <Row icon="plug" label={copy.botRuntime} value={botRuntime.alive ? copy.botAlive : copy.botDead} badgeTone={botRuntime.alive ? 'ok' : 'err'} />
                <Row icon="clock" label={copy.lastHeartbeat} value={botRuntime.last_seen ? formatHeartbeatAge(botRuntime.seconds_ago, copy) : '-'} />
              </>
            ) : (
              <Row icon="plug" label={copy.botRuntime} value="…" />
            )}
          </Section>

          <Section title={copy.account}>
            <Row icon="plug"   label={copy.telegramWebApp} value={tg() ? copy.yes : copy.no} badgeTone={tg() ? 'ok' : 'err'} />
            <Row icon="key"    label={copy.initDataLabel}  value={initData() ? copy.yes : copy.no} badgeTone={initData() ? 'ok' : 'err'} />
            <Row icon="shield" label={copy.admin}          value={copy.roleLabels[me?.role] || me?.role || '-'} badgeTone="ok" caption={me?.admin_source ? `${copy.adminSourcePrefix}: ${me.admin_source}` : undefined} />
            {botInfo?.name && <Row icon="bot" label={copy.botName} value={botInfo.name} />}
          </Section>

          {botInfo && (
            <Section title={copy.botCapabilities}>
              <Row icon="result" label={copy.canJoinGroups}   value={botInfo.can_join_groups ? copy.yes : copy.no}           badgeTone={botInfo.can_join_groups ? 'ok' : ''} />
              <Row icon="result" label={copy.canReadAllGroups} value={botInfo.can_read_all_group_messages ? copy.yes : copy.no} badgeTone={botInfo.can_read_all_group_messages ? 'ok' : ''} />
              <Row icon="result" label={copy.supportsInline}  value={botInfo.supports_inline_queries ? copy.yes : copy.no}   badgeTone={botInfo.supports_inline_queries ? 'ok' : ''} />
            </Section>
          )}

          <Section title={copy.system}>
            <MenuRow icon="refresh" label={copy.recheckAuth} loading={loadingStatus || loadingOverview} disabled={!apiConfigured} onClick={() => { fetchStatus(); fetchOverview(); fetchBotRuntime(); }} />
          </Section>

          <Section title={copy.diagnostic}>
            <details className="details">
              <summary><Icon name="info" />{copy.showDetails}</summary>
              <pre className="details-pre">{[
                `${copy.telegramWebApp}: ${Boolean(tg())}`,
                `${copy.initDataPresent}: ${Boolean(initData())}`,
                `${copy.initDataLength}: ${initData().length}`,
                `${copy.userUnsafe}: ${Boolean(tgUser())}`,
                `${copy.apiConfigured}: ${apiConfigured}`,
                `${copy.apiBase}: ${getApiBase() || copy.notConfigured}`,
                `${copy.admin}: ${Boolean(me?.admin)}`,
                `${copy.role}: ${me?.role || '-'}`,
                `${copy.adminSource}: ${me?.admin_source || '-'}`,
                `${copy.appVersion}: ${sysStatus?.version || '-'}`,
              ].join('\n')}</pre>
            </details>
          </Section>
        </>
      )}

    </div>
  );
}
