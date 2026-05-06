"""
etl/extract.py
--------------
Reads ODS source files for a given year (or all years) and writes
tidy CSV files into assets/data/.

Usage:
    python -m etl.extract 2022
    python -m etl.extract 2025
    python -m etl.extract all

The script is year-agnostic: source file paths and sheet names come
entirely from schema/schema_YYYY.yaml via schema_loader.  Adding a new
survey year only requires a new schema file — no code changes here.
"""

import sys
import os
import pandas as pd
import numpy as np

# ── path setup ──────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from schema.schema_loader import (
    get_source_file, get_source_table, get_available_years,
    get_codelist_for_year, get_label
)

OUT_DIR = os.path.join(ROOT, "assets", "data")

OFFICIAL_YEARS = [2022, 2025]   # years that have a real ODS source file

# ── ODS reader ───────────────────────────────────────────────────────────────

def read_sheet(year, logical_name):
    """Return a raw DataFrame for a logical table name in a given year."""
    src = os.path.join(ROOT, get_source_file(year))
    sheet = get_source_table(logical_name, year)
    return pd.read_excel(src, sheet_name=sheet, engine="odf", header=None)


# ── shared helpers ────────────────────────────────────────────────────────────

def _clean_val(v):
    """Convert a cell value: strip whitespace, return None for NaN/dash."""
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    s = str(v).strip()
    if s in ("-", "", "nan"):
        return None
    # strip parentheses from bracketed values (small sample size warning)
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1].strip()
    try:
        return float(s)
    except ValueError:
        return s


def _label_to_id(label, codelist_items):
    """Reverse-lookup: return the stable ID for a given label string."""
    for id_, lbl in codelist_items:
        if lbl and lbl.strip() == str(label).strip():
            return id_
    return None


