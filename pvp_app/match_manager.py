"""Match execution and management."""

from typing import Tuple, Dict, List
import sys
from pathlib import Path
import json

# Add parent directory to path to import amm_competition
sys.path.insert(0, str(Path(__file__).parent.parent))

from amm_competition.competition.match import MatchRunner, HyperparameterVariance
from amm_competition.competition.config import (
    BASELINE_SETTINGS,
    BASELINE_VARIANCE,
    build_base_config,
    resolve_n_workers
)
from amm_competition.evm.adapter import EVMStrategyAdapter


class MatchManager:
    """Manages match execution between strategies."""

    def __init__(self, db):
        self.db = db

    def run_match(
        self,
        strategy_a_id: int,
        strategy_b_id: int,
        n_simulations: int = 50,
        progress_callback=None
    ) -> Tuple[Dict, List[Dict]]:
        """
        Run a match between two strategies.

        Args:
            strategy_a_id: ID of first strategy
            strategy_b_id: ID of second strategy
            n_simulations: Number of simulations to run
            progress_callback: Optional callback function(current, total) for progress

        Returns:
            Tuple of (match_data, simulation_results)
        """
        # Load strategies from database
        strat_a = self.db.get_strategy(strategy_a_id)
        strat_b = self.db.get_strategy(strategy_b_id)

        if not strat_a or not strat_b:
            raise ValueError("Strategy not found")

        # Create EVM adapters
        adapter_a = EVMStrategyAdapter(
            bytecode=strat_a['bytecode'],
            abi=json.loads(strat_a['abi'])
        )

        adapter_b = EVMStrategyAdapter(
            bytecode=strat_b['bytecode'],
            abi=json.loads(strat_b['abi'])
        )

        # Setup match runner
        config = build_base_config(seed=None)
        runner = MatchRunner(
            n_simulations=n_simulations,
            config=config,
            n_workers=resolve_n_workers(),
            variance=BASELINE_VARIANCE
        )

        # Run match (store_results=True to get detailed data)
        result = runner.run_match(adapter_a, adapter_b, store_results=True)

        # Prepare match data
        match_data = {
            'strategy_a_id': strategy_a_id,
            'strategy_b_id': strategy_b_id,
            'strategy_a_name': strat_a['name'],
            'strategy_b_name': strat_b['name'],
            'wins_a': result.wins_a,
            'wins_b': result.wins_b,
            'draws': result.draws,
            'avg_edge_a': float(result.total_edge_a / n_simulations),
            'avg_edge_b': float(result.total_edge_b / n_simulations),
            'total_edge_a': float(result.total_edge_a),
            'total_edge_b': float(result.total_edge_b),
            'n_simulations': n_simulations
        }

        # Prepare simulation results
        simulation_results = []
        for i, sim_result in enumerate(result.simulation_results):
            edge_a = float(sim_result.edges.get('submission', 0))
            edge_b = float(sim_result.edges.get('normalizer', 0))
            pnl_a = float(sim_result.pnl.get('submission', 0))
            pnl_b = float(sim_result.pnl.get('normalizer', 0))

            winner = 'a' if edge_a > edge_b else ('b' if edge_b > edge_a else 'draw')

            # Store only summary steps (every 100th) to save space
            steps_summary = []
            for j, step in enumerate(sim_result.steps):
                if j % 100 == 0:  # Save every 100th step
                    steps_summary.append({
                        'timestamp': step.timestamp,
                        'fair_price': step.fair_price,
                        'spot_prices': dict(step.spot_prices),
                        'pnls': dict(step.pnls),
                        'fees': {k: list(v) for k, v in step.fees.items()}
                    })

            simulation_results.append({
                'index': i,
                'seed': sim_result.seed,
                'edge_a': edge_a,
                'edge_b': edge_b,
                'pnl_a': pnl_a,
                'pnl_b': pnl_b,
                'winner': winner,
                'steps': steps_summary
            })

            if progress_callback:
                progress_callback(i + 1, n_simulations)

        return match_data, simulation_results

    def get_match_summary(self, match_id: int) -> Dict:
        """Get a summary of a match with winner info."""
        match = self.db.get_match(match_id)
        if not match:
            return None

        total_games = match['wins_a'] + match['wins_b'] + match['draws']
        win_rate_a = match['wins_a'] / total_games if total_games > 0 else 0
        win_rate_b = match['wins_b'] / total_games if total_games > 0 else 0

        winner = None
        if match['wins_a'] > match['wins_b']:
            winner = match['strategy_a_name']
        elif match['wins_b'] > match['wins_a']:
            winner = match['strategy_b_name']

        return {
            **match,
            'winner': winner,
            'win_rate_a': win_rate_a,
            'win_rate_b': win_rate_b,
            'total_games': total_games
        }
