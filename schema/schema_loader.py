"""
schema_loader.py
----------------
Single interface between app.py and the YAML schema layer.
app.py calls these functions — it never reads YAML directly or
references year-specific field names.
"""

import os
import yaml

_SCHEMA_DIR = os.path.dirname(__file__)
_CODELISTS_DIR = os.path.join(_SCHEMA_DIR, "codelists")

# ── internal cache so files are only parsed once ──────────────────────────────

_cache = {}

def _load(path):
    if path not in _cache:
        with open(path, encoding="utf-8") as f:
            _cache[path] = yaml.safe_load(f)
    return _cache[path]

def _codelist(name):
    return _load(os.path.join(_CODELISTS_DIR, f"{name}.yaml"))

def _year_schema(year):
    return _load(os.path.join(_SCHEMA_DIR, f"schema_{year}.yaml"))

def _manifest():
    return _load(os.path.join(_SCHEMA_DIR, "manifest.yaml"))


# ── public API ─────────────────────────────────────────────────────────────────

def get_available_years():
    """Return list of all survey years in ascending order."""
    return sorted(w["year"] for w in _manifest()["survey_waves"])


def get_data_years():
    """Return years that have actual data files (official or synthetic)."""
    return sorted(w["year"] for w in _manifest()["survey_waves"])


def is_available(field_id, domain, year):
    """
    Return True if a field (area / motivation item / demographic) is
    published for the given year.  Returns False when the codelist label
    for that year is null.
    """
    cl = _codelist(domain)
    items = cl.get(domain, [])
    for item in items:
        if item["id"] == field_id:
            return item["labels"].get(year) is not None
    # Field not found in codelist at all → not available
    return False


def get_label(field_id, domain, year, fallback=True):
    """
    Return the display label for a field in a given year.
    If the label is null (field removed/not yet introduced) and fallback=True,
    returns the most recent non-null label with a '(not available)' suffix.
    Returns None if no label exists at all.
    """
    cl = _codelist(domain)
    items = cl.get(domain, [])
    for item in items:
        if item["id"] == field_id:
            label = item["labels"].get(year)
            if label is not None:
                return label
            if fallback:
                all_labels = [v for v in item["labels"].values() if v is not None]
                if all_labels:
                    return f"{all_labels[-1]} (not available in {year})"
            return None
    return None


def get_codelist_for_year(domain, year):
    """
    Return list of (id, label) tuples for all items available in a given year.
    Items with null labels are excluded.
    """
    cl = _codelist(domain)
    items = cl.get(domain, [])
    return [
        (item["id"], item["labels"][year])
        for item in items
        if item["labels"].get(year) is not None
    ]


def get_available_filters(chart, year):
    """
    Return the available_filters dict for a chart in a given year.
    e.g. get_available_filters("activity_bar", 2025)
    → {"vol_types": [...], "demographics": [...], "unavailable_demographics": [...]}
    """
    return _year_schema(year).get("available_filters", {}).get(chart, {})


def get_available_demographics(chart, year):
    """
    Return list of available demographic IDs for a chart in a given year.
    Excludes any that are listed under unavailable_demographics.
    """
    filters = get_available_filters(chart, year)
    return filters.get("demographics", [])


def get_unavailable_demographics(chart, year):
    """
    Return list of dicts describing demographics that are absent for this
    chart/year, including the reason.  Used to show tooltips in the UI.
    """
    filters = get_available_filters(chart, year)
    return filters.get("unavailable_demographics", [])


def get_data_file(dataset, year):
    """
    Return the path to the tidy CSV for a given dataset and year.
    All years currently share the same files (year is a column in each CSV).
    """
    schema = _year_schema(year)
    return schema.get("data_files", {}).get(dataset)


def get_source_file(year):
    """Return the path to the original ODS source file for a given year."""
    return _year_schema(year).get("source_file")


def get_source_table(logical_name, year):
    """Return the ODS sheet name for a logical table name in a given year."""
    return _year_schema(year).get("source_tables", {}).get(logical_name)


def get_changes(year):
    """
    Return list of change dicts for a given year (vs the previous wave).
    Used to surface change notices in the UI.
    """
    for wave in _manifest()["survey_waves"]:
        if wave["year"] == year:
            return wave.get("changes_from_previous", [])
    return []


def get_dimension_categories(dimension_id, year):
    """
    Return list of (id, label) for all categories of a demographic
    dimension available in a given year.
    """
    cl = _codelist("demographics")
    for dim in cl.get("demographics", {}).get("dimensions", []):
        if dim["id"] == dimension_id:
            available_in = dim.get("available_in")
            available_from = dim.get("available_from", 0)
            if available_in is not None and year not in available_in:
                return []
            if year < available_from:
                return []
            return [
                (cat["id"], cat["labels"].get(year, cat["labels"].get(2022, cat["id"])))
                for cat in dim.get("categories", [])
            ]
    return []


def is_dimension_available(dimension_id, year):
    """Return True if a demographic dimension is available for a given year."""
    cl = _codelist("demographics")
    for dim in cl.get("demographics", {}).get("dimensions", []):
        if dim["id"] == dimension_id:
            available_in = dim.get("available_in")
            available_from = dim.get("available_from", 0)
            if available_in is not None:
                return year in available_in
            return year >= available_from
    return False
