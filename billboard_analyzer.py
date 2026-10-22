"""
Billboard Cost Analyzer
=======================
Reads a CSV of billboard locations and works out which ones give the best
value for money.

Key metric: CPM (cost per mille = cost per 1,000 impressions)
    CPM = (monthly_cost / monthly_impressions) * 1000
Lower CPM = cheaper to reach 1,000 people = better value.

What the script does:
    1. Loads and cleans the data
    2. Calculates CPM for every billboard
    3. Ranks billboards from best value (lowest CPM) to worst
    4. Filters the billboards you can afford within a budget
    5. Saves two CSV files and a bar chart into the output/ folder

Usage:
    python billboard_analyzer.py
    python billboard_analyzer.py --budget 150000
    python billboard_analyzer.py --budget 150000 --show
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

# ----------------------------------------------------------------------------
# Settings (constants are written in UPPER_CASE by Python convention)
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent                 # folder this script lives in
DEFAULT_DATA_FILE = BASE_DIR / "data" / "billboards.csv"
OUTPUT_DIR = BASE_DIR / "output"
CURRENCY = "₹"                                   # change to "$" if you like
DEFAULT_BUDGET = 250_000                         # monthly budget per billboard

REQUIRED_COLUMNS = ["location", "city", "type", "monthly_cost", "monthly_impressions"]


# ----------------------------------------------------------------------------
# Step 1: Load and clean
# ----------------------------------------------------------------------------
def load_data(path):
    """Read the CSV file into a pandas DataFrame (think: an in-memory table)."""
    if not path.exists():
        raise FileNotFoundError(f"Could not find data file: {path}")

    df = pd.read_csv(path)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required column(s): {', '.join(missing)}")

    return df


def clean_data(df):
    """Remove rows we cannot calculate with (blank, non-numeric, zero or negative values)."""
    rows_before = len(df)

    # Turn the number columns into real numbers; anything unreadable becomes NaN.
    for col in ["monthly_cost", "monthly_impressions"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows with any blank/NaN in the columns we need.
    df = df.dropna(subset=REQUIRED_COLUMNS)

    # Cost and impressions must be positive (also avoids dividing by zero).
    df = df[(df["monthly_cost"] > 0) & (df["monthly_impressions"] > 0)]

    removed = rows_before - len(df)
    if removed:
        print(f"Note: removed {removed} invalid row(s) from the data.\n")

    return df.copy()


# ----------------------------------------------------------------------------
# Step 2-4: Analyse
# ----------------------------------------------------------------------------
def add_cpm(df):
    """Add a 'cpm' column: cost per 1,000 impressions."""
    df = df.copy()  # work on a copy so we never change the caller's data
    df["cpm"] = (df["monthly_cost"] / df["monthly_impressions"] * 1000).round(2)
    return df


def rank_by_value(df):
    """Sort from cheapest CPM (best value) to most expensive and add a rank column."""
    ranked = df.sort_values("cpm").reset_index(drop=True)
    ranked.insert(0, "rank", ranked.index + 1)  # index starts at 0, ranks start at 1
    return ranked


def filter_by_budget(df, budget):
    """Keep only billboards whose monthly cost is within the budget."""
    return df[df["monthly_cost"] <= budget].reset_index(drop=True)


# ----------------------------------------------------------------------------
# Step 5: Export
# ----------------------------------------------------------------------------
def save_csv(df, path):
    """Write a DataFrame to a CSV file."""
    df.to_csv(path, index=False)
    print(f"Saved: {path.relative_to(BASE_DIR)}")


def plot_cpm_chart(ranked, budget, path, show=False):
    """Horizontal bar chart of CPM per billboard; affordable ones are highlighted."""
    affordable = ranked["monthly_cost"] <= budget
    colors = ["#2a9d8f" if ok else "#b8b8b8" for ok in affordable]
    labels = ranked["location"] + " (" + ranked["city"] + ")"

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(labels, ranked["cpm"], color=colors)

    ax.invert_yaxis()  # rank 1 (best value) at the top
    ax.set_xlabel(f"Cost per 1,000 impressions ({CURRENCY})")
    ax.set_title("Billboard Value Ranking (lower is better)")
    ax.set_xlim(0, ranked["cpm"].max() * 1.12)  # leave room for the value labels

    # Write the CPM value at the end of each bar.
    for bar, value in zip(bars, ranked["cpm"]):
        ax.text(value + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{CURRENCY}{value:,.0f}", va="center", fontsize=8)

    ax.legend(
        handles=[
            Patch(color="#2a9d8f", label=f"Within budget (≤ {CURRENCY}{budget:,.0f}/month)"),
            Patch(color="#b8b8b8", label="Over budget"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.1),  # place the legend below the chart, outside the bars
        ncol=2,
        frameon=False,
    )

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")  # "tight" keeps the legend from being cropped
    print(f"Saved: {path.relative_to(BASE_DIR)}")

    if show:
        plt.show()
    plt.close(fig)


# ----------------------------------------------------------------------------
# Display helper
# ----------------------------------------------------------------------------
def print_table(title, df):
    """Print a neat table to the terminal."""
    columns = ["rank", "location", "city", "type", "monthly_cost", "monthly_impressions", "cpm"]
    print(title)
    print("-" * len(title))
    print(df[columns].to_string(index=False, formatters={
        "monthly_cost": lambda x: f"{CURRENCY}{x:,.0f}",
        "monthly_impressions": lambda x: f"{x:,.0f}",
        "cpm": lambda x: f"{CURRENCY}{x:,.2f}",
    }))
    print()


# ----------------------------------------------------------------------------
# Command-line options and main program
# ----------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Analyze billboard cost per 1,000 impressions.")
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET,
                        help=f"max monthly cost per billboard (default: {DEFAULT_BUDGET})")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_FILE,
                        help="path to the billboard CSV file")
    parser.add_argument("--show", action="store_true",
                        help="also open the chart in a window")
    return parser.parse_args()


def main():
    args = parse_args()
    OUTPUT_DIR.mkdir(exist_ok=True)  # create output/ if it does not exist yet

    df = load_data(args.data)
    df = clean_data(df)
    df = add_cpm(df)
    ranked = rank_by_value(df)
    within_budget = filter_by_budget(ranked, args.budget)  # keeps the overall rank

    print_table("All billboards ranked by value (best first)", ranked)

    budget_title = f"Billboards within budget ({CURRENCY}{args.budget:,.0f}/month)"
    if within_budget.empty:
        print(budget_title)
        print("-" * len(budget_title))
        print("No billboards fit this budget. Try a higher one.\n")
    else:
        print_table(budget_title, within_budget)
        best = within_budget.iloc[0]
        print(f"Best value within budget: {best['location']} ({best['city']}) "
              f"at {CURRENCY}{best['cpm']:,.2f} per 1,000 impressions.\n")

    save_csv(ranked, OUTPUT_DIR / "ranked_billboards.csv")
    save_csv(within_budget, OUTPUT_DIR / "within_budget.csv")
    plot_cpm_chart(ranked, args.budget, OUTPUT_DIR / "cpm_chart.png", show=args.show)


# This line means: only run main() when the file is executed directly
# (not when it is imported from another file). Similar idea to Java's main method.
if __name__ == "__main__":
    main()
