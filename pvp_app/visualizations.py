"""Visualization utilities for match results."""

import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict
import pandas as pd


def create_edge_comparison_chart(simulation_results: List[Dict], strategy_a_name: str, strategy_b_name: str):
    """Create scatter plot comparing edges across simulations."""
    df = pd.DataFrame([
        {
            'Simulation': r['index'] + 1,
            strategy_a_name: r['edge_a'],
            strategy_b_name: r['edge_b'],
            'Winner': 'A' if r['winner'] == 'a' else ('B' if r['winner'] == 'b' else 'Draw')
        }
        for r in simulation_results
    ])

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['Simulation'],
        y=df[strategy_a_name],
        mode='markers',
        name=strategy_a_name,
        marker=dict(size=8, color='#4CAF50')
    ))

    fig.add_trace(go.Scatter(
        x=df['Simulation'],
        y=df[strategy_b_name],
        mode='markers',
        name=strategy_b_name,
        marker=dict(size=8, color='#FF9800')
    ))

    fig.update_layout(
        title='Edge by Simulation',
        xaxis_title='Simulation Number',
        yaxis_title='Edge',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )

    return fig


def create_edge_distribution_chart(simulation_results: List[Dict], strategy_a_name: str, strategy_b_name: str):
    """Create histogram of edge distributions."""
    edges_a = [r['edge_a'] for r in simulation_results]
    edges_b = [r['edge_b'] for r in simulation_results]

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=edges_a,
        name=strategy_a_name,
        opacity=0.7,
        marker_color='#4CAF50',
        nbinsx=20
    ))

    fig.add_trace(go.Histogram(
        x=edges_b,
        name=strategy_b_name,
        opacity=0.7,
        marker_color='#FF9800',
        nbinsx=20
    ))

    fig.update_layout(
        title='Edge Distribution',
        xaxis_title='Edge',
        yaxis_title='Count',
        barmode='overlay',
        template='plotly_white',
        height=400
    )

    return fig


def create_edge_over_time_chart(steps: List[Dict], strategy_a_name: str, strategy_b_name: str):
    """Create line chart showing cumulative edge over simulation steps."""
    timestamps = [s['timestamp'] for s in steps]
    pnls = [s['pnls'] for s in steps]

    # Extract PnLs (which represent cumulative edge + IL)
    pnls_a = [p.get('submission', 0) for p in pnls]
    pnls_b = [p.get('normalizer', 0) for p in pnls]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=pnls_a,
        mode='lines',
        name=strategy_a_name,
        line=dict(color='#4CAF50', width=2)
    ))

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=pnls_b,
        mode='lines',
        name=strategy_b_name,
        line=dict(color='#FF9800', width=2)
    ))

    fig.update_layout(
        title='PnL Over Time (Sample Simulation)',
        xaxis_title='Step',
        yaxis_title='PnL',
        template='plotly_white',
        height=400
    )

    return fig


def create_fee_comparison_chart(steps: List[Dict], strategy_a_name: str, strategy_b_name: str):
    """Create chart showing fee changes over time."""
    timestamps = [s['timestamp'] for s in steps]
    fees = [s['fees'] for s in steps]

    # Extract bid and ask fees
    fees_a = [f.get('submission', [0, 0]) for f in fees]
    fees_b = [f.get('normalizer', [0, 0]) for f in fees]

    bid_fees_a = [f[0] * 10000 for f in fees_a]  # Convert to bps
    ask_fees_a = [f[1] * 10000 for f in fees_a]
    bid_fees_b = [f[0] * 10000 for f in fees_b]
    ask_fees_b = [f[1] * 10000 for f in fees_b]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=bid_fees_a,
        mode='lines',
        name=f'{strategy_a_name} Bid',
        line=dict(color='#4CAF50', dash='solid')
    ))

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=ask_fees_a,
        mode='lines',
        name=f'{strategy_a_name} Ask',
        line=dict(color='#4CAF50', dash='dash')
    ))

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=bid_fees_b,
        mode='lines',
        name=f'{strategy_b_name} Bid',
        line=dict(color='#FF9800', dash='solid')
    ))

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=ask_fees_b,
        mode='lines',
        name=f'{strategy_b_name} Ask',
        line=dict(color='#FF9800', dash='dash')
    ))

    fig.update_layout(
        title='Fee Changes Over Time (Sample Simulation)',
        xaxis_title='Step',
        yaxis_title='Fee (bps)',
        template='plotly_white',
        height=400
    )

    return fig


def create_win_rate_chart(opponent_breakdown: List[Dict]):
    """Create bar chart of win rates against opponents."""
    df = pd.DataFrame(opponent_breakdown)

    if df.empty:
        return None

    # Sort by total matches
    df = df.sort_values('total_matches', ascending=False).head(10)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df['opponent_name'],
        y=df['win_rate'] * 100,
        marker_color='#4CAF50',
        text=[f"{wr:.1f}%" for wr in df['win_rate'] * 100],
        textposition='outside'
    ))

    fig.update_layout(
        title='Win Rate vs Top Opponents',
        xaxis_title='Opponent',
        yaxis_title='Win Rate (%)',
        template='plotly_white',
        height=400,
        yaxis_range=[0, 110]
    )

    return fig
