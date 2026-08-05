# Gravewright — Ajustes Finais Pós-Hardening

## 1. Contexto

Este documento consolida os ajustes finais identificados após a revisão do commit:

```text
0a35f87 — refactor(core): hardening
```

O commit corrigiu os principais problemas funcionais e estruturais levantados anteriormente, incluindo:

- reuso indevido de convites aceitos;
- restauração de membros removidos;
- auditoria sem identificação do autor;
- adoção de bancos legados;
- duplicação e vazamento de Request ID;
- inconsistência na descrição do job de Compose.

As pendências atuais estão concentradas no pipeline de CI e na consistência entre migrações, bootstrap de testes e smoke tests de banco.

---

# 2. Objetivo

Concluir o hardening técnico com:

1. CI totalmente verde;
2. migrações SQLite funcionando em banco vazio;
3. smoke tests PostgreSQL validando o schema real sem repará-lo;
4. `metadata.create_all()` restrito a bancos descartáveis;
5. cobertura de testes para impedir regressões futuras.

---

# 3. Ordem obrigatória de execução

Execute nesta ordem:

1. **Capturar e reproduzir as falhas reais do CI**
2. **Corrigir o upgrade SQLite em banco vazio**
3. **Corrigir os testes unitários e E2E**
4. **Corrigir o smoke test PostgreSQL**
5. **Restringir o bootstrap via metadata**
6. **Executar a validação final integrada**

Não iniciar a implementação de convite por código enquanto os jobs obrigatórios estiverem vermelhos.

---

# Etapa 1 — Reproduzir as falhas do CI

## 1.1 Problema

O pipeline associado ao commit `0a35f87` ainda apresenta falhas em:

```text
Unit + e2e
Schema audit (SQLite)
PostgreSQL (migrations + backend smoke)
```

Os jobs de lint e validação do Compose passam.

## 1.2 Resultado esperado

Cada falha deve ser reproduzida localmente com o mesmo comando, ambiente e dependências utilizados no GitHub Actions.

## 1.3 Arquivos-alvo

```text
.github/workflows/ci.yml
pyproject.toml
uv.lock
alembic.ini
tests/
app/persistence/
migrations/
```

## 1.4 Instruções para o agente de IA

1. Ler integralmente `.github/workflows/ci.yml`.
2. Mapear para cada job:
   - sistema operacional;
   - versão do Python;
   - extras instalados;
   - variáveis de ambiente;
   - serviços auxiliares;
   - comandos executados.
3. Reproduzir os comandos sem alterações.
4. Registrar o primeiro stack trace de cada job.
5. Corrigir a causa raiz antes de executar o job novamente.
6. Não mascarar falhas com:
   - `continue-on-error`;
   - `|| true`;
   - remoção de testes;
   - redução arbitrária da matriz;
   - alteração de asserts sem justificativa;
   - criação automática de schema dentro do teste.
7. Manter um registro por falha:

```text
Job:
Comando:
Primeiro erro:
Causa raiz:
Correção:
Teste de regressão:
```

## 1.5 Comandos-base

```bash
uv sync --frozen --extra dev --extra postgres

uv run ruff check .
uv run ruff format --check .

uv run pytest tests/unit -q -x
uv run pytest tests/e2e -q -x
```

Auditoria SQLite:

```bash
uv run python -m app.cli db upgrade
uv run python -m app.cli db status

uv run pytest \
  tests/unit/test_schema_alembic_parity.py \
  tests/unit/test_schema_legacy_upgrade.py \
  tests/unit/test_schema_startup.py \
  tests/unit/test_schema_metadata_parity.py \
  tests/unit/test_schema_migrations.py \
  tests/unit/test_enum_constraints.py \
  -q -x
```

PostgreSQL:

```bash
DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/gravewright_test" \
GRAVEWRIGHT_TEST_DATABASE_URLS="postgresql+psycopg://user:password@localhost:5432/gravewright_test" \
uv run pytest tests/integration -q -x
```

## 1.6 Critérios de aceite

- [ ] Cada job falho foi reproduzido localmente.
- [ ] O primeiro stack trace foi registrado.
- [ ] A causa raiz foi identificada.
- [ ] Nenhum erro foi mascarado.
- [ ] A correção possui teste de regressão.