# Normalise raw ODS category strings to stable IDs for each demographic.
# Keys must match the demographic names used in extract_time_distribution and
# extract_volunteering_trends.  Only the ODS variants that actually appear in
# Tabellen 10.x / 12.x and Tabelle 1.1 need to be listed here.
_CAT_MAP = {
    "gender": {
        "Männer": "male", "Frauen": "female",
        "Insgesamt": "all", "all": "all",
    },
    "age_group": {
        "jünger als 30 Jahre": "under_30",
        "30\u201339 Jahre": "age_30_39",   # en-dash
        "30-39 Jahre": "age_30_39",
        "40\u201349 Jahre": "age_40_49",
        "40-49 Jahre": "age_40_49",
        "50\u201359 Jahre": "age_50_59",
        "50-59 Jahre": "age_50_59",
        "60\u201369 Jahre": "age_60_69",
        "60-69 Jahre": "age_60_69",
        "70\u201379 Jahre": "age_70_79",
        "70-79 Jahre": "age_70_79",
        "80 Jahre oder älter": "age_80_plus",
    },
    "education": {
        "(max.) Pflichtschule": "compulsory_max",
        "(Max.) Pflichtschule": "compulsory_max",
        "Lehre, Berufsbildende mittlere Schule (BMS)": "apprenticeship_voc",
        "Lehre, BMS": "apprenticeship_voc",
        "Matura": "matura",
        "Universität": "university",
        "Universit\u00e4t": "university",
    },
    "migration_background": {
        "Migrationshintergrund 1. Generation": "first_generation",
        "Migrationshintergrund1": "first_generation",
        "Migrationshintergrund 1": "first_generation",
        "Migrationshintergrund 2. Generation": "second_generation",
        "Migrationshintergrund2": "second_generation",
        "Migrationshintergrund 2)": "second_generation",
        "Kein Migrationshintergrund": "no_migration",
    },
    # alias used in time_distribution extraction
    "migration": {
        "Migrationshintergrund 1. Generation": "first_generation",
        "Migrationshintergrund1": "first_generation",
        "Migrationshintergrund 1": "first_generation",
        "Migrationshintergrund 2. Generation": "second_generation",
        "Migrationshintergrund2": "second_generation",
        "Migrationshintergrund 2)": "second_generation",
        "Kein Migrationshintergrund": "no_migration",
    },
    "employment": {
        "Erwerbstätige Personen": "employed",
        "Erwerbst\u00e4tige Personen": "employed",
        "Personen in Pension": "retired",
        "Alle übrigen Personen": "other_employment",
        "Alle \u00fcbrigen Personen": "other_employment",
    },
    "municipality_size": {
        "Gemeinden <=2\u202f500 Einw.": "up_to_2500",
        "Gemeinden <=2 500 Einw.": "up_to_2500",
        "Gemeinden <=10\u202f000 Einw.": "up_to_10000",
        "Gemeinden <=10 000 Einw.": "up_to_10000",
        "Gemeinden <=100\u202f000 Einw.": "up_to_100000",
        "Gemeinden <=100 000 Einw.": "up_to_100000",
        "Gemeinden >100\u202f000 Einw.": "over_100000",
        "Gemeinden >100 000 Einw.": "over_100000",
    },
    # alias used in time_distribution extraction
    "municipality": {
        "Gemeinden <=2\u202f500 Einw.": "up_to_2500",
        "Gemeinden <=2 500 Einw.": "up_to_2500",
        "Gemeinden <=10\u202f000 Einw.": "up_to_10000",
        "Gemeinden <=10 000 Einw.": "up_to_10000",
        "Gemeinden <=100\u202f000 Einw.": "up_to_100000",
        "Gemeinden <=100 000 Einw.": "up_to_100000",
        "Gemeinden >100\u202f000 Einw.": "over_100000",
        "Gemeinden >100 000 Einw.": "over_100000",
    },
    "region": {
        "Österreich gesamt": "all",
        "\u00d6sterreich gesamt": "all",
        "Österreich": "all",
        "Burgenland": "burgenland",
        "Kärnten": "kaernten",
        "K\u00e4rnten": "kaernten",
        "Niederösterreich": "niederoesterreich",
        "Nieder\u00f6sterreich": "niederoesterreich",
        "Oberösterreich": "oberoesterreich",
        "Ober\u00f6sterreich": "oberoesterreich",
        "Salzburg": "salzburg",
        "Steiermark": "steiermark",
        "Tirol": "tirol",
        "Vorarlberg": "vorarlberg",
        "Wien": "wien",
    },
    "freq_of_volunteering": {
        "mind. 1x pro Woche": "weekly",
        "mind. 1x pro Monat": "monthly",
        "mind. 1x pro Jahr": "yearly",
        "nie": "never",
    },
    "total": {"all": "all", "Insgesamt": "all"},
}


def _normalize_category(label, demographic):
    """Return stable category ID for a raw ODS label under a given demographic.
    Falls back to the label itself if no mapping exists (avoids silent data loss).
    """
    mapping = _CAT_MAP.get(demographic, {})
    raw = str(label).strip()
    # Try exact match first, then case-insensitive
    if raw in mapping:
        return mapping[raw]
    raw_lower = raw.lower()
    for k, v in mapping.items():
        if k.lower() == raw_lower:
            return v
    return raw   # fallback — unknown category kept as-is


# ── parser: areas tables (Tabelle4_1 / Tabelle7_1 / Tabelle8_1) ──────────────

