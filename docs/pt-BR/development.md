# Desenvolvimento

[Documentação](../README.pt-BR.md) · [English](../en/development.md)

## Encontre a camada responsável

Leia a [arquitetura](architecture.md) e o [mapa do código](code-map.md) antes de alterar fluxos entre domínios. Os arquivos `services.py` concentram autorização, validação e persistência. Views traduzem requisições/respostas HTTP; consumers WebSocket traduzem mensagens recebidas, enquanto o despacho em tempo real publica alterações confirmadas. Mantenha regras nos serviços para que entradas Python e do navegador compartilhem as verificações.

Use a [API](api.md) pública ao integrar com o núcleo. Um contexto Python identifica o chamador, mas não concede autorização. Escritas diretas no ORM servem para migrações/fixtures controladas; no fluxo normal podem ignorar permissões, revisões, limpeza de arquivos e notificações dos serviços.

Em mutações, confira as convenções de transação, ID de requisição e versão esperada. Preserve o comportamento de repetição e publique estado confirmado. Snapshots para jogadores e transmissão devem excluir dados ocultos no servidor, sem depender apenas de escondê-los no DOM.

## Fluxo comum

```bash
uv sync --locked
uv run --locked python main.py
```

Edite o serviço responsável e suas views/templates/frontend conforme necessário. Crie teste de regressão para a regra ou o limite alterado e execute as [suítes pertinentes](testing.md). Alterações apenas documentais geralmente precisam de revisão de links/exemplos e verificações focadas, sem novos testes que repitam o texto.

Para mudanças de modelos:

```bash
uv run --locked python manage.py makemigrations
uv run --locked python manage.py migrate
uv run --locked python manage.py makemigrations --check --dry-run
```

Revise migrações geradas antes de aplicá-las a dados importantes. Labels de apps e nomes de modelos também participam dos arquivos portáveis de campanha. Uma mudança de esquema pode exigir testes de importação/exportação e snapshots além dos testes de modelos.

## Contratos e recursos do navegador

O registro do navegador é gerado de `gravewright/modules/contracts/frontend.json`:

```bash
uv run --locked python scripts/generate_frontend_api.py
```

Inclua no mesmo commit o contrato-fonte e `gravewright/modules/static/gravewright_modules/frontend-contract.js`. O contrato separado do SDK usa [contracts/registry.json](../../gravewright/modules/contracts/registry.json), [contracts/api.json](../../gravewright/modules/contracts/api.json) e os arquivos de [contracts/schemas/](../../gravewright/modules/contracts/schemas/), inclusive `manifest.json`. Veja [módulos](modules.md) e [frontend](frontend.md) antes de alterá-los.

O frontend usa módulos JavaScript nativos. Deixe explícita a limpeza de listeners, timers, objetos de renderização e tarefas assíncronas. Alguns bundles de terceiros têm metadados próprios de build; reconstruí-los é separado de iniciar o Django. Preserve avisos de licença e atualize os [avisos de terceiros](../../THIRD_PARTY_NOTICES.pt-BR.md) ao trocar um bundle.

## Convenções da documentação

Os guias em inglês ficam em `docs/en/`; os portugueses usam o mesmo nome em `docs/pt-BR/`. Cada guia aponta para o índice e sua tradução. Use links relativos para funcionar em forks e cópias baixadas. Não inclua caminhos absolutos de um desenvolvedor nem presuma uma URL de repositório não configurada.

Explique por que o código existe, suas responsabilidades e restrições. Mantenha comentários próximos do limite explicado. Em funções públicas importantes, documente identificadores/payloads aceitos, retornos, efeitos colaterais e erros do domínio. Preserve explicações úteis; não adicione comentário redundante a cada atribuição.

Os documentos da gramática de dados são mantidos junto à implementação. Os novos guias devem apontar para essas referências sem duplicar regras de sintaxe que possam divergir.

## Identificadores da versão

A versão atual é **Alpha 0.1.0**. Os identificadores equivalentes seguem os formatos exigidos por cada ferramenta:

| Local | Identificador |
| --- | --- |
| Nome público, aplicação e Runner | `Alpha 0.1.0` |
| Projeto Python e `uv.lock` | `0.1.0a0` |
| Pacote frontend, package lock e API de atualização | `0.1.0-alpha.0` |
| Tag do release | `v0.1.0-alpha.0` |
| Artefato do código-fonte | `Gravewright-0.1.0-alpha.0-django.zip` |

[`pyproject.toml`](../../pyproject.toml) é a fonte da versão instalada. [`gravewright/version.py`](../../gravewright/version.py) deriva o identificador público e o rótulo; mantenha os metadados do pacote frontend alinhados ao alterá-la. O [formato de prévias do Python](https://packaging.python.org/en/latest/specifications/version-specifiers/#pre-releases) e o [versionamento semântico](https://semver.org/) distinguem esta alpha da futura versão estável `0.1.0`. Versões dos contratos de API/SDK e de módulos de terceiros têm ciclos independentes.

O atualizador classifica releases alpha no canal `dev`. O canal escolhido continua sendo uma preferência do host; nomear esta versão como alpha não altera uma preferência existente nem habilita atualizações de prévias automaticamente.

## Antes de enviar

Siga [CONTRIBUTING.pt-BR.md](../../CONTRIBUTING.pt-BR.md). Confira traduções, registro gerado, migrações e avisos de licença conforme o escopo. Descreva a validação exata e eventuais falhas. Não inclua `.env`, dados de execução, uploads privados ou credenciais de navegador de uma implantação real.
