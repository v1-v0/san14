"""
RTK14 Recruitment Log Analyzer
Parses 登庸 (recruitment) events from a game log and generates:
  1. Cleaned CSV of all recruitment attempts
  2. Statistics (recruiter effectiveness, target difficulty)
  3. Network graph visualization
"""

# from asyncio import events
import os
import re
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from collections import Counter, defaultdict
import platform

# ---------------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------------
INPUT_FILE = os.path.expanduser("~/Downloads/san14_recruitment.xlsx")   # your file
OUTPUT_CLEANED = "recruitment_parsed.csv"
OUTPUT_STATS = "recruitment_stats.xlsx"
OUTPUT_GRAPH_SUCCESS = os.path.expanduser("~/Downloads/recruitment_network_success.png")
OUTPUT_GRAPH_FAILED = os.path.expanduser("~/Downloads/recruitment_network_failure.png")
OUTPUT_GRAPH_OUTSTANDING = os.path.expanduser("~/Downloads/recruitment_network_outstanding.png")

# OCR / typo corrections — extend this dictionary as needed
NAME_FIXES = {
    "簡庸": "簡雍",
    "筍諶": "荀諶",
    "軻比飯": "軻比能",
    "呵比能": "軻比能",
    "越雲": "趙雲",
    "越範": "趙範",
    "顏哀": "顏良",
    "顏原": "顏良",
    "顏隊": "顏良隊",          # ambiguous — only fix if context is clear
    "鮑傮": "鮑信",
    "張邻": "張郃",
    "張部": "張郃",
    "雀琰": "崔琰",
    "辣由": "蘇由",
    "穚瑁": "橋瑁",
    "三原": "平原",        # location, not person
    "頁長": "顏良",
    "顏良長": "顏良",
    "關門": "關羽",
    "對備軍": "劉備軍",
    "沮擾": "沮授",
    "中北": "中止",
    "登廉": "登庸",
    "登康": "登庸",
    "率招": "牽招",
    "表譚": "袁譚",
    "達紀": "逢紀",
    "玫以": "改以",
}

# ---------------------------------------------------------------
# 2. LOAD AND CLEAN
# ---------------------------------------------------------------
def load_log(path):
    df = pd.read_excel(path, sheet_name=0)
    # Expect columns like ["Date", "Actions"]
    df.columns = [c.strip() for c in df.columns]
    if "Actions" not in df.columns:
        # fallback: use last column
        df["Actions"] = df.iloc[:, -1]
    df["Actions"] = df["Actions"].astype(str)
    return df

def apply_fixes(text):
    for bad, good in NAME_FIXES.items():
        text = text.replace(bad, good)
    return text

# ---------------------------------------------------------------
# 3. PARSE RECRUITMENT EVENTS
# ---------------------------------------------------------------
# Regex patterns
PAT_SUCCESS = re.compile(r"^(.{2,4}?)登庸(.{2,4}?)成功$")
PAT_FAIL    = re.compile(r"^(.{2,4}?)登庸(.{2,4}?)失敗$")
PAT_CANCEL  = re.compile(r"^(.{2,4}?)中止登庸(.{2,4}?)$")
PAT_PRISONER = re.compile(r"成功登庸了俘虜(.{2,4})$")

def parse_event(text):
    """Return dict or None if line is not a recruitment event."""
    t = text.strip()
    t = apply_fixes(t)

    m = PAT_PRISONER.search(t)
    if m:
        return {"recruiter": "(俘虜系統)", "target": m.group(1),
                "result": "Success", "type": "Prisoner"}

    m = PAT_SUCCESS.match(t)
    if m:
        return {"recruiter": m.group(1), "target": m.group(2),
                "result": "Success", "type": "Normal"}

    m = PAT_FAIL.match(t)
    if m:
        return {"recruiter": m.group(1), "target": m.group(2),
                "result": "Failed", "type": "Normal"}

    m = PAT_CANCEL.match(t)
    if m:
        return {"recruiter": m.group(1), "target": m.group(2),
                "result": "Canceled", "type": "Normal"}

    return None

def parse_log(df):
    rows = []
    for _, r in df.iterrows():
        ev = parse_event(r["Actions"])
        if ev:
            ev["date"] = r.get("Date", "")
            rows.append(ev)
    return pd.DataFrame(rows)

# ---------------------------------------------------------------
# 4. STATISTICS
# ---------------------------------------------------------------

