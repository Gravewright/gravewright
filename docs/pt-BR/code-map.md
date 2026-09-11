# Mapa do código

[Documentação](../README.pt-BR.md) · [English](../en/code-map.md) · [Arquitetura](architecture.md)

Use este mapa para encontrar o responsável por um comportamento antes de alterá-lo.
A maioria dos apps Django usa `models.py` para persistência, `services.py` para regras
de negócio, `views.py` e `urls.py` para HTTP e `tests/` ou `tests.py` para verificações.
Migrations descrevem o histórico do esquema; não são o local para documentar ou
alterar a lógica atual dos serviços.

## Comece aqui

| Local | Responsabilidade |
| --- | --- |
| [`manage.py`](../../manage.py) | Entrada dos comandos de administração Django. |
| [`main.py`](../../main.py) | Inicia o servidor ASGI de desenvolvimento com host e porta configurados. |
| [`scripts/gravewright_runner.py`](../../scripts/gravewright_runner.py) | Prepara configuração pessoal, banco e recursos e executa o servidor Daphne local do Gravewright Runner. |
| [`Gravewright Runner.bat`](../../Gravewright%20Runner.bat) | Launcher CMD Windows: detecta/reaproveita uv, Python e Node/npm, instala ferramentas ausentes, executa comandos fixados de dependências/build e inicia a aplicação. |
| [`scripts/prepare_frontend.py`](../../scripts/prepare_frontend.py) | Planeja a preparação do frontend por impressões das dependências, fontes e saídas e registra os resultados verificados do build para o launcher em lote. |
| [`scripts/windows/create_shortcut.py`](../../scripts/windows/create_shortcut.py) | Cria o atalho com ícone por ctypes da biblioteca padrão e COM do Windows. |
| [`config/runner.py`](../../config/runner.py), [`config/runner_asgi.py`](../../config/runner_asgi.py), [`config/runner_urls.py`](../../config/runner_urls.py) | Perfil dedicado à execução local, recursos estáticos coletados e rotas do executor; veja o [guia Windows](windows-runner.md). |
| [`pyproject.toml`](../../pyproject.toml), [`uv.lock`](../../uv.lock) | Requisitos Python e resolução fixada das dependências. |
| [`config/environment.py`](../../config/environment.py) | Carrega o ambiente e interpreta booleanos, caminhos e origem pública. |
| [`config/engine.py`](../../config/engine.py) | Recursos habilitados e limites validados do motor. |
| [`config/settings.py`](../../config/settings.py) | Apps, SQLite, sessões, templates, mídia e configuração de Channels. |
| [`config/asgi.py`](../../config/asgi.py), [`config/wsgi.py`](../../config/wsgi.py) | Entradas do servidor; ASGI inclui WebSocket da mesa. |
| [`config/proxy.py`](../../config/proxy.py) | Restaura esquemas HTTP/WebSocket a partir de um único cabeçalho forwarded-proto válido enviado por um par conectado confiável. |
| [`config/urls.py`](../../config/urls.py) | Reúne rotas HTTP dos apps. |
| [`config/jinja2.py`](../../config/jinja2.py) | Ambiente de templates da interface Jinja2. |
| [`api/`](../../api) | Importações Python públicas para extensões, reexportando entradas autorizadas dos domínios. |
| [`scripts/generate_frontend_api.py`](../../scripts/generate_frontend_api.py) | Regenera o registro de métodos do navegador a partir do contrato de transporte. |

## Domínios da aplicação

Os caminhos internos abaixo são relativos a `gravewright/`.

