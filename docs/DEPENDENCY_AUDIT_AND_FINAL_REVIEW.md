# DEPENDENCY AUDIT AND FINAL PROJECT REVIEW — ARKHAM BOT

Arquivo operacional para IA do VSCode/Cline/Copilot.

Este documento deve ser lido integralmente antes de qualquer nova alteração no projeto.

Local recomendado:

```txt
docs/DEPENDENCY_AUDIT_AND_FINAL_REVIEW.md
```

Objetivo: executar uma revisão extremamente rigorosa de dependências, empacotamento, testes, execução local, Supabase, Telegram, ArkhamDB, scheduler, comandos, IA, Mini App, Worker, systemd, GitHub Actions, backups e segurança. Este documento não é um resumo. Ele é um checklist técnico de auditoria final.

---

## 0. REGRA ABSOLUTA PARA A IA

A IA deve obedecer a estas regras:

```txt
1. Ler este arquivo inteiro antes de alterar qualquer coisa.
2. Ler também docs/ARKHAM_BOT_EXECUTION_PLAN.md e docs/FIX_BOT.md.
3. Não executar mudanças fora do escopo pedido pelo usuário.
4. Não esconder falhas.
5. Não transformar erro real em warning apenas para passar teste.
6. Não chamar serviços reais sem autorização explícita.
7. Não expor secrets.
8. Não remover validações para simplificar teste.
9. Não fazer refatoração ampla sem necessidade.
10. Não alterar comportamento público do bot sem motivo e registro.
11. Não aplicar migration no Supabase remoto sem autorização explícita.
12. Não publicar Cloudflare Worker/Pages sem autorização explícita.
13. Não instalar systemd sem autorização explícita.
14. Não rodar bot real em Telegram sem confirmação explícita do usuário.
```

Se alguma validação não puder ser feita porque faltam credenciais, a IA deve marcar como:

```txt
BLOQUEADO POR AMBIENTE REAL
```

Não marcar como concluído.

---

## 1. CONTEXTO DO BUG MAIS RECENTE

No Windows, o teste do scheduler falhou com:

```txt
ZoneInfoNotFoundError: 'No time zone found with key America/Sao_Paulo'
ModuleNotFoundError: No module named 'tzdata'
```

Causa: o módulo Python `zoneinfo` depende de uma base IANA de timezones. Em muitos ambientes Windows, essa base não está disponível no sistema operacional. A solução correta para compatibilidade cross-platform é declarar `tzdata` como dependência Python.

Referência oficial:

```txt
https://docs.python.org/3/library/zoneinfo.html
https://pypi.org/project/tzdata/
```

Correção aplicada neste pacote:

```txt
requirements.txt: adicionada dependência tzdata
pyproject.toml: adicionada dependência tzdata
requirements-dev.txt: mantém pytest como dependência de desenvolvimento
```

Decisão de engenharia:

```txt
pytest deve ser dependência de desenvolvimento.
tzdata deve ser dependência de runtime, pois o scheduler usa America/Sao_Paulo em runtime.
```

---

## 2. ESTADO ESPERADO DAS DEPENDÊNCIAS

## 2.1 requirements.txt

O arquivo `requirements.txt` deve conter dependências de runtime:

```txt
python-telegram-bot
requests
python-dotenv
pillow
filelock
httpx
tenacity
tzdata
```

Regras:

```txt
- `tzdata` deve permanecer em runtime.
- `pytest` não deve ficar em runtime, salvo decisão explícita de simplificar ambiente.
- Não fixar versões sem estratégia de atualização, salvo em ambiente de produção controlado.
- Se fixar versões no futuro, criar lock separado ou constraints.txt.
```

## 2.2 requirements-dev.txt

O arquivo `requirements-dev.txt` deve conter:

```txt
-r requirements.txt
pytest
```

Futuras dependências de desenvolvimento possíveis, mas não obrigatórias agora:

```txt
ruff
mypy
pytest-asyncio
coverage
types-requests
```

Não adicionar agora sem necessidade.

## 2.3 pyproject.toml

`pyproject.toml` deve declarar runtime dependencies coerentes com `requirements.txt`.

Obrigatório:

```txt
[project]
dependencies inclui tzdata.
```

Desejável:

```txt
[project.optional-dependencies]
dev = ["pytest"]
```

Critério de aceite:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Tudo deve instalar sem erro.

---

## 3. COMANDOS OBRIGATÓRIOS DE VALIDAÇÃO LOCAL

Executar no Windows PowerShell dentro do venv:

```powershell
cd C:\Users\allan\Desktop\arkham-bot
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m compileall -q .
python -m pytest -q
python main.py --help
python main.py healthcheck
python main.py healthcheck --strict
python -c "from zoneinfo import ZoneInfo; print(ZoneInfo('America/Sao_Paulo'))"
```

Resultado esperado sem `.env` real:

```txt
python -m compileall -q .     -> exit code 0
python -m pytest -q           -> todos os testes passam
python main.py --help         -> exit code 0
python main.py healthcheck    -> exit code 0 com WARNINGs
python main.py healthcheck --strict -> exit code != 0 com ERRORs
ZoneInfo('America/Sao_Paulo') -> deve funcionar
```

Se `healthcheck --strict` passar sem `.env`, está errado.

Se `ZoneInfo('America/Sao_Paulo')` falhar no Windows, `tzdata` não está instalado ou não foi declarado corretamente.

---

## 4. PROIBIÇÕES DURANTE A REVISÃO

Não fazer:

```txt
- Não remover o teste de timezone para “passar”.
- Não trocar America/Sao_Paulo por timezone local do Windows.
- Não transformar scheduler em naive datetime.
- Não remover ZoneInfo.
- Não colocar timezone fixo -03:00 como substituto.
- Não remover healthcheck strict.
- Não colocar secrets fake como padrão.
- Não chamar Telegram real sem autorização.
- Não chamar Supabase real sem autorização.
- Não publicar Cloudflare sem autorização.
- Não aplicar migrations remotas sem autorização.
```

---

## 5. CHECKLIST DE DEPENDÊNCIAS POR MÓDULO

A IA deve validar import por import.

## 5.1 Telegram

Arquivos prováveis:

```txt
main.py
src/arkham_bot/telegram_handlers.py
src/arkham_bot/daily_card.py
scripts/healthcheck.py
```

Dependência:

```txt
python-telegram-bot
```

Validar:

```txt
- ApplicationBuilder importado corretamente.
- Bot usado no healthcheck.
- RetryAfter tratado onde aplicável.
- ParseMode compatível com v22.7.
- Handlers compatíveis com python-telegram-bot v22.7.
```

## 5.2 HTTP ArkhamDB

Arquivos:

```txt
src/arkham_bot/arkhamdb_client.py
```

Dependências:

```txt
requests
httpx
tenacity
```

Validar:

```txt
- requests usado com timeout real.
- httpx usado com timeout real.
- retry não cria loop infinito.
- response.json() da ArkhamDB fica centralizado no client.
- Nenhum handler chama requests/httpx direto para ArkhamDB.
```

## 5.3 Timezone

Arquivos:

```txt
src/arkham_bot/scheduler.py
tests/test_scheduler_logic.py
```

Dependência:

```txt
tzdata
```

Validar:

```txt
- ZoneInfo("America/Sao_Paulo") funciona no Windows.
- Scheduler usa timezone aware datetime.
- Não usa datetime naive para decisão de postagem.
- Janela de postagem não duplica por data/hora.
```

## 5.4 Dotenv/config

Arquivos:

```txt
src/arkham_bot/config.py
scripts/healthcheck.py
```

Dependência:

```txt
python-dotenv
```

Validar:

```txt
- .env é carregado corretamente.
- .env.example não contém secrets reais.
- Variáveis obrigatórias em strict são validadas.
- Variáveis opcionais não quebram import.
```

## 5.5 Imagem

Arquivos:

```txt
src/arkham_bot/daily_card.py
src/arkham_bot/arkhamdb_client.py
```

Dependência:

```txt
pillow
```

Validar:

```txt
- Pillow só é usado onde necessário.
- Falha de imagem não derruba bot inteiro sem log.
- Arquivos temporários de imagem são removidos.
```

## 5.6 Locks

Arquivos:

```txt
main.py
src/arkham_bot/local_storage.py
```

Dependência:

```txt
filelock
```

Validar:

```txt
- Lock impede múltiplos bots interativos.
- Lock de cache/postados protege escrita concorrente.
- Timeout de lock não cria deadlock permanente.
```

## 5.7 Testes

Arquivos:

```txt
tests/
requirements-dev.txt
```

Dependência:

```txt
pytest
```

Validar:

```txt
- python -m pytest -q executa testes.
- Não usar comando `pytest -q` como obrigatório no Windows.
- Testes não dependem de rede real.
- Testes não dependem de secrets.
- Testes não chamam Telegram real.
- Testes não chamam Supabase real.
```

---