def build_stats(events):
    import numpy as np

    # Recruiter performance
    recruiter_stats = (
        events[events["type"] == "Normal"]
        .groupby(["recruiter", "result"])
        .size().unstack(fill_value=0)
    )
    for col in ["Success", "Failed", "Canceled"]:
        if col not in recruiter_stats.columns:
            recruiter_stats[col] = 0

    recruiter_stats["Total_Attempts"] = (
        recruiter_stats["Success"] + recruiter_stats["Failed"]
    )
    # Use np.where to avoid division by zero, keep result as float
    recruiter_stats["Success_Rate"] = np.where(
        recruiter_stats["Total_Attempts"] > 0,
        recruiter_stats["Success"] / recruiter_stats["Total_Attempts"].replace(0, np.nan),
        np.nan,
    )
    recruiter_stats["Success_Rate"] = recruiter_stats["Success_Rate"].round(3)
    recruiter_stats = recruiter_stats.sort_values("Success", ascending=False)

    # Target difficulty
    target_stats = (
        events[events["type"] == "Normal"]
        .groupby(["target", "result"])
        .size().unstack(fill_value=0)
    )
    for col in ["Success", "Failed", "Canceled"]:
        if col not in target_stats.columns:
            target_stats[col] = 0
    target_stats["Total_Attempts"] = (
        target_stats["Success"] + target_stats["Failed"]
    )
    target_stats = target_stats.sort_values("Total_Attempts", ascending=False)

    return recruiter_stats, target_stats



# ---------------------------------------------------------------
# 5. NETWORK GRAPH
# ---------------------------------------------------------------

def setup_chinese_font():
    """Find a Chinese-capable font installed on the system."""
    candidates = [
        "Microsoft JhengHei", "Microsoft YaHei", "SimHei",
        "PingFang TC", "PingFang SC", "Heiti TC", "Heiti SC",
        "Noto Sans CJK TC", "Noto Sans CJK SC",
        "Noto Sans CJK JP", "WenQuanYi Zen Hei",
        "Arial Unicode MS",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for c in candidates:
        if c in available:
            # Set BOTH family and the sans-serif fallback list
            plt.rcParams["font.sans-serif"] = [c] + plt.rcParams["font.sans-serif"]
            plt.rcParams["font.family"] = "sans-serif"
            print(f"[font] Using: {c}")
            return
    print("[font] No CJK font found — Chinese may not render.")


def draw_network(events, out_path, result_filter, title_suffix,
                 edge_color, min_attempts=1):
    """
    Draw a recruitment network filtered by result.
    result_filter: "Success" or "Failed"
    """
    setup_chinese_font()
    plt.rcParams["axes.unicode_minus"] = False

    df = events[(events["type"] == "Normal") &
                (events["result"] == result_filter)].copy()

    if df.empty:
        print(f"[graph] No {result_filter} events — skipped {out_path}")
        return

    # Aggregate edges (count attempts per recruiter→target pair)
    edge_counts = (
        df.groupby(["recruiter", "target"]).size().reset_index(name="count")
    )
    edge_counts = edge_counts[edge_counts["count"] >= min_attempts]

    G = nx.DiGraph()
    for _, r in edge_counts.iterrows():
        G.add_edge(r["recruiter"], r["target"], weight=int(r["count"]))

    if G.number_of_nodes() == 0:
        print(f"[graph] No edges after filtering — skipped {out_path}")
        return

    degrees = dict(G.degree())
    sizes = [250 + 90 * degrees.get(n, 1) for n in G.nodes()]
    widths = [0.6 + G[u][v]["weight"] * 1.0 for u, v in G.edges()]

    fig, ax = plt.subplots(figsize=(20, 16))
    pos = nx.spring_layout(G, k=0.9, iterations=80, seed=42)

    nx.draw_networkx_nodes(G, pos, node_size=sizes,
                           node_color="#cfe2ff",
                           edgecolors="#1f4e8c", linewidths=1.2, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color=edge_color,
                           width=widths, alpha=0.75,
                           arrows=True, arrowsize=14,
                           connectionstyle="arc3,rad=0.08", ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=10, ax=ax)

    # Show count label only for repeated attempts (>1)
    edge_labels = {(u, v): str(G[u][v]["weight"])
                   for u, v in G.edges() if G[u][v]["weight"] > 1}
    if edge_labels:
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                      font_size=8, ax=ax)

    ax.set_title(f"RTK14 登庸 Recruitment Network — {title_suffix}\n"
                 f"Nodes: {G.number_of_nodes()}  |  "
                 f"Edges: {G.number_of_edges()}  |  "
                 f"Total attempts: {int(edge_counts['count'].sum())}",
                 fontsize=14)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    print(f"[graph] Saved: {out_path}")
    plt.close()

