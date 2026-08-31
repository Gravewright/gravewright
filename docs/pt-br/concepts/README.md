# Conceitos fundamentais

Leia estas páginas para formar um modelo mental confiável antes de desenhar um
contrato público.

1. [Arquitetura](arquitetura.md) — o que pertence ao kernel e aos módulos.
2. [Module kinds](module-kinds.md) — os cinco papéis e suas cardinalidades.
3. [Dependências e capabilities](dependencias-e-capabilities.md) — uso concreto e contratos substituíveis.
4. [Lifecycle](../surfaces/lifecycle.md) — planejamento, ativação, rollback e shutdown.
5. [Manifest](../surfaces/manifest.md) — a fronteira estática de validação.
6. [Composição](../surfaces/routes.md) — routes, middleware e slots.

A distinção principal é entre **mecanismo** e **política de produto**. O kernel
garante segurança do grafo, superfícies públicas, lifecycle e um único server.
Os módulos decidem como o VTT armazena dados, renderiza a mesa, aplica regras e
expõe recursos do produto.