def _parse_areas_table(df, year, codelist_name):
    """
    Parse a formal or informal areas table.
    Returns list of dicts: {year, area_id, demographic, category, count_1000, percentage}

    Table structure (rows):
      0-1  : title / blank
      2-4  : multi-level header
      5+   : data — col0=demographic group, col1=area label, col2=count, col3=%
    """
    cl = get_codelist_for_year(codelist_name, year)
    rows = []
    current_group = "all"
    current_group_label = "Insgesamt"

    for i, row in df.iterrows():
        if i < 5:
            continue
        c0 = _clean_val(row.iloc[0])
        c1 = _clean_val(row.iloc[1])
        c2 = _clean_val(row.iloc[2])
        c3 = _clean_val(row.iloc[3])

        # Source footnote row — stop
        if isinstance(c0, str) and c0.startswith("Q:"):
            break

        # Demographic group header (non-null in col0, null in col1)
        if c0 is not None and c1 is None:
            current_group_label = str(c0)
            # Map label to demographic + category
            if str(c0) in ("Alle Personen", "Insgesamt"):
                current_group = ("all", "all")
            elif str(c0) in ("Männer",):
                current_group = ("gender", "male")
            elif str(c0) in ("Frauen",):
                current_group = ("gender", "female")
            else:
                current_group = ("other", str(c0))
            continue

        # Data row: col0 is None, col1 is area label
        if c0 is None and c1 is not None and isinstance(c2, float):
            area_id = _label_to_id(c1, cl)
            if area_id is None:
                continue   # area not in codelist for this year
            demographic, category = current_group if isinstance(current_group, tuple) else ("all", "all")
            rows.append({
                "year": year,
                "area_id": area_id,
                "demographic": demographic,
                "category": category,
                "count_1000": c2,
                "percentage": c3,
            })

    return rows


def extract_formal_areas(year):
    rows = _parse_areas_table(read_sheet(year, "formal_areas_overall"), year, "formal_areas")
    return rows


def extract_informal_areas(year):
    rows = _parse_areas_table(read_sheet(year, "informal_areas_overall"), year, "informal_areas")
    return rows


# ── parser: motivations / barriers ───────────────────────────────────────────

def _parse_motiv_table(df, year, item_type):
    """
    Parse motivations or barriers table.
    Returns list of dicts: {year, type, item_id, gender, population_1000,
                             fully_agree, rather_agree, rather_disagree, not_at_all}

    Table structure:
      0-4  : headers (skip)
      5+   : col0=gender group, col1=item text, col2=population, col3-6=percentages
    """
    codelist_name = "motivations" if item_type == "motivation" else "barriers"
    cl = get_codelist_for_year(codelist_name, year)
    rows = []
    current_gender = "all"

    for i, row in df.iterrows():
        if i < 5:
            continue
        c0 = _clean_val(row.iloc[0])
        c1 = _clean_val(row.iloc[1])
        c2 = _clean_val(row.iloc[2])
        c3 = _clean_val(row.iloc[3])
        c4 = _clean_val(row.iloc[4])
        c5 = _clean_val(row.iloc[5])
        c6 = _clean_val(row.iloc[6]) if len(row) > 6 else None

        if isinstance(c0, str) and c0.startswith("Q:"):
            break

        # Gender header row
        if c0 is not None and c1 is None:
            label = str(c0)
            if label in ("Alle Personen",):
                current_gender = "all"
            elif label in ("Männer",):
                current_gender = "men"
            elif label in ("Frauen",):
                current_gender = "women"
            continue

        # Data row
        if c0 is None and c1 is not None and isinstance(c2, float):
            item_id = _label_to_id(c1, cl)
            if item_id is None:
                continue
            rows.append({
                "year": year,
                "type": item_type,
                "item_id": item_id,
                "gender": current_gender,
                "population_1000": c2,
                "fully_agree": c3,
                "rather_agree": c4,
                "rather_disagree": c5,
                "not_at_all": c6,
            })

    return rows


def extract_motivations(year):
    return _parse_motiv_table(read_sheet(year, "motivations"), year, "motivation")

def extract_barriers(year):
    return _parse_motiv_table(read_sheet(year, "barriers"), year, "barrier")


# ── parser: geo regions ───────────────────────────────────────────────────────

