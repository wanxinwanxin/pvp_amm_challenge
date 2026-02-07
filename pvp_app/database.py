"""Database operations for PVP AMM Challenge."""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class Database:
    """Manages SQLite database for strategies and matches."""

    def __init__(self, db_path: str = "data/strategies.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create strategies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                author TEXT NOT NULL,
                solidity_source TEXT NOT NULL,
                bytecode BLOB NOT NULL,
                abi TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                gas_estimate INTEGER,
                description TEXT
            )
        """)

        # Create matches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_a_id INTEGER NOT NULL,
                strategy_b_id INTEGER NOT NULL,
                strategy_a_name TEXT NOT NULL,
                strategy_b_name TEXT NOT NULL,
                wins_a INTEGER NOT NULL,
                wins_b INTEGER NOT NULL,
                draws INTEGER NOT NULL,
                avg_edge_a REAL NOT NULL,
                avg_edge_b REAL NOT NULL,
                total_edge_a REAL NOT NULL,
                total_edge_b REAL NOT NULL,
                n_simulations INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_a_id) REFERENCES strategies(id),
                FOREIGN KEY (strategy_b_id) REFERENCES strategies(id)
            )
        """)

        # Create simulation_results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                simulation_index INTEGER NOT NULL,
                seed INTEGER NOT NULL,
                edge_a REAL NOT NULL,
                edge_b REAL NOT NULL,
                pnl_a REAL NOT NULL,
                pnl_b REAL NOT NULL,
                winner TEXT,
                steps_json TEXT,
                FOREIGN KEY (match_id) REFERENCES matches(id)
            )
        """)

        # Create users table for Twitter auth
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                twitter_id TEXT NOT NULL UNIQUE,
                twitter_username TEXT NOT NULL,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def add_strategy(
        self,
        name: str,
        author: str,
        source: str,
        bytecode: bytes,
        abi: str,
        description: str = "",
        gas_estimate: int = None
    ) -> int:
        """Add a new strategy to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO strategies (name, author, solidity_source, bytecode, abi, description, gas_estimate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, author, source, bytecode, abi, description, gas_estimate))

            strategy_id = cursor.lastrowid
            conn.commit()
            return strategy_id
        except sqlite3.IntegrityError:
            conn.close()
            raise ValueError(f"Strategy name '{name}' already exists")
        finally:
            conn.close()

    def get_strategy(self, strategy_id: int) -> Optional[Dict]:
        """Get a strategy by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_strategy_by_name(self, name: str) -> Optional[Dict]:
        """Get a strategy by name."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM strategies WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def list_strategies(self, search: str = None) -> List[Dict]:
        """List all strategies with optional search."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if search:
            cursor.execute("""
                SELECT * FROM strategies
                WHERE name LIKE ? OR author LIKE ? OR description LIKE ?
                ORDER BY created_at DESC
            """, (f"%{search}%", f"%{search}%", f"%{search}%"))
        else:
            cursor.execute("SELECT * FROM strategies ORDER BY created_at DESC")

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def add_match(self, match_data: Dict, simulation_results: List[Dict]) -> int:
        """Add a match and its simulation results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert match
        cursor.execute("""
            INSERT INTO matches (
                strategy_a_id, strategy_b_id, strategy_a_name, strategy_b_name,
                wins_a, wins_b, draws, avg_edge_a, avg_edge_b,
                total_edge_a, total_edge_b, n_simulations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_data['strategy_a_id'], match_data['strategy_b_id'],
            match_data['strategy_a_name'], match_data['strategy_b_name'],
            match_data['wins_a'], match_data['wins_b'], match_data['draws'],
            match_data['avg_edge_a'], match_data['avg_edge_b'],
            match_data['total_edge_a'], match_data['total_edge_b'],
            match_data['n_simulations']
        ))

        match_id = cursor.lastrowid

        # Insert simulation results
        for sim in simulation_results:
            cursor.execute("""
                INSERT INTO simulation_results (
                    match_id, simulation_index, seed, edge_a, edge_b,
                    pnl_a, pnl_b, winner, steps_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_id, sim['index'], sim['seed'],
                sim['edge_a'], sim['edge_b'],
                sim['pnl_a'], sim['pnl_b'],
                sim['winner'], json.dumps(sim.get('steps', []))
            ))

        conn.commit()
        conn.close()
        return match_id

    def get_strategy_matches(self, strategy_id: int) -> List[Dict]:
        """Get all matches for a strategy."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM matches
            WHERE strategy_a_id = ? OR strategy_b_id = ?
            ORDER BY created_at DESC
        """, (strategy_id, strategy_id))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_match(self, match_id: int) -> Optional[Dict]:
        """Get a match by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_match_simulations(self, match_id: int) -> List[Dict]:
        """Get all simulation results for a match."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM simulation_results
            WHERE match_id = ?
            ORDER BY simulation_index
        """, (match_id,))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            result = dict(row)
            # Parse steps_json
            if result.get('steps_json'):
                result['steps'] = json.loads(result['steps_json'])
            results.append(result)

        return results

    def get_recent_matches(self, limit: int = 10) -> List[Dict]:
        """Get recent matches."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM matches
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def add_or_update_user(self, twitter_id: str, twitter_username: str, display_name: str = None) -> int:
        """Add or update a user from Twitter OAuth."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (twitter_id, twitter_username, display_name, last_login)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(twitter_id) DO UPDATE SET
                twitter_username = excluded.twitter_username,
                display_name = excluded.display_name,
                last_login = CURRENT_TIMESTAMP
        """, (twitter_id, twitter_username, display_name))

        user_id = cursor.lastrowid
        if user_id == 0:
            # User already existed, get their ID
            cursor.execute("SELECT id FROM users WHERE twitter_id = ?", (twitter_id,))
            user_id = cursor.fetchone()[0]

        conn.commit()
        conn.close()
        return user_id

    def get_user_by_twitter_id(self, twitter_id: str) -> Optional[Dict]:
        """Get user by Twitter ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE twitter_id = ?", (twitter_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None
