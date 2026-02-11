"""Match execution and management."""

from typing import Tuple, Dict, List
import sys
from pathlib import Path
import json

# Add parent directory to path to import amm_competition
sys.path.insert(0, str(Path(__file__).parent.parent))

from amm_competition.competition.match import MatchRunner, NWayMatchRunner, HyperparameterVariance
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

    def run_n_way_match(
        self,
        strategy_ids: List[int],
        n_simulations: int = 50,
        progress_callback=None
    ) -> Tuple[Dict, List[Dict], List[Dict]]:
        """
        Run an n-way match with multiple strategies (3-10).

        Args:
            strategy_ids: List of strategy IDs (3-10 strategies)
            n_simulations: Number of simulations to run
            progress_callback: Optional callback function(current, total) for progress

        Returns:
            Tuple of (match_data, participant_results, simulation_results)
        """
        # Validate number of strategies
        if len(strategy_ids) < 3:
            raise ValueError("N-way matches require at least 3 strategies")
        if len(strategy_ids) > 10:
            raise ValueError("N-way matches support maximum 10 strategies")

        # Validate all strategies exist and are unique
        if len(set(strategy_ids)) != len(strategy_ids):
            raise ValueError("Duplicate strategies not allowed")

        # Load strategies from database
        strategies = []
        strategy_data = []
        for strategy_id in strategy_ids:
            strat = self.db.get_strategy(strategy_id)
            if not strat:
                raise ValueError(f"Strategy with ID {strategy_id} not found")
            strategies.append(strat)
            strategy_data.append((strategy_id, strat['name']))

        # Create EVM adapters
        adapters = []
        for strat in strategies:
            adapter = EVMStrategyAdapter(
                bytecode=strat['bytecode'],
                abi=json.loads(strat['abi'])
            )
            adapters.append(adapter)

        # Setup n-way match runner
        config = build_base_config(seed=None)
        runner = NWayMatchRunner(
            n_simulations=n_simulations,
            config=config,
            n_workers=resolve_n_workers(),
            variance=BASELINE_VARIANCE
        )

        # Run n-way match
        result = runner.run_match(adapters, store_results=True)

        # Prepare match data
        match_data = {
            'match_type': 'n_way',
            'n_participants': len(strategy_ids),
            'n_simulations': n_simulations
        }

        # Prepare participant results
        participant_results = []
        for strategy_id, strategy_name in strategy_data:
            # Find the strategy in the result
            placement_list = result.placements[strategy_name]
            avg_placement = result.avg_placements[strategy_name]
            total_edge = float(result.edges[strategy_name])
            avg_edge = total_edge / n_simulations
            first_place_count = result.first_place_counts[strategy_name]

            # Calculate final placement (average across all simulations)
            # Round to nearest integer for display
            final_placement = round(avg_placement)

            participant_results.append({
                'strategy_id': strategy_id,
                'strategy_name': strategy_name,
                'placement': final_placement,
                'avg_edge': avg_edge,
                'total_edge': total_edge,
                'wins': first_place_count  # Number of 1st place finishes
            })

        # Sort by placement (best first)
        participant_results.sort(key=lambda x: x['placement'])

        # Prepare simulation results
        simulation_results = []
        for i, sim_result in enumerate(result.simulation_results):
            # Build per-strategy data for this simulation
            sim_data = {
                'simulation_index': i,
                'seed': sim_result.seed,
                'strategies': {}
            }

            # Map Rust strategy names (strategy_0, strategy_1, ...) to actual names
            for j, (strategy_id, strategy_name) in enumerate(strategy_data):
                rust_name = f"strategy_{j}"
                edge = float(sim_result.edges.get(rust_name, 0))
                pnl = float(sim_result.pnl.get(rust_name, 0))

                # Find placement for this strategy in this simulation
                placement = result.placements[strategy_name][i]

                sim_data['strategies'][strategy_name] = {
                    'edge': edge,
                    'pnl': pnl,
                    'placement': placement
                }

            # Store sample steps (every 100th) to save space
            steps_summary = []
            for j, step in enumerate(sim_result.steps):
                if j % 100 == 0:
                    steps_summary.append({
                        'timestamp': step.timestamp,
                        'fair_price': step.fair_price,
                        'spot_prices': dict(step.spot_prices),
                        'pnls': dict(step.pnls),
                        'fees': {k: list(v) for k, v in step.fees.items()}
                    })

            sim_data['steps'] = steps_summary
            simulation_results.append(sim_data)

            if progress_callback:
                progress_callback(i + 1, n_simulations)

        return match_data, participant_results, simulation_results

    def get_n_way_match_summary(self, match_id: int) -> Dict:
        """Get a summary of an n-way match with winner info."""
        match = self.db.get_n_way_match(match_id)
        if not match:
            return None

        # Get participants sorted by placement
        participants = sorted(match['participants'], key=lambda p: p['placement'])

        # Winner is the participant with placement = 1
        winner = participants[0] if participants else None

        return {
            **match,
            'winner': winner['strategy_name'] if winner else None,
            'participants': participants
        }