def extract_geo_regions(year):
    """
    Extract regional (Bundesland) statistics.
    Combines perc_any (Tabelle1_1), perc_formal (Tabelle2_1),
    perc_informal (Tabelle2_2) and time data (time_by_region).

    Returns list of dicts per region.
    """
    # Map Austrian Bundesland names to region IDs
    region_id_map = {
        "Burgenland": "Burgenland",
        "Kärnten": "Kärnten",
        "Niederösterreich": "Niederösterreich",
        "Oberösterreich": "Oberösterreich",
        "Salzburg": "Salzburg",
        "Steiermark": "Steiermark",
        "Tirol": "Tirol",
        "Vorarlberg": "Vorarlberg",
        "Wien": "Wien",
    }

    def _extract_regional_perc(df, col_count, col_perc):
        """Return {region: (count_1000, perc)} from a demographics table Bundesland section."""
        result = {}
        in_bundesland = False
        for i, row in df.iterrows():
            c0 = _clean_val(row.iloc[0])
            c1 = _clean_val(row.iloc[1])
            if isinstance(c0, str) and "Bundesland" in str(c0):
                in_bundesland = True
                continue
            if in_bundesland:
                if c0 is not None and c1 is None:
                    # Next section header — stop
                    if c0 not in region_id_map:
                        break
                if c0 is None and c1 is not None and str(c1).strip() in region_id_map:
                    count = _clean_val(row.iloc[col_count])
                    perc  = _clean_val(row.iloc[col_perc])
                    result[str(c1).strip()] = (count, perc)
        return result

    df_any    = read_sheet(year, "volunteering_general")
    df_formal = read_sheet(year, "formal_volunteering")
    df_inf    = read_sheet(year, "informal_volunteering")

    any_data    = _extract_regional_perc(df_any,    col_count=3, col_perc=4)
    formal_data = _extract_regional_perc(df_formal, col_count=3, col_perc=4)
    inf_data    = _extract_regional_perc(df_inf,    col_count=3, col_perc=4)

    # Time data from time_by_region table
    df_time = read_sheet(year, "time_by_region")

    def _extract_time_by_region(df_t):
        """Return {region: {vol_type: {avg, p25, p50, p75}}}"""
        result = {}
        current_region = None
        for i, row in df_t.iterrows():
            if i < 4:
                continue
            c0 = _clean_val(row.iloc[0])
            c1 = _clean_val(row.iloc[1])
            if isinstance(c0, str) and c0.startswith("Q:"):
                break
            if c0 is not None and c1 is None:
                if str(c0).strip() in region_id_map or str(c0).strip() in ("Österreich gesamt", "Österreich"):
                    current_region = str(c0).strip()
                    result[current_region] = {}
                continue
            if c0 is None and c1 is not None and current_region:
                label = str(c1).strip()
                avg  = _clean_val(row.iloc[3])
                p25  = _clean_val(row.iloc[4])
                p50  = _clean_val(row.iloc[5])
                p75  = _clean_val(row.iloc[6])
                if "insgesamt" in label.lower() or "tätige insgesamt" in label.lower():
                    result[current_region]["any"] = {"avg": avg, "p25": p25, "p50": p50, "p75": p75}
                elif "formell" in label.lower():
                    result[current_region]["formal"] = {"avg": avg, "p25": p25, "p50": p50, "p75": p75}
                elif "informell" in label.lower():
                    result[current_region]["informal"] = {"avg": avg, "p25": p25, "p50": p50, "p75": p75}
        return result

    time_data = _extract_time_by_region(df_time)

    rows = []
    for region_name in region_id_map:
        any_count,    any_perc    = any_data.get(region_name,    (None, None))
        formal_count, formal_perc = formal_data.get(region_name, (None, None))
        inf_count,    inf_perc    = inf_data.get(region_name,    (None, None))
        t = time_data.get(region_name, {})
        rows.append({
            "year": year,
            "region": region_name,
            "total_pop":                any_count,
            "perc_volunteers_from_pop": any_perc,
            "perc_formal_from_pop":     formal_perc,
            "perc_informal_from_pop":   inf_perc,
            "avg_hours_vlntrs":   t.get("any",     {}).get("avg"),
            "avg_hours_formal":   t.get("formal",  {}).get("avg"),
            "avg_hours_informal": t.get("informal",{}).get("avg"),
            "median_hours_vlntrs":   t.get("any",     {}).get("p50"),
            "median_hours_formal":   t.get("formal",  {}).get("p50"),
            "median_hours_informal": t.get("informal",{}).get("p50"),
            "25_hrs_vlntrs":  t.get("any",     {}).get("p25"),
            "75_hrs_vlntrs":  t.get("any",     {}).get("p75"),
            "25_hrs_formal":  t.get("formal",  {}).get("p25"),
            "75_hrs_formal":  t.get("formal",  {}).get("p75"),
            "25_hrs_informal":t.get("informal",{}).get("p25"),
            "75_hrs_informal":t.get("informal",{}).get("p75"),
        })
    return rows


