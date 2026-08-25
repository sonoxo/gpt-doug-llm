import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { DatabaseSync } from 'node:sqlite';

export interface HarvestEvent {
  id?: string;
  type: string;
  source?: string;
  payload?: unknown;
  timestamp?: string;
}

export class TelemetryStore {
  private readonly db: DatabaseSync;

  constructor(dbPath = resolve(process.cwd(), 'database.sql')) {
    mkdirSync(dirname(dbPath), { recursive: true });
    this.db = new DatabaseSync(dbPath);
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS sonoxo_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT,
        type TEXT NOT NULL,
        source TEXT,
        payload_json TEXT,
        received_at TEXT NOT NULL
      );
    `);
  }

  ingest(event: HarvestEvent) {
    const receivedAt = new Date().toISOString();
    const statement = this.db.prepare(`
      INSERT INTO sonoxo_events (event_id, type, source, payload_json, received_at)
      VALUES (?, ?, ?, ?, ?)
    `);
    const result = statement.run(
      event.id ?? null,
      event.type,
      event.source ?? null,
      JSON.stringify(event.payload ?? null),
      receivedAt,
    );
    return { rowId: Number(result.lastInsertRowid), receivedAt };
  }

  count(): number {
    const row = this.db.prepare('SELECT COUNT(*) AS count FROM sonoxo_events').get() as { count: number };
    return Number(row.count);
  }

  close() {
    this.db.close();
  }
}
