#!/usr/bin/env python3
"""Analyze SUMO simulation results and generate comparison visualizations.

Produces:
- Static comparison charts (bar charts, timelines, heatmaps)
- Animated queue growth visualization
- Side-by-side network animation (base vs proposed)
- Interactive Plotly HTML dashboard
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
VIZ_DIR = OUTPUT_DIR / "visualizations"

SCENARIO_LABELS = {
    "scenario_4A_base": "Base (2+3 lanes)",
    "scenario_4A_v1": "V1: Proposed (2+2)",
    "scenario_4A_v2": "V2: Worst case (1+1+bus)",
    "scenario_1A_v1": "Sc. 1A on V1 (high demand)",
    "scenario_4A_v1_optimized": "V1 + Optimized signals",
}

SCENARIO_COLORS = {
    "scenario_4A_base": "#2ecc71",       # green
    "scenario_4A_v1": "#e74c3c",         # red
    "scenario_4A_v2": "#e67e22",         # orange
    "scenario_1A_v1": "#9b59b6",         # purple
    "scenario_4A_v1_optimized": "#3498db",  # blue
}


def load_all_results() -> dict:
    """Load combined results from all scenarios."""
    results_file = OUTPUT_DIR / "all_results.json"
    if not results_file.exists():
        print(f"No results file found at {results_file}")
        print("Run scripts/04_run_simulation.py --all first.")
        return {}
    with open(results_file) as f:
        return json.load(f)


def load_tripinfo(scenario: str, seed: int = 1) -> pd.DataFrame:
    """Load tripinfo XML into a DataFrame."""
    filepath = OUTPUT_DIR / scenario / f"seed_{seed}" / "tripinfo.xml"
    if not filepath.exists():
        return pd.DataFrame()

    try:
        tree = ET.parse(str(filepath))
        root = tree.getroot()

        records = []
        for trip in root.findall("tripinfo"):
            records.append({
                "id": trip.get("id"),
                "depart": float(trip.get("depart", 0)),
                "arrival": float(trip.get("arrival", 0)),
                "duration": float(trip.get("duration", 0)),
                "waitingTime": float(trip.get("waitingTime", 0)),
                "timeLoss": float(trip.get("timeLoss", 0)),
                "routeLength": float(trip.get("routeLength", 0)),
                "departDelay": float(trip.get("departDelay", 0)),
            })
        return pd.DataFrame(records)
    except ET.ParseError:
        return pd.DataFrame()


def load_summary(scenario: str, seed: int = 1) -> pd.DataFrame:
    """Load summary XML (per-timestep stats)."""
    filepath = OUTPUT_DIR / scenario / f"seed_{seed}" / "summary.xml"
    if not filepath.exists():
        return pd.DataFrame()

    try:
        tree = ET.parse(str(filepath))
        root = tree.getroot()

        records = []
        for step in root.findall("step"):
            records.append({
                "time": float(step.get("time", 0)),
                "loaded": int(step.get("loaded", 0)),
                "inserted": int(step.get("inserted", 0)),
                "running": int(step.get("running", 0)),
                "waiting": int(step.get("waiting", 0)),
                "ended": int(step.get("ended", 0)),
                "meanSpeed": float(step.get("meanSpeed", 0)),
                "meanTravelTime": float(step.get("meanTravelTime", 0)),
                "halting": int(step.get("halting", 0)),
            })
        return pd.DataFrame(records)
    except ET.ParseError:
        return pd.DataFrame()


def load_fcd(scenario: str, seed: int = 1) -> pd.DataFrame:
    """Load FCD (Floating Car Data) for vehicle positions."""
    filepath = OUTPUT_DIR / scenario / f"seed_{seed}" / "fcd.xml"
    if not filepath.exists():
        return pd.DataFrame()

    records = []
    try:
        for event, elem in ET.iterparse(str(filepath), events=["end"]):
            if elem.tag == "vehicle":
                timestep = elem.getparent() if hasattr(elem, "getparent") else None
                records.append({
                    "x": float(elem.get("x", 0)),
                    "y": float(elem.get("y", 0)),
                    "speed": float(elem.get("speed", 0)),
                    "id": elem.get("id"),
                })
                elem.clear()
    except Exception:
        # Fallback: parse entire file
        try:
            tree = ET.parse(str(filepath))
            root = tree.getroot()
            for timestep in root.findall("timestep"):
                t = float(timestep.get("time", 0))
                for veh in timestep.findall("vehicle"):
                    records.append({
                        "time": t,
                        "x": float(veh.get("x", 0)),
                        "y": float(veh.get("y", 0)),
                        "speed": float(veh.get("speed", 0)),
                        "id": veh.get("id"),
                    })
        except ET.ParseError:
            pass

    return pd.DataFrame(records)


# ============================================================================
# STATIC CHARTS (4c)
# ============================================================================

def chart_travel_times(results: dict):
    """Bar chart: Average travel time per scenario."""
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    scenarios = []
    avg_times = []
    colors = []

    for name, runs in results.items():
        if not runs:
            continue
        avg = np.mean([r.get("avg_duration_s", 0) for r in runs])
        scenarios.append(SCENARIO_LABELS.get(name, name))
        avg_times.append(avg / 60.0)  # Convert to minutes
        colors.append(SCENARIO_COLORS.get(name, "#95a5a6"))

    if not scenarios:
        print("No data for travel time chart")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(scenarios, avg_times, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_xlabel("Gjennomsnittlig reisetid (minutter)", fontsize=12)
    ax.set_title("Gjennomsnittlig reisetid Snarøya → E18\nMorgonrush 07:45-08:45, År 2040", fontsize=14)

    # Add value labels
    for bar, val in zip(bars, avg_times):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f} min", va="center", fontsize=11, fontweight="bold")

    ax.set_xlim(0, max(avg_times) * 1.3 if avg_times else 10)
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "travel_times_comparison.png", dpi=150)
    plt.savefig(VIZ_DIR / "travel_times_comparison.pdf")
    plt.close()
    print(f"✓ Travel time chart → {VIZ_DIR / 'travel_times_comparison.png'}")


def chart_queue_lengths(results: dict):
    """Bar chart: Maximum queue length on Snarøyveien sør per scenario."""
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    scenarios = []
    max_waiting = []
    colors = []

    for name, runs in results.items():
        if not runs:
            continue
        # 'waiting' = vehicles that couldn't enter network ≈ queue proxy
        avg_wait = np.mean([r.get("waiting", 0) for r in runs])
        scenarios.append(SCENARIO_LABELS.get(name, name))
        max_waiting.append(avg_wait)
        colors.append(SCENARIO_COLORS.get(name, "#95a5a6"))

    if not scenarios:
        print("No data for queue chart")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(scenarios, max_waiting, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_xlabel("Kjøretøy som ikke kom inn i modellen", fontsize=12)
    ax.set_title("Kø på Snarøyveien sør (kjøretøy utenfor modellen)\nMorgonrush 07:45-08:45, År 2040",
                 fontsize=14)

    for bar, val in zip(bars, max_waiting):
        ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height() / 2,
                f"{val:.0f} kjt", va="center", fontsize=11, fontweight="bold")

    ax.set_xlim(0, max(max_waiting) * 1.3 if max_waiting else 10)
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "queue_lengths_comparison.png", dpi=150)
    plt.savefig(VIZ_DIR / "queue_lengths_comparison.pdf")
    plt.close()
    print(f"✓ Queue length chart → {VIZ_DIR / 'queue_lengths_comparison.png'}")


def chart_time_loss(results: dict):
    """Bar chart: Total time loss per scenario."""
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    scenarios = []
    time_losses = []
    colors = []

    for name, runs in results.items():
        if not runs:
            continue
        avg_loss = np.mean([r.get("total_time_loss_h", 0) for r in runs])
        scenarios.append(SCENARIO_LABELS.get(name, name))
        time_losses.append(avg_loss)
        colors.append(SCENARIO_COLORS.get(name, "#95a5a6"))

    if not scenarios:
        print("No data for time loss chart")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(scenarios, time_losses, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_xlabel("Total forsinkelse (kjøretøy-timer)", fontsize=12)
    ax.set_title("Total forsinkelse i trafikknettverket\nMorgonrush 07:45-08:45, År 2040", fontsize=14)

    for bar, val in zip(bars, time_losses):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f} t", va="center", fontsize=11, fontweight="bold")

    ax.set_xlim(0, max(time_losses) * 1.3 if time_losses else 10)
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "time_loss_comparison.png", dpi=150)
    plt.savefig(VIZ_DIR / "time_loss_comparison.pdf")
    plt.close()
    print(f"✓ Time loss chart → {VIZ_DIR / 'time_loss_comparison.png'}")


def chart_queue_timeline():
    """Timeline: Queue length (waiting + halting vehicles) over rush hour."""
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6))
    has_data = False

    for scenario_name in SCENARIO_LABELS:
        df = load_summary(scenario_name, seed=1)
        if df.empty:
            continue

        has_data = True
        label = SCENARIO_LABELS.get(scenario_name, scenario_name)
        color = SCENARIO_COLORS.get(scenario_name, "#95a5a6")

        # Convert time to minutes, use waiting + halting as queue proxy
        time_min = df["time"] / 60.0
        queue = df["waiting"] + df["halting"]

        # Smooth with rolling average
        if len(queue) > 10:
            queue = queue.rolling(window=10, min_periods=1).mean()

        ax.plot(time_min, queue, label=label, color=color, linewidth=2)

    if not has_data:
        print("No summary data for queue timeline")
        plt.close()
        return

    ax.set_xlabel("Tid (minutter fra simuleringsstart)", fontsize=12)
    ax.set_ylabel("Ventende + stående kjøretøy", fontsize=12)
    ax.set_title("Køutvikling gjennom morgenrushet\nSnarøyveien, År 2040", fontsize=14)
    ax.legend(fontsize=10, loc="upper left")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "queue_timeline.png", dpi=150)
    plt.savefig(VIZ_DIR / "queue_timeline.pdf")
    plt.close()
    print(f"✓ Queue timeline → {VIZ_DIR / 'queue_timeline.png'}")


# ============================================================================
# ANIMATED QUEUE GROWTH (4b)
# ============================================================================

def animate_queue_growth():
    """Animated line chart showing queue growth over morning rush."""
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    # Load summary data for all scenarios
    scenario_data = {}
    max_time = 0

    for scenario_name in SCENARIO_LABELS:
        df = load_summary(scenario_name, seed=1)
        if df.empty:
            continue
        queue = (df["waiting"] + df["halting"]).values
        if len(queue) > 10:
            # Smooth
            kernel = np.ones(10) / 10
            queue = np.convolve(queue, kernel, mode="same")
        scenario_data[scenario_name] = queue
        max_time = max(max_time, len(queue))

    if not scenario_data:
        print("No data for queue animation")
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    lines = {}

    for name in scenario_data:
        label = SCENARIO_LABELS.get(name, name)
        color = SCENARIO_COLORS.get(name, "#95a5a6")
        line, = ax.plot([], [], label=label, color=color, linewidth=2.5)
        lines[name] = line

    ax.set_xlim(0, max_time / 60.0)
    max_queue = max(max(d) for d in scenario_data.values()) if scenario_data else 100
    ax.set_ylim(0, max_queue * 1.2)
    ax.set_xlabel("Tid (minutter)", fontsize=12)
    ax.set_ylabel("Ventende + stående kjøretøy", fontsize=12)
    ax.set_title("Køutvikling — Snarøyveien morgenrush 2040", fontsize=14)
    ax.legend(fontsize=10, loc="upper left")
    ax.grid(True, alpha=0.3)

    time_text = ax.text(0.02, 0.95, "", transform=ax.transAxes, fontsize=12,
                        verticalalignment="top", fontweight="bold")

    # Animate at ~30 fps, show 1 frame per 10 simulation seconds
    step = 10
    n_frames = max_time // step

    def animate(frame):
        t = frame * step
        for name, data in scenario_data.items():
            end = min(t, len(data))
            x = np.arange(end) / 60.0
            lines[name].set_data(x, data[:end])
        time_text.set_text(f"Kl. 07:45 + {t // 60} min")
        return list(lines.values()) + [time_text]

    anim = animation.FuncAnimation(
        fig, animate, frames=n_frames, interval=33, blit=True
    )

    # Save as GIF
    try:
        anim.save(str(VIZ_DIR / "queue_growth.gif"), writer="pillow", fps=30)
        print(f"✓ Queue animation GIF → {VIZ_DIR / 'queue_growth.gif'}")
    except Exception as e:
        print(f"  GIF save failed: {e}")

    # Save as MP4
    try:
        anim.save(str(VIZ_DIR / "queue_growth.mp4"), writer="ffmpeg", fps=30)
        print(f"✓ Queue animation MP4 → {VIZ_DIR / 'queue_growth.mp4'}")
    except Exception as e:
        print(f"  MP4 save failed (ffmpeg needed): {e}")

    plt.close()


# ============================================================================
# ANIMATED TRAFFIC REPLAY (4a)
# ============================================================================

def animate_traffic_replay(scenario: str = "scenario_4A_v1", seed: int = 1):
    """Animated top-down view with moving dots colored by speed."""
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    fcd_df = load_fcd(scenario, seed)
    if fcd_df.empty:
        print(f"No FCD data for {scenario}")
        return

    print(f"Loaded {len(fcd_df)} FCD records for {scenario}")

    timesteps = sorted(fcd_df["time"].unique())
    if len(timesteps) < 2:
        print("Not enough timesteps for animation")
        return

    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_aspect("equal")
    ax.set_facecolor("#1a1a2e")

    # Get bounds
    x_min, x_max = fcd_df["x"].min() - 50, fcd_df["x"].max() + 50
    y_min, y_max = fcd_df["y"].min() - 50, fcd_df["y"].max() + 50
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    label = SCENARIO_LABELS.get(scenario, scenario)
    ax.set_title(f"Trafikksimulering: {label}\nMorgenrush 2040", fontsize=14, color="white")
    ax.tick_params(colors="white")

    scat = ax.scatter([], [], s=8, c=[], cmap="RdYlGn", vmin=0, vmax=15, zorder=5)
    time_text = ax.text(0.02, 0.98, "", transform=ax.transAxes, fontsize=14,
                        color="white", verticalalignment="top", fontweight="bold")

    # Subsample timesteps for reasonable animation length
    step = max(1, len(timesteps) // 300)
    selected_ts = timesteps[::step]

    def animate(frame):
        t = selected_ts[frame]
        mask = fcd_df["time"] == t
        subset = fcd_df[mask]
        if len(subset) > 0:
            scat.set_offsets(np.column_stack([subset["x"].values, subset["y"].values]))
            scat.set_array(subset["speed"].values)
        minutes = int(t // 60)
        seconds = int(t % 60)
        time_text.set_text(f"07:45 + {minutes:02d}:{seconds:02d}")
        return [scat, time_text]

    anim = animation.FuncAnimation(
        fig, animate, frames=len(selected_ts), interval=33, blit=True
    )

    try:
        anim.save(str(VIZ_DIR / f"traffic_replay_{scenario}.gif"), writer="pillow", fps=30)
        print(f"✓ Traffic replay GIF → {VIZ_DIR / f'traffic_replay_{scenario}.gif'}")
    except Exception as e:
        print(f"  GIF save failed: {e}")

    try:
        anim.save(str(VIZ_DIR / f"traffic_replay_{scenario}.mp4"), writer="ffmpeg", fps=30)
        print(f"✓ Traffic replay MP4 → {VIZ_DIR / f'traffic_replay_{scenario}.mp4'}")
    except Exception as e:
        print(f"  MP4 save failed: {e}")

    plt.close()


def animate_side_by_side(
    scenario_left: str = "scenario_4A_base",
    scenario_right: str = "scenario_4A_v1",
    seed: int = 1,
):
    """Side-by-side split-screen animation: base vs proposed."""
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    fcd_left = load_fcd(scenario_left, seed)
    fcd_right = load_fcd(scenario_right, seed)

    if fcd_left.empty or fcd_right.empty:
        print(f"Missing FCD data for side-by-side ({scenario_left} or {scenario_right})")
        return

    # Get common timesteps
    ts_left = set(fcd_left["time"].unique())
    ts_right = set(fcd_right["time"].unique())
    common_ts = sorted(ts_left & ts_right)

    if len(common_ts) < 2:
        print("Not enough common timesteps for side-by-side")
        return

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(18, 10))

    for ax, title in [(ax_l, SCENARIO_LABELS.get(scenario_left, scenario_left)),
                       (ax_r, SCENARIO_LABELS.get(scenario_right, scenario_right))]:
        ax.set_aspect("equal")
        ax.set_facecolor("#1a1a2e")
        ax.set_title(title, fontsize=13, color="white", pad=10)
        ax.tick_params(colors="white")

    fig.suptitle("Sammenligning: Dagens veiprofil vs. foreslått bygate\nMorgenrush 07:45-08:45, År 2040",
                 fontsize=15, fontweight="bold", y=0.98)
    fig.patch.set_facecolor("#0d1117")

    # Set same bounds for both
    all_fcd = pd.concat([fcd_left, fcd_right])
    x_min, x_max = all_fcd["x"].min() - 50, all_fcd["x"].max() + 50
    y_min, y_max = all_fcd["y"].min() - 50, all_fcd["y"].max() + 50
    for ax in [ax_l, ax_r]:
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)

    scat_l = ax_l.scatter([], [], s=8, c=[], cmap="RdYlGn", vmin=0, vmax=15)
    scat_r = ax_r.scatter([], [], s=8, c=[], cmap="RdYlGn", vmin=0, vmax=15)

    time_text = fig.text(0.5, 0.02, "", ha="center", fontsize=14,
                         color="white", fontweight="bold")

    step = max(1, len(common_ts) // 300)
    selected_ts = common_ts[::step]

    def animate(frame):
        t = selected_ts[frame]

        for scat, fcd_df in [(scat_l, fcd_left), (scat_r, fcd_right)]:
            mask = fcd_df["time"] == t
            subset = fcd_df[mask]
            if len(subset) > 0:
                scat.set_offsets(np.column_stack([subset["x"].values, subset["y"].values]))
                scat.set_array(subset["speed"].values)

        minutes = int(t // 60)
        time_text.set_text(f"Kl. 07:45 + {minutes} min")
        return [scat_l, scat_r, time_text]

    anim = animation.FuncAnimation(
        fig, animate, frames=len(selected_ts), interval=33, blit=True
    )

    try:
        anim.save(str(VIZ_DIR / "side_by_side.gif"), writer="pillow", fps=30)
        print(f"✓ Side-by-side GIF → {VIZ_DIR / 'side_by_side.gif'}")
    except Exception as e:
        print(f"  GIF failed: {e}")

    try:
        anim.save(str(VIZ_DIR / "side_by_side.mp4"), writer="ffmpeg", fps=30)
        print(f"✓ Side-by-side MP4 → {VIZ_DIR / 'side_by_side.mp4'}")
    except Exception as e:
        print(f"  MP4 failed: {e}")

    plt.close()


# ============================================================================
# INTERACTIVE DASHBOARD (4d)
# ============================================================================

def generate_plotly_dashboard():
    """Generate an interactive HTML dashboard using Plotly."""
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    results = load_all_results()
    if not results:
        print("No results for dashboard")
        return

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "Gjennomsnittlig reisetid (min)",
            "Kjøretøy utenfor modellen",
            "Total forsinkelse (kjt-timer)",
            "Køutvikling over tid",
        ],
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "scatter"}]],
    )

    scenarios = []
    avg_times = []
    waiting_counts = []
    time_losses = []
    colors = []

    for name, runs in results.items():
        if not runs:
            continue
        scenarios.append(SCENARIO_LABELS.get(name, name))
        avg_times.append(np.mean([r.get("avg_duration_s", 0) for r in runs]) / 60.0)
        waiting_counts.append(np.mean([r.get("waiting", 0) for r in runs]))
        time_losses.append(np.mean([r.get("total_time_loss_h", 0) for r in runs]))
        colors.append(SCENARIO_COLORS.get(name, "#95a5a6"))

    # Travel times
    fig.add_trace(go.Bar(x=scenarios, y=avg_times, marker_color=colors,
                         text=[f"{v:.1f}" for v in avg_times], textposition="auto"),
                  row=1, col=1)

    # Waiting vehicles
    fig.add_trace(go.Bar(x=scenarios, y=waiting_counts, marker_color=colors,
                         text=[f"{v:.0f}" for v in waiting_counts], textposition="auto"),
                  row=1, col=2)

    # Time loss
    fig.add_trace(go.Bar(x=scenarios, y=time_losses, marker_color=colors,
                         text=[f"{v:.1f}" for v in time_losses], textposition="auto"),
                  row=2, col=1)

    # Queue timeline
    for scenario_name in SCENARIO_LABELS:
        df = load_summary(scenario_name, seed=1)
        if df.empty:
            continue
        queue = df["waiting"] + df["halting"]
        if len(queue) > 10:
            queue = queue.rolling(window=10, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=df["time"] / 60.0, y=queue,
            name=SCENARIO_LABELS.get(scenario_name, scenario_name),
            line=dict(color=SCENARIO_COLORS.get(scenario_name, "#95a5a6"), width=2),
            showlegend=True,
        ), row=2, col=2)

    fig.update_layout(
        title="Snarøyveien Trafikkanalyse — Scenariosammenligning (2040)",
        height=800,
        template="plotly_dark",
        showlegend=True,
    )

    dashboard_file = VIZ_DIR / "dashboard.html"
    fig.write_html(str(dashboard_file), include_plotlyjs=True)
    print(f"✓ Interactive dashboard → {dashboard_file}")


# ============================================================================
# MAIN
# ============================================================================

def analyze_all():
    """Run all analysis and visualization."""
    print("=" * 60)
    print("PHASE 4-5: Analysis and Visualization")
    print("=" * 60)

    results = load_all_results()

    if results:
        print("\n--- Static Comparison Charts ---")
        chart_travel_times(results)
        chart_queue_lengths(results)
        chart_time_loss(results)

        print("\n--- Queue Timeline ---")
        chart_queue_timeline()

        print("\n--- Animated Queue Growth ---")
        animate_queue_growth()

        print("\n--- Traffic Replay Animation ---")
        animate_traffic_replay("scenario_4A_v1")

        print("\n--- Side-by-Side Animation ---")
        animate_side_by_side("scenario_4A_base", "scenario_4A_v1")

        print("\n--- Interactive Dashboard ---")
        generate_plotly_dashboard()

        print("\n✓ All visualizations generated!")
        print(f"  Output directory: {VIZ_DIR}")
    else:
        print("No simulation results found. Run simulations first.")


if __name__ == "__main__":
    analyze_all()