# ── parser: time distribution (error bar chart) ───────────────────────────────

def extract_time_distribution(year):
    """
    Extract time-per-week distributions across all demographic breakdowns.
    Returns list of dicts: {year, demographic, category, vol_type,
                             count_1000, avg_hours, p25, p50, p75}
    """
    demo_tables = {
        "gender":       "time_by_gender",
        "education":    "time_by_edu",
        "migration":    "time_by_migration",
        "employment":   "time_by_employment",
        "municipality": "time_by_municipality",
        "region":       "time_by_region",
    }

    def _parse_time_table(df, demographic):
        rows = []
        current_category = "all"
        for i, row in df.iterrows():
            if i < 4:
                continue
            c0 = _clean_val(row.iloc[0])
            c1 = _clean_val(row.iloc[1])
            if isinstance(c0, str) and c0.startswith("Q:"):
                break

            # Category header (region/gender/etc.) — normalise to stable ID
            if c0 is not None:
                current_category = _normalize_category(str(c0).strip(), demographic)
                continue

            # Volunteering type row
            if c0 is None and c1 is not None:
                label = str(c1).strip()
                # col2 may be sub-area label in some tables; find count column
                try:
                    count = _clean_val(row.iloc[3])
                    avg   = _clean_val(row.iloc[4])
                    p25   = _clean_val(row.iloc[5])
                    p50   = _clean_val(row.iloc[6])
                    p75   = _clean_val(row.iloc[7]) if len(row) > 7 else None
                except IndexError:
                    continue

                if not isinstance(count, float):
                    continue

                if "insgesamt" in label.lower():
                    vol_type = "Total"
                elif "formell" in label.lower() and "informell" not in label.lower():
                    vol_type = "Formal"
                elif "informell" in label.lower():
                    vol_type = "Informal"
                else:
                    continue

                rows.append({
                    "year": year,
                    "demographic": demographic,
                    "category": current_category,
                    "vol_type": vol_type,
                    "count_1000": count,
                    "avg_hours": avg,
                    "p25": p25,
                    "p50": p50,
                    "p75": p75,
                })
        return rows

    all_rows = []
    for demographic, table_key in demo_tables.items():
        df = read_sheet(year, table_key)
        all_rows.extend(_parse_time_table(df, demographic))
    return all_rows


# ── parser: volunteering trends (time-series) ─────────────────────────────────

