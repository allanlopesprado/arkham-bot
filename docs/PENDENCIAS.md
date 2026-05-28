# Pendências e Melhorias Futuras

> Última atualização: 28/05/2026  
> Itens ordenados por prioridade dentro de cada categoria.

---

## 🔴 Alta Prioridade

### Infraestrutura

- **Backup do Supabase não está agendado**  
  O script `scripts/backup_supabase.sh` existe mas nunca foi configurado como cron ou timer systemd no servidor Oracle. Qualquer perda de dados no Supabase não tem recuperação automática.  
  _Ação: configurar `systemd timer` ou `cron` no Oracle para executar o script periodicamente._

- **Comandos `failed` no Supabase não geram notificação**  
  Quando um comando da fila (`post_now`, `sync_arkhamdb`, etc.) atinge o limite de tentativas e vai para `failed`, nenhum admin é alertado. O problema só é descoberto ao verificar o Mini App ou o banco.  
  _Ação: adicionar lógica em `command_worker.py` para notificar admins via Telegram quando um comando vai para `failed`._

---

## 🟡 Média Prioridade

### Funcionalidades

- **`download_image_async` sem retry**  
  A função síncrona `download_image_sync` tem o decorator `@network_retry_sync` com backoff exponencial. A versão assíncrona `download_image_async` não tem — uma falha de rede transiente durante postagem agendada faz a carta não ser enviada sem nova tentativa.  
  _Ação: adicionar retry assíncrono (ex: `tenacity.AsyncRetrying`) em `download_image_async`._

- **Cache do `/decklist` não invalida após sync**  
  O cache in-memory de cartas (`_cards_cache`) tem TTL de 10 minutos. Após um `sync_arkhamdb` que atualiza cartas, o cache pode servir dados stale até expirar.  
  _Ação: invalidar `_cards_cache` e `_cards_encounter_cache` quando sync completa com sucesso no `command_worker.py`._

- **`/cotd` não tem reply à mensagem do usuário**  
  `/faq`, `/card`, `/sets` e `/decklist` fazem reply à mensagem original. `/cotd` não segue esse padrão.  
  _Ação: adicionar `reply_parameters=ReplyParameters(message_id=update.message.message_id)` em `cotd_command`._

- **`/status` e `/help` não fazem reply**  
  Inconsistência com os demais comandos que fazem reply ao usuário.  
  _Ação: adicionar `reply_parameters` em `status_command` e `start_command`._

### Segurança

- **`TELEGRAM_BOT_TOKEN` exposto em URLs de log do Cloudflare**  
  A Telegram Bot API usa o token na URL (`/bot{TOKEN}/sendMessage`). Se o Cloudflare tiver logging de requests habilitado, o token fica exposto nos logs.  
  _Ação: verificar configurações de log no painel Cloudflare e habilitar Log Scrubbing para mascarar o padrão `bot[0-9]+:[A-Za-z0-9_-]+` nas URLs._

- **initData não tem proteção contra replay dentro da janela de 24h**  
  A mesma `initData` pode ser reutilizada durante 24h. Um atacante que interceptar uma requisição pode repeti-la.  
  _Ação (opcional/avançado): implementar nonce store com TTL curto (ex: 5 min) no Worker usando Cloudflare KV para marcar initData já usadas._

---

## 🟢 Baixa Prioridade

### Cobertura de Testes

- **`faq_repo.py` sem testes**  
  As funções `get_cached_faq_codes()`, `upsert_faq()` e `get_faq_by_code()` não têm cobertura de testes unitários.

- **Scheduler: slot-claiming sem teste dedicado**  
  A lógica de `posted_slots` (anti-duplicata em restart) é crítica mas não tem teste unitário isolado. `test_scheduler_logic.py` cobre parte, mas não o cenário de restart mid-post.

- **Multi-destino sem teste de falha parcial**  
  Se o primeiro destino postar com sucesso mas o segundo falhar, o comportamento não está testado. O código continua em loop mas pode deixar histórico inconsistente.

### Melhorias de UX

- **`/card` e `/sets` são funcionalmente equivalentes**  
  `/card` exige digitar o número da carta; `/sets` permite clicar diretamente no nome. Considerar deprecar `/card` em favor de `/sets` ou transformar `/card` em alias.  
  _Decisão pendente do mantenedor._

- **Descrição longa no `/decklist` truncada em 300 caracteres**  
  Decks com descrições longas são cortados. Não há indicação visual de que o texto foi truncado.  
  _Ação: adicionar `…` ao final se truncado._

- **`/faq` sem título da carta acima do FAQ**  
  O FAQ exibe o texto da regra mas não mostra o nome da carta em destaque antes do texto. O título fica apenas no topo da imagem.  
  _Ação (opcional): adicionar `<b>Carta: {nome}</b>` como primeira linha do texto do FAQ._

### Manutenção

- **Worker versão manual**  
  `APP_VERSION` em `worker/src/index.js` é atualizado manualmente. Inconsistência entre código e versão declarada pode ocorrer.  
  _Ação: automatizar leitura da versão a partir de `package.json` ou git tag._

- **Supabase CLI não está linkado ao projeto**  
  `supabase/config.toml` não existe. Migrations precisam ser aplicadas manualmente via SQL Editor. Não há como usar `supabase db push` ou diff.  
  _Ação: criar `supabase/config.toml` com `project_id` e linkar via `supabase link`._

- **`arkham_decklists_cache` nunca é populada**  
  A tabela existe no schema mas nenhum código a lê ou escreve. O `/decklist` sempre busca da API do ArkhamDB.  
  _Ação: implementar cache de decklists na tabela, ou remover a tabela do schema se não for usar._

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
| Cache in-memory de cartas (10 min) | `5007975` |
| Alerta de falha diária para admins | `b76f1b7` |
| 15+ bugs corrigidos (callbacks, rate limiter, etc.) | vários |