## 6. AUDITORIA DE ARQUIVOS CRÍTICOS

## 6.1 `main.py`

Validar:

```txt
[ ] --help funciona.
[ ] healthcheck repassa argumentos como --strict.
[ ] modo interactive não executa postagem única antes de subir bot.
[ ] modo card_code específico funciona.
[ ] modo sem argumento mantém postagem única.
[ ] bootstrap_check não exige Telegram quando healthcheck é chamado.
[ ] locks são usados corretamente.
[ ] não imprime secrets.
```

Comandos:

```bash
python main.py --help
python main.py healthcheck
python main.py healthcheck --strict
```

## 6.2 `scripts/healthcheck.py`

Validar:

```txt
[ ] strict falha se TELEGRAM_BOT_TOKEN faltar.
[ ] strict falha se TELEGRAM_CHAT_ID faltar.
[ ] strict falha se SUPABASE_URL faltar.
[ ] strict falha se SUPABASE_SERVICE_ROLE_KEY faltar.
[ ] modo não strict permite ausência com warning.
[ ] não imprime valores de secrets.
[ ] Telegram getMe só roda quando token existe.
[ ] Supabase check só roda quando URL/key existem.
```

## 6.3 `src/arkham_bot/config.py`

Validar:

```txt
[ ] Carrega .env.
[ ] Define DATA_DIR.
[ ] Define LOG_DIR.
[ ] Define timezone America/Sao_Paulo.
[ ] Define paths operacionais fora da raiz.
[ ] Não tem secrets hardcoded.
[ ] SUPABASE_ENABLED depende de URL + service role.
[ ] TELEGRAM env vars aceitam string vazia sem quebrar import.
```

## 6.4 `src/arkham_bot/scheduler.py`

Validar:

```txt
[ ] Usa ZoneInfo("America/Sao_Paulo").
[ ] Funciona no Windows com tzdata.
[ ] `_is_due` impede duplicidade diária.
[ ] Não cria múltiplas tasks duplicadas.
[ ] Não bloqueia polling Telegram.
[ ] Captura exceções da postagem diária sem derrubar bot.
[ ] Lê settings Supabase se disponível, mas faz fallback local.
[ ] Não requer Supabase para rodar.
```

## 6.5 `src/arkham_bot/daily_card.py`

Validar:

```txt
[ ] Não contém sys.exit dentro de função usada pelo scheduler.
[ ] Retorna DailyPostResult ou resultado estruturado.
[ ] Erros são logados.
[ ] pin falha sem derrubar bot.
[ ] unpin falha sem derrubar bot.
[ ] imagem é baixada com timeout.
[ ] fallback de carta funciona.
[ ] IA opcional não bloqueia postagem se falhar.
[ ] não publica spoiler proibido se filtro estiver ativo.
```

## 6.6 `src/arkham_bot/arkhamdb_client.py`

Validar:

```txt
[ ] Centraliza ArkhamDB HTTP.
[ ] Usa timeout real.
[ ] Usa validators.
[ ] Não implementa OAuth.
[ ] Não implementa Collection/Deck autenticado.
[ ] Decklist pública separada de Deck autenticado.
[ ] Cards, Packs, Factions, FAQ, Taboos cobertos.
[ ] response.json() tratado com erro claro.
```

## 6.7 `src/arkham_bot/arkhamdb_models.py`

Validar:

```txt
[ ] validate_card_payload exige campos críticos.
[ ] validate_cards_payload valida lista e item indexado.
[ ] validate_pack_payload exige code/name.
[ ] validate_faction_payload exige code/name.
[ ] validate_faq_payload é tolerante sem aceitar HTML/string.
[ ] validate_taboos_payload rejeita primitivos.
[ ] validate_decklist_payload é flexível, mas segura.
```

## 6.8 `src/arkham_bot/repositories/*`

Validar:

```txt
[ ] Nenhum repository chama Telegram.
[ ] Nenhum repository chama ArkhamDB diretamente.
[ ] Todos usam supabase_client.
[ ] commands_repo não sobrescreve payload com result.
[ ] commands_repo usa status permitido.
[ ] commands_repo suporta retrying/failed/cancelled.
[ ] Repositories não imprimem service role.
```

## 6.9 `src/arkham_bot/bot_commands_worker.py`

Validar:

```txt
[ ] Não usa eval/exec.
[ ] Valida command_type.
[ ] Valida admin/permissão antes de ação crítica.
[ ] Não executa payload arbitrário.
[ ] Usa retry com limite.
[ ] Marca failed com erro claro.
[ ] Audita execução.
[ ] Não bloqueia polling Telegram.
```