def draw_outstanding_network(events, out_path, min_attempts=1):
    """
    Draw a network of failed recruitment attempts where the target
    was NEVER successfully recruited by anyone in the log.
    """
    setup_chinese_font()
    plt.rcParams["axes.unicode_minus"] = False

    normal = events[events["type"] == "Normal"].copy()

    # Targets who were eventually recruited (by anyone)
    recruited_targets = set(
        normal.loc[normal["result"] == "Success", "target"].unique()
    )

    # Failed attempts on targets NOT in the recruited set
    df = normal[(normal["result"] == "Failed") &
                (~normal["target"].isin(recruited_targets))].copy()

    if df.empty:
        print(f"[graph] No outstanding targets — skipped {out_path}")
        return

    edge_counts = (
        df.groupby(["recruiter", "target"]).size().reset_index(name="count")
    )
    edge_counts = edge_counts[edge_counts["count"] >= min_attempts]

    G = nx.DiGraph()
    for _, r in edge_counts.iterrows():
        G.add_edge(r["recruiter"], r["target"], weight=int(r["count"]))

    if G.number_of_nodes() == 0:
        print(f"[graph] No edges after filtering — skipped {out_path}")
        return

    # Identify outstanding targets (in-degree > 0, no outgoing success)
    outstanding = set(df["target"].unique())

    degrees = dict(G.degree())
    sizes, node_colors, edge_colors_nodes = [], [], []
    for n in G.nodes():
        sizes.append(250 + 90 * degrees.get(n, 1))
        if n in outstanding:
            node_colors.append("#ffd1d1")        # light red = outstanding target
            edge_colors_nodes.append("#a40000")
        else:
            node_colors.append("#cfe2ff")        # light blue = recruiter
            edge_colors_nodes.append("#1f4e8c")

    widths = [0.6 + G[u][v]["weight"] * 1.0 for u, v in G.edges()]

    fig, ax = plt.subplots(figsize=(20, 16))
    pos = nx.spring_layout(G, k=0.9, iterations=80, seed=42)

    nx.draw_networkx_nodes(G, pos, node_size=sizes,
                           node_color=node_colors,
                           edgecolors=edge_colors_nodes,
                           linewidths=1.2, ax=ax)
    nx.draw_networkx_edges(G, pos, edge_color="#d62728",
                           width=widths, alpha=0.75,
                           arrows=True, arrowsize=14,
                           connectionstyle="arc3,rad=0.08", ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=10, ax=ax)

    edge_labels = {(u, v): str(G[u][v]["weight"])
                   for u, v in G.edges() if G[u][v]["weight"] > 1}
    if edge_labels:
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                     font_size=8, ax=ax)

    ax.set_title(
        f"RTK14 登庸 — Outstanding Targets (never recruited)\n"
        f"Targets: {len(outstanding)}  |  "
        f"Recruiters: {G.number_of_nodes() - len(outstanding)}  |  "
        f"Failed attempts: {int(edge_counts['count'].sum())}",
        fontsize=14)
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    print(f"[graph] Saved: {out_path}")
    plt.close()

    # Also print a quick summary to console
    summary = (
        df.groupby("target").size()
          .sort_values(ascending=False)
          .reset_index(name="Failed_Attempts")
    )
    print("\n=== Outstanding Targets (never recruited) ===")
    print(summary.to_string(index=False))


# ---------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------
def main():
    print("Loading log...")
    df = load_log(INPUT_FILE)

    print("Parsing recruitment events...")
    events = parse_log(df)
    print(f"  Found {len(events)} recruitment events.")
    events.to_csv(OUTPUT_CLEANED, index=False, encoding="utf-8-sig")
    print(f"  Saved cleaned data: {OUTPUT_CLEANED}")

    print("Building statistics...")
    recruiter_stats, target_stats = build_stats(events)

    with pd.ExcelWriter(OUTPUT_STATS, engine="openpyxl") as w:
        events.to_excel(w, sheet_name="All_Events", index=False)
        recruiter_stats.to_excel(w, sheet_name="By_Recruiter")
        target_stats.to_excel(w, sheet_name="By_Target")
    print(f"  Saved stats: {OUTPUT_STATS}")

    print("\n=== Top Recruiters (by successful recruitments) ===")
    print(recruiter_stats.head(10).to_string())

    print("\n=== Most-Attempted Targets ===")
    print(target_stats.head(10).to_string())

    print("\nDrawing success network...")
    draw_network(events, OUTPUT_GRAPH_SUCCESS,
                 result_filter="Success",
                 title_suffix="Successful Recruitments",
                 edge_color="#2ca02c",   # green
                 min_attempts=1)

    print("Drawing failure network...")
    draw_network(events, OUTPUT_GRAPH_FAILED,
                 result_filter="Failed",
                 title_suffix="Failed Recruitments",
                 edge_color="#d62728",   # red
                 min_attempts=1)

    print("Drawing outstanding-targets network...")
    draw_outstanding_network(events, OUTPUT_GRAPH_OUTSTANDING, min_attempts=1)

    print("Done.")

if __name__ == "__main__":
    main()