# Guia de atualização

O projeto ainda está em `0.x`; leia o [changelog](../../../CHANGELOG.md) antes de
atualizar. Valide cada módulo com a versão nova da SDK e execute:

```bash
npm ci
npm run typecheck
npm test
npm run grave -- doctor
```

Módulos instalados pelo marketplace devem usar apenas dependências do registry
npm oficial, incluir `package-lock.json` v2 ou v3 e não incluir `.npmrc`.
Dependências Git, URL, arquivo local, workspace, link e aliases npm são
rejeitados. Scripts de instalação permanecem desativados.

Capabilities devem manter um nome estável e expressar compatibilidade na faixa
SemVer de `requires`/`provides`. Rooms devem declarar e renderizar o protocolo e
os pontos de montagem canônicos documentados.
