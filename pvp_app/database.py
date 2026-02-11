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

        # Create matches_v2 table for n-way matches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_type TEXT NOT NULL CHECK(match_type IN ('head_to_head', 'n_way')),
                n_participants INTEGER NOT NULL CHECK(n_participants >= 2 AND n_participants <= 10),
                n_simulations INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create match_participants table for n-way match results
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

        # Create simulation_results_v2 table for n-way simulation data
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

        # Create indexes for performance
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

    # N-Way Match Methods

    def add_n_way_match(
        self,
        match_data: Dict,
        participant_results: List[Dict],
        simulation_results: List[Dict]
    ) -> int:
        """
        Add an n-way match with multiple participants.

        Args:
            match_data: Dict with keys: match_type, n_participants, n_simulations
            participant_results: List of dicts with keys: strategy_id, strategy_name,
                                placement, avg_edge, total_edge, wins
            simulation_results: List of dicts with keys: simulation_index, seed, strategy_id,
                               edge, pnl, placement, steps (optional)

        Returns:
            match_id: ID of the created match
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Insert match
            cursor.execute("""
                INSERT INTO matches_v2 (match_type, n_participants, n_simulations)
                VALUES (?, ?, ?)
            """, (
                match_data['match_type'],
                match_data['n_participants'],
                match_data['n_simulations']
            ))

            match_id = cursor.lastrowid

            # Insert participant results
            for participant in participant_results:
                cursor.execute("""
                    INSERT INTO match_participants (
                        match_id, strategy_id, strategy_name, placement,
                        avg_edge, total_edge, wins
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    match_id,
                    participant['strategy_id'],
                    participant['strategy_name'],
                    participant['placement'],
                    participant['avg_edge'],
                    participant['total_edge'],
                    participant['wins']
                ))

            # Insert simulation results
            for sim in simulation_results:
                cursor.execute("""
                    INSERT INTO simulation_results_v2 (
                        match_id, simulation_index, seed, strategy_id,
                        edge, pnl, placement, steps_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    match_id,
                    sim['simulation_index'],
                    sim['seed'],
                    sim['strategy_id'],
                    sim['edge'],
                    sim['pnl'],
                    sim['placement'],
                    json.dumps(sim.get('steps', []))
                ))

            conn.commit()
            return match_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_n_way_match(self, match_id: int) -> Optional[Dict]:
        """
        Get an n-way match by ID with all participants.

        Returns:
            Dict with match data and participants list, or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get match data
        cursor.execute("SELECT * FROM matches_v2 WHERE id = ?", (match_id,))
        match_row = cursor.fetchone()

        if not match_row:
            conn.close()
            return None

        match_data = dict(match_row)

        # Get participants
        cursor.execute("""
            SELECT * FROM match_participants
            WHERE match_id = ?
            ORDER BY placement
        """, (match_id,))

        participant_rows = cursor.fetchall()
        match_data['participants'] = [dict(row) for row in participant_rows]

        conn.close()
        return match_data

    def get_n_way_match_simulations(self, match_id: int) -> List[Dict]:
        """Get all simulation results for an n-way match, grouped by simulation."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM simulation_results_v2
            WHERE match_id = ?
            ORDER BY simulation_index, placement
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

    def get_match_type(self, match_id: int) -> Optional[str]:
        """
        Determine if a match is legacy (2-player) or n-way.

        Returns:
            'legacy' if in matches table
            'head_to_head' or 'n_way' if in matches_v2 table
            None if match not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check matches_v2 first
        cursor.execute("SELECT match_type FROM matches_v2 WHERE id = ?", (match_id,))
        row = cursor.fetchone()

        if row:
            conn.close()
            return row[0]  # 'head_to_head' or 'n_way'

        # Check legacy matches table
        cursor.execute("SELECT id FROM matches WHERE id = ?", (match_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return 'legacy'

        return None

    def get_strategy_n_way_matches(self, strategy_id: int) -> List[Dict]:
        """Get all n-way matches for a strategy (from matches_v2)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT m.*
            FROM matches_v2 m
            JOIN match_participants mp ON m.id = mp.match_id
            WHERE mp.strategy_id = ?
            ORDER BY m.created_at DESC
        """, (strategy_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_all_matches_combined(self, strategy_id: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """
        Get matches from both legacy and v2 tables, optionally filtered by strategy.
        Returns unified format with match_type indicator.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        matches = []

        # Get legacy matches
        if strategy_id:
            cursor.execute("""
                SELECT *, 'legacy' as match_type FROM matches
                WHERE strategy_a_id = ? OR strategy_b_id = ?
                ORDER BY created_at DESC
            """, (strategy_id, strategy_id))
        else:
            cursor.execute("""
                SELECT *, 'legacy' as match_type FROM matches
                ORDER BY created_at DESC
            """)

        legacy_matches = [dict(row) for row in cursor.fetchall()]
        matches.extend(legacy_matches)

        # Get v2 matches
        if strategy_id:
            cursor.execute("""
                SELECT DISTINCT m.*, m.match_type as match_type_v2
                FROM matches_v2 m
                JOIN match_participants mp ON m.id = mp.match_id
                WHERE mp.strategy_id = ?
                ORDER BY m.created_at DESC
            """, (strategy_id,))
        else:
            cursor.execute("""
                SELECT *, match_type as match_type_v2 FROM matches_v2
                ORDER BY created_at DESC
            """)

        v2_matches = [dict(row) for row in cursor.fetchall()]
        matches.extend(v2_matches)

        conn.close()

        # Sort by created_at and limit
        matches.sort(key=lambda x: x['created_at'], reverse=True)
        return matches[:limit] if limit else matches