---

# Etapa 2 — Corrigir o upgrade SQLite em banco vazio

## 2.1 Problema

O job de auditoria SQLite falha ao executar o upgrade em um banco vazio.

Isso indica que uma ou mais migrações não funcionam corretamente em um ambiente limpo.

## 2.2 Resultado esperado

O comando abaixo deve funcionar em um banco SQLite inexistente:

```bash
uv run python -m app.cli db upgrade
```

Após a execução:

- todas as tabelas devem existir;
- todas as constraints compatíveis com SQLite devem existir;
- todos os índices devem existir;
- `alembic_version` deve apontar para `head`;
- uma segunda execução deve ser idempotente.

## 2.3 Arquivos-alvo

```text
migrations/versions/
app/persistence/tables.py
app/persistence/schema.py
app/persistence/database.py
tests/unit/test_schema_migrations.py
tests/unit/test_schema_alembic_parity.py
tests/unit/test_enum_constraints.py
```

## 2.4 Instruções para o agente de IA

1. Criar um arquivo SQLite novo para cada execução.
2. Executar `alembic upgrade head`.
3. Capturar a primeira migração que falhar.
4. Verificar:
   - SQL incompatível com SQLite;
   - uso incorreto de `ALTER TABLE`;
   - criação duplicada de índice;
   - constraint não suportada;
   - ordem incorreta de criação de FK;
   - uso de valores booleanos específicos de outro banco;
   - dependência indevida do metadata atual;
   - migração que pressupõe tabela ou coluna já existente.
5. Corrigir a migração sem alterar migrações antigas já publicadas, salvo se o projeto ainda não tiver releases ou bancos externos dependentes.
6. Preferir criar uma nova migração corretiva quando houver possibilidade de bancos existentes.
7. Validar schema final contra `metadata`.
8. Executar upgrade duas vezes.
9. Executar downgrade apenas se o projeto suportar oficialmente downgrade seguro.

## 2.5 Testes obrigatórios

### Teste A — Banco inexistente

```text
Dado um caminho SQLite sem arquivo
Quando alembic upgrade head é executado
Então o banco é criado
E todas as migrações são aplicadas
```

### Teste B — Reexecução

```text
Dado um banco já no head
Quando alembic upgrade head é executado novamente
Então o comando termina sem alterações destrutivas
```

### Teste C — Paridade

```text
Dado um banco atualizado até head
Quando o schema é comparado com metadata
Então tabelas, colunas, índices, FKs e checks compatíveis são equivalentes
```

### Teste D — Dados básicos

```text
Dado o schema criado por Alembic
Quando registros mínimos são inseridos
Então operações CRUD básicas funcionam
```

## 2.6 Critérios de aceite

- [ ] Upgrade em banco SQLite vazio passa.
- [ ] `alembic_version` aponta para head.
- [ ] Reexecução é idempotente.
- [ ] Paridade de schema passa.
- [ ] Nenhum `metadata.create_all()` é necessário para completar o schema.
- [ ] O job `Schema audit (SQLite)` fica verde.

## 2.7 Commit sugerido

```text
fix(migrations): make sqlite clean upgrade deterministic
```

---

# Etapa 3 — Corrigir testes unitários e E2E

## 3.1 Problema

O job `Unit + e2e` ainda falha.

A causa exata deve ser determinada pelo primeiro stack trace reproduzido.

## 3.2 Resultado esperado

Todos os testes unitários e E2E devem passar em:

- execução isolada;
- execução completa;
- ordem aleatória, quando suportada;
- clone limpo;
- ambiente sem banco persistente anterior.

## 3.3 Arquivos-alvo

```text
tests/unit/
tests/e2e/
tests/conftest.py
app/
pyproject.toml
```

## 3.4 Instruções para o agente de IA

1. Executar testes com `-x` para capturar a primeira falha.
2. Corrigir a implementação quando o teste representar o contrato correto.
3. Corrigir o teste apenas quando ele estiver desatualizado em relação a uma decisão de domínio explícita.
4. Verificar possíveis causas:
   - fixture compartilhando banco;
   - estado global não resetado;
   - `ContextVar` não restaurado;
   - monkeypatch não removido;
   - ordem de testes;
   - dependência de timezone;
   - diferença entre SQLite em memória e arquivo;
   - evento realtime emitido duas vezes;
   - novo resultado `membership_removed` não tratado;
   - auditoria emitida em camada diferente;
   - alteração do contrato de Request ID.
