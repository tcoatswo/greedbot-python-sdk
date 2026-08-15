"""
GreedBot DataFrame Extraction & Parsing Utilities
-------------------------------------------------
Helper functions to extract tabular data, ranking lists, and signals
from GreedBot API responses and convert them into Python dictionaries,
tuples, or pandas DataFrames.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union


def map_from_df(payload: Dict[str, Any], value_col: str) -> Dict[str, float]:
    """
    Build `{ticker -> value}` mapping from a baked response of shape:
    `{"df": {"ticker": [...], <col>: [...]}}` or `{"<section>": {"df": ...}}`.

    Missing/null values default to 0.0; tickers are lowercased.
    """
    out: Dict[str, float] = {}
    if not isinstance(payload, dict):
        return out

    # Check top-level df, or nested sections like 'pizza', 'targets', 'table'
    df = payload.get("df")
    if not isinstance(df, dict):
        for section in ("pizza", "table", "data", "result"):
            sub = payload.get(section)
            if isinstance(sub, dict) and isinstance(sub.get("df"), dict):
                df = sub.get("df")
                break

    if not isinstance(df, dict):
        return out

    tickers = df.get("ticker")
    values = df.get(value_col)
    if not isinstance(tickers, list) or not isinstance(values, list):
        return out

    for t, v in zip(tickers, values):
        if t is not None:
            t_str = str(t).strip().lower()
            try:
                val = float(v) if v is not None and math.isfinite(float(v)) else 0.0
            except (ValueError, TypeError):
                val = 0.0
            out[t_str] = val

    return out


def ranking_from_pizza(payload: Dict[str, Any]) -> List[Tuple[str, float]]:
    """
    Build a `[(ticker, pizza_slice)]` ranking from a `/pizza/baked` payload,
    sorted ascending by slice (lowest score first, best name last).

    Raises ValueError if payload is missing the pizza/df structure.
    """
    if not isinstance(payload, dict):
        raise ValueError("Invalid payload: expected dictionary")

    pizza = payload.get("pizza") if "pizza" in payload else payload
    if not isinstance(pizza, dict):
        raise ValueError("missing 'pizza' in /pizza/baked payload")

    df = pizza.get("df") if "df" in pizza else pizza
    if not isinstance(df, dict):
        raise ValueError("missing 'df' in /pizza/baked payload")

    tickers = df.get("ticker")
    if not isinstance(tickers, list):
        raise ValueError("missing 'ticker' column in /pizza/baked df")

    slices = df.get("pizza_slice")
    if slices is None:
        # Fallback to rank or score column if pizza_slice not found
        slices = df.get("rank", df.get("score"))
    if not isinstance(slices, list):
        raise ValueError("missing 'pizza_slice' column in /pizza/baked df")

    ranking: List[Tuple[str, float]] = []
    for t, s in zip(tickers, slices):
        if t is not None:
            try:
                score = float(s) if s is not None and math.isfinite(float(s)) else 0.0
            except (ValueError, TypeError):
                score = 0.0
            ranking.append((str(t).strip().lower(), score))

    # Sort ascending by slice score
    ranking.sort(key=lambda item: item[1])
    return ranking


def extract_signal(payload: Dict[str, Any], ticker: str) -> float:
    """
    Extract the aggregated algo signal for `ticker` from a `/targets/baked` payload.
    Prefers the `algos` aggregated column; falls back to `kelly`.

    Raises ValueError if the ticker is explicitly in `excluded_tickers` or
    if both aggregate columns are missing. An absent-but-not-excluded ticker
    returns 0.0 (FLAT).
    """
    ticker_clean = ticker.strip().lower()

    if not isinstance(payload, dict):
        raise ValueError("Invalid payload: expected dictionary")

    # Surface excluded tickers as an error to prevent silent misconfiguration
    excluded = payload.get("excluded_tickers")
    if isinstance(excluded, dict):
        for reason, ticker_list in excluded.items():
            if isinstance(ticker_list, list):
                for t in ticker_list:
                    if str(t).strip().lower() == ticker_clean:
                        raise ValueError(f"ticker {ticker} excluded by server (reason: {reason})")

    df = payload.get("df")
    if not isinstance(df, dict):
        raise ValueError("missing df in /targets/baked payload")

    tickers = df.get("ticker")
    if not isinstance(tickers, list):
        raise ValueError("missing ticker column in /targets/baked df")

    idx = None
    for i, t in enumerate(tickers):
        if t is not None and str(t).strip().lower() == ticker_clean:
            idx = i
            break

    if idx is None:
        return 0.0  # Absent but not excluded -> FLAT

    col = df.get("algos")
    if col is None:
        col = df.get("kelly")

    if not isinstance(col, list):
        raise ValueError("missing both 'algos' and 'kelly' aggregate columns in /targets/baked df")

    if idx < len(col):
        v = col[idx]
        try:
            return float(v) if v is not None and math.isfinite(float(v)) else 0.0
        except (ValueError, TypeError):
            return 0.0

    return 0.0


def to_dataframe(payload: Dict[str, Any], section: Optional[str] = None) -> Any:
    """
    Convert a GreedBot API response containing tabular data into a pandas DataFrame
    if pandas is installed; otherwise returns the raw dictionary.
    """
    try:
        import pandas as pd
    except ImportError:
        # Fallback to dict if pandas is not available
        return payload

    if not isinstance(payload, dict):
        return pd.DataFrame()

    target = payload
    if section:
        target = payload.get(section, {})

    if isinstance(target, dict) and "df" in target and isinstance(target["df"], dict):
        return pd.DataFrame(target["df"])
    elif isinstance(target, dict) and all(isinstance(v, list) for v in target.values()):
        return pd.DataFrame(target)
    elif isinstance(target, list) and all(isinstance(item, dict) for item in target):
        return pd.DataFrame(target)

    return pd.DataFrame()
