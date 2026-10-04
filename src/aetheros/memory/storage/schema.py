"""
SQLite schema and migrations for the memory subsystem (spec Phase 2).

Design decision -- *reuse over table explosion* (CLAUDE.md Rule 2/5). The spec
lists ~25 candidate tables (episodes, actions, outcomes, preferences, facts,
procedures, failures, predictions ...). Rather than one table per cognitive
kind, every kind persists as a single row in ``memory_items`` discriminated by
``memory_type``, carrying its full typed structure in the ``data`` JSON column
(the domain records round-trip losslessly through ``to_dict`` / ``from_dict``).
Dedicated tables exist only where a *distinct query pattern* genuinely needs
one:

* ``memory_embeddings`` -- vector search (Phase 5), separated so the hot
  metadata path never carries float arrays.
* ``entities`` / ``relationships`` -- the knowledge graph (Phase 6), which is
  queried by traversal, not by memory id.
* ``memory_links`` -- typed memory-to-memory edges (failure -> recovery, episode
  -> derived procedure).
* ``memory_tags`` / ``memory_entities`` -- normalised side tables so tag/entity
  filtering is an indexed join rather than a JSON scan.
* ``memory_access`` -- an audit of reads feeding the frequency scorer and the
  observability counters (Phase 22).

Migrations are an ordered, append-only list. ``run_migrations`` applies only the
versions newer than what ``schema_migrations`` records, so the schema evolves
without destructive rebuilds (spec Phase 2 -- "do not make destructive schema
changes without migration support").
"""

from __future__ import annotations

# Each entry: (version, tuple of DDL statements applied atomically).
MIGRATIONS: list[tuple[int, tuple[str, ...]]] = [
    (
        1,
        (
            """
            CREATE TABLE IF NOT EXISTS memory_items (
                id              TEXT PRIMARY KEY,
                memory_type     TEXT NOT NULL,
                veracity        TEXT NOT NULL,
                content         TEXT NOT NULL,
                data            TEXT NOT NULL DEFAULT '{}',
                source          TEXT NOT NULL DEFAULT '{}',
                confidence      REAL NOT NULL DEFAULT 0.5,
                importance      INTEGER NOT NULL DEFAULT 2,
                scope           TEXT NOT NULL DEFAULT 'long_term',
                status          TEXT NOT NULL DEFAULT 'active',
                evidence_count  INTEGER NOT NULL DEFAULT 1,
                access_count    INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                last_accessed_at TEXT,
                expires_at      TEXT,
                version         INTEGER NOT NULL DEFAULT 1,
                tags            TEXT NOT NULL DEFAULT '[]',
                entities        TEXT NOT NULL DEFAULT '[]',
                metadata        TEXT NOT NULL DEFAULT '{}',
                -- Promoted context columns (indexed); mirror of metadata keys.
                session_id      TEXT,
                task_id         TEXT,
                episode_id      TEXT,
                instrument_id   TEXT,
                user_id         TEXT,
                application     TEXT
            )
            """,
            "CREATE INDEX IF NOT EXISTS ix_mem_type ON memory_items(memory_type)",
            "CREATE INDEX IF NOT EXISTS ix_mem_status ON memory_items(status)",
            "CREATE INDEX IF NOT EXISTS ix_mem_created ON memory_items(created_at)",
            "CREATE INDEX IF NOT EXISTS ix_mem_accessed ON memory_items(last_accessed_at)",
            "CREATE INDEX IF NOT EXISTS ix_mem_confidence ON memory_items(confidence)",
            "CREATE INDEX IF NOT EXISTS ix_mem_session ON memory_items(session_id)",
            "CREATE INDEX IF NOT EXISTS ix_mem_task ON memory_items(task_id)",
            "CREATE INDEX IF NOT EXISTS ix_mem_instrument ON memory_items(instrument_id)",
            """
            CREATE TABLE IF NOT EXISTS memory_embeddings (
                memory_id   TEXT PRIMARY KEY,
                dim         INTEGER NOT NULL,
                vector      BLOB NOT NULL,
                model       TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL,
                FOREIGN KEY (memory_id) REFERENCES memory_items(id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS memory_links (
                id          TEXT PRIMARY KEY,
                from_id     TEXT NOT NULL,
                to_id       TEXT NOT NULL,
                link_type   TEXT NOT NULL DEFAULT 'related_to',
                weight      REAL NOT NULL DEFAULT 1.0,
                metadata    TEXT NOT NULL DEFAULT '{}'
            )
            """,
            "CREATE INDEX IF NOT EXISTS ix_link_from ON memory_links(from_id)",
            "CREATE INDEX IF NOT EXISTS ix_link_to ON memory_links(to_id)",
            """
            CREATE TABLE IF NOT EXISTS memory_tags (
                memory_id   TEXT NOT NULL,
                tag         TEXT NOT NULL,
                PRIMARY KEY (memory_id, tag),
                FOREIGN KEY (memory_id) REFERENCES memory_items(id) ON DELETE CASCADE
            )
            """,
            "CREATE INDEX IF NOT EXISTS ix_tag ON memory_tags(tag)",
            """
            CREATE TABLE IF NOT EXISTS memory_entities (
                memory_id   TEXT NOT NULL,
                entity      TEXT NOT NULL,
                PRIMARY KEY (memory_id, entity),
                FOREIGN KEY (memory_id) REFERENCES memory_items(id) ON DELETE CASCADE
            )
            """,
            "CREATE INDEX IF NOT EXISTS ix_mem_entity ON memory_entities(entity)",
            """
            CREATE TABLE IF NOT EXISTS entities (
                id          TEXT PRIMARY KEY,
                key         TEXT NOT NULL UNIQUE,
                name        TEXT NOT NULL,
                entity_type TEXT NOT NULL DEFAULT 'concept',
                attributes  TEXT NOT NULL DEFAULT '{}',
                aliases     TEXT NOT NULL DEFAULT '[]',
                confidence  REAL NOT NULL DEFAULT 0.6,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS ix_entity_name ON entities(name)",
            "CREATE INDEX IF NOT EXISTS ix_entity_type ON entities(entity_type)",
            """
            CREATE TABLE IF NOT EXISTS relationships (
                id          TEXT PRIMARY KEY,
                source_id   TEXT NOT NULL,
                target_id   TEXT NOT NULL,
                relation    TEXT NOT NULL DEFAULT 'related_to',
                weight      REAL NOT NULL DEFAULT 1.0,
                confidence  REAL NOT NULL DEFAULT 0.6,
                evidence_count INTEGER NOT NULL DEFAULT 1,
                evidence_memory_ids TEXT NOT NULL DEFAULT '[]',
                attributes  TEXT NOT NULL DEFAULT '{}',
                valid_from  TEXT NOT NULL,
                valid_to    TEXT
            )
            """,
            "CREATE INDEX IF NOT EXISTS ix_rel_source ON relationships(source_id)",
            "CREATE INDEX IF NOT EXISTS ix_rel_target ON relationships(target_id)",
            "CREATE INDEX IF NOT EXISTS ix_rel_relation ON relationships(relation)",
            """
            CREATE TABLE IF NOT EXISTS memory_access (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id   TEXT NOT NULL,
                accessed_at TEXT NOT NULL,
                context     TEXT NOT NULL DEFAULT '{}'
            )
            """,
            "CREATE INDEX IF NOT EXISTS ix_access_memory ON memory_access(memory_id)",
        ),
    ),
]


LATEST_VERSION: int = MIGRATIONS[-1][0] if MIGRATIONS else 0
