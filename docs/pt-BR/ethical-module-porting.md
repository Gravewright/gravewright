# Como portar módulos para o Gravewright com ética

Portar um módulo começa por identificar quais partes você tem autorização para adaptar. Depois, suas funcionalidades podem ser mapeadas para os domínios do Gravewright. A licença do código, a licença do conteúdo e as permissões de uso de marcas precisam ser analisadas separadamente.

## 1. Como ler a licença de um módulo

Examine a versão exata que pretende portar. Procure arquivos como `LICENSE`, `COPYING`, `NOTICE`, o README, os cabeçalhos dos arquivos e os termos que acompanham imagens, fontes, áudios e coleções de conteúdo. O campo de licença do manifesto é uma indicação; sozinho, não resolve exceções ou materiais com licenciamento próprio.

Para cada parte, responda:

| Pergunta | O que verificar |
| --- | --- |
| Quem pode autorizar o uso? | O titular daquele código ou conteúdo. O mantenedor do módulo pode não controlar os direitos das imagens ou do material de jogo. |
| A licença cobre o quê? | Todo o pacote, somente o código, determinados arquivos ou uma seleção expressamente identificada. |
| Posso modificar? | Permissão para adaptar, traduzir e produzir versões derivadas. |
| Posso distribuir a adaptação? | Modificar para uso próprio e entregar cópias a outras pessoas são situações diferentes. |
| Posso cobrar? | Permissão comercial e eventuais restrições ao contexto de uso. Ser gratuito não dispensa as demais condições. |
| O que preciso preservar ou fornecer? | Créditos, texto da licença, avisos, indicação de alterações e código-fonte, conforme os termos aplicáveis. |
| Existem limites adicionais? | Versão da licença, exceções, materiais excluídos e autorizações restritas a determinados usos ou ambientes. |

Registre a origem, a versão e os termos encontrados. Se houver contradição ou faltar autorização para uma parte, deixe essa parte fora do porte até esclarecer com quem detém os direitos.

