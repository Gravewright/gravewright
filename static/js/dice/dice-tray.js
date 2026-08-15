

















(function () {
  const DADOS = ["F", "4", "6", "8", "10", "12", "20", "%"];
  const MAX_TERMOS = 8;
  const MAX_QUANTIDADE = 99;


  // O histórico agora sobrevive ao reload (localStorage), então ele deixou de ser
  // "as últimas rolagens" e virou a estante de rolagens da pessoa naquela mesa.
  // Por isso o teto é maior e cada entrada pode ter um nome.
  const HISTORICO = 30;
  const HISTORICO_CHAVE = "gravewright.dice.history.v1.";
  const MAX_NOME = 48;

  const trays = new Map();
  const expressionModifiers = new Map();

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[ch]);
  }

  function label(name, fallback) {
    return document.body?.dataset?.[name] || fallback;
  }



  function termoParaTexto(termo) {
    let texto = `${termo.quantidade}d${termo.faces}`;

    if (termo.descartarMenores > 0) texto += `L${termo.descartarMenores}`;
    if (termo.descartarMaiores > 0) texto += `H${termo.descartarMaiores}`;
    if (termo.explode) texto += "!";
    return texto;
  }






  function montarExpressao(termos, modificador) {
    const partes = termos.map(termoParaTexto);
    if (!partes.length) return "";

    let texto = partes.join("+");
    if (modificador > 0) texto += `+${modificador}`;
    else if (modificador < 0) texto += `-${Math.abs(modificador)}`;
    return texto;
  }

  class DiceTray {
    constructor(root) {
      this.root = root;
      this.roomId = root.dataset.roomId || "";
      this.termos = [];
      this.modificador = 0;
      this.selecionado = -1;
      this.formulaManual = "";
      this.nome = "";
      this.historico = this.carregarHistorico();
      trays.set(this.roomId, this);
      this.render();
    }

    chaveHistorico() {
      return `${HISTORICO_CHAVE}${this.roomId}`;
    }


    // Tolera o formato antigo (lista de strings) e qualquer lixo no storage: um
    // histórico corrompido não pode derrubar a bandeja inteira.
    carregarHistorico() {
      let bruto = null;
      try {
        bruto = JSON.parse(window.localStorage.getItem(this.chaveHistorico()) || "[]");
      } catch {
        return [];
      }
      if (!Array.isArray(bruto)) return [];

      const entradas = [];
      bruto.forEach((item) => {
        const expressao = typeof item === "string" ? item : String(item?.expressao || "");
        if (!expressao) return;
        const nome = typeof item === "string" ? "" : String(item?.nome || "").slice(0, MAX_NOME);
        entradas.push({ expressao, nome });
      });
      return entradas.slice(0, HISTORICO);
    }

    salvarHistorico() {
      try {
        window.localStorage.setItem(this.chaveHistorico(), JSON.stringify(this.historico));
      } catch {

        // Modo privado / cota cheia: o histórico segue valendo nesta sessão.
      }
    }



    expressao() {
      return (
        this.formulaManual.trim()
        || this.aplicarModificadores(montarExpressao(this.termos, this.modificador))
      );
    }

    aplicarModificadores(expressao) {
      let resultado = expressao;
      expressionModifiers.forEach((modifier) => {
        resultado = modifier.transform?.(resultado, this) ?? resultado;
      });
      return resultado;
    }

    adicionar(faces) {
      this.formulaManual = "";
      const existente = this.termos.find((t) => t.faces === faces);
      if (existente) {
        existente.quantidade = Math.min(existente.quantidade + 1, MAX_QUANTIDADE);
        this.selecionado = this.termos.indexOf(existente);
      } else {
        if (this.termos.length >= MAX_TERMOS) return;
        this.termos.push({
          faces, quantidade: 1, descartarMenores: 0, descartarMaiores: 0, explode: false,
        });
        this.selecionado = this.termos.length - 1;
      }
      this.render();
    }

    remover(indice) {
      this.formulaManual = "";
      this.termos.splice(indice, 1);
      if (this.selecionado >= this.termos.length) this.selecionado = this.termos.length - 1;
      this.render();
    }

    limpar() {
      this.termos = [];
      this.modificador = 0;
      this.selecionado = -1;
      this.formulaManual = "";
      this.nome = "";
      expressionModifiers.forEach((modifier) => modifier.reset?.(this));
      this.render();
    }

    ajustarTermo(campo, delta) {
      const termo = this.termos[this.selecionado];
      if (!termo) return;
      this.formulaManual = "";

      if (campo === "explode") {
        termo.explode = !termo.explode;
      } else if (campo === "quantidade") {
        termo.quantidade = Math.min(Math.max(termo.quantidade + delta, 1), MAX_QUANTIDADE);
      } else {

        const outro = campo === "descartarMenores" ? "descartarMaiores" : "descartarMenores";
        const teto = Math.max(termo.quantidade - termo[outro] - 1, 0);
        termo[campo] = Math.min(Math.max(termo[campo] + delta, 0), teto);
      }
      this.render();
    }



    async rolar(paraGm) {
      const expressao = this.expressao();
      if (!expressao || !this.roomId) return;

      const comando = paraGm ? "/gmroll" : "/roll";


      // `#` não existe na notação do avaliador, então é o separador do rótulo.
      // Sem nome a mensagem sai exatamente como antes.
      const nome = this.nome.trim().slice(0, MAX_NOME).replace(/#/g, "");
      const body = new URLSearchParams({
        csrf_token: window.csrfToken ? window.csrfToken() : "",
        campaign_id: this.roomId,
        message: `${comando} ${expressao}${nome ? ` # ${nome}` : ""}`,
      });

      const status = this.root.querySelector("[data-dice-status]");
      try {
        const res = await fetch("/game/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Accept: "application/json",
          },
          body,
          credentials: "same-origin",
        });
        if (!res.ok) {


          if (status) status.textContent = label("diceLabelInvalid", "Invalid expression.");
          return;
        }
        if (status) status.textContent = "";
        this.lembrar(expressao);
      } catch {
        if (status) status.textContent = label("diceLabelFailed", "Could not roll.");
      }
    }

    lembrar(expressao) {
      const nome = this.nome.trim().slice(0, MAX_NOME);
      const entrada = { expressao, nome };


      // Mesma fórmula com nomes diferentes são duas entradas: "2d6" e "2d6 (Dano)"
      // são atalhos distintos para quem montou.
      this.historico = [
        entrada,
        ...this.historico.filter((e) => e.expressao !== expressao || e.nome !== nome),
      ].slice(0, HISTORICO);
      this.salvarHistorico();
      this.renderHistorico();
    }

    esquecer(indice) {
      if (!this.historico[indice]) return;
      this.historico.splice(indice, 1);
      this.salvarHistorico();
      this.renderHistorico();
    }

    usar(indice) {
      const entrada = this.historico[indice];
      if (!entrada) return;
      this.formulaManual = entrada.expressao;
      this.nome = entrada.nome;
      this.render();
    }



    render() {
      this.renderPool();
      this.renderOpcoes();
      this.renderFormula();
      this.renderHistorico();
    }

    renderPool() {
      const host = this.root.querySelector("[data-dice-pool]");
      if (!host) return;
      if (!this.termos.length) {
        host.innerHTML = `<p class="dice-pool__empty">${esc(label("diceLabelEmptyPool", "Pick dice above."))}</p>`;
        return;
      }
      host.innerHTML = this.termos.map((termo, i) => `
        <button type="button" class="dice-chip ${i === this.selecionado ? "is-active" : ""}"
                data-dice-select="${i}">
          <span class="dice-chip__text">${esc(termoParaTexto(termo))}</span>
          <span class="dice-chip__remove" data-dice-remove="${i}" role="button"
                aria-label="${esc(label("diceLabelRemove", "Remove"))}">×</span>
        </button>`).join("");
    }

    renderOpcoes() {
      const host = this.root.querySelector("[data-dice-term-options]");
      if (!host) return;
      const termo = this.termos[this.selecionado];
      host.hidden = !termo;
      if (!termo) return;

      const passo = (campo, valor, rotulo) => `
        <div class="dice-step">
          <span class="dice-step__label">${esc(rotulo)}</span>
          <button type="button" data-dice-term="${campo}" data-dice-delta="-1">−</button>
          <output>${valor}</output>
          <button type="button" data-dice-term="${campo}" data-dice-delta="1">+</button>
        </div>`;

      host.innerHTML =
        passo("quantidade", termo.quantidade, label("diceLabelCount", "Dice")) +
        passo("descartarMenores", termo.descartarMenores, label("diceLabelDropLow", "Drop lowest")) +
        passo("descartarMaiores", termo.descartarMaiores, label("diceLabelDropHigh", "Drop highest")) +
        `<label class="dice-toggle">
           <input type="checkbox" data-dice-term="explode" ${termo.explode ? "checked" : ""}>
           <span>${esc(label("diceLabelExplode", "Explode (!)"))}</span>
         </label>`;
    }

    renderFormula() {
      const campo = this.root.querySelector("[data-dice-formula]");
      if (campo && document.activeElement !== campo) campo.value = this.expressao();

      const nome = this.root.querySelector("[data-dice-name]");
      if (nome && document.activeElement !== nome) nome.value = this.nome;

      const mod = this.root.querySelector("[data-dice-modifier-value]");
      if (mod) mod.textContent = this.modificador > 0 ? `+${this.modificador}` : String(this.modificador);
    }

    renderHistorico() {
      const host = this.root.querySelector("[data-dice-history]");
      if (!host) return;
      const remover = label("diceLabelHistoryRemove", "Remove from history");
      host.innerHTML = this.historico
        .map((entrada, i) => `
          <span class="dice-recent ${entrada.nome ? "dice-recent--named" : ""}">
            <button type="button" class="dice-recent__use" data-dice-reuse="${i}"
                    title="${esc(entrada.nome ? `${entrada.nome}: ${entrada.expressao}` : entrada.expressao)}">
              ${esc(entrada.nome || entrada.expressao)}
            </button>
            <button type="button" class="dice-recent__remove" data-dice-forget="${i}"
                    aria-label="${esc(remover)}" title="${esc(remover)}">×</button>
          </span>`)
        .join("");
    }
  }

  function trayFromElement(element) {
    const root = element.closest("[data-dice-tray]");
    return root ? trays.get(root.dataset.roomId || "") || null : null;
  }



  document.addEventListener("click", (event) => {
    const tray = trayFromElement(event.target);
    if (!tray) return;

    const remover = event.target.closest("[data-dice-remove]");
    if (remover) {
      event.stopPropagation();
      tray.remover(Number(remover.dataset.diceRemove));
      return;
    }

    const dado = event.target.closest("[data-dice-add]");
    if (dado) return tray.adicionar(dado.dataset.diceAdd);

    const chip = event.target.closest("[data-dice-select]");
    if (chip) {
      tray.selecionado = Number(chip.dataset.diceSelect);
      tray.render();
      return;
    }

    const passo = event.target.closest("[data-dice-term]");
    if (passo && passo.tagName === "BUTTON") {
      return tray.ajustarTermo(passo.dataset.diceTerm, Number(passo.dataset.diceDelta || 0));
    }

    const modificador = event.target.closest("[data-dice-modifier]");
    if (modificador) {
      tray.formulaManual = "";
      tray.modificador += Number(modificador.dataset.diceModifier || 0);
      tray.render();
      return;
    }

    if (event.target.closest("[data-dice-clear]")) return tray.limpar();

    const esquecer = event.target.closest("[data-dice-forget]");
    if (esquecer) {
      event.stopPropagation();
      tray.esquecer(Number(esquecer.dataset.diceForget));
      return;
    }

    const reuso = event.target.closest("[data-dice-reuse]");
    if (reuso) return tray.usar(Number(reuso.dataset.diceReuse));

    const rolar = event.target.closest("[data-dice-roll]");
    if (rolar) return void tray.rolar(rolar.dataset.diceRoll === "gm");
  });

  document.addEventListener("change", (event) => {
    const caixa = event.target.closest('[data-dice-term="explode"]');
    if (!caixa) return;
    const tray = trayFromElement(caixa);
    if (tray) tray.ajustarTermo("explode", 0);
  });


  document.addEventListener("input", (event) => {
    const campo = event.target.closest("[data-dice-formula]");
    if (campo) {
      const tray = trayFromElement(campo);
      if (tray) tray.formulaManual = campo.value;
      return;
    }

    const nome = event.target.closest("[data-dice-name]");
    if (!nome) return;
    const tray = trayFromElement(nome);
    if (tray) tray.nome = nome.value.slice(0, MAX_NOME);
  });

  document.addEventListener("keydown", (event) => {
    const campo = event.target.closest("[data-dice-formula], [data-dice-name]");
    if (!campo || event.key !== "Enter") return;
    event.preventDefault();
    const tray = trayFromElement(campo);
    if (tray) void tray.rolar(event.shiftKey);
  });

  function montar() {
    document.querySelectorAll("[data-dice-tray]").forEach((root) => {
      if (!trays.has(root.dataset.roomId || "")) new DiceTray(root);
    });
  }

  function registerExpressionModifier(id, modifier) {
    if (!id || typeof modifier?.transform !== "function") return;
    expressionModifiers.set(String(id), modifier);
    trays.forEach((tray) => tray.render());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", montar);
  } else {
    montar();
  }

  window.GravewrightDiceTray = {
    montar,
    trays,
    montarExpressao,
    termoParaTexto,
    registerExpressionModifier,
    DADOS,
  };
})();
