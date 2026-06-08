# Fichas Declarativas

Fichas sao definidas por layouts JSON e schemas associados.

## Objetivo

O sistema descreve campos, grupos, acoes e apresentacao. O core renderiza e valida conforme o contrato publico.

## Regras

- Campos devem apontar para paths validos do schema.
- Acoes devem usar intents e formulas declaradas.
- Layouts nao devem depender de APIs internas do frontend.
- Scripts customizados devem usar APIs publicas de extensao.