5. Rodar o teste falho isoladamente.
6. Rodar o módulo completo.
7. Rodar toda a suíte.
8. Rodar pelo menos uma vez com ordem aleatória, se houver plugin disponível.
9. Não manter sleeps arbitrários para resolver concorrência.
10. Não depender de horário real em testes.

## 3.5 Testes de regressão mínimos

### Convites

```text
convite pendente
→ aceite
→ membership criado
→ evento publicado uma vez
```

```text
convite aceito
→ aceite repetido
→ sucesso idempotente
→ sem novo evento
```

```text
convite aceito
→ membro removido
→ aceite repetido
→ membership não recriado
```

### Auditoria

```text
GM bane membro
→ evento contém actor_id
→ evento contém target_user_id
→ evento contém campaign_id
→ evento contém request_id
```

### Request ID

```text
requisições concorrentes
→ IDs distintos
→ ausência de vazamento de contexto
```

### Banco

```text
cada teste
→ banco isolado
→ estado limpo
```

## 3.6 Critérios de aceite

- [ ] `tests/unit` passa integralmente.
- [ ] `tests/e2e` passa integralmente.
- [ ] Testes isolados e completos produzem o mesmo resultado.
- [ ] Não há dependência de ordem.
- [ ] Não há sleeps usados como correção.
- [ ] O job `Unit + e2e` fica verde.

## 3.7 Commit sugerido

```text
fix(tests): align unit and e2e suites with hardening behavior
```

---

# Etapa 4 — Corrigir o smoke test PostgreSQL

## 4.1 Problema

O smoke test PostgreSQL executa reparos de schema depois das migrações:

```python
metadata.create_all(conn, checkfirst=True)
```

e cria manualmente um índice:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_scenes_active_campaign
ON scenes (campaign_id)
WHERE active = 1
```

Isso invalida o objetivo do teste.

Caso a migração tenha esquecido uma tabela ou índice, o próprio teste pode corrigir o banco antes da validação.

## 4.2 Resultado esperado

O smoke test deve validar exclusivamente o schema produzido por:

```bash
alembic upgrade head
```

O teste não pode criar tabelas, colunas, constraints ou índices.

## 4.3 Arquivos-alvo

```text
tests/integration/test_database_backends.py
tests/integration/
migrations/versions/
app/persistence/tables.py
.github/workflows/ci.yml
```

## 4.4 Instruções para o agente de IA

1. Remover `metadata.create_all()` do smoke test PostgreSQL.
2. Remover criação manual de índices do teste.
3. Após `alembic upgrade head`, usar `inspect(engine)` para validar o schema.
4. Verificar explicitamente:
   - tabelas críticas;
   - colunas críticas;
   - índices críticos;
   - unique constraints;
   - FKs;
   - check constraints, quando expostas pelo driver.
5. Executar operações reais:
   - insert;
   - select;
   - update;
   - upsert;
   - delete;
   - rollback controlado.
6. Se um objeto estiver ausente, corrigir a migração, não o teste.
7. Garantir cleanup por transação ou banco dedicado.
8. Não reutilizar banco de desenvolvimento.

## 4.5 Estrutura recomendada

```python
def test_postgres_migrated_schema_supports_repository_operations(engine):
    inspector = inspect(engine)

    tables = set(inspector.get_table_names())

    assert "users" in tables
    assert "campaigns" in tables
    assert "campaign_members" in tables
    assert "campaign_invitations" in tables
    assert "session_store" in tables

    # Validar índices e constraints.
    # Executar operações reais sem criar ou reparar schema.