def extract_volunteering_trends(year):
    """
    Extract cross-demographic volunteering rates for the time-series charts.
    Reads the general table (Tabelle1_1) and the formal/informal tables.
    Returns list of dicts: {year, demographic, category, vol_type,
                             population_1000, count_1000, percentage}
    """
    vol_type_tables = {
        "any":    "volunteering_general",
        "formal": "formal_volunteering",
        "informal": "informal_volunteering",
    }

    # Which section headers map to which demographic dimension
    SECTION_MAP = {
        "Altersgruppen": "age_group",
        "(Aus-)bildungsniveau": "education",
        "Bildungsniveau": "education",
        "Staatsbürgerschaft": "citizenship",
        "Geburtsland": "birth_country",
        "Migrationshintergrund": "migration_background",
        "Migrationshintergrund 1": "migration_background",
        "Teilnahme am Erwerbsleben": "employment",
        "Unselbständig Erwerbstätige": "employment_type",
        "Gemeindegrößenklassen": "municipality_size",
        "Bundesland": "region",
        "Haushaltsgröße": "household_size",
    }

    def _parse_general_table(df, vol_type):
        rows = []
        current_demographic = "gender"
        current_category = None

        for i, row in df.iterrows():
            if i < 4:
                continue
            c0 = _clean_val(row.iloc[0])
            c1 = _clean_val(row.iloc[1])
            c2 = _clean_val(row.iloc[2])
            c3 = _clean_val(row.iloc[3])   # population
            c4 = _clean_val(row.iloc[4])   # count yes
            c5 = _clean_val(row.iloc[5])   # % yes

            if isinstance(c0, str) and c0.startswith("Q:"):
                break

            # Main demographic group row (col0 set, col1 null, col2 null)
            if c0 is not None and c1 is None and c2 is None:
                label = str(c0).strip()
                if label in SECTION_MAP:
                    current_demographic = SECTION_MAP[label]
                    current_category = None
                elif label in ("Männer",):
                    current_demographic = "gender"
                    current_category = "male"
                    if isinstance(c3, float):
                        rows.append({"year": year, "demographic": "gender", "category": "male",
                                     "vol_type": vol_type, "population_1000": c3,
                                     "count_1000": c4, "percentage": c5})
                elif label in ("Frauen",):
                    current_demographic = "gender"
                    current_category = "female"
                    if isinstance(c3, float):
                        rows.append({"year": year, "demographic": "gender", "category": "female",
                                     "vol_type": vol_type, "population_1000": c3,
                                     "count_1000": c4, "percentage": c5})
                elif label in ("Insgesamt",):
                    current_demographic = "total"
                    current_category = "all"
                    if isinstance(c3, float):
                        rows.append({"year": year, "demographic": "total", "category": "all",
                                     "vol_type": vol_type, "population_1000": c3,
                                     "count_1000": c4, "percentage": c5})
                continue

            # Sub-category row (col0 null, col1 set, col2 null)
            # Skip sub-rows when inside a gender/total section — those are age-within-gender
            # crossbreaks; the pure age breakdown is captured in the age section below.
            if c0 is None and c1 is not None and c2 is None and isinstance(c3, float):
                if current_demographic not in ("gender", "total"):
                    cat_id = _normalize_category(str(c1).strip(), current_demographic)
                    rows.append({"year": year, "demographic": current_demographic,
                                 "category": cat_id, "vol_type": vol_type,
                                 "population_1000": c3, "count_1000": c4, "percentage": c5})
                continue

        return rows

    all_rows = []
    for vol_type, table_key in vol_type_tables.items():
        df = read_sheet(year, table_key)
        all_rows.extend(_parse_general_table(df, vol_type))
    return all_rows


# ── parser: gender comparison ────────────────────────────────────────────────

