# Distribuição Desktop

Como entregar o aplicativo desktop do Gravewright para os usuários finais. O build
desktop é um pacote autocontido gerado pelo PyInstaller no modo *one-dir*: ele
embute o Python, todas as dependências e o próprio projeto e oferece um launcher
nativo em PySide6 para a CLI `grave`. O launcher sobe o servidor local e abre a
mesa no navegador padrão do usuário. O usuário só
**descompacta e executa**: sem Python, sem `uv`, sem terminal.

A versão em inglês desta página é [`../distribution/desktop.md`](../distribution/desktop.md).

## 1. Gerar o pacote

O build é definido pelo `grave.spec` na raiz do repositório. A partir de um
checkout com as dependências de dev instaladas (`uv sync`):

```bash
uv run pyinstaller --noconfirm grave.spec
```

Saída: `dist/Gravewright/`, contendo:

- `Gravewright.exe`, o lançador (alvo do duplo-clique, sem console).
- `Gravewright-debug.exe`, o mesmo app, mas abre um console mostrando os logs do
  uvicorn e os tracebacks do Python. Para diagnosticar uma falha; o usuário final
  usa o exe normal.
- `_internal/`: runtime do Python, bibliotecas, templates, assets estáticos,
  schemas (compartilhado pelos dois exes).

A pasta `GravewrightData/` **não** faz parte do build. Ela é criada ao lado do exe
no primeiro uso e guarda o banco SQLite, os pacotes instalados e os uploads. Não
distribua nem versione essa pasta.

## 2. Montar o ZIP

Distribua a **pasta `Gravewright` inteira**. O exe não roda sozinho: ele precisa
do `_internal/` ao lado. Mantenha essa pasta como raiz do ZIP, para o usuário
extrair um único diretório autocontido:

```powershell
Compress-Archive -Path dist/Gravewright -DestinationPath Gravewright-1.0.0-beta.1-win64.zip
```

Nomeie o arquivo com a versão e a arquitetura, ex.:
`Gravewright-1.0.0-beta.1-win64.zip`.

## 3. Publicar

O GitHub Releases é o canal recomendado: gratuito, versionado, com link de
download direto, e o corpo da release guarda as instruções de instalação. Suba o
ZIP como asset da release e cole as instruções da próxima seção nas notas.

## 4. Notas de release prontas para colar

```markdown
## Instalação (Windows)

1. Baixe o `Gravewright-<versão>-win64.zip`.
2. Clique com o botão direito no ZIP → **Extrair Tudo**.
3. Abra a pasta `Gravewright` extraída e execute o **Gravewright.exe**.
4. Pressione **Start Gravewright**. A mesa abrirá no navegador padrão.
5. Se o Windows mostrar "O Windows protegeu o seu PC": clique em **Mais informações**
   → **Executar assim mesmo**. (O app ainda não é assinado, então esse aviso é esperado.)

Seus dados (campanhas, uploads, pacotes instalados) ficam na pasta `GravewrightData`,
criada ao lado do app. Faça backup dela para preservar seus jogos; apague-a para
começar do zero.

O launcher também oferece Doctor, Backup, Restore, gerenciamento de pacotes,
acesso à pasta de dados e logs ao vivo sem exigir um terminal.
```

## Configuração (`.env`)

O app congelado lê um `.env` opcional colocado **ao lado do `Gravewright.exe`** (a
pasta que o usuário extrai). Os valores ali têm precedência sobre os defaults
embutidos, então é a forma suportada de configurar uma cópia instalada. Não edite
nada dentro de `_internal/`: essa pasta é sobrescrita a cada atualização.

```dotenv
# dist/Gravewright/.env  (opcional)
APP_NAME=Minha Mesa
SESSION_SECRET=troque-por-uma-string-longa-e-aleatoria
```

Observações:
- Alguns valores são fixados pelo lançador e não podem ser sobrescritos pelo
  `.env`, a menos que o lançador ainda não os defina: ele força `ALLOWED_HOSTS=*`
  (janela só loopback) e, quando você não os define, `DATABASE_URL` e
  `GRAVEWRIGHT_DATA_DIR` (apontando para `GravewrightData/` ao lado do exe).
- Se sobrescrever `GRAVEWRIGHT_DATA_DIR` ou `DATABASE_URL`, use **caminhos
  absolutos**: caminhos relativos são resolvidos contra uma pasta interna, não
  contra o exe.
- Deixar o `.env` ausente é normal; o app roda com defaults locais sensatos.

## Observações e ressalvas

- **Navegador**: a mesa roda no navegador padrão do usuário. O launcher PySide6
  permanece aberto para parar o servidor e executar comandos de manutenção.
- **SmartScreen**: executáveis não assinados disparam o "O Windows protegeu o seu
  PC". O usuário contorna com **Mais informações → Executar assim mesmo**. Para
  eliminar o aviso, assine o exe com um certificado Authenticode (um certificado EV
  remove na hora; um certificado comum ganha reputação com o tempo).
- **Falsos positivos de antivírus**: executáveis do PyInstaller às vezes são
  marcados por heurística. A assinatura de código reduz isso; reporte falsos
  positivos ao fornecedor se ocorrerem.
- **Build por plataforma**: um build feito no Windows roda só no Windows. Gere o
  build no macOS/Linux para essas plataformas.

## Diagnosticar uma falha ao abrir

Rode o **`Gravewright-debug.exe`**: ele abre um console com os logs do servidor ao
vivo e qualquer traceback do Python, que é a forma mais rápida de ver por que o exe
normal falhou.

Pegadinha de build: se um rebuild falhar com `PermissionError [WinError 32] ... is
being used by another process` em `dist/Gravewright`, feche completamente o
launcher e seu console de debug antes de gerar o build novamente.
