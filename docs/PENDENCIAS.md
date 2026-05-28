# Pendências

> Última atualização: 28/05/2026  
> Apenas itens que requerem ação externa ao código.

---

## 🔧 Requer ação do mantenedor no servidor/painel

- **Backup do Supabase não está agendado**  
  O script `scripts/backup_supabase.sh` existe mas não foi configurado no servidor Oracle.  
  _Configurar `systemd timer` ou `cron` para execução periódica._

- **Log Scrubbing no Cloudflare**  
  O Worker chama a API do Telegram com o token na URL. Se o Cloudflare tiver logging habilitado, o token aparece nos logs.  
  _Painel Cloudflare → habilitar Log Scrubbing com padrão `bot[0-9]+:[A-Za-z0-9_-]+`._

- **Supabase CLI não está linkado ao projeto**  
  Migrations precisam ser aplicadas manualmente via SQL Editor.  
  _Rodar: `supabase link --project-ref uqtmwnjxrxiylstbezhy`_

---

## 🟡 Decisões pendentes do mantenedor

- **Deprecar `/card`**  
  `/sets` é funcionalmente superior (clique direto no nome, sem digitar número). `/card` existe mas é redundante.  
  _Decidir se remove ou mantém como alias._

- **initData sem proteção contra replay (24h)**  
  A mesma `initData` pode ser reutilizada dentro de 24h. Mitigação requer Cloudflare KV para nonce store.  
  _Decisão: implementar ou aceitar o risco dado o perfil de uso._
