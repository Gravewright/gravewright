# Contribuindo com o Gravewright

[English](CONTRIBUTING.md) · [Português (Brasil)](CONTRIBUTING.pt-BR.md)

Contribuições podem melhorar código, testes, acessibilidade, documentação, traduções ou exemplos. Comece pela [instalação local](docs/pt-BR/getting-started.md) e pela [arquitetura](docs/pt-BR/architecture.md).

## Preparar uma alteração

1. Para funcionalidades grandes ou mudanças de API, descreva o problema e o comportamento proposto em uma issue para discutir compatibilidade com mantenedores e autores de módulos. Correções pequenas podem ir direto para um pull request.
2. Trabalhe em uma branch do seu checkout. Mantenha o escopo focado e preserve alterações não relacionadas.
3. Siga os padrões existentes de serviços, permissões, transações e eventos do domínio. O guia de [desenvolvimento](docs/pt-BR/development.md) explica onde alterar cada responsabilidade.
4. Execute as verificações relevantes do guia de [testes](docs/pt-BR/testing.md). Para permissões ou persistência, cubra usuários autorizados e não autorizados, repetição de requisições e conflitos de versão.
5. Atualize a documentação em inglês e a correspondente em português quando mudar comportamento ou instalação. Preserve identificadores e comandos entre traduções.
6. Descreva problema, comportamento resultante, validação e limitações no pull request. Inclua capturas quando houver mudanças visuais; use dados fictícios de campanha.

## Código e documentação

Use inglês em novos comentários, docstrings, documentação de APIs e identificadores. Explique responsabilidades, limites de confiança, efeitos colaterais e restrições pouco óbvias. Evite comentários que apenas repitam uma instrução. Funções públicas devem explicar entradas, retornos, suposições de permissão e exceções relevantes quando isso não estiver claro na assinatura.

Mantenha alterações de esquema em migrações. Não mude o significado de uma migração já publicada. Não edite `frontend-contract.js` diretamente; altere o contrato-fonte e execute o gerador. Preserve cabeçalhos de direitos autorais, licenças e avisos ao trabalhar com recursos de terceiros.

Não inclua `.env`, bancos, documentos enviados, módulos instalados, chaves privadas, sessões de navegador ou `test-results/` nos commits. Use contas fictícias e recursos que você possa distribuir nas fixtures.

Atualmente não há configuração global de formatador/linter nem workflow de CI que defina verificações adicionais obrigatórias. Siga o estilo próximo e informe os comandos efetivamente executados; não declare aprovação de CI sem que ela tenha ocorrido.

## Licenciamento das contribuições

Ao enviar intencionalmente uma contribuição original ao núcleo, você a oferece sob **GPL-3.0-only com a Permissão para Módulos Independentes do Gravewright**. Você mantém seus direitos autorais. Confirme que pode contribuir com o material e identifique licenças separadas. Consulte [LICENSING.pt-BR.md](LICENSING.pt-BR.md) e [LICENSE-EXCEPTION.pt-BR.md](LICENSE-EXCEPTION.pt-BR.md).

Módulos de terceiros desenvolvidos de forma independente podem usar qualquer licença conforme essa permissão, utilizando ou não as APIs fornecidas. Contribuir com o núcleo é diferente de distribuir um módulo independente. Ao adicionar uma dependência, documente origem, versão, licença e avisos nos dois arquivos de avisos de terceiros e preserve os textos necessários.

## Comunicação

Trate as pessoas com respeito, descreva comportamentos observáveis e forneça feedback que permita agir. Relatos de bugs devem incluir versão do projeto, sistema operacional, versões de Python/navegador, passos mínimos, resultado esperado e observado e logs sem dados sensíveis. Use as issues para problemas comuns e [SECURITY.pt-BR.md](SECURITY.pt-BR.md) para vulnerabilidades.
