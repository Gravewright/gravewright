# Diretórios de personagens, itens e diários

Os painéis de personagens, itens e diários usam o mesmo modelo de diretório.
Isso mantém navegação, busca e organização consistentes entre os três tipos de
conteúdo.

## Organização

- Crie pastas e subpastas pelos controles no topo do painel.
- Arraste uma entrada para a pasta desejada ou para a raiz do diretório.
- Arraste pastas para reorganizar a hierarquia. Movimentos que criariam ciclos
  são rejeitados pelo servidor.
- Pastas e entradas aparecem em ordem alfabética estável. A contagem ao lado da
  pasta inclui o conteúdo de todas as subpastas.
- O Gravewright preserva, por campanha e por painel, quais pastas estavam
  expandidas neste navegador.

## Busca hierárquica

A busca ignora diferenças entre maiúsculas, minúsculas e acentos.

- Ao encontrar uma entrada, seus diretórios ancestrais ficam visíveis e são
  abertos temporariamente.
- Ao encontrar o nome de uma pasta, toda a sua subárvore é exibida.
- Ao limpar a busca, o estado de expansão anterior é restaurado.

O botão ao lado da busca recolhe todas as pastas; quando todas já estão
recolhidas, o mesmo botão expande a árvore inteira.

## Permissões

Pastas organizam conteúdo, mas não substituem as permissões de cada entrada.
Usuários continuam vendo e editando apenas os recursos autorizados para sua
função na campanha. Contagens e resultados da busca são calculados sobre o
conteúdo que o usuário pode acessar.
