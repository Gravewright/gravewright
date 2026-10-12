// Local SVG masks preserve the original assets and follow the interface color.
const root = '/static/gravewright_web/vendor/rpg-icons/';
export const rpgIcons = Object.freeze({
  journal: 'comigo/Book_Open.svg',
  quest: 'comigo/Scroll_Open.svg',
  map: 'comigo/Map.svg',
  marker: 'comigo/Pin.svg',
  actors: 'comigo/Human.svg',
  items: 'comigo/Backpack.svg',
  combat: 'game-icons/lorc/crossed-swords.svg',
  objective: 'game-icons/delapouite/check-mark.svg',
  assignees: 'game-icons/lorc/rally-the-troops.svg',
  positive: 'game-icons/delapouite/sparkles.svg',
  negative: 'game-icons/lorc/skull-crossed-bones.svg',
  neutral: 'game-icons/lorc/diamond-hard.svg',
});

export function rpgIcon(name) {
  const path = rpgIcons[name];
  if (!path) throw new Error('Unknown RPG icon');
  const el = document.createElement('span');
  el.className = 'rpg-icon'; el.dataset.rpgIcon = name;
  el.setAttribute('aria-hidden', 'true');
  el.style.setProperty('--rpg-icon', `url("${root + path}")`);
  return el;
}
