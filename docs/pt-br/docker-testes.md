# Docker De Testes

Os arquivos Docker Compose de teste vivem em `tests/` para separar infraestrutura de teste da infraestrutura principal da aplicacao.

```text
tests/docker-compose.perf.yml
tests/docker-compose.max-stress.yml
tests/docker-compose.i5-stress.yml
tests/docker-compose.chunk-stream.yml
```

Todos usam o `Dockerfile` da raiz como imagem da aplicacao, com `context: ..` quando vistos a partir de `tests/`.

## Scripts

```bash
bash tests/run_perf_test.sh
bash tests/run_max_stress.sh
bash tests/run_i5_stress.sh
bash tests/run_chunk_stream_test.sh
```

Os scripts resolvem caminhos a partir da propria pasta, entao podem ser chamados da raiz do repositorio ou de outro diretorio.

## Validacao

```bash
docker compose -f tests/docker-compose.perf.yml config
docker compose -f tests/docker-compose.max-stress.yml config
docker compose -f tests/docker-compose.i5-stress.yml config
docker compose -f tests/docker-compose.chunk-stream.yml config
```
