# Portando módulos para o Gravewright

Este guia ensina como adaptar para o Gravewright um módulo criado originalmente
para outra plataforma de mesa virtual. Neste documento, **módulo original** é o
projeto usado como referência, **plataforma de origem** é o ambiente para o qual
ele foi escrito e **port** é o novo pacote compatível com a Gravewright SDK.

Um port não deve ser uma troca mecânica de nomes de APIs. Plataformas diferentes
possuem modelos de dados, autoridade, permissões, ciclo de vida e interfaces
distintos. O objetivo é preservar a experiência e o comportamento úteis do módulo,
reimplementando-os pelos contratos públicos do Gravewright.

> [!IMPORTANT]
> Use somente código e materiais que você tenha direito de estudar, modificar e
> redistribuir. Este guia é técnico e não substitui orientação jurídica.

## 1. Introdução

No Gravewright, toda extensão instalável é um pacote da SDK. Antes de começar,
identifique qual [`kind`](kinds.md) representa o resultado pretendido:

| O port oferece | Kind provável |
|---|---|
| Comportamento opcional, comandos, UI ou automação | `addon` |
| Regras-base de um sistema de jogo | `ruleset` |
| Aparência e estilos | `theme` |
| Conteúdo importável | `content` |
| Imagens, áudio, mapas ou outros recursos reutilizáveis | `assets` |
| Código ou dados compartilhados como dependência | `library` |

Na maioria dos casos, um módulo de funcionalidade deve virar um `addon`. Não use
um `ruleset` apenas porque o projeto original chama sua extensão de “sistema” ou
“módulo”; escolha pelo papel que o pacote terá no Gravewright.

Leia antes o [modelo declarativo](declarative-model.md), o
[início rápido](quick-start.md) e o [mapa de capabilities](power-map.md).

## 2. Antes de começar: avaliar o módulo

Faça uma auditoria curta antes de escrever código. Registre:

- repositório, versão e commit exatos usados como origem;
- licença do código e de cada grupo de assets;
- autores e avisos que precisam acompanhar a redistribuição;
- funcionalidades essenciais e funcionalidades opcionais;
- dependências de terceiros, versões e licenças;
- APIs, eventos, dados, UI e permissões usados na plataforma de origem;
- recursos que podem ser implementados declarativamente;
- recursos que exigem JavaScript no navegador;
- comportamento que depende de internals privados e não deve ser reproduzido;
- riscos de desempenho, segurança e compatibilidade multiplayer.

Ao final, classifique o projeto:

- **portável**: licença e SDK permitem entregar o comportamento principal;
- **portável com escopo reduzido**: algumas funções ou assets precisam ser
  substituídos, redesenhados ou excluídos;
- **bloqueado por SDK GAP**: falta uma operação pública indispensável;
- **não redistribuível**: a licença ou os direitos sobre os materiais não permitem
  distribuir o resultado pretendido.

Não comece pelo código mais complexo. Faça primeiro uma prova mínima usando a SDK
pública para validar que a integração fundamental é possível.

## 3. Licença

A licença determina o que pode ser copiado, modificado e distribuído. Localizar um
projeto publicamente não significa que ele possa ser reutilizado.

Antes do port:

1. leia o texto integral da licença do módulo original;
2. confirme se modificação e redistribuição são permitidas;
3. verifique obrigações de atribuição, disponibilização de código-fonte, avisos e
   indicação de alterações;
4. verifique se dependências e arquivos incorporados usam licenças diferentes;
5. escolha uma licença compatível para o port;
6. preserve copyrights e avisos exigidos.

### Licenças que normalmente permitem um port

