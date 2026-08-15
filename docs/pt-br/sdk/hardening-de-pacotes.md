# Segurança do SDK

Pacotes são conteúdo não confiável. O SDK aplica várias fronteiras.

## Segurança de paths

Todo path declarado no manifest e toda entrada de archive devem permanecer dentro do diretório do pacote. O loader/validador rejeita:

```text
paths vazios          paths absolutos       URLs
barras invertidas     prefixos de drive     traversal com ..
segmentos "."         barras duplas         barra final em arquivos
dois-pontos           nomes reservados      segmentos terminando em espaço/ponto
paths resolvidos fora do diretório do pacote
```

Veja `app/engine/sdk/package_paths.py` (`package_id_is_safe`, `path_is_safe`, `safe_join`).

## Capabilities

Capabilities são uma allow-list. Capabilities desconhecidas são rejeitadas, e o conjunto proibido (`backend.execute`, `database.raw`, `filesystem.raw`, `network.raw`, `permissions.override`) é sempre rejeitado. Não há execução de código server-side no SDK v1.

Gates de capability no navegador são contrato para autores e defesa em profundidade, não sandbox de JavaScript. Um pacote que declara `assets.scripts` roda JavaScript confiável na mesma página da mesa e pode acessar globais como `window`, `document` e `fetch`. Instalar um pacote com script significa confiar no autor. Pacotes declarativos sem JavaScript continuam sendo o caminho mais seguro.

Rotas do servidor ainda aplicam estado do pacote, papel do usuário e capabilities relevantes para operações mutáveis. Gates client-side nunca são a única fronteira de autorização:

- `POST /sdk/packages/settings` exige pacote habilitado e capability `settings` (`sdk.errors.capability_required`).
- `POST /sdk/packages/content/import` exige pacote habilitado e capability `content.packs` (`sdk.errors.capability_required`).

Instalar, habilitar, desabilitar, remover e ativar pacotes são ações de operador/GM protegidas por papel, não por capability de pacote.

## Posse de script (nonce por pacote)

Scripts de pacote registram no runtime via `GravewrightSDK.register({ id })`. Para vincular um `<script>` ao pacote que ele declara, o servidor marca cada script com `data-gw-package` e um `data-gw-nonce` novo por render, e envia o mapa `{ id: nonce }` no contexto da mesa (`packageNonces`). O SDK aceita `register` apenas quando o id e nonce do script batem com o par emitido pelo servidor.

Isso torna a ligação script -> pacote explícita e testável, em vez de inferida apenas por `document.currentScript.src`, e impede que um pacote registre em nome de outro. Nonces são por render, então não podem ser reutilizados entre carregamentos.

## Servir assets

A rota de assets serve apenas arquivos **declarados** no manifest, apenas para pacote habilitado, com allow-list de content-type. Qualquer outra coisa é 404.

No v1 este é um modelo **público e estático**: `GET /sdk/packages/<id>/asset/<path>` serve qualquer arquivo declarado de qualquer pacote globalmente habilitado, para qualquer pessoa, sem checar campanha ou membership. Isso é correto para os pacotes incluídos hoje, cujos assets não são secretos.

## Futuro: assets privados ou pagos

Se um pacote incluir assets **privados ou pagos**, o modelo público deixa de ser adequado e deve virar **serving de asset escopado por campanha**:

- autorizar cada request de asset contra a membership do usuário na campanha e o pacote ativo nessa campanha;
- escopar a URL por campanha, por exemplo `/sdk/campaigns/<campaign-id>/packages/<id>/asset/<path>`;
- tratar os bytes como recurso protegido, sem cache público de CDN, usando URLs assinadas ou expirantes quando necessário.

Até esse requisito existir, mantenha assets públicos/declarados/habilitados. Não coloque nada secreto atrás da rota atual.

## Upload de ZIP não confiável

Uploads de pacote continuam não confiáveis. Rejeite arquivos que não são zip, excesso de entradas, pacotes grandes demais, paths absolutos, traversal com `..`, prefixos de drive Windows, barras invertidas, symlinks, `.env`, `storage/`, arquivos SQLite, `__pycache__/`, `.pyc`, logs e `node_modules/`.

O archive deve conter `manifest.json` na raiz ou `{kind_plural}/{id}/manifest.json`. Valide o manifest e todos os paths declarados antes de promover para `data/packages/{kind_plural}/{id}/`.

## Autorização

- Somente owner: instalar, habilitar, desabilitar, remover ou fazer upload global de pacote.
- Somente GM por campanha: definir ruleset, ativar/desativar pacotes, alterar settings de escopo `campaign`, importar conteúdo de pacote.
- Escopo de usuário: alterar settings de escopo `user`.
