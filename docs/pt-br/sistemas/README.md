# System API v1

Sistemas definem regras, modelos de ficha, rolagens, combate, assets e conteudo inicial para um ruleset.

Materiais da System API sao MIT. O runtime do Gravewright que carrega, valida, armazena, renderiza e executa sistemas permanece Apache-2.0.

## Guias

- `criando-um-sistema.md` explica a estrutura recomendada do pacote.
- `manifest.md` resume o `manifest.json`.
- `fichas.md` documenta fichas declarativas.
- `rolagens.md` documenta a configuracao de rolagens.
- `combate.md` documenta integracao de combate.
- `pacotes-de-conteudo.md` documenta conteudo inicial.

## Layout Do Pacote

```text
data/systems/<system-id>/
  manifest.json
  schemas/
  layouts/
  rules/
  assets/
  packs/
```

O manifest e a entrada. Todos os arquivos referenciados devem permanecer dentro do diretorio do sistema.
