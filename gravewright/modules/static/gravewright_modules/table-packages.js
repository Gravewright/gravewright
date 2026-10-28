// Table controls expose the selected system and all ordinary extensions.
export function tablePackages(packages, systemId, modules = []) {
  return packages.filter(pkg => !pkg.system || (
    pkg.id === systemId && modules.some(active => active.id === pkg.id && active.version === pkg.version)
  ));
}
