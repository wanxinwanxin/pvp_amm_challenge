"""PVP AMM Challenge - Main Streamlit Application."""

import streamlit as st
import sys
from pathlib import Path
import json
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pvp_app.database import Database
from pvp_app.match_manager import MatchManager
from pvp_app.stats import StatsCalculator
from pvp_app.visualizations import (
    create_edge_comparison_chart,
    create_edge_distribution_chart,
    create_edge_over_time_chart,
    create_fee_comparison_chart,
    create_win_rate_chart
)

from amm_competition.evm.validator import SolidityValidator
from amm_competition.evm.compiler import SolidityCompiler

# Page config
st.set_page_config(
    page_title="PVP AMM Challenge",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = Database()
    st.session_state.match_manager = MatchManager(st.session_state.db)
    st.session_state.stats_calc = StatsCalculator(st.session_state.db)

db = st.session_state.db
match_manager = st.session_state.match_manager
stats_calc = st.session_state.stats_calc

# Sidebar navigation
st.sidebar.title("⚔️ PVP AMM Challenge")

# Simple auth (for MVP - replace with Twitter OAuth later)
if 'user' not in st.session_state:
    with st.sidebar:
        st.subheader("Sign In")
        username = st.text_input("Username (temporary)")
        if st.button("Sign In"):
            if username:
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Please enter a username")
else:
    st.sidebar.write(f"Signed in as: **{st.session_state.user}**")
    if st.sidebar.button("Sign Out"):
        del st.session_state.user
        st.rerun()

# Navigation
page = st.sidebar.selectbox(
    "Navigation",
    ["🏠 Home", "📤 Submit Strategy", "📚 Browse Strategies", "⚔️ Create Match", "📊 Leaderboard"]
)

# ============================================================================
# HOME PAGE
# ============================================================================

if page == "🏠 Home":
    st.title("🏆 PVP AMM Challenge")
    st.markdown("""
    Welcome to the **Player vs Player AMM** competition!

    Design dynamic fee strategies for automated market makers and compete head-to-head
    against other strategies. Your goal: maximize edge by capturing retail flow while
    minimizing losses to arbitrageurs.
    """)

    # Stats overview
    col1, col2, col3, col4 = st.columns(4)

    strategies = db.list_strategies()
    total_strategies = len(strategies)

    recent_matches = db.get_recent_matches(limit=100)
    total_matches = len(recent_matches)

    with col1:
        st.metric("Total Strategies", total_strategies)

    with col2:
        st.metric("Total Matches", total_matches)

    with col3:
        if strategies:
            top_strategy = stats_calc.get_leaderboard(limit=1)
            if top_strategy:
                st.metric("Top Strategy", top_strategy[0]['name'])
            else:
                st.metric("Top Strategy", "None yet")
        else:
            st.metric("Top Strategy", "None yet")

    with col4:
        if recent_matches:
            st.metric("Recent Matches", f"{len([m for m in recent_matches if m['created_at'][:10] == time.strftime('%Y-%m-%d')])} today")
        else:
            st.metric("Recent Matches", "0 today")

    # Recent matches
    st.subheader("📜 Recent Matches")

    if not recent_matches:
        st.info("No matches yet. Create the first match!")
    else:
        for match in recent_matches[:10]:
            winner = "Draw" if match['wins_a'] == match['wins_b'] else (
                match['strategy_a_name'] if match['wins_a'] > match['wins_b'] else match['strategy_b_name']
            )
            winner_icon = "🤝" if winner == "Draw" else "🏆"

            with st.expander(
                f"{winner_icon} {match['strategy_a_name']} vs {match['strategy_b_name']} - Winner: {winner}"
            ):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**{match['strategy_a_name']}**")
                    st.write(f"Wins: {match['wins_a']}")
                    st.write(f"Avg Edge: {match['avg_edge_a']:.2f}")

                with col2:
                    st.write(f"**{match['strategy_b_name']}**")
                    st.write(f"Wins: {match['wins_b']}")
                    st.write(f"Avg Edge: {match['avg_edge_b']:.2f}")

                with col3:
                    st.write(f"**Match Info**")
                    st.write(f"Draws: {match['draws']}")
                    st.write(f"Simulations: {match['n_simulations']}")
                    st.write(f"Date: {match['created_at'][:10]}")

                if st.button("View Details", key=f"view_match_{match['id']}"):
                    st.session_state.view_match_id = match['id']
                    st.rerun()

# ============================================================================
# SUBMIT STRATEGY PAGE
# ============================================================================

elif page == "📤 Submit Strategy":
    if 'user' not in st.session_state:
        st.warning("Please sign in to submit a strategy")
    else:
        st.title("📤 Submit New Strategy")

        st.markdown("""
        Create your own dynamic fee strategy! Your strategy will compete against others
        to maximize edge across randomized market conditions.
        """)

        name = st.text_input("Strategy Name", help="Unique name for your strategy")
        description = st.text_area("Description (optional)", help="Explain your strategy's approach")

        # Default starter code
        default_code = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AMMStrategyBase} from "./AMMStrategyBase.sol";
