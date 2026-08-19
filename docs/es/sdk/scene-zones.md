# Zonas de escena

Las zonas son regiones semánticas persistentes, propiedad de la campaña y expresadas en coordenadas del mundo. `scene.zones.read` lee proyecciones autorizadas y miembros observables; `scene.zones.write` crea, modifica y elimina bajo la autoridad actual de la escena.

Las geometrías iniciales son círculo, rectángulo y polígono simple de 3–256 vértices. Los límites verticales opcionales son inclusivos. La audiencia puede ser campaña, GM o usuarios explícitos. El servidor calcula membership aunque la geometría no pueda revelarse.

`zone.entered`, `zone.left` y `zone.crossed` son eventos autoritativos. Un movimiento continuo puede cruzar y terminar fuera; un teletransporte no implica trayectoria. Updates usan `expectedVersion`. Delete limpia membership derivado sin leaves sintéticos y unload no elimina estado de campaña.