## 6.10 `src/arkham_bot/telegram_handlers.py`

Validar:

```txt
[ ] /start funciona.
[ ] /status funciona.
[ ] /card funciona.
[ ] /cancel funciona.
[ ] /help e /menu funcionam se implementados.
[ ] comandos extras não quebram handlers antigos.
[ ] callbacks inline funcionam.
[ ] rate limit é aplicado aos públicos.
[ ] admin bypass é seguro.
[ ] busca privada não quebra se usuário nunca abriu privado.
```

## 6.11 `miniapp/`

Validar sem publicar:

```txt
[ ] package.json existe.
[ ] build script existe.
[ ] usa Supabase anon/publishable key, não service role.
[ ] usa Worker para ação sensível se aplicável.
[ ] não hardcoda secrets.
[ ] documenta env vars.
[ ] não confia em initDataUnsafe para ação crítica.
```

## 6.12 `worker/`

Validar sem publicar:

```txt
[ ] wrangler.toml.example não contém secrets.
[ ] Worker valida input.
[ ] Worker não expõe service role no frontend.
[ ] CORS mínimo e controlado.
[ ] Telegram initData validation planejada/implementada.
[ ] Falhas retornam status HTTP adequado.
```

## 6.13 `supabase/migrations/`

Validar:

```txt
[ ] Migration 001 cria tabelas base.
[ ] Migration 002 cria policies seguras, se existir.
[ ] RLS habilitado.
[ ] Sem policy `true` para escrita crítica.
[ ] bot_commands tem status CHECK.
[ ] bot_admins role CHECK.
[ ] audit_logs source CHECK.
[ ] bot_commands tem result jsonb.
[ ] next_attempt_at existe se retry usa esse campo.
[ ] indexes existem para status/created_at/code.
```

## 6.14 `.github/workflows/deploy.yml`

Validar:

```txt
[ ] Instala requirements-dev para rodar tests.
[ ] Roda compileall.
[ ] Roda pytest.
[ ] Não usa secrets do app indevidamente.
[ ] Deploy SSH só após testes.
[ ] Healthcheck antes/depois do restart.
[ ] Rollback básico documentado.
```

## 6.15 `deploy/systemd/arkham-bot.service`

Validar:

```txt
[ ] WorkingDirectory correto para Oracle.
[ ] ExecStart usa venv Python.
[ ] EnvironmentFile aponta para .env na Oracle.
[ ] Restart=always.
[ ] RestartSec adequado.
[ ] Não roda em diretório errado.
```

---

## 7. AUDITORIA DE SEGURANÇA

Validar:

```txt
[ ] Nenhum secret em .env.example.
[ ] Nenhum secret em docs.
[ ] Nenhum secret em GitHub Actions.
[ ] Nenhum service_role no miniapp.
[ ] Nenhum token Telegram em código.
[ ] Nenhum OpenAI key em código.
[ ] Nenhum log imprime secrets.
[ ] Supabase service role usado apenas no backend.
[ ] RLS não libera escrita crítica anônima.
[ ] bot_commands exige validação de admin.
[ ] OAuth ArkhamDB não implementado sem storage seguro.
```

Comandos sugeridos:

```bash
grep -R "TELEGRAM_BOT_TOKEN\|SUPABASE_SERVICE_ROLE_KEY\|OPENAI_API_KEY\|ARKHAMDB_OAUTH_CLIENT_SECRET" -n . --exclude-dir=venv --exclude-dir=.git
```

Atenção: encontrar nomes de variáveis é aceitável. Encontrar valores reais não é aceitável.

---

## 8. AUDITORIA DE ARTEFATOS

Antes de zip/commit:

```bash
find . -type d -name "__pycache__"
find . -type f -name "*.pyc"
find . -type f -name "*.log"
find . -type d -name ".pytest_cache"
find . -type d -name "debug_logs"
```

Resultado esperado:

```txt
Sem saída, exceto se a IA explicar artefato intencional não versionado.
```

Limpeza:

```bash
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
rm -rf .pytest_cache debug_logs
rm -f *.log
```

---

## 9. AUDITORIA DE TESTES

Obrigatório:

```bash
python -m compileall -q .
python -m pytest -q
```

Critérios:

