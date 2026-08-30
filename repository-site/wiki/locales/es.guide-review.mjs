const revisions = new Map([
  ["SDK 1 es la línea estable.", "SDK 1 RC 1 es el candidato público congelado; los packages siguen declarando `sdkVersion: \"1\"`."],
  ["[!NOTA]", "[!NOTE]"],
  ["[!CONSEJO]", "[!TIP]"],
  ["[!ADVERTENCIA]", "[!WARNING]"],
  ["para un desplazamiento público", "para una tirada pública"],
  ["Los desplazamientos y el chat", "Las tiradas y el chat"],
  ["Nombre del rollo", "Nombre de la tirada"],
  ["**Rollo** o **Para GM**", "**Tirar** o **Para el GM**"],
  ["`actors.read` lanza", "`actors.read` habilita"],
  ["`actors.write` lanzamiento", "`actors.write` habilita"],
  ["`actors.data.write` lanza un parche de datos de enchufe validado", "`actors.data.write` habilita patches validados de datos de hoja"],
  ["calcula el desplazamiento", "evalúa la tirada"],
  ["recupérelo al desmontar", "ejecútelo durante unmount"],
  ["muestre un brindis", "muestre una notificación"],
  ["brindis debe mostrar", "la notificación debe mostrar"],
  ["Windows: pago del código fuente", "Windows: checkout del código fuente"],
  ["Al finalizar la compra", "En un checkout del código fuente"],
  ["La puerta es dinámica", "El puerto es dinámico"],
  ["## Banco tardío", "## Base de datos desactualizada"],
  ["director general", "GM"],
  ["PROPIETARIO", "OWNER"],
  ["Solo maestro", "Solo GM"],
  ['sdk.ui.toast("Addon carregado nesta campanha")', 'sdk.ui.toast("Addon cargado en esta campaña")'],
  ['console.log("configurando",', 'console.log("configurando",'],
  ['label: "Teste de " + hero.name', 'label: "Prueba: " + hero.name'],
  ['condition: "cego"', 'condition: "cegado"'],
  ["arquivo.zip", "copia-de-seguridad.zip"],
  ['"label": "Personagem"', '"label": "Personaje"'],
  ['aria-label="Nome"', 'aria-label="Nombre"'],
  [">Força <", ">Fuerza <"],
  [">Tipo: <", ">Tipo: <"],
  ['data-roll-label="Teste de Força"', 'data-roll-label="Prueba de Fuerza"'],
  [">Rolar</button>", ">Tirar</button>"],
  [">Resumo</button>", ">Resumen</button>"],
  ['": Força "', '": Fuerza "'],
  ["// remova timers, observers e listeners externos aqui", "// elimine aquí timers, observers y listeners externos"],
  ['"name": "Saudação da Mesa"', '"name": "Saludo de la mesa"'],
  ['"default": "Bem-vindos à aventura!"', '"default": "¡Bienvenidos a la aventura!"'],
  ['"label": "Mensagem de saudação"', '"label": "Mensaje de saludo"'],
  ['"description": "Texto mostrado pelo comando /saudacao."', '"description": "Texto mostrado por el comando /saudacao."'],
  ['sdk.ui.toast(mensagem || "Bem-vindos!")', 'sdk.ui.toast(mensagem || "¡Bienvenidos!")'],
]);

export function reviewSpanishGuides(guides) {
  return guides.map((guide) => {
    let section = guide.section;
    let title = guide.title;
    let summary = guide.summary;
    let body = guide.body;
    for (const [before, after] of revisions) {
      section = section.replaceAll(before, after);
      title = title.replaceAll(before, after);
      summary = summary.replaceAll(before, after);
      body = body.replaceAll(before, after);
    }
    return { ...guide, section, title, summary, body };
  });
}

export const forbiddenSpanishSdkTerms = [
  "desplazamiento público",
  "Nombre del rollo",
  "datos de enchufe",
  "recupérelo al desmontar",
  "muestre un brindis",
  "[!ADVERTENCIA]",
  "[!NOTA]",
  "[!CONSEJO]",
  "pago del código fuente",
  "Al finalizar la compra",
  "La puerta es dinámica",
  "Banco tardío",
  "director general",
  "PROPIETARIO",
  "Solo maestro",
  "Addon carregado nesta campanha",
  "arquivo.zip",
  'label: "Teste de "',
  'condition: "cego"',
  'aria-label="Nome"',
  'data-roll-label="Teste de Força"',
  "Bem-vindos à aventura!",
  "Mensagem de saudação",
];