import {TradeInfo} from "./IAMMStrategy.sol";

contract Strategy is AMMStrategyBase {
    function afterInitialize(uint256, uint256) external override returns (uint256, uint256) {
        // Return initial bid and ask fees (in WAD: 30 * BPS = 30 basis points)
        return (bpsToWad(30), bpsToWad(30));
    }

    function afterSwap(TradeInfo calldata trade) external override returns (uint256, uint256) {
        // Example: Increase fees after large trades
        uint256 tradeRatio = wdiv(trade.amountY, trade.reserveY);
        uint256 baseFee = bpsToWad(30);

        if (tradeRatio > WAD / 20) { // > 5% of reserves
            uint256 newFee = baseFee + bpsToWad(10);
            return (clampFee(newFee), clampFee(newFee));
        }

        return (baseFee, baseFee);
    }

    function getName() external pure override returns (string memory) {
        return "My Strategy";
    }
}
"""

        code = st.text_area(
            "Solidity Code",
            value=default_code,
            height=500,
            help="Write your strategy contract"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✓ Validate", use_container_width=True):
                with st.spinner("Validating..."):
                    validator = SolidityValidator()
                    validation = validator.validate(code)

                    if validation.valid:
                        st.success("✓ Validation passed!")
                        if validation.warnings:
                            st.warning("Warnings:")
                            for warning in validation.warnings:
                                st.warning(f"  - {warning}")
                    else:
                        st.error("✗ Validation failed:")
                        for error in validation.errors:
                            st.error(f"  - {error}")

        with col2:
            if st.button("🚀 Compile & Submit", use_container_width=True, type="primary"):
                if not name:
                    st.error("Please provide a strategy name")
                elif not st.session_state.user:
                    st.error("Please sign in first")
                else:
                    with st.spinner("Compiling..."):
                        # Validate
                        validator = SolidityValidator()
                        validation = validator.validate(code)

                        if not validation.valid:
                            st.error("Validation failed. Please fix errors first.")
                            for error in validation.errors:
                                st.error(f"  - {error}")
                        else:
                            # Compile
                            compiler = SolidityCompiler()
                            compilation = compiler.compile(code)

                            if not compilation.success:
                                st.error("Compilation failed:")
                                for error in compilation.errors or []:
                                    st.error(f"  - {error}")
                            else:
                                try:
                                    # Handle bytecode - it might be hex string or already bytes
                                    if isinstance(compilation.bytecode, bytes):
                                        bytecode = compilation.bytecode
                                    elif isinstance(compilation.bytecode, str):
                                        # Remove 0x prefix if present
                                        hex_str = compilation.bytecode[2:] if compilation.bytecode.startswith('0x') else compilation.bytecode
                                        bytecode = bytes.fromhex(hex_str)
                                    else:
                                        bytecode = bytes.fromhex(compilation.bytecode)

                                    # Save to database
                                    strategy_id = db.add_strategy(
                                        name=name,
                                        author=st.session_state.user,
                                        source=code,
                                        bytecode=bytecode,
                                        abi=json.dumps(compilation.abi),
                                        description=description
                                    )

                                    st.success(f"✓ Strategy '{name}' submitted successfully! (ID: {strategy_id})")
                                    st.balloons()

                                except ValueError as e:
                                    st.error(str(e))

# ============================================================================
# BROWSE STRATEGIES PAGE
# ============================================================================

elif page == "📚 Browse Strategies":
    st.title("📚 All Strategies")

    # Search bar
    search = st.text_input("🔍 Search strategies", placeholder="Search by name, author, or description...")

    strategies = db.list_strategies(search=search if search else None)

    if not strategies:
        st.info("No strategies found. Be the first to submit!")
    else:
        st.write(f"Found {len(strategies)} strateg{'y' if len(strategies) == 1 else 'ies'}")

        for strat in strategies:
            stats = stats_calc.get_strategy_stats(strat['id'])

            with st.expander(f"**{strat['name']}** by {strat['author']}"):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Matches", stats['total_matches'])

                with col2:
                    st.metric("Wins", stats['wins'])

                with col3:
                    if stats['total_matches'] > 0:
                        st.metric("Win Rate", f"{stats['win_rate']*100:.1f}%")
                    else:
                        st.metric("Win Rate", "N/A")

                with col4:
                    st.metric("Avg Edge", f"{stats['avg_edge']:.2f}")

                if strat['description']:
                    st.write("**Description:**", strat['description'])

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("📊 View Details", key=f"details_{strat['id']}"):
                        st.session_state.view_strategy_id = strat['id']
                        st.rerun()

                with col2:
                    if st.button("⚔️ Challenge", key=f"challenge_{strat['id']}"):
                        st.session_state.challenge_strategy_id = strat['id']
                        # Navigate to Create Match page
                        st.info("Navigate to 'Create Match' to challenge this strategy")

# Strategy detail view
if 'view_strategy_id' in st.session_state:
    st.divider()
    strategy_id = st.session_state.view_strategy_id
    strat = db.get_strategy(strategy_id)

    if strat:
        st.title(f"📊 {strat['name']}")
        st.write(f"**Author:** {strat['author']}")
        st.write(f"**Created:** {strat['created_at']}")

        if strat['description']:
            st.write(f"**Description:** {strat['description']}")

        # Stats
        stats = stats_calc.get_strategy_stats(strategy_id)

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Matches", stats['total_matches'])
        with col2:
            st.metric("Wins", stats['wins'])
        with col3:
            st.metric("Losses", stats['losses'])
        with col4:
            st.metric("Draws", stats['draws'])
        with col5:
            if stats['total_matches'] > 0:
                st.metric("Win Rate", f"{stats['win_rate']*100:.1f}%")
            else:
                st.metric("Win Rate", "N/A")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Avg Edge", f"{stats['avg_edge']:.2f}")
        with col2:
            st.metric("Best Edge", f"{stats['best_edge']:.2f}")
        with col3:
            st.metric("Worst Edge", f"{stats['worst_edge']:.2f}")

        # Opponent breakdown
        if stats['total_matches'] > 0:
            st.subheader("🎯 Performance vs Opponents")

            opponent_breakdown = stats_calc.get_opponent_breakdown(strategy_id)

            if opponent_breakdown:
                # Show chart
                fig = create_win_rate_chart(opponent_breakdown)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

                # Show table
                st.dataframe(
                    [{
                        'Opponent': o['opponent_name'],
                        'Wins': o['wins'],
                        'Losses': o['losses'],
                        'Draws': o['draws'],
                        'Win Rate': f"{o['win_rate']*100:.1f}%"
                    } for o in opponent_breakdown],
                    use_container_width=True
                )

        # Match history
        st.subheader("📜 Match History")

        matches = db.get_strategy_matches(strategy_id)

        if not matches:
            st.info("No matches yet")
        else:
            for match in matches:
                is_strategy_a = match['strategy_a_id'] == strategy_id

                if is_strategy_a:
                    opponent = match['strategy_b_name']
                    wins = match['wins_a']
                    losses = match['wins_b']
                    edge = match['avg_edge_a']
                else:
                    opponent = match['strategy_a_name']
                    wins = match['wins_b']
                    losses = match['wins_a']
                    edge = match['avg_edge_b']

                result = "Win" if wins > losses else ("Loss" if losses > wins else "Draw")
                result_icon = "🏆" if result == "Win" else ("❌" if result == "Loss" else "🤝")

                with st.expander(f"{result_icon} vs {opponent} - {result} ({wins}-{losses}-{match['draws']})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Score:** {wins}W - {losses}L - {match['draws']}D")
                        st.write(f"**Edge:** {edge:.2f}")
                    with col2:
                        st.write(f"**Date:** {match['created_at']}")
                        st.write(f"**Simulations:** {match['n_simulations']}")

        # Source code
        with st.expander("💻 View Source Code"):
            st.code(strat['solidity_source'], language='solidity')

        if st.button("← Back to Browse"):
            del st.session_state.view_strategy_id
            st.rerun()

# ============================================================================
# CREATE MATCH PAGE
# ============================================================================

elif page == "⚔️ Create Match":
    st.title("⚔️ Create New Match")

    strategies = db.list_strategies()

    if len(strategies) < 2:
        st.warning("Need at least 2 strategies to create a match. Submit more strategies first!")
    else:
        # Match type selection
        match_type = st.radio(
            "Match Type",
            ["Head-to-Head (2 strategies)", "N-Way Match (3-10 strategies)"],
            help="Head-to-head: Classic 1v1. N-way: Multiple strategies compete simultaneously."
        )

        is_n_way = match_type.startswith("N-Way")

        if is_n_way:
            st.markdown("""
            Select 3-10 strategies to compete simultaneously. Strategies are ranked by placement
            (1st, 2nd, 3rd, etc.) based on edge performance. Points: 1st=3pts, 2nd=2pts, 3rd=1pt.
            """)
        else:
            st.markdown("""
            Select two strategies to compete head-to-head. Each strategy runs as a separate AMM,
            competing for retail flow based on their fee schedules.
            """)

        strategy_options = {f"{s['name']} by {s['author']}": s['id'] for s in strategies}

        if is_n_way:
            # N-way match: multi-select
            selected_strategies = st.multiselect(
                "Select Strategies (3-10)",
                options=strategy_options.keys(),
                help="Choose 3-10 strategies to compete"
            )

            # Validation feedback
            if selected_strategies:
                n_selected = len(selected_strategies)
                if n_selected < 3:
                    st.warning(f"Selected {n_selected}/3 strategies minimum")
                elif n_selected > 10:
                    st.error(f"Selected {n_selected}/10 strategies maximum. Please deselect some.")
                else:
                    st.success(f"✓ {n_selected} strategies selected")
        else:
            # Head-to-head: two selectboxes
            col1, col2 = st.columns(2)

            with col1:
                strategy_a = st.selectbox(
                    "Select Strategy A",
                    options=strategy_options.keys(),
                    help="First strategy in the matchup"
                )

            with col2:
                strategy_b = st.selectbox(
                    "Select Strategy B",
                    options=strategy_options.keys(),
                    help="Second strategy in the matchup"
                )

        # Match configuration
        st.subheader("Match Configuration")

        col1, col2 = st.columns(2)

        with col1:
            n_sims = st.slider(
                "Number of Simulations",
                min_value=10,
                max_value=100,
                value=50,
                step=10,
                help="More simulations = more accurate but slower"
            )

        with col2:
            if is_n_way:
                # N-way matches take longer due to complexity
                est_time = n_sims * (len(selected_strategies) if 'selected_strategies' in locals() and selected_strategies else 3) * 0.3
                st.info(f"Estimated time: ~{est_time:.0f} seconds")
            else:
                st.info(f"Estimated time: ~{n_sims * 0.5:.0f} seconds")

        # Validation and start button
        can_start = False
        if is_n_way:
            if 'selected_strategies' in locals() and selected_strategies:
                n_selected = len(selected_strategies)
                can_start = 3 <= n_selected <= 10
        else:
            can_start = True

        if st.button("🚀 Start Match", type="primary", use_container_width=True, disabled=not can_start):
            if is_n_way:
                # N-way match execution
                strategy_ids = [strategy_options[name] for name in selected_strategies]

                if len(set(strategy_ids)) != len(strategy_ids):
                    st.error("Duplicate strategies selected")
                elif len(strategy_ids) < 3:
                    st.error("Please select at least 3 strategies")
                elif len(strategy_ids) > 10:
                    st.error("Maximum 10 strategies allowed")
                else:
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    try:
                        status_text.text(f"Running {len(strategy_ids)}-way match...")

                        match_data, participant_results, sim_results = match_manager.run_n_way_match(
                            strategy_ids,
                            n_simulations=n_sims,
                            progress_callback=lambda curr, total: progress_bar.progress(curr / total)
                        )

                        match_id = db.add_n_way_match(match_data, participant_results, sim_results)

                        progress_bar.progress(1.0)
                        status_text.text("Match complete!")

                        st.success("✓ N-way match completed successfully!")
                        st.balloons()

                        # Display N-way results
                        st.divider()
                        st.subheader("🏆 Results")

                        # Winner announcement
                        winner = participant_results[0]  # Already sorted by placement
                        st.success(f"🏆 Winner: **{winner['strategy_name']}**")

                        # Podium display
                        st.subheader("🥇 Final Standings")
                        cols = st.columns(min(len(participant_results), 3))
                        medals = ["🥇", "🥈", "🥉"]

                        for i, participant in enumerate(participant_results[:3]):
                            with cols[i]:
                                medal = medals[i] if i < 3 else f"{i+1}th"
                                st.metric(
                                    f"{medal} {participant['strategy_name']}",
                                    f"Avg Edge: {participant['avg_edge']:.2f}",
                                    delta=f"{participant['wins']} wins"
                                )

                        # Full rankings table
                        st.subheader("📊 Complete Rankings")
                        rankings_data = []
                        for i, p in enumerate(participant_results, 1):
                            rankings_data.append({
                                "Rank": i,
                                "Strategy": p['strategy_name'],
                                "Avg Edge": f"{p['avg_edge']:.2f}",
                                "1st Place Finishes": p['wins'],
                                "Points": f"{3 * p['wins'] if i == 1 else 0}"  # Simplified
                            })
                        st.dataframe(rankings_data, use_container_width=True)

                        st.info(f"Match ID: {match_id} | {n_sims} simulations")

                    except Exception as e:
                        st.error(f"Error running match: {str(e)}")
                        progress_bar.empty()
                        status_text.empty()
            else:
                # Head-to-head match execution (existing logic)
                strat_a_id = strategy_options[strategy_a]
                strat_b_id = strategy_options[strategy_b]

                if strat_a_id == strat_b_id:
                    st.error("Please select two different strategies")
                else:
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()

                try:
                    status_text.text("Running match...")

                    match_data, sim_results = match_manager.run_match(
                        strat_a_id,
                        strat_b_id,
                        n_simulations=n_sims,
                        progress_callback=lambda curr, total: progress_bar.progress(curr / total)
                    )

                    match_id = db.add_match(match_data, sim_results)

                    progress_bar.progress(100)
                    status_text.text("Match complete!")

                    st.success("✓ Match completed successfully!")
                    st.balloons()

                    # Display results
                    st.divider()
                    st.subheader("🏆 Results")

                    # Winner announcement
                    if match_data['wins_a'] > match_data['wins_b']:
                        winner = match_data['strategy_a_name']
                        st.success(f"🏆 Winner: **{winner}**")
                    elif match_data['wins_b'] > match_data['wins_a']:
                        winner = match_data['strategy_b_name']
                        st.success(f"🏆 Winner: **{winner}**")
                    else:
                        st.info("🤝 Match ended in a draw!")

                    # Score
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            f"{match_data['strategy_a_name']} Wins",
                            match_data['wins_a']
                        )
                    with col2:
                        st.metric(
                            f"{match_data['strategy_b_name']} Wins",
                            match_data['wins_b']
                        )
                    with col3:
                        st.metric("Draws", match_data['draws'])

                    # Edge comparison
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            f"{match_data['strategy_a_name']} Avg Edge",
                            f"{match_data['avg_edge_a']:.2f}"
                        )
                    with col2:
                        st.metric(
                            f"{match_data['strategy_b_name']} Avg Edge",
                            f"{match_data['avg_edge_b']:.2f}"
                        )

                    # Charts
                    st.subheader("📊 Analysis")

                    # Edge comparison scatter
                    fig1 = create_edge_comparison_chart(
                        sim_results,
                        match_data['strategy_a_name'],
                        match_data['strategy_b_name']
                    )
                    st.plotly_chart(fig1, use_container_width=True)

                    # Edge distribution
                    fig2 = create_edge_distribution_chart(
                        sim_results,
                        match_data['strategy_a_name'],
                        match_data['strategy_b_name']
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                    # Show sample simulation
                    if sim_results and sim_results[0]['steps']:
                        st.subheader("📈 Sample Simulation (First Run)")

                        # PnL over time
                        fig3 = create_edge_over_time_chart(
                            sim_results[0]['steps'],
                            match_data['strategy_a_name'],
                            match_data['strategy_b_name']
                        )
                        st.plotly_chart(fig3, use_container_width=True)

                        # Fee changes
                        fig4 = create_fee_comparison_chart(
                            sim_results[0]['steps'],
                            match_data['strategy_a_name'],
                            match_data['strategy_b_name']
                        )
                        st.plotly_chart(fig4, use_container_width=True)

                    st.info(f"Match ID: {match_id}")

                except Exception as e:
                    st.error(f"Error running match: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

# ============================================================================
# LEADERBOARD PAGE
# ============================================================================

elif page == "📊 Leaderboard":
    st.title("📊 Leaderboard")

    # Sort options
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("Top strategies ranked by performance")

    with col2:
        sort_by = st.selectbox(
            "Sort by",
            options=['win_rate', 'avg_edge', 'matches'],
            format_func=lambda x: {'win_rate': 'Win Rate', 'avg_edge': 'Avg Edge', 'matches': 'Total Matches'}[x]
        )

    leaderboard = stats_calc.get_leaderboard(sort_by=sort_by, limit=100)

    if not leaderboard:
        st.info("No matches played yet. Create the first match!")
    else:
        # Display as table
        for i, entry in enumerate(leaderboard):
            rank = i + 1
            medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else f"{rank}."))

            with st.expander(f"{medal} **{entry['name']}** by {entry['author']}"):
                col1, col2, col3, col4, col5, col6 = st.columns(6)

                with col1:
                    st.metric("Matches", entry['total_matches'])
                with col2:
                    st.metric("Wins", entry['wins'])
                with col3:
                    st.metric("Losses", entry['losses'])
                with col4:
                    st.metric("Win Rate", f"{entry['win_rate']*100:.1f}%")
                with col5:
                    st.metric("Avg Edge", f"{entry['avg_edge']:.2f}")
                with col6:
                    if st.button("View Details", key=f"lb_{entry['id']}"):
                        st.session_state.view_strategy_id = entry['id']
                        st.rerun()

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("Built with ❤️ using Streamlit")
st.sidebar.markdown("Powered by [amm-challenge](https://github.com/benedictbrady/amm-challenge)")
