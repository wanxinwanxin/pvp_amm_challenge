"""Statistics calculator for strategies and matches."""

from typing import Dict, List, Tuple
from collections import defaultdict


class StatsCalculator:
    """Calculate statistics for strategies and matches."""

    def __init__(self, db):
        self.db = db

    def get_strategy_stats(self, strategy_id: int) -> Dict:
        """Calculate comprehensive stats for a strategy."""
        matches = self.db.get_strategy_matches(strategy_id)

        if not matches:
            return {
                'total_matches': 0,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'win_rate': 0.0,
                'avg_edge': 0.0,
                'best_edge': 0.0,
                'worst_edge': 0.0,
                'total_simulations': 0
            }

        wins = 0
        losses = 0
        draws = 0
        total_edge = 0.0
        edges = []

        for match in matches:
            # Determine if this strategy was A or B
            is_strategy_a = match['strategy_a_id'] == strategy_id

            if is_strategy_a:
                if match['wins_a'] > match['wins_b']:
                    wins += 1
                elif match['wins_a'] < match['wins_b']:
                    losses += 1
                else:
                    draws += 1
                edge = match['avg_edge_a']
            else:
                if match['wins_b'] > match['wins_a']:
                    wins += 1
                elif match['wins_b'] < match['wins_a']:
                    losses += 1
                else:
                    draws += 1
                edge = match['avg_edge_b']

            total_edge += edge
            edges.append(edge)

        total_matches = len(matches)
        win_rate = wins / total_matches if total_matches > 0 else 0.0

        return {
            'total_matches': total_matches,
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'win_rate': win_rate,
            'avg_edge': total_edge / total_matches if total_matches > 0 else 0.0,
            'best_edge': max(edges) if edges else 0.0,
            'worst_edge': min(edges) if edges else 0.0,
            'total_simulations': sum(m['n_simulations'] for m in matches)
        }

    def get_head_to_head(self, strategy_a_id: int, strategy_b_id: int) -> Dict:
        """Get head-to-head record between two strategies."""
        all_matches = self.db.get_strategy_matches(strategy_a_id)

        # Filter to only matches between these two strategies
        h2h_matches = [
            m for m in all_matches
            if (m['strategy_a_id'] == strategy_b_id or m['strategy_b_id'] == strategy_b_id)
        ]

        if not h2h_matches:
            return {
                'matches_played': 0,
                'a_wins': 0,
                'b_wins': 0,
                'draws': 0,
                'a_win_rate': 0.0
            }

        a_wins = 0
        b_wins = 0
        draws = 0

        for match in h2h_matches:
            # Figure out which side strategy_a was on
            if match['strategy_a_id'] == strategy_a_id:
                if match['wins_a'] > match['wins_b']:
                    a_wins += 1
                elif match['wins_a'] < match['wins_b']:
                    b_wins += 1
                else:
                    draws += 1
            else:
                if match['wins_b'] > match['wins_a']:
                    a_wins += 1
                elif match['wins_b'] < match['wins_a']:
                    b_wins += 1
                else:
                    draws += 1

        total = len(h2h_matches)

        return {
            'matches_played': total,
            'a_wins': a_wins,
            'b_wins': b_wins,
            'draws': draws,
            'a_win_rate': a_wins / total if total > 0 else 0.0
        }

    def get_leaderboard(self, sort_by: str = 'win_rate', limit: int = 100) -> List[Dict]:
        """
        Get leaderboard of strategies.

        Args:
            sort_by: 'win_rate', 'matches', 'avg_edge'
            limit: Max number of strategies to return

        Returns:
            List of dicts with strategy info and stats
        """
        strategies = self.db.list_strategies()

        leaderboard = []
        for strat in strategies:
            stats = self.get_strategy_stats(strat['id'])

            # Only include strategies with at least 1 match
            if stats['total_matches'] > 0:
                leaderboard.append({
                    'id': strat['id'],
                    'name': strat['name'],
                    'author': strat['author'],
                    'created_at': strat['created_at'],
                    **stats
                })

        # Sort
        if sort_by == 'win_rate':
            leaderboard.sort(key=lambda x: (x['win_rate'], x['total_matches']), reverse=True)
        elif sort_by == 'matches':
            leaderboard.sort(key=lambda x: x['total_matches'], reverse=True)
        elif sort_by == 'avg_edge':
            leaderboard.sort(key=lambda x: x['avg_edge'], reverse=True)

        return leaderboard[:limit]

    def get_matchup_matrix(self, strategy_ids: List[int]) -> Dict[Tuple[int, int], Dict]:
        """
        Get head-to-head matrix for a list of strategies.

        Returns:
            Dict mapping (strategy_a_id, strategy_b_id) -> h2h_stats
        """
        matrix = {}

        for i, strat_a in enumerate(strategy_ids):
            for strat_b in strategy_ids[i+1:]:
                h2h = self.get_head_to_head(strat_a, strat_b)
                matrix[(strat_a, strat_b)] = h2h

        return matrix

    def get_opponent_breakdown(self, strategy_id: int) -> List[Dict]:
        """
        Get breakdown of performance against each opponent.

        Returns:
            List of dicts with opponent name and record
        """
        matches = self.db.get_strategy_matches(strategy_id)

        # Group by opponent
        opponents = defaultdict(lambda: {'wins': 0, 'losses': 0, 'draws': 0, 'matches': []})

        for match in matches:
            # Determine opponent
            is_strategy_a = match['strategy_a_id'] == strategy_id

            if is_strategy_a:
                opponent_id = match['strategy_b_id']
                opponent_name = match['strategy_b_name']
                won = match['wins_a'] > match['wins_b']
                lost = match['wins_a'] < match['wins_b']
            else:
                opponent_id = match['strategy_a_id']
                opponent_name = match['strategy_a_name']
                won = match['wins_b'] > match['wins_a']
                lost = match['wins_b'] < match['wins_a']

            if won:
                opponents[opponent_id]['wins'] += 1
            elif lost:
                opponents[opponent_id]['losses'] += 1
            else:
                opponents[opponent_id]['draws'] += 1

            opponents[opponent_id]['name'] = opponent_name
            opponents[opponent_id]['matches'].append(match['id'])

        # Convert to list and calculate win rate
        breakdown = []
        for opp_id, data in opponents.items():
            total = data['wins'] + data['losses'] + data['draws']
            win_rate = data['wins'] / total if total > 0 else 0.0

            breakdown.append({
                'opponent_id': opp_id,
                'opponent_name': data['name'],
                'wins': data['wins'],
                'losses': data['losses'],
                'draws': data['draws'],
                'total_matches': total,
                'win_rate': win_rate,
                'match_ids': data['matches']
            })

        # Sort by total matches
        breakdown.sort(key=lambda x: x['total_matches'], reverse=True)

        return breakdown
