# Pendências e Melhorias Futuras

> Última atualização: 28/05/2026  
> Itens marcados com 🔧 são do lado do **mantenedor/servidor** e não podem ser resolvidos só em código.

---

## 🔧 Requer ação do mantenedor

- **Backup do Supabase não está agendado**  
  O script `scripts/backup_supabase.sh` existe mas nunca foi configurado. Qualquer perda de dados no Supabase não tem recuperação automática.  
  _Configurar `systemd timer` ou `cron` no Oracle para executar periodicamente._

- **`TELEGRAM_BOT_TOKEN` exposto em URLs de log do Cloudflare**  
  A Telegram Bot API usa o token na URL. Se o Cloudflare tiver logging habilitado, o token fica visível nos logs.  
  _Verificar painel Cloudflare → habilitar Log Scrubbing com padrão `bot[0-9]+:[A-Za-z0-9_-]+`._

- **Supabase CLI não está linkado ao projeto**  
  `supabase/config.toml` não existe. Migrations precisam ser aplicadas manualmente via SQL Editor.  
  _Criar `supabase/config.toml` e rodar `supabase link --project-ref uqtmwnjxrxiylstbezhy`._

---

## 🟡 Pendências técnicas (implementáveis em código)

- **initData sem proteção contra replay (24h)**  
  A mesma `initData` pode ser reutilizada em qualquer momento dentro da janela de 24h.  
  _Implementar nonce store com TTL curto no Worker usando Cloudflare KV._

- **`arkham_decklists_cache` nunca é populada**  
  A tabela existe mas nenhum código a usa. `/decklist` sempre vai à API do ArkhamDB.  
  _Implementar cache da decklist na tabela após primeiro fetch, ou remover a tabela._

---

## 🟢 Decisões pendentes do mantenedor

- **`/card` vs `/sets`**  
  Os dois comandos são funcionalmente equivalentes. `/sets` é mais intuitivo (clique direto no nome); `/card` exige digitar número.  
  _Decidir se depreca `/card` ou mantém os dois._

- **`/faq` sem título da carta antes do texto**  
  O nome da carta só aparece na imagem, não no texto do FAQ.  
  _Decidir se adiciona `<b>{nome}</b>` como cabeçalho do texto._

---

## ✅ Concluído nesta sessão (referência)

| Item | Commit |
|---|---|
| Suporte a tópicos do Telegram (PEND-009) | `62aa106` |
| Remoção de wrappers Python (WRK-004) | `62aa106` |
| Scheduler: slot gravado antes de postar | `42fe9c3` |
| Fix: pré-mensagem duplicada da IA | `caf73a5` |
| Cache-on-demand para FAQ | `7698413` |
| UX/navegação Mini App (overhaul completo) | `c3b036b` |
| /decklist com imagem + lista agrupada | `f005b7e` |
| /sets e /card paginados | `5b2556e` |
| /faq com imagem reply + formatação HTML | `541b056` |
| /status redesenhado | `e506dbf` |
| /taboo paginado (5/página) | `c4e6fff` |
| Cache in-memory de cartas (10 min) + invalidação após sync | `5007975` |
| Alerta de falha diária para admins (i18n) | `b76f1b7` |
| Alerta de comandos failed para admins (i18n) | atual |
| download_image_async com retry | atual |
| Testes: faq_repo (8 casos) | atual |
| Testes: scheduler slot-claiming (4 casos) | atual |
| /status e /help com reply ao usuário | `c43d0df` |
| Descrição /decklist com indicador de truncamento | `c43d0df` |
| 20+ bugs corrigidos (callbacks, rate limiter, etc.) | vários |
