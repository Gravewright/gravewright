# Segurança

[English](SECURITY.md) · [Português (Brasil)](SECURITY.pt-BR.md)

## Relatar uma vulnerabilidade

Use o recurso de relato privado de vulnerabilidades da plataforma que hospeda o repositório, caso esteja habilitado. Este código-fonte não informa um e-mail de segurança nem garante que relatos privados estejam ativados. Se não houver canal privado disponível, abra uma issue pedindo contato reservado, sem incluir detalhes de exploração, credenciais ou dados dos usuários afetados.

Informe versão afetada, passos de reprodução com dados fictícios, limite de permissão afetado e impacto esperado. Remova cookies, tokens, valores do `.env` e uploads privados. O repositório não publica janela de suporte nem compromisso de prazo de resposta.

## Limites relevantes

Sessões autenticam as requisições do navegador; proprietário do VTT, papel de mestre/jogador na campanha, permissões de documentos e acesso de transmissão são verificações separadas. Um superusuário Django não é automaticamente proprietário do VTT. Chamadas HTTP que alteram estado exigem proteção CSRF; o cabeçalho configurado é `X-CSRF-Token`. Conexões WebSocket exigem origem e host correspondentes, e os comandos revalidam a autorização pertinente.

Para HTTPS, configure a origem pública e use um endpoint TLS. A verificação de origem WebSocket exige esquema, domínio e porta efetiva configurados, inclusive quando Daphne omite o esquema WebSocket. Esquemas e IPs encaminhados só são confiáveis a partir de pares conectados em `TRUSTED_PROXIES`; mantenha `--proxy-headers` do Daphne desativado e substitua cabeçalhos de encaminhamento no proxy. Siga o [guia de implantação HTTPS](docs/pt-BR/deployment.md) para a configuração completa do proxy.

Arquivos privados devem passar pelas views protegidas da aplicação. Não exponha `MEDIA_ROOT`, bancos SQLite ou backups como diretórios estáticos públicos. Trate módulos instalados como código confiável da aplicação: seu JavaScript executa na página principal, na mesma origem. Assinaturas e manifestos verificam identidade/integridade do pacote; não isolam código nem comprovam que ele seja inofensivo.

O [executor Windows](docs/pt-BR/windows-runner.md) escuta somente em `127.0.0.1` e usa um perfil local separado com debug desativado, chave pessoal persistente e um único processo Channels em memória. Suas configurações HTTP locais não são uma configuração de implantação para LAN nem proxy reverso público. As verificações de origem, host, sessão, CSRF e campanha continuam aplicáveis. Proteja a pasta de dados pessoais e seus backups com o mesmo cuidado dedicado aos dados do servidor.

A política de segurança de conteúdo atual permite `unsafe-eval` para expressões Datastar e estilos inline. Use os validadores de diários/documentos para conteúdo não confiável, sem inseri-lo como markup executável.

Consulte [configuração](docs/pt-BR/configuration.md), [módulos](docs/pt-BR/modules.md) e [avisos de terceiros](THIRD_PARTY_NOTICES.pt-BR.md) ao alterar esses limites ou atualizar dependências.
