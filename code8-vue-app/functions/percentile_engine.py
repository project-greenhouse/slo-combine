"""Cohort-aware percentile engine.

A "cohort" is a list of metric values from a population (e.g. all sprint times
across all combine athletes). The engine maps an athlete's value to a 0-100
percentile against that list.

Two cohort sources:
- **dynamic** — gathered live from stored test data (Firestore collections or
  cached HD test results)
- **static** — reconstructed from the existing seeded percentile tables
  (combine_percentiles, fp_percentiles), representing elite benchmarks

The frontend selects between them via a `cohort` parameter on get_athlete_metrics.
"""
import numpy as np


def compute_percentile(value, cohort_values, lower_is_better=False):
    """Return an athlete's percentile (0-100) against a cohort.

    For lower-is-better metrics (sprint times, agility times), inverts the
    comparison so that fast times yield high percentiles.

    Returns None if cohort_values is empty or value is None.
    """
    if value is None or not cohort_values:
        return None
    arr = sorted(float(v) for v in cohort_values if v is not None)
    if not arr:
        return None
    n = len(arr)
    v = float(value)
    # Count how many cohort values v is better than
    if lower_is_better:
        better_than = sum(1 for x in arr if x > v)
    else:
        better_than = sum(1 for x in arr if x < v)
    # 0-100 scale, rounded to 1 decimal
    return round(100.0 * better_than / n, 1)


def gather_dynamic_cohort_firestore(db, collection_name, extractor):
    """Stream a Firestore collection, extract a metric value per doc, return list.

    `extractor` is a callable taking the doc dict and returning a numeric value
    (or None to skip).
    """
    values = []
    for doc in db.collection(collection_name).stream():
        d = doc.to_dict()
        v = extractor(d)
        if v is not None:
            try:
                values.append(float(v))
            except (TypeError, ValueError):
                pass
    return values


def gather_dynamic_cohort_hd(hd_tests, field):
    """Pull a field value from each HD test record (already loaded in hd_cache)."""
    if not hd_tests:
        return []
    values = []
    for t in hd_tests:
        v = t.get(field)
        if v is None:
            continue
        try:
            values.append(float(v))
        except (TypeError, ValueError):
            pass
    return values


def gather_static_cohort(db, table_name, column_name):
    """Reconstruct a representative cohort from a seeded percentile table.

    The seeded tables (combine_percentiles, fp_percentiles) have one row per
    percentile (1..99) with the column value at that percentile. We treat each
    of those values as a "cohort member" — using them directly as the comparison
    array yields the same answer the original np.interp lookup gave.
    """
    values = []
    for doc in db.collection(table_name).stream():
        d = doc.to_dict()
        v = d.get(column_name)
        if v is None:
            continue
        try:
            values.append(float(v))
        except (TypeError, ValueError):
            pass
    return values


def rank(value, cohort_values, lower_is_better=False, cohort_label="combine"):
    """Convenience wrapper: returns a rank object {percentile, n, cohort}.

    Returns None if cohort is empty or value is missing — callers should treat
    None as "no rank available" (don't render a badge).
    """
    pct = compute_percentile(value, cohort_values, lower_is_better)
    if pct is None:
        return None
    return {
        "percentile": pct,
        "n": len(cohort_values),
        "cohort": cohort_label,
    }


def best(values, lower_is_better=False):
    """Pick the athlete's best value from a list (min for time, max for everything else)."""
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return min(nums) if lower_is_better else max(nums)
