# Segurança

## Reportar uma Vulnerabilidade

Se você encontrou uma vulnerabilidade de segurança neste projeto, entre em contato diretamente pelo Telegram ou e-mail antes de divulgar publicamente.

Não abra issues públicas para relatar problemas de segurança.

## Boas Práticas do Projeto

- O arquivo `.env` nunca deve ser commitado — contém tokens e chaves reais.
- `SUPABASE_SERVICE_ROLE_KEY` é usado apenas no backend Python e no Cloudflare Worker — nunca no frontend.
- O Mini App não recebe nenhum secret — toda autenticação passa pelo Worker.
- O Worker valida o `initData` do Telegram antes de aceitar qualquer comando.
- Logs mascaram tokens conhecidos (`TELEGRAM_BOT_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`).
- Deploy de produção ocorre apenas via workflow ou ação manual explícita — nunca direto na Oracle.
