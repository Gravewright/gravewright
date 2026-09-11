# Licenciamento

[English](LICENSING.md) · [Português (Brasil)](LICENSING.pt-BR.md)

## Concessão de licença do projeto

Salvo indicação diferente em um arquivo ou aviso de terceiros preservado, o código próprio, a documentação e os recursos originais do Gravewright usam **GNU General Public License, versão 3 somente**, com a permissão adicional de [LICENSE-EXCEPTION](LICENSE-EXCEPTION).

Você pode redistribuir e modificar esse material sob a GPL versão 3 publicada pela Free Software Foundation. Não é concedida a opção de usar uma versão posterior. O projeto é distribuído sem garantia, inclusive garantias implícitas de comercialização ou adequação a uma finalidade específica, na extensão permitida por lei. Consulte [LICENSE](LICENSE) para os termos completos.

O texto da GPL é preservado sem alterações. A expressão “or any later version” no exemplo do apêndice não é a concessão de licença do projeto; a concessão acima especifica somente a versão 3.

## Módulos independentes

O projeto permite expressamente módulos escritos de forma independente sob qualquer licença, inclusive proprietária, **usando ou não suas APIs**. Trata-se de uma permissão adicional prevista na seção 7 da GPLv3; [LICENSE-EXCEPTION](LICENSE-EXCEPTION) é o texto com efeito normativo. A [tradução em português](LICENSE-EXCEPTION.pt-BR.md) é informativa.

| Situação | Política do projeto |
| --- | --- |
| Módulo original usando SDK do navegador, interfaces Python, HTTP ou WebSockets | Qualquer licença para o módulo, observando a permissão adicional e suas dependências |
| Módulo original usando interfaces internas ou outro mecanismo | Mesma permissão; sem promessa de estabilidade da API ou suporte técnico |
| Modificações do núcleo distribuídas a terceiros | GPL-3.0-only continua aplicável ao núcleo, inclusive obrigações de fornecer o código-fonte |
| Implementação do núcleo copiada para um módulo | O material copiado/adaptado continua sujeito à sua licença; o nome “módulo” não é uma exceção |
| Mapas, livros, músicas, PDFs, dados de campanhas ou outros uploads | Não há transferência de propriedade nem aplicação automática da GPL; valem os termos do titular |
| Código ou recursos de terceiros incluídos | Preservar e cumprir suas próprias licenças e avisos |

Um módulo pago pode ser aberto ou proprietário. A permissão abrange ambos. Ela não concede direitos sobre recursos de outras pessoas nem elimina obrigações copyleft de dependências. Somente o material cujos titulares tenham concedido a permissão se beneficia dela.

## Contribuições e avisos

Ao enviar intencionalmente contribuições originais para inclusão no núcleo, você as oferece sob GPL-3.0-only com a mesma permissão adicional para módulos. Cada contribuidor mantém seus direitos autorais. Identifique material reutilizado e sua licença; não substitua avisos originais por avisos do projeto. Consulte [CONTRIBUTING.pt-BR.md](CONTRIBUTING.pt-BR.md).

Para um novo arquivo próprio, pode-se usar este cabeçalho curto em inglês:

```text
Licensed under GNU GPL version 3 only, with the Gravewright Independent Module
Permission. See LICENSE, LICENSE-EXCEPTION and LICENSING.md in the source root.
```

Não o adicione a arquivos de terceiros. A referência SPDX personalizada de `pyproject.toml` identifica o conjunto GPL-3.0-only mais a permissão para módulos; seu texto está em [LICENSES/LicenseRef-Gravewright-GPL-3.0-only-with-module-permission.txt](LICENSES/LicenseRef-Gravewright-GPL-3.0-only-with-module-permission.txt). É uma referência definida pelo projeto, não uma exceção cadastrada na lista SPDX nem uma afirmação de aprovação separada da permissão pela OSI. O identificador da licença GPL subjacente é `GPL-3.0-only`.

## Distribuição

Distribuições devem incluir `LICENSE`, `LICENSE-EXCEPTION`, esta política, [THIRD_PARTY_NOTICES.pt-BR.md](THIRD_PARTY_NOTICES.pt-BR.md) e os arquivos de licença de terceiros aplicáveis. Confira o conteúdo efetivo da release, inclusive wheels, JavaScript, fontes e bibliotecas nativas; o inventário do código-fonte não descreve automaticamente toda imagem de implantação possível.

A permissão usa o mecanismo da [seção 7 da GPLv3](https://www.gnu.org/licenses/gpl-3.0.html#section7). A [discussão do projeto GNU sobre plugins](https://www.gnu.org/licenses/gpl-faq.en.html#GPLPlugins) explica por que uma política deve considerar a interação entre programas, sem depender apenas do nome “plugin”. A permissão própria acima implementa a política mais ampla de integração desejada.
