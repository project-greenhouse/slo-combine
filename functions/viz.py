import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import streamlit as st
import plotly.graph_objects as go


#--------------------------------------------------------------------------------------------#
# Re-import necessary modules after code execution state reset

# Custom combine-themed style configuration
def set_combine_theme():
    sns.set_theme(context="notebook", style="whitegrid")
    plt.rcParams.update({
        "figure.figsize": (6, 4),
        "axes.titlesize": 16,
        "axes.labelsize": 14,
        "axes.titleweight": 'bold',
        "axes.edgecolor": "#222222",
        "axes.linewidth": 1.25,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,
        "font.family": "DejaVu Sans",
        "axes.prop_cycle": plt.cycler(color=sns.color_palette("deep")),
        "savefig.dpi": 300,
        "savefig.bbox": "tight"
    })

#-------------------------------#
# --- Percentile Strip Chart ---#
#-------------------------------#
def set_combine_theme():
    sns.set_theme(context="notebook", style="whitegrid")
    plt.rcParams.update({
        "figure.figsize": (8, 2.5),
        "axes.titlesize": 16,
        "axes.labelsize": 14,
        "axes.titleweight": 'bold',
        "axes.edgecolor": "#222222",
        "axes.linewidth": 1.25,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,
        "font.family": "DejaVu Sans",
        "axes.prop_cycle": plt.cycler(color=sns.color_palette("deep")),
        "savefig.dpi": 300,
        "savefig.bbox": "tight"
    })

def percentile_strip_plot_from_table(value: int | float, metric: str, table: pd.DataFrame, metric_label: str = None, title: str = None):
    """
    Create a horizontal percentile strip plot for a test result value.

    Parameters:
    - value: the athlete's test result
    - metric: the column name in the percentile table
    - table: a DataFrame with 'percentile' and metric columns
    - metric_label: custom label for x-axis (optional)
    - title: custom chart title (optional)

    Returns:
    - Matplotlib figure object
    """
    set_combine_theme()

    # Extract and sort relevant percentiles
    df = table.loc[:, ["Percentile", metric]].dropna()
    df_sorted = df.sort_values("Percentile")
    df_sorted = df_sorted[df_sorted["Percentile"].between(0, 100)]

    fig, ax = plt.subplots(figsize=(8, 2.5))

    p_values = df_sorted[metric].values
    p_percentiles = df_sorted["Percentile"].values

    # Reverse axis if lower is better but keep bar growing left to right
    reverse = metric in ["Sprint40", "ProAgility"]
    if reverse:
        p_values = p_values[::-1]
        p_percentiles = p_percentiles[::-1]

    # Estimate percentile rank
    est_percentile = float(np.interp(value, p_values, p_percentiles))

    # Color tier
    if est_percentile <= 40:
        color = "#E30613"
    elif est_percentile >= 70:
        color = "#00A651"
    else:
        color = "#FFC20E"

    xmin = min(p_values)
    xmax = max(p_values)
    bar_height = 1.0

    # Always draw bar from left edge (xmin) to value
    bar_start = xmin
    bar_width = value - xmin

    ax.barh(y=0.5, width=bar_width, left=bar_start, height=bar_height,
            color=color, edgecolor='white', linewidth=0)

    # Align result text to right end of bar
    ax.text(value - 0.5, 0.5, f"{value:.2f}",
            va='center', ha='right', fontsize=18, color='black', fontweight='bold')

    # Percentile label outside bar
    ax.text(xmax + (xmax - xmin) * 0.01, 0.5, f"{int(est_percentile)}%",
            va='center', ha='left', fontsize=14, color=color, fontweight='bold')

    # Reverse x-axis direction if lower is better
    if reverse:
        ax.set_xlim(xmax * 1.05, xmin)
    else:
        ax.set_xlim(xmin, xmax * 1.05)

    # Style and labels
    ax.set_yticks([])
    ax.set_title(title or f"{metric_label or metric} Percentile Rank", pad=20)
    ax.set_xlabel(metric_label or metric.replace("_", " ").title())

    ax.tick_params(left=False, bottom=True, labelbottom=True)
    ax.xaxis.grid(True, linestyle='--', color='#e0e0e0', linewidth=0.8)
    ax.yaxis.grid(False)

    for spine in ['top', 'left', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color("#e0e0e0")

    return st.pyplot(fig)


#------------------------------------#
# --- Strip Plot for Speed ---#
#------------------------------------#
# Prepare data for horizontal stacked bar plot
def plot_reactive_performance(sprint_df, agility_df):
    sprint_trial = sprint_df
    agility_trial = agility_df

    sprint_splits = [
        sprint_trial["split_time_10yd"].mean().round(2),
        sprint_trial["split_time_40yd"].mean().round(2),
    ]
    agility_splits = [
        agility_trial["split_time_5yd"].mean().round(2),
        agility_trial["split_time_10yd"].mean().round(2),
        agility_trial["split_time_15yd"].mean().round(2),
        agility_trial["split_time_20yd"].mean().round(2),
    ]

    y_labels = ["40 Yard Sprint", "Pro Agility Shuttle"]
    colors_sprint = ["#de425b", "#ea715f"]
    colors_agility = ["#efb51b", "#f5c04a", "#f9cb6d", "#fdd68e"]

    fig = go.Figure()

    # Sprint segments
    sprint_start = 0
    for val, name, color in zip(sprint_splits, ["0–10 yd", "10–40 yd"], colors_sprint):
        fig.add_trace(go.Bar(
            y=[y_labels[0]],
            x=[val],
            name=name,
            orientation='h',
            marker=dict(color=color),
            offsetgroup=0,
            base=sprint_start,
            showlegend=False,
            width=0.5  # Increase bar width
        ))
        sprint_start += val

    # Agility segments
    agility_start = 0
    for val, name, color in zip(agility_splits, ["0–5", "5–10", "10–15", "15–20"], colors_agility):
        fig.add_trace(go.Bar(
            y=[y_labels[1]],
            x=[val],
            name=name,
            orientation='h',
            marker=dict(color=color),
            offsetgroup=1,
            base=agility_start,
            showlegend=False,
            width=0.5  # Increase bar width
        ))
        agility_start += val

    fig.update_layout(
        barmode='stack',
        #title='Sprint & Pro Agility Test Performance',
        xaxis_title='Time (s)',
        yaxis_title='',
        yaxis=dict(
            categoryorder='array',
            categoryarray=y_labels[::-1],  # keep top-down order
            tickfont=dict(color="black", size=12)
        ),
        xaxis=dict(
            tick0=0,
            dtick=0.5,  # more x-axis ticks every 0.5s
            tickfont=dict(color="black", size=14),
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            griddash='dash'
        ),
        height=150,
        margin=dict(t=5, l=60, r=20, b=10),
    )

    return fig



#-------------------------------------#
# Sample plotting functions using the theme
def bar_comparison_plot(df, metric, athlete_label="Athlete", norm_label="Population", title=None):
    """
    Creates a simple bar plot comparing an athlete score to population norm.
    """
    set_combine_theme()

    # Prepare plot
    fig, ax = plt.subplots()
    sns.barplot(data=df, x="Label", y=metric, ax=ax)

    # Style
    ax.set_title(title or f"{metric} Comparison")
    ax.set_xlabel("")
    ax.set_ylabel(metric.replace("_", " ").title())

    # Add values on bars
    for p in ax.patches:
        ax.annotate(f"{p.get_height():.2f}", (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='bottom', fontsize=12)

    return fig


#------------------------------------#
# --- Radial Gauge for Movement ---#
#------------------------------------#
def radial_gauge(value, max_value=100, title="Movement Quality", figsize=(1, 1)):
    """
    Create a radial gauge chart to visualize movement quality.
    """
    # Set color based on value
    if value < 70:
        color = "#FF4B4B"   # red
    elif 70 <= value <= 85:
        color = "#FFC107"   # amber
    else:
        color = "#00A651"   # green

    # Normalize value
    percent = value / max_value
    angle = percent * 360

    # Create figure and polar axis
    fig, ax = plt.subplots(figsize=figsize, subplot_kw={'projection': 'polar'})
    ax.set_theta_direction(-1)
    ax.set_theta_offset(np.pi / 2.0)

    # Set background
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    # Limit radius
    ax.set_ylim(0, 1.05)

    # Remove ticks and grid
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])

    # Remove frame/spines
    ax.spines['polar'].set_visible(False)

    # Background arc
    theta_bg = np.linspace(0, 2*np.pi, 500)
    ax.plot(theta_bg, [1]*len(theta_bg), color='gray', linewidth=8, alpha=0.2)

    # Value arc
    theta_val = np.linspace(0, np.radians(angle), 300)
    ax.plot(theta_val, [1]*len(theta_val), color=color, linewidth=8)

    # Add score text with adjusted font size based on figure size
    font_size = max(8, min(16, figsize[0] * 8))
    ax.text(0, 0, f"{int(value)}", fontsize=font_size, color='black', ha='center', va='center', weight='bold')

    # Adjust layout to minimize whitespace and center the plot
    plt.tight_layout(pad=0.1)
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    # Return in Streamlit with centered display
    return st.pyplot(fig, use_container_width=True)


