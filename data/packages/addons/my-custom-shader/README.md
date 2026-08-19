# My Custom Shader

A system-agnostic, reusable GM library for Gravewright custom shaders. Create a
shader once, then find it by name, description, tags, or favorite status and use
it in any campaign where the addon is active. Definitions can be imported and
exported as versioned JSON.

Custom shaders are trusted user content. Gravewright's core owns validation,
compilation, live preview, placement, and scene authority; this addon only stores
definitions explicitly created or imported by a GM.

The managed `global` SQLite scope is shared across campaigns on this installation
and readable only by a GM. On installations with multiple GMs it is an
installation-wide GM library, not a separate database per user.
