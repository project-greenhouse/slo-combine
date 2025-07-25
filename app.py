import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats as stats
import matplotlib.ticker as ticker

# Load your data (replace with actual file path if needed)
df = pd.read_csv("C:\\Users\\LaurenGreen\\OneDrive - Hawkin Dynamics\\Desktop\\Norm Data\\Norms\\baseballNorms.csv")

# Mock athlete assignment (3 trials per athlete)
athletes = ['John Smith', 'Mike Johnson', 'Alex Rivera', 'Chris Lee', 'Danny Lopez']
df = df.iloc[:len(athletes) * 3].copy()
df['Athlete'] = [athletes[i // 3] for i in range(len(df))]

def plot_percentile_chart(athlete_name):
    athlete_data = df[df['Athlete'] == athlete_name]

    metrics = {
        'Jump Height (m)': ('Jump Height', 'm'),
        'Peak Rel Propulsive Power': ('Peak Relative Propulsive Power', 'W/kg')
    }

    fig, axs = plt.subplots(len(metrics), 1, figsize=(10, 3.5 * len(metrics)), sharex=True)

    for i, (label, (col_name, unit)) in enumerate(metrics.items()):
        ax = axs[i] if len(metrics) > 1 else axs
        values = athlete_data[col_name]
        group_vals = df[col_name]

        mean_val = values.mean()
        peak_val = values.max()

        mean_pct = stats.percentileofscore(group_vals, mean_val, kind='rank')
        peak_pct = stats.percentileofscore(group_vals, peak_val, kind='rank')

        ax.barh(y=0, width=100, height=0.4, color='#eeeeee', edgecolor='lightgray')
        ax.barh(y=0, width=mean_pct, height=0.4, color='steelblue')
        ax.plot(peak_pct, 0, 'o', color='darkred', markersize=8)

        for q in [25, 50, 75]:
            ax.axvline(x=q, color='black', linestyle='--', linewidth=0.7)

        ax.set_xlim(0, 100)
        ax.set_yticks([])
        ax.set_title(label)
        ax.grid(False)
        ax.set_xlabel("Percentile Rank")
        ax.xaxis.set_major_locator(ticker.MultipleLocator(10))

        # Add larger mean and best text directly under the bar like a legend
        text_y = -0.35
        ax.text(1, text_y, f"Mean: {mean_val:.2f} {unit} ({mean_pct:.0f}%)", fontsize=11, color='steelblue', fontweight='bold', ha='left')
        ax.text(50, text_y, f"|", fontsize=11, ha='center', va='center', color='gray')
        ax.text(55, text_y, f"Best: {peak_val:.2f} {unit} ({peak_pct:.0f}%)", fontsize=11, color='darkred', fontweight='bold', ha='left')

    fig.suptitle(f'Percentile Performance: {athlete_name}', fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    st.pyplot(fig)

# Streamlit UI
st.title("CMJ Percentile Report")
selected_athlete = st.selectbox("Select Athlete", sorted(df['Athlete'].unique()))
plot_percentile_chart(selected_athlete)
