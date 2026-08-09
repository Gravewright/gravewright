/*
 * Gravewright PDF System — controlador da ficha.
 *
 * A ideia do sistema: o PDF é a APARÊNCIA da ficha, não o depósito dos dados.
 * Cada campo do PDF é ligado a um caminho de dado, e o valor vive em
 * scoped-json-v1 (SQLite) como qualquer outra ficha. Isso é o que permite a barra
 * de HP do token ler o mesmo número que o jogador digitou no papel.
 *
 * Duas origens de PDF, mesmo modelo de dado:
 *   - templates do pacote, com mapeamento escrito à mão (mappings/pdf-fields.gw.json);
 *   - PDFs enviados pelo GM para a biblioteca da campanha, mapeados sozinhos a
 *     partir dos nomes de campo que o próprio arquivo declara.
 *
 * Como se encaixa no SDK: a ficha é `mode: "html"`, então o host carrega o
 * template, chama este controlador e só depois liga os atributos que conhece
 * (data-bind, data-action, data-text). Os campos são criados aqui já com
 * data-bind — quem grava e persiste é o host, pelo mesmo caminho de qualquer
 * outra ficha. Este controlador não inventa transporte.
 */
(() => {
  const PACKAGE_ID = "gravewright-pdf-system";
  const SHEET_TYPE = "character";

  // Quais valores do token podem ser alimentados por um campo do PDF. O caminho é
  // o MESMO que mappings/token.gw.json lê — e um teste garante que os dois não
  // se separem, senão a escolha aqui não chegaria ao token.
  //
  // As barras são bar_1 (embaixo do token) e bar_2 (em cima). Nenhuma delas quer
  // dizer "vida": esta ficha é um PDF qualquer, e quem decide o que cada barra
  // conta é quem escolhe o campo aqui.
  const BAR_SLOTS = [
    { key: "bar1Value", path: "sheet.bars.bar_1.value", label: "bar1Value" },
    { key: "bar1Max", path: "sheet.bars.bar_1.max", label: "bar1Max" },
    { key: "bar2Value", path: "sheet.bars.bar_2.value", label: "bar2Value" },
    { key: "bar2Max", path: "sheet.bars.bar_2.max", label: "bar2Max" },
    { key: "initiative", path: "sheet.init", label: "initiative" },
    { key: "defense", path: "sheet.ac", label: "defense" },
  ];

  // O mapeamento guarda o caminho CANÔNICO do servidor (core.name, sheet.hp.value)
  // porque token.gw.json lê os mesmos caminhos. Já o data-bind do host fala outro
  // vocabulário — ctx.data é { actor, system, canEdit } e a escrita reconverte
  // actor.* / system.* de volta para core.* / sheet.*. A tradução mora aqui.
  function bindingPath(canonical) {
    const path = String(canonical || "");
    if (path === "core.name") return "actor.name";
    if (path.startsWith("sheet.")) return `system.${path.slice("sheet.".length)}`;
    return path;
  }

  function readPath(source, dottedPath) {
    return String(dottedPath || "")
      .split(".")
      .reduce((cursor, key) => (cursor == null ? undefined : cursor[key]), source);
  }

  function writePath(target, dottedPath, value) {
    const keys = String(dottedPath || "").split(".");
    const last = keys.pop();
    if (!last) return;
    let cursor = target;
    for (const key of keys) {
      if (cursor[key] == null || typeof cursor[key] !== "object") cursor[key] = {};
      cursor = cursor[key];
    }
    cursor[last] = value;
  }

  // Nome de campo de PDF é texto livre: aceita ponto (hierarquia de formulário),
  // espaço e acento. Como vira segmento de um caminho pontilhado, tudo que não é
  // seguro precisa virar "_", senão "Ataque.Bônus" abriria um objeto aninhado por
  // acidente e o valor sumiria do lugar esperado.
  function safeSegment(fieldName) {
    return String(fieldName || "")
      .replace(/[^A-Za-z0-9_-]/g, "_")
      .replace(/^_+|_+$/g, "") || "campo";
  }

  window.GravewrightSDK.register({
    id: PACKAGE_ID,

    setup(sdk) {
      const t = (key, fallback) => sdk.i18n.t(`${PACKAGE_ID}.${key}`, fallback);
      const asset = sdk.package.assetUrl;

      // Um documento aberto por raiz de ficha: duas fichas lado a lado não podem
      // disputar o mesmo estado do visualizador.
      const open = new WeakMap();

      // Gravar é sempre duas coisas, na ordem que o host usa em bindHtmlSheet:
      // atualizar ctx.data e só então avisar. Chamar só ctx.onChange deixava
      // ctx.data com o valor antigo, e qualquer releitura logo em seguida —
      // remontar a ficha depois de escolher outro PDF, por exemplo — via o valor
      // que acabou de ser substituído.
      function change(ctx, path, value) {
        writePath(ctx.data, path, value);
        ctx.onChange?.(path, value);
      }

      // Ouvinte de clique-fora do seletor, por ficha. Guardado para poder ser
      // removido: um listener no document que sobrevive à ficha é vazamento.
      const outsideClick = new WeakMap();

      async function loadMapping() {
        const response = await fetch(asset("mappings/pdf-fields.gw.json"), {
          credentials: "same-origin",
          headers: { Accept: "application/json" },
        });
        if (!response.ok) throw new Error(`mapeamento ${response.status}`);
        return response.json();
      }

      async function uploadedPdfs() {
        try {
          return await sdk.assets.list({ kind: "pdf" });
        } catch (error) {
          console.warn("[gravewright-pdf-system] biblioteca indisponível", error);
          return [];
        }
      }

      function labelButtons(root) {
        for (const node of root.querySelectorAll("[data-pdf-title]")) {
          const label = t(`ui.${node.dataset.pdfTitle}`, node.dataset.pdfTitle);
          node.title = label;
          node.setAttribute("aria-label", label);
        }
        // O host não traduz atributo nem texto: quem escreve os rótulos é o
        // controlador, com o catálogo do pacote.
        for (const [attr, prefixo] of [
          ["pdfTabLabel", "ui"],
          ["pdfHeading", "ui"],
          ["pdfHint", "hint"],
        ]) {
          const seletor = `[data-${attr.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}]`;
          for (const node of root.querySelectorAll(seletor)) {
            const chave = node.dataset[attr];
            node.textContent = t(`${prefixo}.${chave}`, chave);
          }
        }
      }

      // Um seletor por valor do token, com os campos que o PDF aberto declara.
      // Sem PDF aberto não há o que escolher, e a lista fica vazia com um aviso.
      function buildBarMap(ctx, fieldNames) {
        const host = ctx.root.querySelector("[data-pdf-bar-map]");
        if (!host) return;
        host.replaceChildren();

        if (!fieldNames.length) {
          const aviso = document.createElement("p");
          aviso.className = "pdf-sheet-hint";
          aviso.textContent = t("hint.barsNeedPdf", "Open a PDF with form fields first.");
          host.append(aviso);
          return;
        }

        for (const slot of BAR_SLOTS) {
          const linha = document.createElement("label");
          linha.className = "pdf-sheet-bar-row";

          const titulo = document.createElement("span");
          titulo.textContent = t(`ui.${slot.label}`, slot.label);
          linha.append(titulo);

          const select = document.createElement("select");
          select.className = "pdf-sheet-select";
          select.dataset.bind = `system.token.bars.${slot.key}`;
          select.disabled = !ctx.data?.canEdit;

          const vazio = document.createElement("option");
          vazio.value = "";
          vazio.textContent = t("ui.barNone", "— none —");
          select.append(vazio);
          for (const name of fieldNames) {
            const opcao = document.createElement("option");
            opcao.value = name;
            opcao.textContent = name;
            select.append(opcao);
          }

          linha.append(select);
          host.append(linha);
        }

        // Trocar a origem muda só para onde o campo grava. Reconstruir a ficha
        // inteira aqui reabriria o PDF do zero — o documento pisca, a página
        // volta para a primeira, e parece que a ficha deu submit.
        host.addEventListener("change", () => {
          void remapFields(ctx).catch((error) => {
            console.error("[gravewright-pdf-system] falha ao remapear as barras", error);
          });
        });
      }

      // Um PDF enviado pelo GM não tem mapeamento escrito. Os nomes de campo vêm do
      // próprio arquivo, então cada um cai em sheet.fields.<nome> — que o schema
      // deixa aberto de propósito. Nomes conhecidos (HP, CA...) reaproveitam o
      // caminho canônico do template do pacote, e só por isso a barra do token
      // funciona num PDF que ninguém mapeou.
      function autoMapFields(fieldNames, canonicalFields, viewer, barChoices) {
        const fields = {};
        // Campo escolhido para uma barra grava direto no caminho canônico: um
        // valor num lugar só, sem espelhamento e sem escrita dupla.
        const paraBarra = new Map();
        for (const slot of BAR_SLOTS) {
          const escolhido = barChoices?.[slot.key];
          if (escolhido) paraBarra.set(escolhido, slot.path);
        }

        // Dois nomes diferentes podem virar o mesmo segmento seguro ("HP atual" e
        // "HP-atual"), e aí os dois gravariam no mesmo caminho — um apagando o
        // outro sem aviso. O sufixo mantém cada campo com o seu lugar.
        const usados = new Map();

        for (const name of fieldNames) {
          const daBarra = paraBarra.get(name);
          if (daBarra) {
            fields[name] = { path: daBarra, type: "number" };
            continue;
          }
          const known = canonicalFields?.[name];
          if (known) {
            fields[name] = { path: known.path, type: known.type };
            continue;
          }

          let segmento = safeSegment(name);
          const repetido = usados.get(segmento) || 0;
          usados.set(segmento, repetido + 1);
          if (repetido) segmento = `${segmento}_${repetido + 1}`;

          // Caixa de seleção guarda um booleano; como texto ela pediria que a
          // pessoa digitasse onde deveria marcar.
          const tipo = viewer?.fieldType?.(name) === "Btn" ? "boolean" : "string";
          fields[name] = { path: `sheet.fields.${segmento}`, type: tipo };
        }
        return fields;
      }

      // Os inputs entram com data-bind; o host os liga ao dado logo depois. Por
      // isso não há gravação manual aqui — seria um segundo caminho de escrita.
      // A cor vale para a camada inteira, não campo a campo: uma variável CSS no
      // container evita reescrever estilo em 124 inputs a cada troca.
      function applyTextColor(ctx) {
        const host = ctx.root.querySelector("[data-pdf-fields]");
        if (!host) return;
        const cor = readPath(ctx.data, "system.pdf.textColor");
        host.style.setProperty("--pdf-field-text", cor || "#111111");
      }

      function buildFields(ctx, fields, viewer) {
        const host = ctx.root.querySelector("[data-pdf-fields]");
        host.replaceChildren();
        const canEdit = Boolean(ctx.data?.canEdit);

        // Desligar a camada esconde os inputs, não os destrói: a ficha continua
        // sendo dado, e voltar a ligar não precisa recarregar nada.
        host.hidden = sdk.settings.get("showFieldOverlay", true) === false;

        for (const [pdfField, spec] of Object.entries(fields || {})) {
          const input = document.createElement("input");
          input.type =
            spec.type === "number" ? "number" : spec.type === "boolean" ? "checkbox" : "text";
          input.className = "pdf-sheet-field";
          input.dataset.pdfField = pdfField;
          input.dataset.bind = bindingPath(spec.path);
          // readOnly não trava checkbox — só campo de texto. Sem o disabled, quem
          // não pode editar ainda marcaria a caixa.
          if (input.type === "checkbox") input.disabled = !canEdit;
          else input.readOnly = !canEdit;
          input.title = pdfField;
          if (viewer) viewer.placeField(input, pdfField);
          host.append(input);
        }
        applyTextColor(ctx);
      }

      // Refaz só a camada de campos, com o documento que já está aberto. É o que
      // muda quando se escolhe outra origem para uma barra: o PDF é o mesmo.
      async function remapFields(ctx) {
        const atual = open.get(ctx.root);
        if (!atual?.viewer || !atual.fieldNames?.length) return;

        const barChoices = readPath(ctx.data, "system.token.bars") || {};
        const fields = autoMapFields(
          atual.fieldNames,
          atual.mapping?.templates?.generic?.fields,
          atual.viewer,
          barChoices,
        );
        buildFields(ctx, fields, atual.viewer);
        await atual.viewer.refresh();
        window.GravewrightHTMLSheets?.update?.(ctx.root, ctx.data);
      }

      // Decide de onde vem o PDF desta ficha. O envio do GM ganha do template do
      // pacote: se a pessoa escolheu um arquivo, é esse que ela espera ver.
      async function resolveSource(ctx, mapping) {
        const assetId = readPath(ctx.data, "system.pdf.asset") || "";
        if (assetId) {
          const found = (await uploadedPdfs()).find((item) => item.id === assetId);
          if (found) {
            return { kind: "asset", id: assetId, url: found.src, fields: null };
          }
          // Arquivo apagado da biblioteca: cai no template em vez de abrir vazio.
          console.warn("[gravewright-pdf-system] PDF enviado não está mais na biblioteca", assetId);
        }

        const available = Object.keys(mapping?.templates || {});
        // Sem nada resolvido a ficha não desenha e não cria campo algum. Com um
        // template só, cair nele é melhor do que pedir para escolher entre um.
        const templateId =
          readPath(ctx.data, "system.pdf.template") ||
          sdk.settings.get("defaultTemplate") ||
          (available.length === 1 ? available[0] : "");

        const template = mapping?.templates?.[templateId] || null;
        if (!template) return null;
        return {
          kind: "template",
          id: templateId,
          url: asset(template.file),
          fields: template.fields || {},
        };
      }

      async function build(ctx) {
        const root = ctx.root;
        const stage = root.querySelector("[data-pdf-stage]");
        const empty = root.querySelector("[data-pdf-empty]");
        const emptyText = root.querySelector("[data-pdf-empty-text]");
        const pageLabel = root.querySelector("[data-pdf-page-label]");
        const status = root.querySelector("[data-pdf-status]");

        labelButtons(root);
        emptyText.textContent = t("ui.noTemplate", "No PDF chosen yet.");

        let mapping;
        try {
          mapping = await loadMapping();
        } catch (error) {
          console.warn("[gravewright-pdf-system] mapeamento indisponível", error);
          mapping = { templates: {} };
        }

        const source = await resolveSource(ctx, mapping);
        if (!source) {
          empty.hidden = false;
          return;
        }
        empty.hidden = true;

        // O renderizador é opcional de propósito: a ficha é dado, não arquivo.
        const viewer = window.GravewrightPdfViewer || null;
        const barChoices = readPath(ctx.data, "system.token.bars") || {};
        let fields = source.fields;
        let nomesDoPdf = [];

        if (viewer) {
          try {
            const opened = await viewer.open({
              host: root.querySelector("[data-pdf-page-host]"),
              url: source.url,
              assetUrl: asset,
              page: Number(readPath(ctx.data, "system.pdf.page")) || 1,
              zoom: Number(readPath(ctx.data, "system.pdf.zoom")) || 1,
              spread: Boolean(readPath(ctx.data, "system.pdf.spread")),
              onPageChange: ({ page, pages }) => {
                pageLabel.textContent = `${page} / ${pages}`;
              },
            });
            // PDF enviado: os nomes vêm do arquivo, lidos pelo visualizador.
            nomesDoPdf = opened.fields || [];
            if (!fields) {
              fields = autoMapFields(
                opened.fields, mapping?.templates?.generic?.fields, viewer, barChoices,
              );
            } else if (opened.fields?.length) {
              // Template do pacote cujo mapeamento não bate com o arquivo — o PDF
              // foi trocado sem atualizar o mapeamento. Sem isto a ficha abre com a
              // página desenhada e nenhum campo, porque todo input mapeado aponta
              // para um nome que o arquivo não tem.
              const real = new Set(opened.fields);
              if (!Object.keys(fields).some((name) => real.has(name))) {
                console.warn(
                  `[gravewright-pdf-system] o mapeamento de "${source.id}" não bate com o PDF;`,
                  "usando os campos declarados pelo próprio arquivo",
                );
                fields = autoMapFields(
                  opened.fields, mapping?.templates?.generic?.fields, viewer, barChoices,
                );
              }
            }
            open.set(root, { viewer, source, mapping, fieldNames: nomesDoPdf });
            status.textContent = "";
          } catch (error) {
            console.warn("[gravewright-pdf-system] falha ao abrir o PDF", error);
            stage.dataset.viewerMissing = "true";
            status.textContent = t("ui.openFailed", "Could not open the PDF.");
          }
        } else {
          stage.dataset.viewerMissing = "true";
          sdk.ui.toast(t("ui.noViewer", "No PDF renderer available."), { type: "warning" });
        }

        if (!open.has(root)) open.set(root, { viewer: null, source, mapping, fieldNames: [] });

        // Só um PDF enviado pode ficar sem campos aqui: sem renderizador não há de
        // onde tirar os nomes. Template do pacote sempre tem o mapeamento à mão.
        if (!fields) {
          status.textContent = t("ui.noFieldsWithoutViewer", "Fields need the PDF renderer.");
          fields = {};
        }

        const active = open.get(root).viewer;
        buildFields(ctx, fields, active);
        buildBarMap(ctx, nomesDoPdf);
        // Os inputs nasceram depois do render() do open(), então ainda não têm
        // posição. Sem esta passada eles se empilham na origem do palco e viram
        // uma barra só no canto, com apenas o último clicável.
        await active?.refresh?.();

        // Os campos nasceram depois que o host já ligou o template. Um update
        // devolve a ligação para ele, em vez de este controlador manter um
        // segundo caminho de escrita só para os campos que criou.
        window.GravewrightHTMLSheets?.update?.(root, ctx.data);
      }

      function rebuild(ctx, current) {
        current?.viewer?.close?.();
        open.delete(ctx.root);
        void build(ctx).catch((error) => {
          console.error("[gravewright-pdf-system] falha ao trocar o PDF", error);
        });
      }

      // Lista o que dá para abrir: os templates do pacote e os PDFs que o GM
      // enviou para a biblioteca da campanha.
      async function chooseTemplate(ctx, current) {
        const picker = ctx.root.querySelector("[data-pdf-picker]");
        const button = ctx.root.querySelector('[data-action="pdf:choose"]');
        if (!picker || !ctx.data?.canEdit) return;

        if (!picker.hidden) {
          closePicker(ctx);
          return;
        }

        let mapping;
        try {
          mapping = await loadMapping();
        } catch (error) {
          console.warn("[gravewright-pdf-system] mapeamento indisponível", error);
          mapping = { templates: {} };
        }

        const options = [
          ...Object.entries(mapping?.templates || {}).map(([id, template]) => ({
            kind: "template",
            id,
            label: template.label || id,
          })),
          ...(await uploadedPdfs()).map((item) => ({
            kind: "asset",
            id: item.id,
            label: item.filename || item.id,
          })),
        ];

        picker.replaceChildren();
        if (!options.length) {
          const hint = document.createElement("p");
          hint.className = "pdf-sheet-picker-empty";
          hint.textContent = t("ui.noPdfsYet", "Upload a PDF to the asset library first.");
          picker.append(hint);
        }

        for (const option of options) {
          const entry = document.createElement("button");
          entry.type = "button";
          entry.className = "pdf-sheet-picker-option";
          entry.setAttribute("role", "option");
          entry.dataset.pdfSource = option.kind;
          entry.dataset.pdfId = option.id;
          entry.textContent = option.label;
          const chosen = option.kind === current?.source?.kind && option.id === current?.source?.id;
          entry.setAttribute("aria-selected", String(chosen));
          entry.addEventListener("click", () => {
            closePicker(ctx);
            if (chosen) return;
            // As duas origens são exclusivas: gravar uma limpa a outra, senão um
            // envio antigo continuaria ganhando do template recém-escolhido.
            change(ctx, "system.pdf.asset", option.kind === "asset" ? option.id : "");
            change(ctx, "system.pdf.template", option.kind === "template" ? option.id : "");
            // A página lembrada era do PDF anterior; abrir a página 7 de um arquivo
            // com 2 páginas não faz sentido.
            change(ctx, "system.pdf.page", 1);
            rebuild(ctx, current);
          });
          picker.append(entry);
        }

        picker.hidden = false;
        button?.setAttribute("aria-expanded", "true");

        // Clicar fora fecha. O ouvinte vive só enquanto a lista está aberta, então
        // não sobra nada preso ao documento depois que a ficha some.
        const onOutside = (event) => {
          if (picker.parentElement?.contains(event.target)) return;
          closePicker(ctx);
        };
        outsideClick.set(ctx.root, onOutside);
        document.addEventListener("click", onOutside, true);
      }

      function closePicker(ctx) {
        const picker = ctx.root.querySelector("[data-pdf-picker]");
        if (picker) picker.hidden = true;
        ctx.root.querySelector('[data-action="pdf:choose"]')?.setAttribute("aria-expanded", "false");

        const listener = outsideClick.get(ctx.root);
        if (listener) {
          document.removeEventListener("click", listener, true);
          outsideClick.delete(ctx.root);
        }
      }

      sdk.sheets.registerController(SHEET_TYPE, {
        // O host chama isto quando um campo ligado muda. Trocar a cor é só
        // repintar — reconstruir a ficha aqui reabriria o PDF a cada ajuste.
        update(ctx) {
          applyTextColor(ctx);
        },

        mount(ctx) {
          // O host não espera por mount: o trabalho assíncrono (mapeamento, pdf.js,
          // biblioteca) corre solto e se reencaixa pelo update acima.
          void build(ctx).catch((error) => {
            console.error("[gravewright-pdf-system] falha ao montar a ficha", error);
          });
        },

        // Devolver `true` reivindica a ação e impede o host de encaminhá-la como
        // ação server-side do ruleset. Todas as daqui são de cliente puro — virar
        // página não é regra de sistema, e encaminhar daria 400 a cada clique.
        onAction(action, ctx) {
          const current = open.get(ctx.root);
          const viewer = current?.viewer;

          switch (action.name) {
            case "pdf:next-page":
              void viewer?.nextPage?.();
              return true;
            case "pdf:prev-page":
              void viewer?.prevPage?.();
              return true;
            case "pdf:zoom-in":
              void viewer?.zoomBy?.(1.2);
              return true;
            case "pdf:zoom-out":
              void viewer?.zoomBy?.(1 / 1.2);
              return true;
            case "pdf:fit":
              void viewer?.fitPage?.();
              return true;
            case "pdf:spread":
              void Promise.resolve(viewer?.toggleSpread?.()).then((on) => {
                action.element?.setAttribute("aria-pressed", String(Boolean(on)));
              });
              return true;
            case "pdf:download":
              void viewer?.download?.(ctx.data?.actor?.name);
              return true;
            case "pdf:choose":
              void chooseTemplate(ctx, current);
              return true;
            default:
              // Ação desconhecida segue para o host: pode ser regra do sistema.
              return false;
          }
        },

        unmount(ctx) {
          closePicker(ctx);
          const current = open.get(ctx.root);
          if (!current) return;
          // Onde a pessoa parou faz parte da ficha: reabrir na página 1 de um PDF
          // de doze páginas e perder o lugar toda vez. Vai pelo mesmo onChange que
          // qualquer campo usa.
          const view = current.viewer?.viewState?.();
          if (view && ctx.data?.canEdit) {
            change(ctx, "system.pdf.page", view.page);
            change(ctx, "system.pdf.zoom", view.zoom);
            change(ctx, "system.pdf.spread", view.spread);
          }
          current.viewer?.close?.();
          open.delete(ctx.root);
        },
      });
    },
  });
})();
