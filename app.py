import pandas as pd
import streamlit as st

st.set_page_config(page_title="Week 17 QB Projections", layout="wide")
st.title("2025 Week 17 QB Projections (Weeks 1–16 data)")

LAMBDA = 0.2  # your validated shrinkage factor

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["week"] = df["week"].astype(int)
    df["fantasy_points"] = pd.to_numeric(df["fantasy_points"], errors="coerce")
    df["passer_player_name"] = df["passer_player_name"].astype(str)
    return df

# data_path = st.sidebar.text_input("Data file", "qb_weekly_2025.csv")
data_path = "Practice/qb_weekly_2025.csv"
df = load_data(data_path)

projection_week = 17
latest_week = projection_week - 1
st.caption(f"Using 2025 weeks 1–{latest_week}. Projection = QB roll5 + {LAMBDA} × (Defense roll5 allowed − League avg).")

# ------------------------
# Build QB roll5 through latest week
# ------------------------
df_sorted = df.sort_values(["passer_player_name", "week"]).copy()
df_sorted["qb_roll5"] = (
    df_sorted.groupby("passer_player_name")["fantasy_points"]
    .rolling(5, min_periods=1).mean()
    .reset_index(level=0, drop=True)
)

qb_roll5_latest = (
    df_sorted[df_sorted["week"] == latest_week]
    .set_index("passer_player_name")["qb_roll5"]
)

# ------------------------
# Build defense roll5 allowed through latest week
# opponent_team = defense faced that week
# ------------------------
def_allowed = (
    df.groupby(["opponent_team", "week"], as_index=False)
    .agg(qb_fp_allowed=("fantasy_points", "mean"))
    .sort_values(["opponent_team", "week"])
)

def_allowed["def_roll5_allowed"] = (
    def_allowed.groupby("opponent_team")["qb_fp_allowed"]
    .rolling(5, min_periods=1).mean()
    .reset_index(level=0, drop=True)
)

def_roll5_latest = (
    def_allowed[def_allowed["week"] == latest_week]
    .set_index("opponent_team")["def_roll5_allowed"]
)

league_avg_def = float(def_roll5_latest.mean())

qb_names = sorted(df["passer_player_name"].dropna().unique().tolist())
defenses = sorted(def_roll5_latest.index.dropna().unique().tolist())

# ------------------------
# Sidebar selections
# ------------------------
st.sidebar.subheader("Compare Two QBs")

qb1 = st.sidebar.selectbox("QB 1", qb_names, index=0)
opp1 = st.sidebar.selectbox("QB 1 Week 17 opponent defense", defenses, index=0)

qb2 = st.sidebar.selectbox("QB 2", qb_names, index=1 if len(qb_names) > 1 else 0)
opp2 = st.sidebar.selectbox("QB 2 Week 17 opponent defense", defenses, index=1 if len(defenses) > 1 else 0)

# ------------------------
# Projection function
# ------------------------
def project(qb_name: str, opponent_def: str) -> dict:
    base = float(qb_roll5_latest.get(qb_name, float("nan")))
    dval = float(def_roll5_latest.get(opponent_def, float("nan")))
    proj = base + LAMBDA * (dval - league_avg_def)
    return {
        "QB": qb_name,
        "Week 17 Opponent": opponent_def,
        "QB roll5": base,
        "Defense roll5 allowed": dval,
        "League avg": league_avg_def,
        "Projected": proj,
    }

p1 = project(qb1, opp1)
p2 = project(qb2, opp2)

# ------------------------
# Display: single QB view + comparison
# ------------------------
left, right = st.columns([1.2, 1])

with left:
    st.subheader("QB 1 Trend")
    hist1 = df_sorted[df_sorted["passer_player_name"] == qb1].sort_values("week")
    st.line_chart(hist1.set_index("week")["fantasy_points"])
    st.dataframe(hist1[["week", "fantasy_points", "opponent_team"]].tail(10).reset_index(drop=True), use_container_width=True)

with right:
    st.subheader("QB 2 Trend")
    hist2 = df_sorted[df_sorted["passer_player_name"] == qb2].sort_values("week")
    st.line_chart(hist2.set_index("week")["fantasy_points"])
    st.dataframe(hist2[["week", "fantasy_points", "opponent_team"]].tail(10).reset_index(drop=True), use_container_width=True)

st.divider()
st.subheader("Week 17 Projection Comparison")

compare_df = pd.DataFrame([
    {"QB": p1["QB"], "Opponent": p1["Week 17 Opponent"], "Projected Points": p1["Projected"]},
    {"QB": p2["QB"], "Opponent": p2["Week 17 Opponent"], "Projected Points": p2["Projected"]},
])

def highlight_winner(df_in: pd.DataFrame):
    # green for max, red for min in "Projected Points"
    max_val = df_in["Projected Points"].max()
    min_val = df_in["Projected Points"].min()

    def color_row(row):
        if pd.isna(row["Projected Points"]):
            return [""] * len(row)
        if row["Projected Points"] == max_val and max_val != min_val:
            return ["background-color: rgba(0, 200, 0, 0.25)"] * len(row)
        if row["Projected Points"] == min_val and max_val != min_val:
            return ["background-color: rgba(200, 0, 0, 0.20)"] * len(row)
        # tie (or single unique value): no color
        return [""] * len(row)

    return df_in.style.apply(color_row, axis=1).format({"Projected Points": "{:.2f}"})

st.dataframe(highlight_winner(compare_df), use_container_width=True)

st.caption(
    "Note: Opponent adjustment uses defense roll5 allowed through Week "
    f"{latest_week}. League avg is the mean of defenses’ roll5 allowed."
)
