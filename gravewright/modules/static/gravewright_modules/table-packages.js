// Table controls expose the selected system and all ordinary extensions.
// A compendium module that requires another system stays listed only while
// selected, so the GM can still deactivate it.
export function tablePackages(packages, systemId, modules = []) {
  const active = pkg => modules.some(row => row.id === pkg.id && row.version === pkg.version);
  return packages.filter(pkg => pkg.system ? pkg.id === systemId && active(pkg) : (
    !pkg.content?.requiresSystem || pkg.content.requiresSystem.id === systemId || active(pkg)
  ));
}

// The API reports only an error code, so explain activation failures here.
const ACTIVATION_ERRORS = {
  system_required: [
    "This module requires another system, or another version of this table's system.",
    "Este módulo exige outro sistema, ou outra versão do sistema desta mesa.",
    "Este módulo requiere otro sistema, u otra versión del sistema de esta mesa.",
  ],
  incompatible_content: [
    "This module's compendiums use document types that this table's system does not register.",
    "Os compêndios deste módulo usam tipos de documento que o sistema desta mesa não registra.",
    "Los compendios de este módulo usan tipos de documento que el sistema de esta mesa no registra.",
  ],
  conflict: [
    "Table modules changed meanwhile. Review the list and try again.",
    "Os módulos da mesa mudaram nesse meio-tempo. Revise a lista e tente de novo.",
    "Los módulos de la mesa cambiaron mientras tanto. Revisa la lista e inténtalo de nuevo.",
  ],
};
const ACTIVATION_FAILED = [
  "The table modules could not be changed. Refresh and try again.",
  "Não foi possível alterar os módulos da mesa. Atualize e tente de novo.",
  "No se pudieron cambiar los módulos de la mesa. Actualiza e inténtalo de nuevo.",
];

export function activationMessage(error, language = "en") {
  const [en, pt, es] = ACTIVATION_ERRORS[error?.code] ?? ACTIVATION_FAILED;
  return language.startsWith("pt") ? pt : language.startsWith("es") ? es : en;
}
