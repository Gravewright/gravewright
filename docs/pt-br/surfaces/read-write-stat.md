# `read`, `write` e `stat`

Todo módulo publica estes comandos inspirados em POSIX por `exports.get`.

- `read(resource)` lê um recurso pertencente ao módulo.
- `write(resource, value)` solicita uma alteração validada.
- `stat(resource?)` retorna metadados leves ou o estado atual.

Os recursos e retornos pertencem à API documentada de cada módulo. Um storage pode
oferecer `read("campaigns/42")`; um server pode retornar
`{ running: true, port: 3000 }` em `stat()`. São comandos em `exports.get`, não
atribuições diretas entre módulos.