| App | Modelos principais | Leia primeiro | Implementação relacionada |
| --- | --- | --- | --- |
| [`accounts/`](../../gravewright/accounts) | `User`, `AuthAttempt`, `UserPreference` | `services.py`, `models.py` | `forms.py` valida contas; `managers.py` normaliza identidades; `client_ip.py` trata proxies confiáveis; `middleware.py` limita requisições de autenticação e define políticas de resposta. |
| [`campaigns/`](../../gravewright/campaigns) | `Campaign`, `Membership`, `AccessCode`, `JoinAttempt`, `Onboarding`, `StreamerLink` | `services.py`, `streamer.py` | `onboarding.py` prepara orientações iniciais; `catalog.py` descreve o sistema nativo; views tratam convites, participantes e capas. |
| [`web/`](../../gravewright/web) | Nenhum | `inside.py`, `responses.py` | Compõe páginas de conta, campanha e configurações; `iconography.py` fornece ícones; `jinja2/` e `static/` guardam a interface compartilhada. |
| [`table/`](../../gravewright/table) | `LobbyState` | `domain.py`, `views.py`, `services.py` | `media.py` recebe e entrega áudio/cartas; `events.py` declara sinais confiáveis; `dock.json` e arquivos JSON de mensagens configuram a interface. |
| [`actors/`](../../gravewright/actors) | `Actor`, `Folder`, `Asset` | `services.py` | Views implementam leitura de fichas, uploads e entrega autenticada de PDF/imagens. |
| [`pdf_system/`](../../gravewright/pdf_system) | Nenhum | `schema.py` | Padrões e validação da ficha PDF nativa; comportamento no navegador fica em `static/`. |
| [`tokens/`](../../gravewright/tokens) | `Token` | `services.py` | Vínculos com atores, snapshots, movimento, visão e prévias filtradas de arraste; `views.py` expõe estado. |
| [`maps/`](../../gravewright/maps) | `Scene`, `Tile`, `Broadcast`, `SceneState`, `SceneObject`, `Folder`, `Receipt`, `MapAsset`, `AssetFolder` | `services.py`, `objects.py`, `views.py` | `assets.py` cuida da biblioteca; `extra_objects.py`, `markers.py`, `zones.py` validam camadas especializadas; auxiliares de renderização e pré-carregamento priorizam blocos. |
| [`journals/`](../../gravewright/journals) | `Journal`, `Folder`, `Access`, `Asset`, `Receipt`, `BoardEntry` | `services.py`, `data.py`, `types.py` | `documents.py` valida texto estruturado e blocos secretos; `presentations.py` gerencia tickets; views protegem uploads e downloads. |
| [`chat/`](../../gravewright/chat) | `Message`, `Recipient`, `SendWindow`, `CardAttachment` | `services.py`, `context.py` | `card_attachments.py` captura faces imutáveis; templates renderizam chat e resultados de dados persistidos. |
| [`dice/`](../../gravewright/dice) | `Submission` | `services.py`, `engine.py` | `grammar/parser.py`, `compiler.py`, `runtime.py` implementam notação e avaliação; documentação e testes com resultados determinísticos ficam próximos. |
| [`items/`](../../gravewright/items) | `Item`, `Folder` | `services.py` | Documentos filtrados por permissão; `types()` atualmente não retorna tipos nativos. |
| [`combat/`](../../gravewright/combat) | `Encounter` | `services.py`, `effects.py` | `active_effects.py` auxilia os efeitos; `formula_engine.py` é um interpretador separado de fórmulas declarativas. |
| [`cards/`](../../gravewright/cards) | `Deck`, `Card`, `CardAsset`, `DeckDefinition` | `services.py` | Ciclo de vida de baralhos, compras, propriedade e visibilidade; rotas de arquivos ficam em `table/media.py`. |
| [`audio/`](../../gravewright/audio) | `Track`, `Playlist`, `Playback` | `services.py`, `transport.py` | `metadata.py` inspeciona arquivos; `soundtrack.py` agenda música; `geometry.py` calcula atenuação pelas paredes. |
| [`compendiums/`](../../gravewright/compendiums) | `Pack`, `Entry`, `EntryAsset`, `ContentAccess` | `services.py`, `catalog.py` | `graph.py` seleciona dependências portáteis; `assets.py` copia/restaura arquivos; `signals.py` limpa arquivos próprios. |
| [`realtime/`](../../gravewright/realtime) | `PresenceConnection` | `consumers.py`, `services.py`, `dispatch.py` | `routing.py`, `security.py`, `scene_stream.py`, `gm_guided_prefetch.py` tratam sockets, origem e agendamento de viewport. |
| [`administration/`](../../gravewright/administration) | `HostSettings`, `Snapshot`, `AuditEvent` | `views.py`, `archives.py`, `preferences.py` | `updates.py` consulta versões; `release_metadata.py` busca e valida metadados das versões. |
| [`modules/`](../../gravewright/modules) | Estado de pacotes/catálogo | `packages.py`, `operations.py`, `contracts/` | Instalação de extensões, marketplace e contratos; consulte ao alterar capacidades de pacotes ou declarações geradas da API. |

## Acompanhando uma funcionalidade

### Salvamento de ficha de personagem

1. Navegador/API envia `actors.command` com a ação `sheet.save`.
2. `realtime/consumers.py` ou `api.actors.command` chega a
   `actors/services.py:command`.