Um repositório público ou um download gratuito não equivalem a uma licença de adaptação e redistribuição. Na ausência de licença, não presuma essas permissões. [Referência sobre ausência de licença](https://choosealicense.com/no-permission/).

## 2. Tipos de licença e o que observar

Esta tabela orienta a leitura; as condições efetivas são as do texto e da versão aplicáveis ao material.

| Tipo | Consequência para o porte |
| --- | --- |
| Permissivas, como MIT e BSD | Em geral permitem adaptar e redistribuir, inclusive comercialmente, preservando os avisos exigidos. Confira a variante; nomes parecidos podem ter condições diferentes. |
| Apache-2.0 | Permite adaptação e distribuição com condições como preservar a licença, indicar arquivos modificados e reproduzir avisos pertinentes de `NOTICE`, quando houver. Inclui disposições sobre patentes e não concede autorização geral de uso de marcas. |
| Copyleft forte, como GPL | Permite portar, inclusive comercialmente. Ao distribuir uma obra derivada coberta, exige cumprir o copyleft e disponibilizar o código-fonte correspondente nas condições da licença. Verifique versão, exceções e compatibilidade das partes combinadas. |
| AGPL | Além do copyleft, tem uma obrigação específica de oferecer o código-fonte correspondente aos usuários que interagem remotamente com uma versão modificada, nas condições da licença. |
| Copyleft por arquivo, como MPL-2.0 | Os arquivos cobertos e suas modificações mantêm as obrigações da MPL quando distribuídos. Arquivos independentes podem ter outra licença; mover código coberto para um arquivo novo não elimina suas obrigações. |
| Licença proprietária ou personalizada | Leia as permissões expressas. Comprar ou receber acesso ao módulo não demonstra, por si só, autorização para distribuir um porte. |
| Licenciamento duplo | Verifique se é possível escolher uma das licenças ou se diferentes partes exigem cumprir condições cumulativas. |
| Sem licença identificada | Solicite autorização para reutilizar o material; não trate silêncio como permissão. |

Referências: [comparação de licenças](https://choosealicense.com/appendix/), [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0), [GPL-3.0](https://choosealicense.com/licenses/gpl-3.0/), [AGPL-3.0](https://choosealicense.com/licenses/agpl-3.0/) e [explicação da MPL-2.0](https://www.mozilla.org/en-US/MPL/2.0/FAQ/).

### Licenças de conteúdo

Textos, ilustrações e outros recursos podem adotar condições diferentes das do código. Nas licenças Creative Commons, observe os elementos presentes:

| Elemento | O que significa na análise |
| --- | --- |
| BY — atribuição | Dê os créditos exigidos, indique a licença e informe alterações quando aplicável. |
| SA — compartilhar igual | Ao compartilhar uma adaptação, use a mesma licença ou uma licença admitida como compatível. |
| NC — não comercial | O uso comercial fica fora da autorização. A análise considera a finalidade e o contexto; não basta o arquivo ser gratuito. |
| ND — sem derivações | Não autoriza compartilhar material adaptado. Uma simples mudança de formato não é automaticamente uma adaptação, mas traduzir ou transformar o conteúdo exige análise distinta. |

Os elementos se combinam: uma licença com BY, NC e ND exige observar os três. Confira também a versão. [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) e [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/).

## 3. O que pode e o que não pode ser portado

A decisão deve ser feita por componente, não apenas pelo nome ou pela licença principal do módulo.

| Situação | Decisão |
| --- | --- |
| Código com licença que autoriza adaptação e distribuição | Pode ser portado cumprindo suas condições e as das dependências utilizadas. |
| Código aberto acompanhado de imagens com direitos reservados | A autorização do código não cobre automaticamente as imagens. Exclua-as ou obtenha autorização própria. |
| Conteúdo expressamente liberado para adaptação e redistribuição | Pode integrar o porte dentro do escopo autorizado, com os avisos e condições exigidos. |
| Autorização apenas para uso pessoal ou para um ambiente específico | Não estenda essa autorização à distribuição no Gravewright. Solicite uma permissão que cubra o uso pretendido. |
| Livro, aventura, mapa ou coleção adquiridos pelo usuário | A compra não demonstra autorização para incorporar esse material a um módulo distribuído. Confira os direitos concedidos separadamente. |
| Material sem licença ou com titularidade incerta | Não o inclua enquanto a autorização necessária não estiver esclarecida. |
| Recursos produzidos por você | Podem ser usados na medida em que você detenha os direitos necessários; confira eventuais contribuições e materiais incorporados. |

Por exemplo: um módulo pode ter código permissivo, ícones de um artista e descrições licenciadas por uma editora. O porte do código pode estar autorizado enquanto o dos ícones e descrições depende de outras permissões. A licença principal não transforma o pacote inteiro em material livre para reutilização.

## 4. Cuidados com propriedade intelectual

**Separe funcionalidade de expressão.** Descrever que uma função calcula uma rolagem ajuda a mapear seu comportamento. Copiar sua implementação, seus textos ou sua apresentação envolve materiais que precisam ser examinados. Reescrever código não libera automaticamente conteúdo incorporado nem resolve todas as questões de propriedade intelectual.

**Não use conversão como justificativa.** Traduzir descrições, extrair texto de um documento ou converter uma coleção para outro formato não cria uma autorização de redistribuição. Verifique os termos do conteúdo de origem.

**Trate marcas e identidade visual separadamente.** Não presuma que a licença de software permite reutilizar logotipos ou apresentar o porte como oficial. Preserve os créditos sem sugerir parceria, aprovação ou endosso inexistentes. A própria Apache-2.0 distingue a licença do código dos direitos de marca. [Seção 6 da Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0).

**Crédito não substitui permissão.** Informar o autor é necessário em diversas licenças, mas não autoriza uma utilização que os termos não permitem. Guarde autorizações específicas e respeite exatamente o material e as condições que elas cobrem.

**A licença do Gravewright não altera a licença da origem.** A permissão para módulos independentes permite que eles adotem outras licenças, inclusive proprietárias, dentro de seu escopo. Ela não concede direitos sobre código ou recursos de terceiros, nem elimina as obrigações sobre código do núcleo copiado ou adaptado. Consulte a [política de licenciamento](../../LICENSING.pt-BR.md) e o [texto normativo da permissão para módulos independentes](../../LICENSE-EXCEPTION).

## 5. Como mapear funcionalidades para os domínios

Depois de identificar o que está autorizado, descreva cada funcionalidade pelo que ela faz e pelos dados que utiliza. Em seguida, encontre o domínio responsável no Gravewright. Os nomes e a organização interna do módulo de origem não precisam ser reproduzidos.

| Funcionalidade | Domínio do Gravewright | Como interpretar o mapeamento |
| --- | --- | --- |
| Personagens, criaturas e dados de ficha | `actors` | O personagem é um ator nativo. A apresentação específica da ficha corresponde à superfície `actor.sheet`. |
| Representação do personagem no mapa, posição, visão e condições | `tokens` | Diferencie os dados do ator dos dados de sua representação em uma cena. A superfície de ficha correspondente é `token.sheet`. |
| Inventário, equipamentos, poderes, heranças, complicações e habilidades adicionáveis | `items` + `actors` | Modele os componentes como itens; a ficha mantém os dados da associação ou cópia pertencente ao personagem, conforme a regra. O drag and drop conecta a biblioteca de itens à ficha. |
| Edição dos dados específicos de um item | `items` | Use o item nativo como documento e `item.sheet` como superfície de apresentação. |
| Mapas e objetos de cena | `maps` | Relacione os recursos aos mapas e às operações de cena disponíveis no contrato. |
| Notas, documentos, aventuras e informações compartilhadas | `journals` | Mapeie o documento e seu acesso, incluindo conteúdo reservado ao mestre. |
| Participantes, iniciativa, rodadas e turnos | `combat` | O domínio controla o estado do combate; a regra específica determina como calcular os valores. |
| Baralhos, compra, descarte e embaralhamento | `cards` | Separe as operações do baralho das regras que interpretam a carta comprada. |
| Trilhas, playlists e sons posicionais | `audio` | Mapeie o comportamento de reprodução; a autorização para distribuir o áudio continua sendo independente. |
| Bibliotecas reutilizáveis de documentos | `compendiums` | Mapeie a coleção e seus documentos, incluindo os direitos e permissões de cada conteúdo. |

Domínios cuidam dos dados e das operações. Superfícies como `actor.sheet` e `item.sheet` cuidam da apresentação. Uma ficha personalizada não implica criar outro diretório de personagens; tipos próprios de item não implicam criar outro inventário global. Use a estrutura nativa correspondente.

Para cada funcionalidade, registre:

| Campo | Exemplo |
| --- | --- |
| Comportamento | Adicionar um equipamento ao personagem e considerar seu modificador. |
| Material envolvido | Lógica de cálculo, dados do equipamento, descrição e ícone. |
| Direitos identificados | Licença e autorização de cada parte, incluindo exclusões. |
| Domínios | `items` para o equipamento; `actors` para os dados do personagem. |
| Apresentação | `item.sheet` para editar; `actor.sheet` para visualizar o equipamento na ficha. |
| Limite do porte | Implementar o comportamento autorizado e excluir descrição ou ícone sem permissão. |

Uma funcionalidade pode envolver vários domínios. Uma carta que altera a iniciativa combina `cards` e `combat`; um poder aplicado a uma criatura pode envolver `items`, `actors` e `tokens`. Se não houver uma operação correspondente no contrato, registre a lacuna em vez de presumir que qualquer comportamento da origem já tem suporte.

Os domínios e as operações disponíveis estão na [documentação da API](api.md); as superfícies estão na [documentação de módulos](modules.md). Esse mapeamento deve preservar as permissões nativas de acesso e distinguir os dados compartilhados daqueles pertencentes a cada personagem ou cena.
