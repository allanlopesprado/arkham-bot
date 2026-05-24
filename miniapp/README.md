# Arkham Bot Mini App

Scaffold inicial para React + Vite + Cloudflare Pages.

Regras:
- Nunca usar SUPABASE_SERVICE_ROLE_KEY no frontend.
- Usar anon/publishable key + RLS.
- Ações críticas devem inserir registros em `bot_commands`.
- Validar Telegram initData server-side antes de ações sensíveis.