```

## 4.6 Testes obrigatórios

### Teste A — Schema integralmente migrado

```text
Dado PostgreSQL vazio
Quando alembic upgrade head é executado
Então todas as tabelas e índices esperados existem
```

### Teste B — Repository smoke

```text
Dado o schema migrado
Quando repositories executam operações básicas
Então inserts, upserts, selects e deletes funcionam
```

### Teste C — Ausência de reparo

```text
Dado um objeto propositalmente ausente em uma branch de teste
Quando o smoke é executado
Então o teste falha
E não recria o objeto
```

### Teste D — Idempotência do upsert

```text
Dado um registro existente
Quando o upsert é executado novamente
Então não há duplicação
E o estado final é consistente
```

## 4.7 Critérios de aceite

- [ ] O smoke test não usa `metadata.create_all()`.
- [ ] O smoke test não executa DDL corretivo.
- [ ] Objetos ausentes causam falha explícita.
- [ ] Operações reais de repository funcionam.
- [ ] O job PostgreSQL fica verde.

## 4.8 Commit sugerido

```text
fix(ci): stop repairing migrated schemas in backend smoke
```

---

# Etapa 5 — Restringir bootstrap via metadata

## 5.1 Problema

A função de seleção do bootstrap permite `metadata.create_all()` para bancos SQLite quando o ambiente é `test`.

Isso pode incluir arquivos SQLite persistentes configurados acidentalmente.

## 5.2 Resultado esperado

`metadata.create_all()` deve ser permitido somente para bancos explicitamente descartáveis.

## 5.3 Arquivos-alvo

```text
app/persistence/database.py
app/persistence/schema.py
app/config.py
tests/unit/test_schema_startup.py
tests/unit/test_database_bootstrap.py
```

## 5.4 Regra recomendada

```text
SQLite :memory:
  permitido

Arquivo dentro do diretório temporário da suíte:
  permitido apenas com flag explícita

Arquivo persistente:
  proibido

PostgreSQL:
  proibido
```

## 5.5 Instruções para o agente de IA

1. Localizar `_use_metadata_bootstrap()` ou função equivalente.
2. Remover a regra genérica baseada apenas em `app_env == "test"`.
3. Permitir automaticamente apenas:

```python
effective_sqlite_path() == ":memory:"
```

4. Caso testes precisem de arquivo temporário:
   - exigir flag explícita;
   - validar que o caminho está dentro de diretório temporário;
   - recusar caminhos do projeto, home ou storage persistente.
5. Adicionar mensagem de erro acionável:

```text
Persistent databases must be initialized with Alembic.
Use `grave db upgrade` or a disposable in-memory database for tests.
```

6. Garantir que produção nunca use metadata bootstrap.
7. Garantir que desenvolvimento persistente use Alembic.
8. Atualizar fixtures que dependiam do comportamento anterior.

## 5.6 Exemplo de implementação

```python
def _use_metadata_bootstrap() -> bool:
    if _backend() != "sqlite":
        return False

    path = effective_sqlite_path()

    if path == ":memory:":
        return True

    if not config.allow_metadata_bootstrap:
        return False

    return is_disposable_test_path(path)
```

## 5.7 Testes obrigatórios

### Teste A — SQLite em memória

```text
Dado SQLite :memory:
Quando o ambiente de teste inicia
Então metadata bootstrap é permitido
```

### Teste B — Arquivo persistente

```text
Dado um arquivo SQLite em storage
Quando o ambiente de teste inicia
Então metadata bootstrap é recusado
```

### Teste C — Temporário explícito

```text
Dado um arquivo em diretório temporário
E flag explícita habilitada
Quando o teste inicia
Então metadata bootstrap é permitido
```

### Teste D — PostgreSQL

```text
Dado PostgreSQL
Quando qualquer ambiente inicia
Então metadata bootstrap não é usado
```

### Teste E — Desenvolvimento

```text
Dado banco SQLite persistente de desenvolvimento
Quando a aplicação inicia
Então Alembic é usado
E alembic_version existe
```

## 5.8 Critérios de aceite

- [ ] `create_all()` não é usado em banco persistente.
- [ ] SQLite em memória continua suportado.
- [ ] Arquivos temporários exigem opt-in explícito.
- [ ] PostgreSQL nunca usa metadata bootstrap.
- [ ] Mensagens de erro orientam o operador.
- [ ] Testes existentes foram adaptados sem enfraquecer o contrato.

## 5.9 Commit sugerido

```text
fix(database): restrict metadata bootstrap to disposable databases
```

---

# Etapa 6 — Validação final integrada

## 6.1 Execução local obrigatória

```bash
uv sync --frozen --extra dev --extra postgres