```txt
[ ] Testes passam no Windows.
[ ] Testes passam no Linux.
[ ] Testes não usam rede real.
[ ] Testes não dependem de .env real.
[ ] Testes cobrem healthcheck strict.
[ ] Testes cobrem scheduler com America/Sao_Paulo.
[ ] Testes cobrem validators ArkhamDB.
[ ] Testes cobrem commands_repo result vs payload.
[ ] Testes cobrem rate limiter.
[ ] Testes cobrem formatters.
```

Se um teste só passa em Linux, corrigir. Se um teste só passa no Windows, corrigir.

---

## 10. AUDITORIA DE FUNCIONALIDADE REAL — SOMENTE COM AUTORIZAÇÃO

Estes testes exigem `.env` real e serviços reais. Não executar sem autorização explícita.

## 10.1 Telegram real

```bash
python main.py healthcheck --strict
python main.py interactive
```

Validar:

```txt
/start
/status
/help
/menu
/card
/random
/search
/today
/faq
/taboo
/decklist
/admin_status
```

Validar pin/unpin:

```txt
- bot tem permissão admin.
- nova carta fixa.
- anterior desafixa.
- falha de pin não derruba bot.
```

## 10.2 Supabase real

Validar:

```txt
- migrations aplicadas.
- tabelas existem.
- RLS habilitado.
- service_role backend funciona.
- anon key não escreve em tabelas críticas.
- sync ArkhamDB popula cards/packs/factions/taboos.
- bot_commands pending -> processing -> executed/failed.
```

## 10.3 Cloudflare

Validar:

```txt
- Mini App builda.
- Cloudflare Pages publica.
- Worker publica.
- Secrets ficam em Cloudflare, não no repo.
- initData validação server-side antes de ações críticas.
```

## 10.4 Oracle/systemd

Validar:

```txt
- venv criado.
- .env real criado na Oracle.
- service instalado.
- systemctl start/status funciona.
- journalctl mostra logs.
- restart automático funciona.
```

---

## 11. RESULTADO ESPERADO DA IA APÓS REVISÃO

Responder exatamente:

```txt
RESULTADO:
- Revisão executada: Dependency Audit and Final Project Review
- Dependências validadas:
- Dependências corrigidas:
- Arquivos revisados:
- Testes locais executados:
- Testes externos não executados:
- Bloqueios por ambiente real:
- Riscos encontrados:
- Correções aplicadas:
- Pendências restantes:
- Status: aprovado / aprovado com ressalvas / bloqueado
```

Se houver qualquer erro não corrigido:

```txt
ERRO:
- Revisão executada: Dependency Audit and Final Project Review
- Erro encontrado:
- Arquivo/linha provável:
- Impacto:
- Correção recomendada:
- Status: bloqueado
```

---

## 12. PROMPT DIRETO PARA A IA

Copiar e colar:

```txt
Leia integralmente:

docs/ARKHAM_BOT_EXECUTION_PLAN.md
docs/FIX_BOT.md
docs/DEPENDENCY_AUDIT_AND_FINAL_REVIEW.md

Execute somente:

Dependency Audit and Final Project Review

Objetivo:
Revisar cada detalhe do projeto, com foco em dependências, compatibilidade Windows/Linux, testes, timezone, scheduler, Supabase, Telegram, ArkhamDB, IA, Mini App, Worker, GitHub Actions, systemd, backups, segurança e artefatos.

Obrigatório:
1. Confirmar que tzdata está em requirements.txt e pyproject.toml.
2. Confirmar que pytest está em requirements-dev.txt ou dev optional dependencies.
3. Confirmar que python -m pytest -q passa.
4. Confirmar que ZoneInfo("America/Sao_Paulo") funciona.
5. Confirmar que healthcheck strict falha sem env real.
6. Confirmar que nenhum teste chama rede real.
7. Confirmar que nenhum secret está hardcoded.
8. Confirmar que migrations não têm policy aberta perigosa.
9. Confirmar que bot_commands não sobrescreve payload com result.
10. Confirmar que daily_card não usa sys.exit em fluxo do scheduler.
11. Confirmar que scheduler não duplica postagem diária.
12. Confirmar que Mini App não contém service role.
13. Confirmar que Worker não contém secrets reais.
14. Confirmar que systemd/GitHub Actions são templates seguros.
15. Confirmar que __pycache__, *.pyc, *.log e .pytest_cache não estão no pacote final.

Proibido:
- Não chamar Telegram real.
- Não chamar Supabase real.
- Não publicar Cloudflare.
- Não aplicar migrations remotas.
- Não alterar comportamento público sem documentar.
- Não esconder falhas.

Ao finalizar, responder no formato RESULTADO definido no documento.
```