O Gravewright não restringe pacotes a uma lista fechada de licenças: o campo
`license` do manifesto aceita uma string. Para evitar ambiguidades, use um
[identificador SPDX](https://spdx.org/licenses/) reconhecido. A possibilidade
técnica de declarar uma licença não garante que ela seja compatível com o código,
as dependências e os assets usados pelo seu port.

Estas licenças de software normalmente permitem criar e distribuir adaptações,
desde que suas condições sejam cumpridas:

| Licença | Declaração no manifesto | Principal obrigação ao distribuir o port |
|---|---|---|
| MIT | `MIT` | Preservar o texto da licença e os avisos de copyright. |
| Apache License 2.0 | `Apache-2.0` | Preservar licença, notices aplicáveis e indicar arquivos modificados; também possui cláusula de patentes. |
| BSD de 2 cláusulas | `BSD-2-Clause` | Preservar copyright, condições e disclaimer. |
| BSD de 3 cláusulas | `BSD-3-Clause` | Cumprir a BSD-2-Clause e não usar nomes dos autores para endosso sem permissão. |
| Mozilla Public License 2.0 | `MPL-2.0` | Disponibilizar sob MPL o código-fonte dos arquivos cobertos que forem modificados. |
| GNU Lesser GPL 2.1 | `LGPL-2.1-only` ou `LGPL-2.1-or-later` | Preservar a LGPL e permitir o uso/substituição da biblioteca conforme seus termos. |
| GNU Lesser GPL 3.0 | `LGPL-3.0-only` ou `LGPL-3.0-or-later` | Cumprir a LGPL para a biblioteca e modificações cobertas. |
| GNU GPL 2.0 | `GPL-2.0-only` ou `GPL-2.0-or-later` | Distribuir o trabalho derivado coberto sob GPL compatível e fornecer o código-fonte correspondente. |
| GNU GPL 3.0 | `GPL-3.0-only` ou `GPL-3.0-or-later` | Distribuir o trabalho derivado coberto sob GPL compatível e fornecer o código-fonte correspondente. |
| GNU Affero GPL 3.0 | `AGPL-3.0-only` ou `AGPL-3.0-or-later` | Cumprir a GPL e oferecer o código-fonte correspondente também aos usuários que interagem com a versão modificada pela rede. |
| Unlicense | `Unlicense` | Preservar o texto aplicável; confirme a adequação jurídica à sua distribuição. |

O port dos dados 3D, por exemplo, deriva de código coberto pela GNU Affero GPL 3.0;
a declaração SPDX precisa para a variante usada deve ser `AGPL-3.0-only` ou
`AGPL-3.0-or-later`, conforme o texto de origem. Chamar essa licença apenas de
“GNU” é insuficiente:
GPL, LGPL e AGPL têm condições diferentes, e `only` e `or-later` também não são
intercambiáveis.

Para assets, fontes e documentação, são comuns licenças diferentes das usadas no
código:

| Material | Exemplos de declaração | Observação |
|---|---|---|
| Asset em domínio público | `CC0-1.0` | Pode ser reutilizado sem as condições de atribuição das licenças CC BY. |
| Asset com atribuição | `CC-BY-4.0` | Credite autor, obra, licença, link e alterações. |
| Asset com atribuição e compartilhamento pela mesma licença | `CC-BY-SA-4.0` | Além da atribuição, adapte e distribua o material derivado sob licença compatível. |
| Fonte | `OFL-1.1` | Preserve a licença e confira nomes reservados antes de modificar a fonte. |

Licenças Creative Commons são apropriadas para conteúdo e assets, mas normalmente
não são recomendadas para código de software. Materiais `CC-BY-NC-*` restringem uso
comercial e exigem que a distribuição do pacote respeite essa limitação. Materiais
`CC-BY-ND-*` não permitem distribuir adaptações e, por isso, não servem como base
para um asset modificado.

### Casos que não autorizam o port

Não copie ou distribua material quando ele estiver:

- sem licença;
- marcado como `All Rights Reserved`;
- limitado a uso pessoal quando o pacote será redistribuído;
- sob licença que proíba modificações ou trabalhos derivados;
- disponível apenas em um produto comprado, sem permissão separada de redistribuição;
- acompanhado de termos incompatíveis com a forma como o port será publicado.

Ter acesso ao código-fonte não equivale a receber uma licença de portabilidade. Se o
autor concedeu uma permissão específica, preserve uma cópia dessa autorização e
descreva no pacote o escopo concedido.

### Como declarar a licença

Para um pacote inteiramente MIT, declare no `manifest.json`:

```json
{
  "license": "MIT"
}
```

Para um port coberto exclusivamente pela GNU Affero GPL 3.0:

```json
{
  "license": "AGPL-3.0-only"
}
```

Quando todo o pacote puder ser usado alternativamente sob uma de duas licenças, use
uma expressão SPDX com `OR`:

```json
{
  "license": "MIT OR Apache-2.0"
}
```

Use `AND` somente quando o mesmo trabalho estiver realmente sujeito, ao mesmo tempo,
a todas as licenças indicadas. Não use `AND` para resumir arquivos independentes com
licenças diferentes. Nesse caso, declare no manifesto a licença do código principal
e use `THIRD_PARTY_NOTICES.md` para mapear cada componente sem tentar relicenciá-lo:

```json
{
  "license": "MIT"
}
```

```md
# Licenças de terceiros

## Código do pacote
- Arquivos: `scripts/**`
- Licença: MIT
- Copyright: 2026 Nome do autor

## Ícones
- Arquivos: `assets/icons/**`
- Obra e autor: Nome da coleção — Nome do autor
- Origem: URL
- Licença: CC BY 4.0 — URL da licença
- Alterações: cores e dimensões adaptadas
```

Além do campo no manifesto:

1. inclua o texto integral da licença principal em `LICENSE`;
2. preserve headers e avisos exigidos nos arquivos relevantes;
3. registre dependências e assets em `THIRD_PARTY_NOTICES.md`;
4. registre projeto, versão, commit e licença original em `UPSTREAM.md`;
5. explique no `README.md` qual licença cobre o port e onde estão os avisos;
6. ofereça o código-fonte correspondente quando a licença copyleft exigir.

Arquivos recomendados no pacote:

```text
meu-port/
├── LICENSE
├── README.md
├── THIRD_PARTY_NOTICES.md
└── UPSTREAM.md
```

`UPSTREAM.md` deve identificar a origem de forma reproduzível:

```md
# Origem

- Projeto: Nome do projeto original
- Repositório: URL
- Versão: 1.2.3
- Commit: hash completo
- Licença: identificador da licença
- Autores declarados: nomes
- Data do port: AAAA-MM-DD

## Material reutilizado

- `src/geometry.js`: geometria e dados de rotação.

## Material reimplementado

- Ciclo de vida, eventos, integração de UI e acesso a dados.

## Material excluído

- Configurador visual e integração com APIs privadas da origem.
```

Se não for possível determinar os direitos de um arquivo, não o inclua até obter
permissão ou substituí-lo por uma alternativa segura.

## 4. Propriedade intelectual e uso de assets

Licença de código não resolve automaticamente os direitos sobre marcas, nomes,
ilustrações, modelos 3D, mapas, textos, regras publicadas, áudio, fontes ou outros
assets. Audite cada categoria separadamente.

Crie um inventário como este:

| Material | Origem | Autor | Licença/permissão | Alterado? | Destino |
|---|---|---|---|---|---|
| Código de geometria | repositório original | autor declarado | licença aplicável | sim | `src/` |
| Fonte | site do autor | autor da fonte | licença da fonte | não | `assets/fonts/` |
| Ícones | criação própria | equipe do port | própria | sim | `assets/icons/` |

Boas práticas:

- não use a marca ou identidade visual da plataforma de origem para sugerir
  afiliação ou endosso;
- remova assets cuja licença seja ausente, ambígua ou incompatível;
- substitua materiais proprietários por criações próprias ou alternativas
  devidamente licenciadas;
- mantenha atribuições próximas ao pacote distribuído;
- registre transformações relevantes no inventário;
- não inclua conteúdo de campanhas, credenciais, bancos ou arquivos pessoais.

## 5. Definindo o escopo do port

Separe o módulo em funcionalidades observáveis, não em arquivos. Para cada uma,
decida entre **portar**, **reimplementar**, **substituir** ou **excluir**.

| Funcionalidade original | Decisão | Implementação Gravewright | Motivo |
|---|---|---|---|
| Reagir a uma rolagem pública | reimplementar | evento público + DTO de chat | modelo de eventos diferente |
| Renderizar efeito visual | portar parcialmente | slot público de UI + assets próprios | motor reaproveitável |
| Ler configuração do usuário | substituir | `sdk.settings` ou apresentação pública | storage original não existe |
| Alterar internals do canvas | excluir | nenhuma | depende de superfície privada |

Escreva explicitamente o que **não** faz parte da primeira versão. Um port menor,
com fronteiras claras e bem testado, é preferível a uma cópia incompleta que parece
oferecer recursos que não funcionam.

## 6. Mapeando a arquitetura original para o Gravewright

Produza uma tabela de tradução antes da implementação:

| Conceito necessário | Contrato Gravewright possível |
|---|---|
| Inicialização do módulo | `window.GravewrightSDK.register` |
| Metadados e compatibilidade | `manifest.json` |
| Permissão para usar uma API | `capabilities` |
| Dados atuais da mesa | `sdk.context()` e `sdk.game.*` |
| Eventos entre pacotes | `sdk.bus.*` |
| Mensagens e rolagens | `sdk.chat.*` e DTOs públicos |
| Configuração | declaração de `settings` e `sdk.settings.*` |
| Extensão de ficha | `sdk.sheets.*` |
| Integração de combate | `sdk.combat.*` |
| Cena e tokens | `sdk.scene.*`, `sdk.tokens.*` e `sdk.tools.*` |
| Interface | slots e métodos documentados em `sdk.ui.*` |
| Traduções | locales declarados e `sdk.i18n.*` |
| Conteúdo e mídia | packs e paths relativos declarados |

Confirme cada mapeamento na [referência da SDK](reference.md). Sem um método,
evento, DTO, capability ou slot documentado, a superfície deve ser considerada
privada.

### Autoridade e multiplayer

Não replique suposições da plataforma de origem sobre quem pode ler ou alterar
estado. Documente para cada ação:

- quem inicia a operação: GM, jogador ou qualquer usuário;
- quem é autoridade para validar e persistir a mudança;
- quem pode observar o resultado;
- se o estado é local, compartilhado ou durável;
- o que ocorre em reconexão, repetição ou concorrência.

Não tente contornar permissões pelo DOM, por requests privados, por frames crus de
WebSocket ou por estruturas internas do banco. Leia o
[modelo de autoridade](authority-model.md) e a [segurança da SDK](security.md).

## 7. Estrutura do pacote

Crie o scaffold adequado:

```bash
grave addon new meu-port --name "Meu Port" --js --settings
```

Adapte as opções ao escopo. Uma estrutura típica pode ser:

```text
data/packages/addons/meu-port/
├── manifest.json
├── README.md
├── LICENSE
├── UPSTREAM.md
├── THIRD_PARTY_NOTICES.md
├── src/
├── scripts/
├── styles/
├── assets/
└── locales/
```

Declare no manifesto somente os arquivos, recursos e capabilities realmente usados.
Prefira definições declarativas a JavaScript sempre que a SDK oferecer ambas as
formas. Não copie manifestos, identificadores, URLs ou formatos específicos da
plataforma de origem.

O runtime mínimo segue este ciclo de vida:

```js
window.GravewrightSDK.register({
  id: "meu-port",
  setup(sdk) {
    // Registre listeners, comandos e integrações.
  },
  ready(sdk) {
    // Monte comportamento que depende do jogo ou do DOM pronto.
  },
});
```

O `id` deve ser idêntico ao do manifesto. A inicialização deve ser idempotente e a
desmontagem deve remover listeners, timers, elementos e recursos criados pelo pacote.

### Dependências reaproveitadas

Para cada biblioteca incorporada:

- fixe uma versão conhecida;
- preserve sua licença e seus avisos;
- importe apenas o necessário;
- remova adapters e código específicos da plataforma de origem;
- evite publicar `node_modules` ou arquivos de desenvolvimento no ZIP;
- gere bundles reproduzíveis e documente o comando de build;
- confira se nenhum secret, source map privado ou arquivo local entrou no artefato.

## 8. Implementando o port com a SDK

Implemente em fatias verticais pequenas:

1. carregamento e registro do pacote;
2. leitura do evento ou dado público necessário;
3. transformação para um modelo interno do port;
4. efeito observável mínimo;
5. permissões e multiplayer;
6. configurações e persistência;
7. acessibilidade, traduções e tratamento de erros;
8. limpeza e desmontagem.

Mantenha um adapter explícito entre os DTOs públicos do Gravewright e o motor
reaproveitado. Assim, atualizações da SDK ou da biblioteca não contaminam todo o
código.

```text
evento/DTO público → adapter do port → motor independente → UI/efeito do pacote
```

Não envie objetos internos do runtime diretamente ao motor antigo. Extraia apenas os
campos públicos necessários e trate campos opcionais, versões e ausência de recursos.

## 9. Usando IA para automatizar o port

IA ajuda a inventariar dependências, criar adapters, converter formatos, gerar testes
e explicar erros. Ela não decide se você possui direitos sobre um material e não deve
ser autorizada a contornar a SDK.

### Prepare contexto controlado

Forneça à ferramenta:

- o escopo aprovado;
- os arquivos licenciados que podem ser usados;
- o manifesto e a documentação pública relevante da SDK;
- a tabela de mapeamento arquitetural;
- os comandos de validação;
- uma fronteira de edição limitada ao diretório do pacote.

Prompt inicial sugerido:

```text
Você está adaptando um módulo licenciado para um addon Gravewright SDK 1.

Objetivo: [descreva o comportamento observável].
Escopo excluído: [liste o que não será portado].

Regras:
- edite somente data/packages/addons/meu-port;
- use apenas APIs públicas documentadas da Gravewright SDK;
- não invente capabilities, eventos, DTOs ou slots;
- não acesse banco, filesystem, rede, WebSocket, DOM ou globals privados;
- preserve licenças, atribuições e proveniência;
- não inclua assets sem licença confirmada;
- prefira manifesto e recursos declarativos;
- adicione testes para GM, jogador, reconexão e ausência de dependências;
- mantenha uma lista de funcionalidades portadas, substituídas e excluídas.

Depois de cada alteração, execute:
grave package validate data/packages/addons/meu-port
grave package doctor meu-port
```

### Trabalhe por etapas

Peça primeiro uma auditoria, depois um plano e só então patches pequenos. Para cada
patch, exija:

- APIs e capabilities utilizadas;
- arquivos de origem reaproveitados;
- comportamento que mudou;
- testes adicionados;
- riscos e limitações ainda abertos.

Nunca envie `.env`, bancos, saves, campanhas, mapas privados, credenciais ou pacotes
comerciais a um serviço externo de IA. Consulte também
[`criando-pacotes-com-ia.md`](criando-pacotes-com-ia.md).

## 10. Validando, testando e depurando

Valide continuamente:

```bash
grave package validate data/packages/addons/meu-port
grave package doctor meu-port
```

Um port com runtime precisa de mais que validação estrutural. Teste, quando aplicável:

- instalação, ativação, desativação e reinstalação;
- primeiro carregamento e recarregamento da página;
- GM e jogadores em sessões reais simultâneas;
- visibilidade e permissões para cada papel;
- criação, atualização e exclusão dos recursos envolvidos;
- sincronização, reconexão e repetição de eventos;
- duas ações concorrentes ou eventos duplicados;
- campanhas novas e campanhas com dados existentes;
- configurações padrão, alteração e persistência;
- dependências presentes, ausentes, desativadas e incompatíveis;
- desmontagem sem listeners, timers ou UI órfãos;
- desempenho com volume realista de dados;
- teclado, foco, contraste, redução de movimento e leitores de tela na UI;
- erros seguros, sem exposição de dados privados.

Use testes unitários para adapters e transformações determinísticas. Use testes E2E
com navegadores reais para ciclo de vida, UI, permissões e multiplayer. Um teste do
caminho feliz em uma única sessão não certifica um port multiplayer.

Antes de publicar, teste o ZIP ou artefato final a partir de uma instalação limpa. O
diretório de desenvolvimento pode esconder dependências ou arquivos que não foram
incluídos na distribuição.

## 11. Relatando uma SDK GAP

Uma **SDK GAP** existe quando um comportamento legítimo e geral não pode ser
implementado por composição das APIs públicas. Ela não existe apenas porque a API
original tinha outro nome ou porque uma implementação privada parece mais simples.

Antes de relatar:

1. procure o objetivo no [`power-map.md`](power-map.md), na
   [referência](reference.md) e nos [DTOs](dto-reference.md);
2. tente uma composição das capabilities e eventos públicos existentes;
3. reduza o bloqueio a um caso mínimo reproduzível;
4. confirme que o pedido não viola autoridade, privacidade ou segurança;
5. descreva a necessidade sem exigir que o core copie a API da origem.

Modelo de relatório:

```md
## SDK GAP: título orientado ao objetivo

### Caso de uso
Como [tipo de pacote/usuário], preciso [operação] para [resultado observável].

### Comportamento esperado
[O que deveria acontecer, para quem e com qual durabilidade.]

### APIs públicas avaliadas
- `sdk.exemplo.metodo`: insuficiente porque [...]
- evento `exemplo.criado`: insuficiente porque [...]

### Reprodução mínima
1. Instale o pacote mínimo anexado.
2. Entre como [...].
3. Execute [...].

### Restrição encontrada
[Erro, ausência de DTO/evento/slot ou limitação de autoridade.]

### Proposta de capacidade, não de implementação
[A menor operação pública geral que desbloquearia o caso.]

### Segurança e autoridade
- Chamadores permitidos: [...]
- Dados expostos: [...]
- Validação esperada no servidor: [...]

### Alternativas consideradas
- [...]
```

Não publique o port acessando internals enquanto aguarda a GAP. Marque a
funcionalidade como bloqueada, entregue um escopo reduzido ou mantenha a versão como
experimental.

## 12. Documentando autoria, origem e modificações

O `README.md` do port deve informar:

- o que o pacote faz;
- quais partes foram adaptadas e quais foram reimplementadas;
- funcionalidades deliberadamente excluídas;
- ausência de afiliação ou endosso, quando aplicável;
- instalação, ativação e configuração;
- capabilities solicitadas e por que são necessárias;
- versões da SDK compatíveis;
- build reproduzível;
- limitações e problemas conhecidos;
- licença e links para `UPSTREAM.md` e `THIRD_PARTY_NOTICES.md`.

Também mantenha um changelog do port. Diferencie correções próprias, sincronizações
com o projeto original e mudanças exigidas pela SDK.

## 13. Publicando

Prepare um artefato contendo somente arquivos necessários em runtime e documentação
obrigatória. Antes da publicação:

1. rode validação, Package Doctor e todos os testes;
2. instale o artefato limpo e teste sua ativação;
3. confira manifesto, versão, compatibilidade, dependências e conflitos;
4. confira licenças, atribuições e inventário de assets;
5. gere e registre o SHA-256 do artefato;
6. publique release notes com escopo e limitações;
7. escolha conscientemente o canal `dev`, `testing` ou `stable`;
8. envie o manifesto do canal ao catálogo conforme o
   [guia do marketplace](marketplace.md).

Não inclua no pacote:

- `.env`, tokens, chaves ou credenciais;
- bancos, saves ou conteúdo de campanhas;
- dependências de desenvolvimento e caches;
- código-fonte ou assets sem permissão de redistribuição;
- testes, referências e cópias integrais desnecessárias do projeto original;
- arquivos da plataforma de origem sem uso no Gravewright.

## 14. Mantendo e atualizando o port

Trate o port como um projeto próprio. Fixe a versão de origem usada em cada release e
nunca sincronize automaticamente uma atualização sem revisar licença, API e assets.

Para atualizar:

1. compare a nova versão da origem com o commit registrado;
2. classifique mudanças relevantes ao escopo do port;
3. reaplique somente mudanças necessárias ao motor independente;
4. preserve o adapter Gravewright e seus testes;
5. atualize proveniência, avisos e inventário de assets;
6. execute novamente a matriz multiplayer e o teste do artefato limpo;
7. documente divergências permanentes entre origem e port.

Use testes de contrato no adapter para descobrir cedo quando um DTO ou comportamento
documentado não corresponde mais às suposições do pacote.

## 15. Checklist final

### Direitos e proveniência

- [ ] A licença permite modificar e redistribuir cada parte incluída.
- [ ] Código, dependências e assets foram auditados separadamente.
- [ ] Autores, copyrights e avisos obrigatórios foram preservados.
- [ ] `UPSTREAM.md` fixa versão e commit da origem.
- [ ] `THIRD_PARTY_NOTICES.md` e o inventário de assets estão completos.
- [ ] O pacote não sugere afiliação ou endosso indevidos.

### Arquitetura

- [ ] O `kind` corresponde à função do pacote.
- [ ] O escopo portado, substituído e excluído está documentado.
- [ ] Toda integração usa contrato público da SDK.
- [ ] Cada capability declarada tem uso e justificativa.
- [ ] Autoridade, visibilidade e durabilidade foram definidas por ação.
- [ ] Nenhum internals privado, rota, store, DOM ou protocolo cru é requisito.

### Qualidade

- [ ] `grave package validate` passa.
- [ ] `grave package doctor` passa.
- [ ] Adapters possuem testes unitários.
- [ ] Fluxos de GM e jogadores possuem testes E2E quando aplicável.
- [ ] Reconexão, concorrência, dependências ausentes e desmontagem foram testadas.
- [ ] A UI é acessível e o desempenho foi medido com carga realista.
- [ ] O artefato final foi instalado e testado em ambiente limpo.

### Publicação e manutenção

- [ ] Manifesto, versão, compatibilidade e canais estão corretos.
- [ ] O ZIP contém somente o necessário.
- [ ] Hash e release notes foram publicados.
- [ ] README explica capacidades, configuração, limitações e build.
- [ ] Existe um processo documentado para acompanhar a origem sem sobrescrever o port.

Concluído esse checklist, o port deixa de ser apenas código que “funciona na máquina
do autor” e passa a ser um pacote Gravewright auditável, instalável e sustentável.
