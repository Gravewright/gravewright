# Documentação

[English](README.md) · [Português (Brasil)](README.pt-BR.md) · [Página do projeto](../README.pt-BR.md)

Inglês é o idioma principal da documentação. Cada guia tem uma versão correspondente em português; identificadores, nomes de APIs e comandos permanecem iguais. Os guias descrevem a implementação deste checkout, inclusive suas limitações atuais. Documentos de direção identificam separadamente as capacidades propostas.

| Guia | O que explica |
| --- | --- |
| [Executor Windows](pt-BR/windows-runner.md) | Instalação com dois cliques, execução local, atalho com ícone e dados pessoais |
| [Executor Linux](pt-BR/linux-runner.md) | Detecção da distribuição, ferramentas privadas, execução local e verificações sem perguntas |
| [Executor macOS](pt-BR/macos-runner.md) | Instalação Intel/Apple Silicon, launcher pelo Finder, ferramentas privadas e execução local |
| [Primeiros passos](pt-BR/getting-started.md) | Dependências, configuração, migrações e primeiro acesso |
| [Guia de uso](pt-BR/user-guide.md) | Campanhas, cenas, fichas, diários e fluxos da mesa |
| [Map Builder](pt-BR/map-builder.md) | Estúdio, projetos editáveis, assets próprios e geração de paredes e portas nativas |
| [Universal VTT](pt-BR/universal-vtt.md) | Importação e exportação de cenas nativas, campos aceitos e limitações do formato |
| [Direção dos Objetos Inteligentes](pt-BR/smart-objects-direction.md) | Proposta de editor de nós, capacidades dos elementos, referências e ordem de entrega |
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

Release atual: [Gravewright 0.2.3 — Alpha](releases/0.2.3.md), com importação genérica de imagens de cartas, chamadas públicas do host na inicialização e em Personalizar e tradução dos controles nativos de janela. Inclui instaladores Windows, Linux e macOS. Hosts na 0.2.1 ou 0.2.2 podem usar a atualização gerenciada normal. As [notas da 0.2.2](releases/0.2.2.md) preservam o histórico da versão anterior.