uv run ruff check .
uv run ruff format --check .

uv run pytest tests/unit -q
uv run pytest tests/e2e -q
uv run pytest tests/integration -q
```

## 6.2 Validação SQLite

Usar banco novo:

```bash
rm -f /tmp/gravewright-final-check.sqlite3

DATABASE_URL="sqlite:////tmp/gravewright-final-check.sqlite3" \
uv run python -m app.cli db upgrade

DATABASE_URL="sqlite:////tmp/gravewright-final-check.sqlite3" \
uv run python -m app.cli db status
```

Executar novamente:

```bash
DATABASE_URL="sqlite:////tmp/gravewright-final-check.sqlite3" \
uv run python -m app.cli db upgrade
```

## 6.3 Validação PostgreSQL

```bash
DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/gravewright_test" \
uv run python -m app.cli db upgrade
```

```bash
DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/gravewright_test" \
GRAVEWRIGHT_TEST_DATABASE_URLS="postgresql+psycopg://user:password@localhost:5432/gravewright_test" \
uv run pytest tests/integration -q
```

## 6.4 Validação Compose

```bash
docker compose config
```

Executar também para todos os arquivos alternativos usados pelo CI.

## 6.5 Critérios de aceite

- [ ] Ruff passa.
- [ ] Formatação passa.
- [ ] Unit passa.
- [ ] E2E passa.
- [ ] Integration passa.
- [ ] SQLite vazio migra até head.
- [ ] PostgreSQL vazio migra até head.
- [ ] Reexecução de upgrade é idempotente.
- [ ] Smoke tests não criam schema.
- [ ] GitHub Actions fica integralmente verde.

---

# 4. Cenários de regressão obrigatórios

## 4.1 Convite antigo

```text
Criar convite
→ aceitar
→ remover membro
→ repetir aceite
→ membership não é recriado
```

## 4.2 Banco SQLite limpo

```text
Excluir banco
→ executar upgrade
→ iniciar aplicação
→ executar operação básica
```

## 4.3 Banco PostgreSQL limpo

```text
Criar banco vazio
→ executar upgrade
→ executar repository smoke
→ confirmar ausência de DDL no teste
```

## 4.4 Banco persistente em teste

```text
Configurar arquivo SQLite persistente
→ iniciar suíte
→ metadata bootstrap recusado
```

## 4.5 Banco em memória

```text
Configurar SQLite :memory:
→ iniciar suíte
→ metadata bootstrap permitido
```

---

# 5. Definition of Done

Os ajustes finais estarão concluídos quando:

- [ ] Os três jobs anteriormente falhos estiverem verdes.
- [ ] O upgrade SQLite funcionar em banco vazio.
- [ ] O smoke PostgreSQL validar, mas não reparar, o schema.
- [ ] O metadata bootstrap estiver restrito a bancos descartáveis.
- [ ] Nenhum teste depender de banco persistente anterior.
- [ ] Nenhum teste executar DDL para esconder falhas de migração.
- [ ] SQLite e PostgreSQL tiverem paridade de schema compatível.
- [ ] O GitHub Actions completo passar no commit final.
- [ ] A documentação de banco estiver atualizada.
- [ ] A feature de convite por código estiver liberada para início.

---

# 6. Sequência sugerida de commits

```text
fix(migrations): make sqlite clean upgrade deterministic
fix(tests): align unit and e2e suites with hardening behavior
fix(ci): stop repairing migrated schemas in backend smoke
fix(database): restrict metadata bootstrap to disposable databases
```

Caso a correção do CI exija alterações específicas adicionais:

```text
fix(ci): restore hardening pipeline
```

---

# 7. Restrição para o convite por código

A feature de convite por código só deve começar quando:

```text
Unit + e2e = verde
Schema audit SQLite = verde
PostgreSQL migrations + smoke = verde
```

O novo fluxo deve ser implementado sobre:

- migrações determinísticas;
- banco gerenciado por Alembic;
- membership idempotente;
- testes concorrentes;
- pipeline verde.

Não reutilizar nenhum caminho de teste ou runtime que dependa de `metadata.create_all()` para bancos persistentes.