3. O comando bloqueia a campanha, recarrega o vínculo e verifica o recibo.
4. `save_sheet()` resolve ator ou snapshot de token, verifica revisões e chama
   `pdf_system/schema.py:normalize`.
5. O serviço salva dados e revisões e chama `realtime/dispatch.py:changed`.
6. Invalidações confirmadas de atores, tokens e camadas fazem cada socket inscrito
   consultar seu próprio estado autorizado.

### Atualização do viewport do mapa

1. O socket recebe `scene.viewport`.
2. `scene_stream.py:resolve` verifica acesso, nível de detalhe, coordenadas, geração
   e limites configurados do viewport.
3. `SceneStreamMixin` alimenta `maps/render_scheduler.py` e, quando aplicável,
   compartilha amostras do mestre por Channels.
4. O consumidor emite avisos de blocos prontos ou de pré-carregamento. O navegador
   baixa as imagens pela rota autenticada de blocos em `maps/views.py`.

### Nova rolagem no chat

1. `realtime/consumers.py:roll` valida a requisição e solicita uma reserva persistente
   a `dice/services.py`.
2. `dice/engine.py:evaluate` analisa, compila e executa a expressão fora do executor
   do banco. Uma repetição já concluída pula essa avaliação.
3. `dice/services.py:complete` verifica vínculo/sessão novamente e confirma a mensagem.
4. `realtime/dispatch.py:message` publica os dados confirmados; cada receptor verifica
   autorização atual, cena e destinatários antes de entregá-los.

### Importação de conteúdo reutilizável

1. `compendiums/services.py` verifica visibilidade, permissão e sistema do pacote.
2. Entradas com arquivos portáteis passam por
   `administration/archives.py:import_campaign`.
3. O importador valida manifesto e grafo permitido, reescreve referências de recursos
   e arquivos e mescla os dados na campanha de destino.
4. `table/domain.py` registra o resultado e agenda atualizações dos estados afetados
   após o commit.

## Onde fazer uma alteração

| Alteração | Responsável provável | Revisar em conjunto |
| --- | --- | --- |
| Permissão de campanha/recurso | Serviço do domínio, frequentemente `journals.services.member` ou `maps.services.scene` | Entrega HTTP de arquivos, projeções dos sockets, streamers e repetições de comandos. |
| Novo comando de recurso | `services.py` correspondente e contrato de transporte | Validação, identidade da requisição, revisões, despacho, API Python e geração do wrapper do navegador. |
| Novo campo/modelo | `models.py` correspondente e uma nova migration | Projeções, padrões, grafo de importação/exportação e dados de teste. |
| Novo objeto de cena | `maps/objects.py` ou auxiliar especializado | Filtro por destinatário, revisão, interação com tokens/visão/áudio e renderizador. |
| Notação de dados | `dice/grammar/` | Limites do compilador, fatos do runtime, compatibilidade de resultados persistidos e testes determinísticos. |
| Novo formato de upload | View e inspetor do formato | Propriedade do arquivo, download autenticado, limpeza em falhas e extensões permitidas nos arquivos portáteis. |
| Interface compartilhada da mesa | `table/jinja2/`, `table/static/`, `table/dock.json` | Estado do navegador, contrato da API e capacidades correspondentes no servidor. |
| Configuração do servidor | `config/engine.py` ou `administration/preferences.py` | Validação de ambiente, exposição na interface, documentação e ativação dos recursos. |
| Comportamento de extensão/pacote | `modules/` e `api/` | Contratos de manifests instalados, importações públicas, aviso de licença e geração do transporte. |

## Convenções de leitura e documentação

Docstrings usam inglês, como a documentação principal. Explicam o ponto de entrada
ou a regra que deve ser preservada, em vez de repetir atribuições. `help()` do Python
exibe as docstrings públicas; [Arquitetura](architecture.md) explica as regras de
domínio e as interações entre arquivos.

Nomes como `who` normalmente indicam um `Membership` recém-resolvido. Parâmetros
`campaign`/`user` em serviços públicos podem ser IDs, enquanto auxiliares internos
recebem instâncias dos modelos. Leia a assinatura e os chamadores antes de passar um
valor. `table.domain.module()` seleciona um dos cinco serviços nativos de recursos;
não é o instalador de pacotes de terceiros em `gravewright/modules/`.

Mantenha os guias em inglês e português sincronizados ao alterar comportamentos.
Preserve licenças e comentários de terceiros nos arquivos incorporados e evite
editar wrappers gerados da API diretamente. Veja [Desenvolvimento](development.md)
e [Testes](testing.md) para o fluxo de contribuição.
