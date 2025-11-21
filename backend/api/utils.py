# api/utils.py
import pandas as pd

def compute_summary_from_csv_file(path, include_preview_rows=20):
    """
    Read CSV with pandas and compute summary stats for numeric columns.
    Returns a dictionary suitable for JSONField / response.
    """
    # read CSV (let pandas infer dtypes)
    df = pd.read_csv(path)

    # build preview rows (convert to list of dicts)
    preview = df.head(include_preview_rows).to_dict(orient="records")

    # numeric columns
    numeric = df.select_dtypes(include="number").columns.tolist()

    summary = {}
    for col in numeric:
        s = df[col].dropna()
        summary[col] = {
            "count": int(s.count()),
            "mean": None if s.empty else float(s.mean()),
            "median": None if s.empty else float(s.median()),
            "std": None if s.empty else float(s.std()),
            "min": None if s.empty else float(s.min()),
            "max": None if s.empty else float(s.max()),
        }

    payload = {
        "rows": len(df),
        "columns": df.columns.tolist(),
        "numeric_columns": numeric,
        "summary": summary,
        "raw_preview": preview
    }
    return payload