#------------------------------------#
# --- Strip Plot for Power ---#
#------------------------------------#
# Prepare data for horizontal stacked bar plot
def plot_power_ranks(fdData: pd.DataFrame, show=True, key=None):
    """
    Plots Reactive Strength and Relative Power percentiles for each 'Comp' group
    using horizontal grouped bars.
    """
    # Define color map for each Comp
    comp_colors = {
        "SLO Combine": "#de425b",
        "Elite": "#efb51b"
    }

    # Unique metrics (rows)
    metrics = fdData["Metric"].unique().tolist()

    fig = go.Figure()

    for comp in fdData["Comp"].unique():
        for metric in metrics:
            row = fdData[(fdData["Comp"] == comp) & (fdData["Metric"] == metric)]
            if not row.empty:
                fig.add_trace(go.Bar(
                    y=[metric],
                    x=[row["Value"].values[0]],
                    name=comp,
                    orientation="h",
                    marker=dict(color=comp_colors.get(comp, "gray")),
                    width=0.5,
                    showlegend=metric == metrics[0]  # only show legend once per group
                ))

    fig.update_layout(
        barmode="group",
        xaxis_title="Percentile Rank",
        yaxis_title="",
        yaxis=dict(
            categoryorder='array',
            categoryarray=metrics,
            tickfont=dict(size=12)
        ),
        xaxis=dict(
            range=[0, 100],
            tick0=0,
            dtick=10,
            tickfont=dict(size=12),
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            griddash='dash'
        ),
        height=200,
        margin=dict(t=5, l=60, r=20, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )

    if show:
        st.plotly_chart(fig, use_container_width=True, key=key)
    return fig