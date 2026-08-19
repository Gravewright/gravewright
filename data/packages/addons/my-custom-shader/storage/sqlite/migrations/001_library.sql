CREATE TABLE custom_shader_library (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  tags TEXT NOT NULL DEFAULT '[]',
  favorite INTEGER NOT NULL DEFAULT 0,
  definition TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  CHECK (favorite IN (0, 1)),
  CHECK (length(name) BETWEEN 1 AND 100),
  CHECK (length(description) <= 500),
  CHECK (length(tags) <= 2000),
  CHECK (length(definition) <= 40000)
);
CREATE INDEX custom_shader_library_sort_idx ON custom_shader_library(favorite DESC, updated_at DESC);
