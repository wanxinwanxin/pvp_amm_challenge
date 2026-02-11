"""
Database Migration: Add N-Way Match Support
===========================================

This migration adds support for n-way matches (3-10 strategies competing simultaneously).

Changes:
- Adds matches_v2 table for n-way matches
- Adds match_participants table for participant results
- Adds simulation_results_v2 table for n-way simulation data
- Adds indexes for performance
- Preserves all existing data (additive only, no destructive changes)

Usage:
    python -m pvp_app.migrations.001_n_way_support

Rollback:
    python -m pvp_app.migrations.001_n_way_support --rollback
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pvp_app.database import Database


def migrate_up(db_path: str = "data/strategies.db"):
    """Apply the migration (add new tables)."""
    print(f"🔄 Applying migration to {db_path}...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if migration already applied
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='matches_v2'")
        if cursor.fetchone():
            print("⚠️  Migration already applied (matches_v2 table exists)")
            return

        print("📝 Creating matches_v2 table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_type TEXT NOT NULL CHECK(match_type IN ('head_to_head', 'n_way')),
                n_participants INTEGER NOT NULL CHECK(n_participants >= 2 AND n_participants <= 10),
                n_simulations INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        print("📝 Creating match_participants table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                strategy_id INTEGER NOT NULL,
                strategy_name TEXT NOT NULL,
                placement INTEGER NOT NULL CHECK(placement > 0),
                avg_edge REAL NOT NULL,
                total_edge REAL NOT NULL,
                wins INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (match_id) REFERENCES matches_v2(id) ON DELETE CASCADE,
                FOREIGN KEY (strategy_id) REFERENCES strategies(id)
            )
        """)

        print("📝 Creating simulation_results_v2 table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_results_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                simulation_index INTEGER NOT NULL,
                seed INTEGER NOT NULL,
                strategy_id INTEGER NOT NULL,
                edge REAL NOT NULL,
                pnl REAL NOT NULL,
                placement INTEGER NOT NULL,
                steps_json TEXT,
                FOREIGN KEY (match_id) REFERENCES matches_v2(id) ON DELETE CASCADE,
                FOREIGN KEY (strategy_id) REFERENCES strategies(id)
            )
        """)

        print("🔍 Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_match_participants_match_id
            ON match_participants(match_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_match_participants_strategy_id
            ON match_participants(strategy_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_simulation_results_v2_match_id
            ON simulation_results_v2(match_id)
        """)

        print("💾 Creating migration tracking table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT INTO schema_migrations (version, name) VALUES (1, 'n_way_match_support')
        """)

        conn.commit()
        print("✅ Migration completed successfully!")

        # Verify tables created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Current tables: {', '.join(tables)}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def migrate_down(db_path: str = "data/strategies.db"):
    """Rollback the migration (remove new tables)."""
    print(f"⏪ Rolling back migration from {db_path}...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("🗑️  Dropping simulation_results_v2 table...")
        cursor.execute("DROP TABLE IF EXISTS simulation_results_v2")

        print("🗑️  Dropping match_participants table...")
        cursor.execute("DROP TABLE IF EXISTS match_participants")

        print("🗑️  Dropping matches_v2 table...")
        cursor.execute("DROP TABLE IF EXISTS matches_v2")

        print("🗑️  Removing migration record...")
        cursor.execute("DELETE FROM schema_migrations WHERE version = 1")

        conn.commit()
        print("✅ Rollback completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Rollback failed: {e}")
        raise
    finally:
        conn.close()


def validate_migration(db_path: str = "data/strategies.db"):
    """Validate that the migration was applied correctly."""
    print(f"🔍 Validating migration...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check tables exist
        required_tables = ['matches_v2', 'match_participants', 'simulation_results_v2']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in required_tables:
            if table in existing_tables:
                print(f"✅ Table {table} exists")
            else:
                print(f"❌ Table {table} missing!")
                return False

        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        required_indexes = [
            'idx_match_participants_match_id',
            'idx_match_participants_strategy_id',
            'idx_simulation_results_v2_match_id'
        ]

        for index in required_indexes:
            if index in indexes:
                print(f"✅ Index {index} exists")
            else:
                print(f"⚠️  Index {index} missing (may not be critical)")

        print("✅ Migration validation passed!")
        return True

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database migration for n-way match support")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback the migration (remove new tables)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the migration was applied correctly"
    )
    parser.add_argument(
        "--db",
        default="data/strategies.db",
        help="Path to database file (default: data/strategies.db)"
    )

    args = parser.parse_args()

    if args.validate:
        validate_migration(args.db)
    elif args.rollback:
        migrate_down(args.db)
    else:
        migrate_up(args.db)
        validate_migration(args.db)