def extract_gender_comparison(year):
    """
    Extract data for the gender-comparison chart.
    Reads six sub-tables and returns list of dicts:
      {year, vol_type, dimension, category, men_count, men_perc, women_count, women_perc}

    Dimensions produced:
      Formal_Areas        — from formal_areas_by_gender  (Tabelle4_3 / 4_3)
      Informal_Areas      — from informal_areas_by_gender (Tabelle8_2 / 7_2)
      Formal_NumberOfOrgs — from num_orgs                 (Tabelle5_1)
      Formal_TaskTypes    — from task_types               (Tabelle6_1)   [2022 only]
      Formal_Time/week    — from time_by_gender           (Tabelle12_2 / 10_2)
      Informal_Time/week  — from time_by_gender           (same table, informal section)
    """
    from schema.schema_loader import get_available_filters, get_codelist_for_year

    rows = []

    def _parse_gender_areas(df, codelist_name, dimension, vol_type):
        """
        Parse a by-gender areas table (Tabelle4_3 / Tabelle7_2 / Tabelle8_2).
        Real column layout: c0=None, c1=area_label, c2=None(total), c3=men, c4=men%, c5=women, c6=women%
        The c2 column is always None for area data rows (total is c3... actually col indices:
          col0  col1         col2    col3      col4    col5       col6
          None  area_label   None    total     men     men%       women    women%  ← col7
        Wait — from ODS: [None, label, None, total, men, men%, women, women%]
        → men_count=col[4], men_perc=col[5], women_count=col[6], women_perc=col[7]
        """
        cl = get_codelist_for_year(codelist_name, year)
        inner_rows = []
        for i, row in df.iterrows():
            if i < 5:
                continue
            c0 = _clean_val(row.iloc[0])
            c1 = _clean_val(row.iloc[1])
            if isinstance(c0, str) and c0.startswith("Q:"):
                break
            if c0 is None and c1 is not None:
                area_id = _label_to_id(c1, cl)
                if area_id is None:
                    continue
                try:
                    # Formal table has a null spacer at col[2]: [None, label, None, total, men, men%, women, women%]
                    # Informal table does not:                  [None, label, total, men, men%, women, women%]
                    c2 = _clean_val(row.iloc[2])
                    offset = 4 if c2 is None else 3
                    men_count   = _clean_val(row.iloc[offset])
                    men_perc    = _clean_val(row.iloc[offset + 1])
                    women_count = _clean_val(row.iloc[offset + 2])
                    women_perc  = _clean_val(row.iloc[offset + 3])
                except IndexError:
                    continue
                if not isinstance(men_count, float):
                    continue
                inner_rows.append({
                    "year": year, "vol_type": vol_type, "dimension": dimension,
                    "category": area_id,
                    "men_count": men_count, "men_perc": men_perc,
                    "women_count": women_count, "women_perc": women_perc,
                })
        return inner_rows

    def _parse_gender_simple(df, dimension, vol_type, skip_rows=4):
        """
        Parse a by-gender table where categories are in col1 (num_orgs, task_types).
        Real column layout: c0=None, c1=label, c2=total, c3=men, c4=men%, c5=women, c6=women%
        Skip the "Insgesamt" total row (c0 not None).
        """
        inner_rows = []
        for i, row in df.iterrows():
            if i < skip_rows:
                continue
            c0 = _clean_val(row.iloc[0])
            c1 = _clean_val(row.iloc[1])
            if isinstance(c0, str) and c0.startswith("Q:"):
                break
            if c0 is not None:   # total/header row — skip
                continue
            if c1 is None:
                continue
            try:
                men_count   = _clean_val(row.iloc[3])
                men_perc    = _clean_val(row.iloc[4])
                women_count = _clean_val(row.iloc[5])
                women_perc  = _clean_val(row.iloc[6])
            except IndexError:
                continue
            if not isinstance(men_count, float):
                continue
            inner_rows.append({
                "year": year, "vol_type": vol_type, "dimension": dimension,
                "category": str(c1).strip(),
                "men_count": men_count, "men_perc": men_perc,
                "women_count": women_count, "women_perc": women_perc,
            })
        return inner_rows

    def _parse_time_gender(df):
        """
        Parse time_by_gender table for Formal_Time/week and Informal_Time/week.

        Table layout (Tabelle12_2 / Tabelle10_2):
          c0=gender_header ("Männer"/"Frauen"), c1=None  → gender section start
          c0=None, c1=vol_type label, c2=None, c3=count, c4=avg_hours, c5-7=percentiles
          c0=None, c1=None, c2=area_label  → sub-area row (skip)

        The ODS does not have a hours-range × gender cross-tab (that would require
        a different survey table). Instead we store: for each gender × vol_type,
        the count of volunteers and their avg hours/week.  These are written as
        two extra columns (men_avg_hours, women_avg_hours) rather than men_perc/
        women_perc, which remain null for Time/week rows.
        """
        inner_rows = []
        # We collect data per gender first, then join into single rows
        data = {}   # (vol_type) → {"male": (count, avg), "female": (count, avg)}
        current_gender = None

        for i, row in df.iterrows():
            if i < 4:
                continue
            c0 = _clean_val(row.iloc[0])
            c1 = _clean_val(row.iloc[1])
            c2 = _clean_val(row.iloc[2])
            if isinstance(c0, str) and c0.startswith("Q:"):
                break

            # Gender section header
            if c0 is not None and c1 is None:
                label = str(c0).strip()
                if label == "Männer":
                    current_gender = "male"
                elif label == "Frauen":
                    current_gender = "female"
                continue

            # Vol-type summary row: c0=None, c1=label, c2=None, c3=count, c4=avg
            if c0 is None and c1 is not None and c2 is None and current_gender:
                label = str(c1).strip()
                try:
                    count = _clean_val(row.iloc[3])
                    avg   = _clean_val(row.iloc[4])
                except IndexError:
                    continue
                if not isinstance(count, float):
                    continue
                if "insgesamt" in label.lower():
                    vt = "Total"
                elif "formell" in label.lower() and "informell" not in label.lower():
                    vt = "Formal"
                elif "informell" in label.lower():
                    vt = "Informal"
                else:
                    continue
                if vt not in data:
                    data[vt] = {}
                data[vt][current_gender] = (count, avg)

        # Emit one row per vol_type with both gender values side by side
        for vt, genders in data.items():
            male   = genders.get("male",   (None, None))
            female = genders.get("female", (None, None))
            dim = "Formal_Time/week" if vt == "Formal" else (
                  "Informal_Time/week" if vt == "Informal" else "Total_Time/week")
            inner_rows.append({
                "year": year,
                "vol_type": vt,
                "dimension": dim,
                "category": "avg_hours_summary",
                "men_count":      male[0],
                "men_avg_hours":  male[1],
                "women_count":    female[0],
                "women_avg_hours": female[1],
                "men_perc":       None,
                "women_perc":     None,
            })
        return inner_rows

    # Formal areas by gender
    rows += _parse_gender_areas(
        read_sheet(year, "formal_areas_by_gender"), "formal_areas", "Formal_Areas", "Formal"
    )

    # Informal areas by gender
    rows += _parse_gender_areas(
        read_sheet(year, "informal_areas_by_gender"), "informal_areas", "Informal_Areas", "Informal"
    )

    # Number of organisations (Formal_NumberOfOrgs)
    rows += _parse_gender_simple(
        read_sheet(year, "num_orgs"), "Formal_NumberOfOrgs", "Formal"
    )

    # Task types — only if available for this year (absent in 2025)
    avail_filters = get_available_filters("gender_comparison", year)
    formal_dims = avail_filters.get("dimensions", {}).get("Formal", [])
    if "Formal_TaskTypes" in formal_dims:
        rows += _parse_gender_simple(
            read_sheet(year, "task_types"), "Formal_TaskTypes", "Formal"
        )

    # Time/week by gender
    rows += _parse_time_gender(read_sheet(year, "time_by_gender"))

    return rows


