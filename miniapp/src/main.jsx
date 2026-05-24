import React, { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createClient } from '@supabase/supabase-js';
import './style.css';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
const commandsApiUrl = import.meta.env.VITE_COMMANDS_API_URL;

function getTelegramInitData() {
  return window.Telegram?.WebApp?.initData || '';
}

function App() {
  const [status, setStatus] = useState('Ready');
  const [cardCode, setCardCode] = useState('01001');
  const [referenceCards, setReferenceCards] = useState([]);
  const supabase = useMemo(() => {
    if (!supabaseUrl || !supabaseAnonKey) return null;
    return createClient(supabaseUrl, supabaseAnonKey);
  }, []);

  async function loadReferenceCards() {
    if (!supabase) {
      setStatus('Supabase env vars are not configured in the frontend.');
      return;
    }
    const { data, error } = await supabase
      .from('arkham_cards')
      .select('code,name,type_code,faction_code,pack_code')
      .order('name')
      .limit(10);
    if (error) {
      setStatus(`Card reference load failed: ${error.message}`);
      return;
    }
    setReferenceCards(data || []);
    setStatus('Public card reference loaded.');
  }

  async function enqueue(command_type, payload = {}) {
    if (!commandsApiUrl) {
      setStatus('VITE_COMMANDS_API_URL is not configured. Use the Worker for critical commands.');
      return;
    }
    const resp = await fetch(commandsApiUrl, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-telegram-init-data': getTelegramInitData(),
      },
      body: JSON.stringify({ command_type, payload }),
    });
    const json = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      setStatus(`Command failed: ${json.error || resp.status}`);
      return;
    }
    setStatus(`Command queued: ${command_type}`);
  }

  return (
    <main className="app">
      <header className="hero">
        <p className="eyebrow">Arkham Horror LCG</p>
        <h1>Arkham Bot Admin</h1>
        <p>Mini App administrativo. O frontend usa apenas anon key. Ações críticas passam pelo Worker e entram em <code>bot_commands</code>.</p>
      </header>

      <section className="card">
        <h2>Status</h2>
        <p>{status}</p>
        <button onClick={loadReferenceCards}>Carregar cartas públicas</button>
      </section>

      <section className="grid">
        <div className="card">
          <h2>Comandos</h2>
          <label>
            Card code
            <input value={cardCode} onChange={(e) => setCardCode(e.target.value)} />
          </label>
          <div className="actions">
            <button onClick={() => enqueue('post_now', { card_code: cardCode })}>Postar agora</button>
            <button onClick={() => enqueue('skip_card', { card_code: cardCode })}>Pular carta</button>
            <button onClick={() => enqueue('pause_daily_post')}>Pausar diário</button>
            <button onClick={() => enqueue('resume_daily_post')}>Retomar diário</button>
            <button onClick={() => enqueue('sync_arkhamdb', { sync_faq: false })}>Sync ArkhamDB</button>
          </div>
        </div>

        <div className="card">
          <h2>Cartas públicas</h2>
          {referenceCards.length === 0 ? <p>Nenhuma carta carregada.</p> : (
            <ul>
              {referenceCards.map((item) => (
                <li key={item.code}><strong>{item.name}</strong>: <code>{item.code}</code></li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
