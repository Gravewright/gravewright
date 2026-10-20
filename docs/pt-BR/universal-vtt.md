# Intercâmbio Universal VTT

[Documentação](../README.pt-BR.md) · [English](../en/universal-vtt.md) · [Map Builder](map-builder.md)

O GM pode importar um arquivo `.uvtt`, `.dd2vtt` ou `.df2vtt` como uma cena nativa
nova, ou exportar uma cena existente. Essas extensões usam o mesmo contêiner
JSON. O Gravewright aceita a versão `0.2` com uma imagem PNG ou WebP incorporada.
A [descrição do formato da Arkenforge](https://arkenforge.com/universal-vtt-files/)
documenta os campos comuns e suas coordenadas em células.

## Importação

Acesse **Nova cena → Importar Universal VTT**. A mesma ação está disponível no
painel **Projetos salvos** do Builder.

Escolha **Importar Universal VTT**, selecione o arquivo e informe o nome da cena.
A importação cria uma **cena exclusiva do GM** em Cenas, sem ativá-la para os
jogadores. Leia os avisos e ajuste a cena nativa antes de transmiti-la.
O nome do arquivo enviado nunca vira um caminho no servidor.

O fundo é uma imagem única. A importação não cria um projeto do Map Builder nem
recupera seus tiles, pinceladas, camadas ou assets individuais. Paredes, portas
e luzes são objetos nativos separados, que o GM pode editar normalmente.

| Entrada | Resultado nativo |
| --- | --- |
| Resolução e imagem | Fundo dividido em tiles e grade da cena |
| `map_origin` | Deslocamento das coordenadas; origens fracionárias mantêm o alinhamento da grade |
| `line_of_sight`, `objects_line_of_sight` | Segmentos de parede |
| Limites dos portais | Portas; paredes colineares são recortadas nas aberturas |
| Luzes | Cor, raio, intensidade e posição nativos |

As posições viram `(ponto - map_origin) × pixels_per_grid`. As dimensões da imagem
devem corresponder às dimensões declaradas em células, arredondadas para pixels.
Os metadados da imagem são removidos, e a orientação EXIF não é aplicada às
coordenadas do mapa.

A semântica dos portais varia entre consumidores. O Gravewright trata
`closed: true` como porta fechada e `closed: false` como porta aberta, e sempre
retorna um aviso. O [código do importador Foundry](https://github.com/moo-man/FVTT-DD-Import/blob/master/ddimport.js)
interpreta o segundo caso como janela. Confira essas aberturas manualmente após
o intercâmbio, especialmente seu comportamento de movimento e visão.

Cores de oito dígitos usam `AARRGGBB`; cores RGB de seis dígitos também são
aceitas. O alfa da cor escala a intensidade da luz nativa. A cor da iluminação
ambiente é aproximada pela escuridão da cena; sombras individuais por luz não
têm equivalente direto. Luzes de uma imagem marcada com iluminação incorporada
começam desativadas, assim como luzes de alcance zero. O resultado lista essas
aproximações explicitamente.
Alcances externos acima de 200 células e intensidades acima de 1 são limitados
a esses máximos nativos, com avisos, sem rejeitar o mapa inteiro.

## Exportação

Clique com o botão direito em uma cena em **Cenas** e escolha **Exportar
Universal VTT**. Prepare a exportação, confira os avisos e escolha **Baixar
Universal VTT**.

A exportação lê a cena nativa atual, incluindo seu raster mais recente e imagens
visíveis. Superfícies dinâmicas mantêm material ativo, máscara, opacidade,
rotação e apagamento por camada ao serem achatadas. Imagens ocultas do GM são
omitidas. A imagem de uma porta aberta mantém o giro de 90° em torno do pivô
explicitamente escolhido no início, centro ou fim da porta. Sprites e imagens de
estado ajustados à caixa mantêm o tamanho exibido, inclusive com escalas fora da
faixa do editor comum de imagens.
O exportador não lê rascunhos do Builder não salvos ou não publicados e
não modifica cena, projeto, recibos nem arquivos armazenados.

O download contém um fundo PNG único, informações da grade, segmentos de parede,
portais refletindo o estado aberto/fechado atual e luzes nativas ativadas.
Trancas, apresentação de portas secretas, faixas de altura e canais independentes
de barreira não são preservados nessa representação. Uma grade com pixels
fracionários é reamostrada para pixels inteiros e informada nos avisos.

Blueprints, variáveis, temporizadores, regiões de presença, tokens, cartas,
permissões, partículas, shaders, névoa, desenhos e áudio são excluídos.
Imagens individuais e materiais dinâmicos viram pixels do fundo exportado.
Cones de luz, animações, elevação e alcances ilimitados são aproximados. Leia
os avisos antes de baixar: o arquivo é uma cópia de intercâmbio, não um backup
da campanha.

## Limites e autorização

Estes limites de intercâmbio se somam à configuração da instalação:

| Recurso | Limite |
| --- | --- |
| JSON enviado/baixado | 64 MiB |
| Imagem comprimida incorporada | 48 MiB |
| Área do raster | 16.777.216 pixels, ou o menor limite configurado de mapas/Pillow |
| Objetos nativos após recortar portais | 5.000 |
| Vértices das linhas de visão | 20.000 |
| Verificações de interseção parede/portal | 2.000.000 |
| Grupos de composição de pisos | 32 |
| Trabalho acumulado de composição | 134.217.728 pixels |
| Pixels por célula da grade | Inteiro de 1 a 10.000 |
| Alcance / intensidade de entrada | Finitos, não negativos, até 1.000.000; limitados aos máximos nativos de 200 células / 1 |

Os limites configurados de upload, dimensões de imagem e quantidade de tiles
podem ser menores. Números inválidos, chaves JSON duplicadas, base64 inválido,
tipos de imagem não aceitos, animação, dimensões inconsistentes e geometria
excessiva são rejeitados antes de publicar a cena. As imagens nativas devem
pertencer à campanha; máscaras geradas também devem pertencer àquela cena exata.

Somente um GM pode importar ou exportar. A importação verifica novamente a
participação e a posse da pasta antes de confirmar, registra um recibo e remove
os tiles novos se a operação falhar. Repetir a mesma operação com o mesmo UUID
retorna a cena original; mudar o payload exige um UUID novo.

## Contrato HTTP e verificações

- `POST /api/containers/{campanha}/universal-vtt/import`: multipart `file`,
  `name`, `request_id` e `folderId` opcional; retorna
  `{scene, warnings, builderEditable: false}`.
- `GET /api/maps/{cena}/universal-vtt`: retorna
  `{filename, document, warnings}`. `document` é o JSON UVTT para download.

O serviço fica em `gravewright/maps/universal_vtt.py`. Os testes focados estão
em `gravewright/maps/tests/test_universal_vtt.py` e cobrem conversão de origem,
grade e ARGB, aberturas, ida e volta do raster, materiais dinâmicos e borrachas,
isolamento do GM, recibos, limpeza após falhas e limites de recursos. Execute-os
com o ambiente isolado descrito em [Testes](testing.md).
