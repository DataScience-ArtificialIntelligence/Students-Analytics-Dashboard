"""
Flask API — Student Performance Analytics Backend
Reads the processed CSV exported from HDFS and exposes REST endpoints.

Endpoints:
  GET /data              → full dataset (JSON)
  GET /at-risk           → students with label=1
  GET /summary           → aggregate stats
  GET /branch/<branch>   → filter by branch
  GET /health            → health check
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from functools import lru_cache
import pandas as pd
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FlaskAPI")

app = Flask(__name__)
CORS(app)  # Allow React dev server on different port

# ─────────────────────────────────────────────
# CONFIG — update path to wherever you export
# the HDFS CSV locally (e.g. via hdfs dfs -get)
# ─────────────────────────────────────────────
CSV_PATH = os.environ.get(
    "PROCESSED_CSV",
    os.path.join(os.path.dirname(__file__), "data", "predictions.csv")
)
RAW_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "raw_data"))
SUBJECTS = ["BDA", "DL", "DSP", "DBMS"]
SUBJECT_MARK_COLUMNS = [
    "quiz1_marks",
    "quiz2_marks",
    "assignment_marks",
    "mid_sem_marks",
    "end_sem_marks",
]
SUBJECT_MAX_MARKS = 100.0
SUBJECT_RISK_THRESHOLD = round(SUBJECT_MAX_MARKS * 0.33, 2)


# ─────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────
@lru_cache(maxsize=1)
def _load_base_data() -> pd.DataFrame:
    """Load and lightly clean the processed CSV."""
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"CSV not found at {CSV_PATH}. "
            "Run: hdfs dfs -get /students_data/processed_data/predictions.csv flask/data/"
        )

    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip()

    # Ensure correct types
    df["attendance_pct"] = df["attendance_pct"].astype(float).round(4)
    df["avg_marks"]      = df["avg_marks"].astype(float).round(2)
    df["label"]          = df["label"].astype(int)
    df["year"]           = df["year"].astype(int)

    if "risk_score" in df.columns:
        df["risk_score"] = df["risk_score"].astype(float).round(4)
    logger.info(f"Loaded {len(df)} records from {CSV_PATH}")
    return df


@lru_cache(maxsize=1)
def load_subject_totals() -> pd.DataFrame:
    """Build per-subject total marks for each student from raw CSV files."""
    subject_frames = {subject: [] for subject in SUBJECTS}

    for filename in os.listdir(RAW_DATA_DIR):
        if not filename.endswith("_marks.csv"):
            continue

        stem = filename[:-10]
        parts = stem.split("_")
        if len(parts) < 2:
            continue

        subject = parts[-1].upper()
        if subject not in SUBJECTS:
            continue

        path = os.path.join(RAW_DATA_DIR, filename)
        marks_df = pd.read_csv(path, usecols=["student_id", *SUBJECT_MARK_COLUMNS])
        marks_df["student_id"] = marks_df["student_id"].astype(int)
        marks_df[f"total_{subject}"] = (
            marks_df["quiz1_marks"].astype(float)
            + marks_df["quiz2_marks"].astype(float)
            + marks_df["assignment_marks"].astype(float)
            + (marks_df["mid_sem_marks"].astype(float) * 0.4)
            + (marks_df["end_sem_marks"].astype(float) * 0.4)
        ).round(2)
        subject_frames[subject].append(marks_df[["student_id", f"total_{subject}"]])

    combined = None
    for subject in SUBJECTS:
        if not subject_frames[subject]:
            continue

        subject_df = pd.concat(subject_frames[subject], ignore_index=True)
        if combined is None:
            combined = subject_df
        else:
            combined = combined.merge(subject_df, on="student_id", how="outer")

    if combined is None:
        raise FileNotFoundError(f"No raw marks CSV files found in {RAW_DATA_DIR}")

    for subject in SUBJECTS:
        col = f"total_{subject}"
        if col in combined.columns:
            combined[col] = combined[col].astype(float).round(2)

    return combined


def load_data() -> pd.DataFrame:
    """Load processed data and enrich it with per-subject total marks."""
    df = _load_base_data().copy()
    subject_totals = load_subject_totals().copy()
    df = df.merge(subject_totals, on="student_id", how="left")

    for subject in SUBJECTS:
        col = f"total_{subject}"
        if col in df.columns:
            df[col] = df[col].astype(float).round(2)

    return df


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def df_to_records(df: pd.DataFrame):
    return df.to_dict(orient="records")


def error(msg: str, code: int = 400):
    return jsonify({"error": msg}), code


def resolve_subject(subject: str) -> str:
    candidate = (subject or "").upper()
    return candidate if candidate in SUBJECTS else SUBJECTS[0]


def apply_subject_context(df: pd.DataFrame, subject: str):
    selected_subject = resolve_subject(subject)
    subject_col = f"total_{selected_subject}"
    scoped = df.copy()

    scoped["selected_subject"] = selected_subject
    scoped["selected_marks"] = scoped[subject_col].astype(float).round(2)
    scoped["marks_threshold"] = SUBJECT_RISK_THRESHOLD
    scoped["marks_max"] = SUBJECT_MAX_MARKS
    scoped["subject_risk"] = (
        (scoped["selected_marks"] < SUBJECT_RISK_THRESHOLD)
        | (scoped["attendance_pct"] < 0.75)
    ).astype(int)

    return scoped, selected_subject, subject_col


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "csv": CSV_PATH})


@app.route("/data")
def get_all_data():
    """Return full dataset. Optional query params: branch, subject."""
    try:
        df = load_data()
        df, selected_subject, _ = apply_subject_context(df, request.args.get("subject", ""))

        branch = request.args.get("branch", "").upper()

        if branch:
            df = df[df["branch"].str.upper() == branch]

        return jsonify({
            "subject": selected_subject,
            "subject_options": SUBJECTS,
            "subject_max_marks": SUBJECT_MAX_MARKS,
            "marks_threshold": SUBJECT_RISK_THRESHOLD,
            "total": len(df),
            "students": df_to_records(df)
        })
    except FileNotFoundError as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Error in /data")
        return error(str(e), 500)


@app.route("/at-risk")
def get_at_risk():
    """Return students below the subject threshold or attendance threshold."""
    try:
        df = load_data()
        df, selected_subject, _ = apply_subject_context(df, request.args.get("subject", ""))
        at_risk = df[df["subject_risk"] == 1]

        if "risk_score" in at_risk.columns:
            at_risk = at_risk.sort_values("risk_score", ascending=False)

        return jsonify({
            "subject": selected_subject,
            "subject_options": SUBJECTS,
            "subject_max_marks": SUBJECT_MAX_MARKS,
            "marks_threshold": SUBJECT_RISK_THRESHOLD,
            "total_at_risk": len(at_risk),
            "students": df_to_records(at_risk)
        })
    except FileNotFoundError as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Error in /at-risk")
        return error(str(e), 500)


@app.route("/summary")
def get_summary():
    """Return subject-aware aggregate statistics across branches."""
    try:
        df = load_data()
        df, selected_subject, _ = apply_subject_context(df, request.args.get("subject", ""))

        overall = {
            "total_students":   int(len(df)),
            "at_risk_count":    int(df["subject_risk"].sum()),
            "at_risk_pct":      round(float(df["subject_risk"].mean()) * 100, 2),
            "subject_marks_mean": round(float(df["selected_marks"].mean()), 2),
            "subject_marks_min":  round(float(df["selected_marks"].min()), 2),
            "subject_marks_max":  round(float(df["selected_marks"].max()), 2),
            "attendance_mean":  round(float(df["attendance_pct"].mean()), 4),
        }

        branch_stats = []
        for branch, grp in df.groupby("branch"):
            branch_stats.append({
                "branch":          branch,
                "total":           int(len(grp)),
                "at_risk":         int(grp["subject_risk"].sum()),
                "subject_marks":   round(float(grp["selected_marks"].mean()), 2),
                "avg_attendance":  round(float(grp["attendance_pct"].mean()), 4),
            })

        return jsonify({
            "subject":      selected_subject,
            "subject_options": SUBJECTS,
            "subject_max_marks": SUBJECT_MAX_MARKS,
            "marks_threshold": SUBJECT_RISK_THRESHOLD,
            "overall":      overall,
            "by_branch":    branch_stats,
        })
    except FileNotFoundError as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Error in /summary")
        return error(str(e), 500)


@app.route("/branch/<branch>")
def get_branch(branch: str):
    try:
        df = load_data()
        filtered = df[df["branch"].str.upper() == branch.upper()]
        if filtered.empty:
            return error(f"No data for branch: {branch}", 404)
        return jsonify({
            "branch":   branch.upper(),
            "total":    len(filtered),
            "students": df_to_records(filtered)
        })
    except FileNotFoundError as e:
        return error(str(e), 404)
    except Exception as e:
        logger.exception("Error in /branch")
        return error(str(e), 500)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask API on port {port}")
    logger.info(f"Using CSV: {CSV_PATH}")
    app.run(host="0.0.0.0", port=port, debug=True)
