from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

# ---------- Data loading from repo root (flat layout) ----------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_csv(filename: str) -> pd.DataFrame:
    path = os.path.join(ROOT_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing data file: {filename} (expected in repo root)")
    return pd.read_csv(path)

try:
    states_df = load_csv("states_and_union_territories.csv")
    cities_df = load_csv("cities.csv")
    budget_duration_df = load_csv("city_budget_duration.csv")
    cities_type_df = load_csv("cities_type_data.csv")
except Exception as e:
    print(f"Startup data load error: {e}")
    raise

# ---------- Preprocess ----------
def preprocess():
    # Normalize IDs
    for df in [cities_df, budget_duration_df, cities_type_df]:
        if "City_ID" in df.columns:
            df["City_ID"] = pd.to_numeric(df["City_ID"], errors="coerce").astype("Int64")
    if "Type_ID" in cities_type_df.columns:
        cities_type_df["Type_ID"] = pd.to_numeric(cities_type_df["Type_ID"], errors="coerce").astype("Int64")

    # Clean duration "3-5 days" -> "3-5"
    if "Duration_Range" in budget_duration_df.columns:
        budget_duration_df["Duration_Range"] = (
            budget_duration_df["Duration_Range"].astype(str).str.replace(r"[^\d\-]", "", regex=True)
        )

    # Maps
    global TYPE_NAME_MAP, CITY_META_MAP
    TYPE_NAME_MAP = (
        cities_type_df[["Type_ID", "Type_Name"]]
        .dropna()
        .drop_duplicates()
        .set_index("Type_ID")["Type_Name"]
        .to_dict()
    )
    CITY_META_MAP = (
        cities_df[["City_ID", "City_Name", "State_Name"]]
        .dropna()
        .drop_duplicates()
        .set_index("City_ID")
        .to_dict("index")
    )

preprocess()

def parse_range(range_str: str):
    if not isinstance(range_str, str) or "-" not in range_str:
        return None
    parts = [p.strip() for p in range_str.split("-", 1)]
    try:
        return int(parts[0].replace(" ", "")), int(parts[1].replace(" ", ""))
    except Exception:
        return None

def filter_by_budget_duration(df: pd.DataFrame, budget: float, duration: int) -> pd.DataFrame:
    bd = df.copy()
    bd["budget_low"] = bd["Budget_Range"].apply(lambda s: (parse_range(s) or (None, None)))
    bd["budget_high"] = bd["Budget_Range"].apply(lambda s: (parse_range(s) or (None, None))[1])
    bd["dur_low"] = bd["Duration_Range"].apply(lambda s: (parse_range(s) or (None, None)))
    bd["dur_high"] = bd["Duration_Range"].apply(lambda s: (parse_range(s) or (None, None))[1])

    bd = bd.dropna(subset=["budget_low", "budget_high", "dur_low", "dur_high"])
    return bd[
        (bd["budget_low"] <= budget) &
        (bd["budget_high"] >= budget) &
        (bd["dur_low"] <= duration) &
        (bd["dur_high"] >= duration)
    ]

# ---------- API ----------

@app.route("/api/recommendations", methods=["POST"])
def recommendations():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    # Expect { budget:number, duration:number, types:[Type_ID,...] }
    missing = [k for k in ["budget", "duration", "types"] if k not in data]
    if missing:
        return jsonify({"error": f"Missing keys: {', '.join(missing)}"}), 400

    budget = data["budget"]
    duration = data["duration"]
    types = data["types"]

    if not isinstance(budget, (int, float)) or not isinstance(duration, (int, float)):
        return jsonify({"error": "budget and duration must be numbers"}), 400
    if not isinstance(types, list) or not types or not all(isinstance(t, (int, float)) for t in types):
        return jsonify({"error": "types must be a non-empty list of numeric Type_IDs"}), 400

    requested_types = [int(t) for t in types]

    filtered = filter_by_budget_duration(budget_duration_df, float(budget), int(duration))
    if filtered.empty:
        return jsonify({"cities": []})

    ct = cities_type_df[["City_ID", "Type_ID"]].dropna()
    ct = ct[ct["City_ID"].isin(filtered["City_ID"])]
    grouped = ct.groupby("City_ID").agg({"Type_ID": lambda x: list(set(x.dropna().astype(int)))})

    merged = filtered.merge(grouped, on="City_ID", how="left").rename(columns={"Type_ID": "available_types"})
    merged["available_types"] = merged["available_types"].apply(lambda x: x if isinstance(x, list) else [])

    req_set = set(requested_types)
    def score_and_names(avail):
        inter = req_set.intersection(set(avail))
        score = (len(inter) / len(req_set) * 100.0) if req_set else 0.0
        names = [TYPE_NAME_MAP.get(tid, str(tid)) for tid in sorted(inter)]
        return score, names

    tmp = merged["available_types"].apply(score_and_names)
    merged["match_score"] = tmp.apply(lambda x: x[0])
    merged["matching_type_names"] = tmp.apply(lambda x: x[1])

    def city_meta(cid, fallback_name):
        meta = CITY_META_MAP.get(int(cid)) if pd.notnull(cid) else None
        name = meta["City_Name"] if meta else fallback_name or "Unknown"
        state = meta["State_Name"] if meta else None
        return name, state

    merged[["city_name", "state_name"]] = merged.apply(
        lambda r: pd.Series(city_meta(r["City_ID"], r.get("City_Name"))), axis=1
    )

    merged = merged.sort_values("match_score", ascending=False)

    cities = []
    for _, r in merged.iterrows():
        if r["match_score"] <= 0:
            continue
        cities.append({
            "name": r["city_name"],
            "country": r["state_name"],   # using State_Name as region label
            "match_score": round(float(r["match_score"]), 2),
            "matching_types": r["matching_type_names"],
        })

    return jsonify({"cities": cities})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 4001)), debug=True)