# ── write helpers ─────────────────────────────────────────────────────────────

def _append_or_create(filename, new_rows):
    """Append rows to an existing CSV (or create it if new)."""
    path = os.path.join(OUT_DIR, filename)
    new_df = pd.DataFrame(new_rows)
    if os.path.exists(path):
        existing = pd.read_csv(path)
        # Remove any existing rows for this year to avoid duplicates
        if "year" in existing.columns and not new_df.empty:
            year = new_df["year"].iloc[0]
            existing = existing[existing["year"] != year]
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined.to_csv(path, index=False)
    else:
        new_df.to_csv(path, index=False)
    print(f"  -> {filename}: {len(new_rows)} rows written")


# ── main ──────────────────────────────────────────────────────────────────────

def extract_year(year):
    print(f"\n=== Extracting {year} ===")

    print("  geo_regions...")
    _append_or_create("geo_regions.csv", extract_geo_regions(year))

    print("  formal_areas...")
    _append_or_create("formal_areas.csv", extract_formal_areas(year))

    print("  informal_areas...")
    _append_or_create("informal_areas.csv", extract_informal_areas(year))

    print("  motivations...")
    _append_or_create("motivations.csv", extract_motivations(year))

    print("  barriers...")
    _append_or_create("barriers.csv", extract_barriers(year))

    print("  time_distribution...")
    _append_or_create("time_distribution.csv", extract_time_distribution(year))

    print("  volunteering_trends...")
    _append_or_create("volunteering_trends.csv", extract_volunteering_trends(year))

    print("  gender_comparison...")
    _append_or_create("gender_comparison.csv", extract_gender_comparison(year))

    print(f"  Done — {year}.")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(OUT_DIR, exist_ok=True)

    if arg == "all":
        for y in OFFICIAL_YEARS:
            extract_year(y)
    else:
        extract_year(int(arg))
