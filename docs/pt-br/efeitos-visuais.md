# Efeitos visuais, shaders e partículas

Os efeitos visuais de cena fazem parte da iluminação dinâmica e são editados
pelo mestre. Desative `DYNAMIC_LIGHTING_ENABLED` para ocultar a interface e as
rotas relacionadas sem remover os dados persistidos.

## Shaders de cena

Um shader é criado no ponto do mapa em que o mestre clicar. Sua origem permanece
presa a essa coordenada do mundo durante zoom e movimento de câmera. O trecho
GLSL implementa `void main()` e escreve em `finalColor`; o runtime envolve esse
trecho com os uniforms e helpers documentados pelo editor.

O editor oferece opacidade e modos de mistura processados pelo renderizador,
incluindo normal, multiplicar, escurecer, tela e luz intensa. Por serem aplicados
fora do código fornecido, os modos funcionam com qualquer snippet válido.

A biblioteca contém 50 presets internacionalizados e visualmente distintos,
organizados em famílias como fogo, eletricidade, névoa, runas, portais, clima,
energia e sombras. A seleção de um preset atualiza o editor imediatamente.

## Partículas

O sistema possui diferentes tipos de partícula, emissores e movimentos. Os
controles incluem quantidade/taxa, duração, velocidade, direção, dispersão,
gravidade, escala, rotação, cor e opacidade. Alterações salvas aparecem na cena
ativa sem exigir F5.

## Desempenho e segurança

- Shaders e partículas são renderizados no dispositivo de cada usuário.
- Reduza intensidade, alcance, partículas ou desative shaders em GPUs limitadas.
- Código GLSL inválido deve ser corrigido no editor; erros do shader não devem
  alterar a posição do efeito nem o zoom do mapa.
- Faça backup antes de atualizar uma instalação Beta com campanhas importantes.

## Visibilidade de camadas

Efeitos, paredes e iluminação são três interruptores separados no HUD de
camadas, guardados por mesa no navegador. Esconder a iluminação não leva junto
partículas e shaders, e esconder os efeitos não mexe na visão. Portas só são
clicáveis onde estão de fato visíveis.

## Sandbox de composição do streamer

A visão de streamer compõe iluminação, paredes, partículas e shaders como se
fosse GM, mas nada disso sai do navegador: as alterações são aplicadas ao estado
local da cena e nunca chegam ao servidor, à mesa nem ao banco. É superfície de
enquadramento, não uma segunda cadeira de GM: recarregar a página descarta a
composição.
