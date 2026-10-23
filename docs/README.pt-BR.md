# Documentação

[English](README.md) · [Português (Brasil)](README.pt-BR.md) · [Página do projeto](../README.pt-BR.md)

Inglês é o idioma principal da documentação. Cada guia tem uma versão correspondente em português; identificadores, nomes de APIs e comandos permanecem iguais. Os guias descrevem a implementação deste checkout, inclusive suas limitações atuais. Documentos de direção identificam separadamente as capacidades propostas.

| Guia | O que explica |
| --- | --- |
| [Executor Windows](pt-BR/windows-runner.md) | Instalação com dois cliques, execução local, atalho com ícone e dados pessoais |
| [Executor Linux](pt-BR/linux-runner.md) | Detecção da distribuição, ferramentas privadas, execução local e verificações sem perguntas |
| [Executor macOS](pt-BR/macos-runner.md) | Instalação Intel/Apple Silicon, launcher pelo Finder, ferramentas privadas e execução local |
| [Primeiros passos](pt-BR/getting-started.md) | Dependências, configuração, migrações e primeiro acesso |
| [Atualização e recuperação](pt-BR/upgrading.md) | Preparação para a 0.3.2, migrações necessárias, atualização de dependências e recuperação por backup |
| [Guia de uso](pt-BR/user-guide.md) | Campanhas, cenas, fichas, diários e fluxos da mesa |
| [Diários e referências](pt-BR/journals.md) | Inserir vínculos no texto, abrir ferramentas nativas e preservar destinos privados ao editar ou copiar campanhas |
| [Gerenciamento de campanha](pt-BR/campaign-management.md) | Área do mestre, painel pessoal, planejador de sessões, cronologia, colunas de missões, conexões, prévia de jogador e histórico/lixeira |
| [PDF System](pt-BR/pdf-system.md) | Campos manuais para PDFs não editáveis, barras do token, rolagens salvas, cálculos, mapeamentos reutilizáveis, exportação e diagnósticos |
| [Relógios de progresso](pt-BR/clocks.md) | Progresso compartilhado, público, escopo de cena e relógios fixados na mesa e no gerenciamento |
| [Pistas](pt-BR/clues.md) | Descobertas progressivas, notas privadas do mestre, revelação aos jogadores e mecanismos do MapBuilder |
| [Mapas mentais](pt-BR/mindmaps.md) | Grafos colaborativos de tópicos, vínculos autorizados com 37 tipos de recursos nativos e ações do MapBuilder |
| [Map Builder](pt-BR/map-builder.md) | Primeiro projeto, Tiles/Pintura, fundo de mapa pronto, camadas, salvamento, Objetos Inteligentes e atualização de cenas |
| [Importador/exportador Universal VTT](pt-BR/universal-vtt.md) | Fluxos de importação, mapas/paredes/portas/luzes nativos, avisos e recuperação de erros |
| [Direção dos Objetos Inteligentes](pt-BR/smart-objects-direction.md) | Etapas entregues do editor de nós, capacidades dos elementos, referências e extensões propostas |
| [Arquitetura](pt-BR/architecture.md) | Requisições, persistência, autorização e tempo real |
| [Mapa do código](pt-BR/code-map.md) | Responsabilidade de cada domínio e onde alterar |
| [Desenvolvimento](pt-BR/development.md) | Fluxo de contribuição, convenções e contratos |
| [API](pt-BR/api.md) | Fachada Python, API do navegador e transportes |
| [Módulos](pt-BR/modules.md) | Manifestos, confiança, ciclo de vida e exemplos |
| [Porte ético de módulos](pt-BR/ethical-module-porting.md) | Licenças, direitos sobre conteúdo e mapeamento para os domínios nativos |
| [Frontend](pt-BR/frontend.md) | Jinja2, Datastar, JavaScript, renderização e dependências |
| [Configuração](pt-BR/configuration.md) | Variáveis de ambiente, padrões e preferências persistidas |
| [Testes](pt-BR/testing.md) | Verificações Django, Node.js e regressões no navegador |
| [Implantação](pt-BR/deployment.md) | ASGI, Redis, armazenamento privado, backups e releases |

Políticas: [contribuição](../CONTRIBUTING.pt-BR.md), [segurança](../SECURITY.pt-BR.md), [licenciamento](../LICENSING.pt-BR.md), [permissão para módulos](../LICENSE-EXCEPTION.pt-BR.md), [avisos de terceiros](../THIRD_PARTY_NOTICES.pt-BR.md).

Para a implementação de dados, consulte os documentos existentes de [arquitetura da gramática](../gravewright/dice/grammar/ARCHITECTURE.pt-BR.md) e [notação](../gravewright/dice/grammar/notation/GRAMMAR.pt-BR.md).

Os contratos de módulos processáveis por máquina ficam em [contracts/](../gravewright/modules/contracts/), acompanhados da [nota de transporte](../gravewright/modules/contracts/transport.pt-BR.md).

Versão atual do projeto: [Gravewright 0.3.2 — Alpha](releases/0.3.2.md). As notas da release apresentam preparação de campanha, histórico/lixeira de diários, relógios e pistas, mapas mentais colaborativos, mapeamento/ações de PDF, integração do MapBuilder, Pillow 13 e seis novas migrações de banco em relação à 0.3.1. Veja [atualização e recuperação](pt-BR/upgrading.md) antes de atualizar uma instalação existente.

As notas históricas permanecem: [0.3.1](releases/0.3.1.md) cobre formulários, modelos de objetos e sincronização de cenas; [0.3.0](releases/0.3.0.md) cobre o Map Builder original e o suporte a Universal VTT; [0.2.3](releases/0.2.3.md) preserva o histórico anterior. A numeração e as informações de migração históricas descrevem aquelas releases, não a versão atual.
