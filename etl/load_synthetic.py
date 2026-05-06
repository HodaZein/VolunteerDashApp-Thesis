"""
etl/load_synthetic.py
---------------------
Converts existing fake JSON data files for survey years 2006, 2012, 2016 into
tidy CSV rows that match the schema produced by etl/extract.py for official years.

Why this is needed:
  - The Austrian volunteering surveys for 2006/2012/2016 have no machine-readable
    source files; the app previously used hand-crafted JSON approximations.
  - For time-series continuity these years must appear in the same tidy CSVs as
    the real 2022/2025 data, with identical column names and stable category IDs.

Inconsistencies fixed vs. the original fake JSON files:
  1. All category values are mapped to stable IDs (matching the demographics
     codelist) instead of English free-text labels.
  2. Years 1988-2003 in volunteering_time_series_fake.json are excluded — those
     pre-date any documented survey wave in manifest.yaml.
  3. "Care for refugees" / "refugee_support" is dropped for 2006-2016 because the
     codelist marks that area as null for those years (it only appeared in 2022).
  4. The "gardening" (lowercase) duplicate entry in informal fake data is merged
     into the canonical "garden_support" stable ID.
  5. The "migration" demographic key is normalised to "migration_background".
  6. The "municipality size classes" demographic key is normalised to
     "municipality_size".
  7. The "houshold size" (typo) key and "multi-person/single-person households"
     variants are unified under "household_size".

Usage:
    python -m etl.load_synthetic
"""

import os
import sys
import json
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

ASSETS = os.path.join(ROOT, "assets")
OUT_DIR = os.path.join(ROOT, "assets", "data")

SYNTHETIC_YEARS = [2006, 2012, 2016]

# ── label → stable ID mappings ────────────────────────────────────────────────

FORMAL_AREA_MAP = {
    "Disaster relief and rescue services": "disaster_rescue",
    "Arts, culture, entertainment":        "arts_culture",
    "Environment, nature and animal protection": "environment_nature",
    "Religion and Church":                 "religion_church",
    "Social and Health":                   "social_health",
    "Political work and advocacy":         "politics_advocacy",
    "Civic activities and community":      "civic_community",
    "Education":                           "education",
    "Sports and exercise":                 "sports",
    "Refugee aid":                         "refugee_aid",
}

INFORMAL_AREA_MAP = {
    "Various housework":                   "household_tasks",
    "Repairs, craft work":                 "repairs_crafts",
    "Gardening":                           "garden_support",
    "gardening":                           "garden_support",   # original typo
    "Visits to persons requiring care":    "visit_services",
    "Care for people in need of care":     "care_dependent",
    "Travel services":                     "transport_services",
    "Assistance in disasters":             "disaster_aid",
    "Official procedures and correspondence": "admin_paperwork",
    "Tutoring":                            "tutoring",
    "Childcare":                           "childcare",
    "Care for refugees":                   "refugee_support",  # only valid 2022
    "Other activity":                      "other_informal",
}

MOTIVATION_MAP = {
    "I enjoy the work.":                                           "enjoy_work",
    "I want to contribute something useful to the common good.":   "common_good",
    "I would like to help others.":                                "help_others",
    "The activity helps me in my job.":                            "career_benefit",
    "I can contribute my skills and knowledge.":                   "use_skills",
    "I meet people and make friends.":                             "social_connection",
    "I get social recognition.":                                   "social_recognition",
    "It keeps me physically and mentally active.":                 "stay_active",
    "I can share my experience.":                                  "share_experience",
    "I have the opportunity to learn and further my education.":   "learning",
    "I hope to find a job as a result.":                           "find_job",
    "I would also like to receive help myself when I need it.":    "reciprocity",
    "I want to get involved in an important cause.":               "important_cause",
}

BARRIER_MAP = {
    "I have never been asked or requested.":                       "never_asked",
    "I never thought about it.":                                   "never_thought",
    "I am busy with tasks in the family.":                         "family_burden",
    "I feel unable to do so due to illness or disability.":        "illness_disability",
    "I can't afford it financially.":                              "financial",
    "I can't reconcile it with my job.":                           "work_incompatible",
    "I have had bad experiences.":                                 "bad_experience",
    "I have the feeling that I can't make a contribution.":        "no_contribution",
    "I'm not the right age.":                                      "wrong_age",
    "I am not sufficiently informed about the possibilities.":     "lack_information",
    "There is no job in the neighbourhood that is interesting for me.": "nothing_nearby",
}

# Fake errorBars demographic keys → canonical names (matching time_distribution.csv)
ERRORBAR_DEMO_MAP = {
    "Total":              "Total",
    "Gender":             "gender",
    "Age":                "age_group",
    "Education":          "education",
    "MigrationBackground": "migration_background",
    "Employment":         "employment",
    "MunicipalitySize":   "municipality_size",
    "Region":             "region",
    "TaskType":           "task_type",   # synthetic only; absent in 2025
}

# Fake errorBars category values → stable IDs
ERRORBAR_CAT_MAP = {
    # gender
    "Men": "male", "Women": "female", "All": "all",
    # age
    "younger than 30 years": "under_30",
    "30-39 years": "age_30_39", "30–39 years": "age_30_39",
    "40-49 years": "age_40_49", "40–49 years": "age_40_49",
    "50-59 years": "age_50_59", "50–59 years": "age_50_59",
    "60-69 years": "age_60_69", "60–69 years": "age_60_69",
    "70-79 years": "age_70_79", "70–79 years": "age_70_79",
    "80 years or older": "age_80_plus",
    # education
    "(max.) Compulsory education": "compulsory_max",
    "teaching, BMS": "apprenticeship_voc",
    "matura": "matura",
    "university": "university",
    # migration
    "1. Generation": "first_generation",
    "2. Generation": "second_generation",
    "no migration background": "no_migration",
    # employment
    "employed": "employed",
    "unemployed": "other_employment",
    "retired": "retired",
    "in training": "in_training",
    "haushold leader": "homemaker",
    "miscellaneous": "other_employment",
    # municipality
    "<= 2 500 inhabitants": "up_to_2500",
    "<= 10 000 inhabitants": "up_to_10000",
    "<= 100 000 inhabitants": "up_to_100000",
    "> 100 000 inhabitants": "over_100000",
    # region
    "Austria": "all",
    "Burgenland": "burgenland", "Kärnten": "kaernten",
    "Niederösterreich": "niederoesterreich",
    "Oberösterreich": "oberoesterreich",
    "Salzburg": "salzburg", "Steiermark": "steiermark",
    "Tirol": "tirol", "Vorarlberg": "vorarlberg", "Wien": "wien",
    # task type (synthetic years only — 3-category 2022 structure)
    "Leadership": "leadership",
    "Core tasks": "core_tasks",
    "Support tasks": "support_tasks",
}

# Fake time-series demographic / category normalisation
TS_DEMO_MAP = {
    "total": "total",
    "gender": "gender",
    "age": "age_group",
    "education": "education",
    "citizenship": "citizenship",
    "birth_country": "birth_country",
    "migration": "migration_background",
    "employment": "employment",
    "occupation": "employment",         # same data, different key name
    "municipality size classes": "municipality_size",
    "region": "region",
    # "houshold size" (typo), "multi-person households", "single-person households"
    # all collapsed to household_size
    "houshold size": "household_size",
    "household size": "household_size",
    "multi-person households": "household_size",
    "single-person households": "household_size",
}

TS_CAT_MAP = {
    # gender
    "men": "male", "women": "female", "total": "all",
    # age
    "younger than 30 years": "under_30",
    "30–39 years": "age_30_39", "30-39 years": "age_30_39",
    "40–49 years": "age_40_49", "40-49 years": "age_40_49",
    "50–59 years": "age_50_59", "50-59 years": "age_50_59",
    "60–69 years": "age_60_69", "60-69 years": "age_60_69",
    "70–79 years": "age_70_79", "70-79 years": "age_70_79",
    "80 years or older": "age_80_plus",
    # education
    "(max.) Compulsory education": "compulsory_max",
    "teaching, BMS": "apprenticeship_voc",
    "matura": "matura", "university": "university",
    # citizenship / birth country (kept as-is, no stable ID in demographics codelist)
    "Austria": "austria", "not Austria": "not_austria",
    # migration
    "1. Generation": "first_generation",
    "2. Generation": "second_generation",
    "no migration background": "no_migration",
    # employment
    "employed": "employed", "unemployed": "other_employment",
    "retired": "retired", "in training": "in_training",
    "haushold leader": "homemaker", "miscellaneous": "other_employment",
    "higher job": "employed", "highly qualified job": "employed",
    "middle job": "employed", "auxiliary work": "employed",
    # municipality
    "<= 2 500 inhabitants": "up_to_2500",
    "<= 10 000 inhabitants": "up_to_10000",
    "<= 100 000 inhabitants": "up_to_100000",
    "> 100 000 inhabitants": "over_100000",
    # region
    "Burgenland": "burgenland", "Kärnten": "kaernten",
    "Niederösterreich": "niederoesterreich",
    "Oberösterreich": "oberoesterreich",
    "Salzburg": "salzburg", "Steiermark": "steiermark",
    "Tirol": "tirol", "Vorarlberg": "vorarlberg", "Wien": "wien",
    # household size (categories used in fake ts data)
    "1 Person": "1_person",
    "2 Personen": "2_persons",
    "3 Personen": "3_persons",
    "4 or more persons": "4plus_persons",
    "no kids": "no_children",
    "with 1 kid": "1_child",
    "with 2 or more kids": "2plus_children",
    "with kids": "with_children",
    # freq of volunteering
    "mind. 1x pro Woche": "weekly",
    "mind. 1x pro Monat": "monthly",
    "mind. 1x pro Jahr": "yearly",
    "nie": "never",
}

# Gender comparison dimension / category maps
GC_DIM_MAP = {
    "Formal_NumberOfOrgs": "Formal_NumberOfOrgs",
    "Formal_TaskTypes":    "Formal_TaskTypes",
    "Formal_Areas":        "Formal_Areas",
    "Informal_Areas":      "Informal_Areas",
    "Formal_Time/week":    "Formal_Time/week",
    "Informal_Time/week":  "Informal_Time/week",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _map(value, mapping):
    """Return mapping[value] or value itself if not found (no silent data loss)."""
    return mapping.get(str(value).strip(), str(value).strip())


def _write(filename, new_rows):
    """Append new rows to an existing tidy CSV (or create it)."""
    if not new_rows:
        print(f"  -> {filename}: 0 rows (skipped)")
        return
    path = os.path.join(OUT_DIR, filename)
    new_df = pd.DataFrame(new_rows)
    if os.path.exists(path):
        existing = pd.read_csv(path)
        years_in_new = new_df["year"].unique() if "year" in new_df.columns else []
        if len(years_in_new) and "year" in existing.columns:
            existing = existing[~existing["year"].isin(years_in_new)]
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined.to_csv(path, index=False)
    else:
        new_df.to_csv(path, index=False)
    print(f"  -> {filename}: {len(new_rows)} rows written")


# ── loaders ───────────────────────────────────────────────────────────────────

def load_volunteering_trends():
    """
    Convert volunteering_time_series_fake.json → volunteering_trends.csv rows
    for years 2006, 2012, 2016.

    Notes:
    - Years 1988-2003 are excluded (no matching survey wave in manifest.yaml).
    - The fake JSON stores vol_type as separate columns; we pivot to one row per
      vol_type so the schema matches the real extracted data.
    - Demographics are normalised to canonical names; categories to stable IDs.
    - "multi-person/single-person households" are merged into "household_size".
    """
    with open(os.path.join(ASSETS, "volunteering_time_series_fake.json")) as f:
        raw = json.load(f)

    rows = []
    # Vol types in fake data and their column suffixes
    vol_types = {
        "any":                    ("any_volunteer_count",    "any_volunteer_perc"),
        "formal":                 ("formal_volunteer_count", "formal_volunteer_perc"),
        "informal":               ("informal_volunteer_count","informal_volunteer_perc"),
        "both_formal_informal":   ("both_formal_and_informal_volunteer_count",
                                   "both_formal_and_informal_volunteer_perc"),
        "formal_only":            ("formal_only_volunteer_count", "formal_only_volunteer_perc"),
        "informal_only":          ("informal_only_volunteer_count","informal_only_volunteer_perc"),
    }

    for rec in raw:
        year = rec["year"]
        if year not in SYNTHETIC_YEARS:
            continue

        raw_demo = str(rec.get("demographic", "total")).lower()
        demo = _map(raw_demo, TS_DEMO_MAP)

        raw_cat = str(rec.get("category", "total"))
        cat = _map(raw_cat.lower(), TS_CAT_MAP) if raw_cat.lower() in TS_CAT_MAP else _map(raw_cat, TS_CAT_MAP)

        pop = rec.get("population")

        for vol_type, (count_col, perc_col) in vol_types.items():
            count = rec.get(count_col)
            perc  = rec.get(perc_col)
            rows.append({
                "year":            year,
                "demographic":     demo,
                "category":        cat,
                "vol_type":        vol_type,
                "population_1000": pop,
                "count_1000":      count,
                "percentage":      perc,
            })

    _write("volunteering_trends.csv", rows)


def load_areas(vol_type):
    """
    Convert formal_volunteering_fake_data.json or informal_volunteering_fake_data.json
    → formal_areas.csv / informal_areas.csv rows for 2006, 2012, 2016.

    Known fix: "Care for refugees" (refugee_support) is dropped for 2006-2016 because
    the codelist marks that area null for those years.
    """
    filename = f"{vol_type}_volunteering_fake_data.json"
    csv_name = f"{vol_type}_areas.csv"
    area_map = FORMAL_AREA_MAP if vol_type == "formal" else INFORMAL_AREA_MAP

    # Areas that are null (non-existent) in a given year per the codelist
    null_for_synthetic = {
        "informal_areas": {"refugee_support"},   # only valid in 2022
        "formal_areas":   set(),
    }
    null_ids = null_for_synthetic[f"{vol_type}_areas"]

    with open(os.path.join(ASSETS, filename)) as f:
        raw = json.load(f)

    DEMO_MAP = {
        "Total": ("all", "all"),
        "Gender": None,   # expanded below
        "Age": None,
        "Education": None,
        "Freq_of_volunteering": None,
    }
    GENDER_CAT = {"Men": "male", "Women": "female"}
    AGE_CAT = {
        "< 30 years": "under_30", "Under 30": "under_30",
        "30-44 years": "age_30_39", "45-59 years": "age_40_49",
        "60+ years": "age_60_69", "60 years or older": "age_60_69",
    }
    EDU_CAT = {
        "(max.) Compulsory education": "compulsory_max",
        "teaching, BMS": "apprenticeship_voc",
        "matura": "matura", "university": "university",
    }
    FREQ_CAT = {
        "At least weekly": "weekly", "At least monthly": "monthly",
        "At least yearly": "yearly", "Never": "never",
    }

    rows = []
    for yr_str, demo_data in raw.items():
        year = int(yr_str)
        if year not in SYNTHETIC_YEARS:
            continue

        for demo_key, area_list in demo_data.items():
            if not isinstance(area_list, list):
                continue

            for rec in area_list:
                # The first record for 'Total' is the all-volunteer headline total
                if "all_volunteers" in rec:
                    continue
                area_label = rec.get("name", "")
                area_id = area_map.get(area_label)
                if area_id is None:
                    continue
                if area_id in null_ids:
                    continue   # area doesn't exist for synthetic years per codelist

                count = rec.get("count")
                category_raw = rec.get("category", "all")

                # Map category string → demographic + stable category ID
                if demo_key == "Total":
                    demographic, category = "all", "all"
                elif demo_key == "Gender":
                    demographic = "gender"
                    category = GENDER_CAT.get(category_raw, category_raw.lower())
                elif demo_key == "Age":
                    demographic = "age_group"
                    category = AGE_CAT.get(category_raw, category_raw)
                elif demo_key == "Education":
                    demographic = "education"
                    category = EDU_CAT.get(category_raw, category_raw)
                elif demo_key == "Freq_of_volunteering":
                    demographic = "freq_of_volunteering"
                    category = FREQ_CAT.get(category_raw, category_raw)
                else:
                    demographic, category = demo_key.lower(), category_raw

                rows.append({
                    "year":       year,
                    "area_id":    area_id,
                    "demographic": demographic,
                    "category":   category,
                    "count_1000": count,
                    "percentage": None,   # not provided in fake data
                })

    _write(csv_name, rows)


def load_motivations_barriers():
    """
    Convert motivations_barriers_fake_data.json → motivations.csv and
    barriers.csv rows for 2006, 2012, 2016.
    """
    with open(os.path.join(ASSETS, "motivations_barriers_fake_data.json")) as f:
        raw = json.load(f)

    motiv_rows, barrier_rows = [], []
    for rec in raw:
        year = rec["year"]
        if year not in SYNTHETIC_YEARS:
            continue

        item_type = rec["type"]
        cat_label = rec.get("category", "")
        gender = rec.get("gender", "all")   # already "all"/"men"/"women"

        if item_type == "motivation":
            item_id = MOTIVATION_MAP.get(cat_label)
            if item_id is None:
                continue
            motiv_rows.append({
                "year":            year,
                "type":            "motivation",
                "item_id":         item_id,
                "gender":          gender,
                "population_1000": rec.get("population"),
                "fully_agree":     rec.get("fully_agree"),
                "rather_agree":    rec.get("rather_agree"),
                "rather_disagree": rec.get("rather_disagree"),
                "not_at_all":      rec.get("not_at_all"),
            })
        elif item_type == "barrier":
            item_id = BARRIER_MAP.get(cat_label)
            if item_id is None:
                continue
            barrier_rows.append({
                "year":            year,
                "type":            "barrier",
                "item_id":         item_id,
                "gender":          gender,
                "population_1000": rec.get("population"),
                "fully_agree":     rec.get("fully_agree"),
                "rather_agree":    rec.get("rather_agree"),
                "rather_disagree": rec.get("rather_disagree"),
                "not_at_all":      rec.get("not_at_all"),
            })

    _write("motivations.csv", motiv_rows)
    _write("barriers.csv", barrier_rows)


def load_time_distribution():
    """
    Convert errorBars_data_multiyear.json → time_distribution.csv rows
    for 2006, 2012, 2016.

    Notes:
    - 'TaskType' demographic is included for synthetic years (it doesn't exist
      in 2025 but was present in 2022 as 3 broad categories; synthetic data
      follows the same 3-category structure).
    - All category values are mapped to stable IDs.
    """
    with open(os.path.join(ASSETS, "errorBars_data_multiyear.json")) as f:
        raw = json.load(f)

    rows = []
    for yr_str, demo_data in raw.items():
        year = int(yr_str)
        if year not in SYNTHETIC_YEARS:
            continue

        for demo_key, records in demo_data.items():
            demographic = ERRORBAR_DEMO_MAP.get(demo_key, demo_key.lower())

            for rec in records:
                cat_raw = rec.get("category_value", "all")
                category = _map(cat_raw, ERRORBAR_CAT_MAP)
                vol_type_raw = rec.get("volunteering_type", "Total")
                vol_type = vol_type_raw  # already "Total"/"Formal"/"Informal"

                rows.append({
                    "year":        year,
                    "demographic": demographic,
                    "category":    category,
                    "vol_type":    vol_type,
                    "count_1000":  rec.get("persons_1000"),
                    "avg_hours":   rec.get("avg_hours"),
                    "p25":         rec.get("percentile_25"),
                    "p50":         rec.get("percentile_50"),
                    "p75":         rec.get("percentile_75"),
                })

    _write("time_distribution.csv", rows)


def load_geo_regions():
    """
    Convert Geo_interpolated_by_year.json → geo_regions.csv rows
    for 2006, 2012, 2016.

    The Geo JSON already has all required columns; region names are
    normalised to stable IDs but kept as display names for the choropleth
    (the geojson feature names use the full German spelling).
    """
    with open(os.path.join(ASSETS, "Geo_interpolated_by_year.json")) as f:
        raw = json.load(f)

    # Region name map: display name in Geo JSON → stable region ID
    # (geo_regions.csv stores the German name used by the choropleth GeoJSON)
    REGION_DISPLAY = {
        "Austria": "Österreich gesamt",
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

    rows = []
    for rec in raw:
        year = rec.get("year")
        if year not in SYNTHETIC_YEARS:
            continue
        region_raw = rec.get("region", "")
        region = REGION_DISPLAY.get(region_raw, region_raw)
        if region_raw == "Austria":
            continue   # geo_regions only stores Bundesländer, not the Austria total

        rows.append({
            "year":                     year,
            "region":                   region,
            "total_pop":                rec.get("total_pop"),
            "perc_volunteers_from_pop": rec.get("perc_volunteers_from_pop"),
            "perc_formal_from_pop":     rec.get("perc_formal_from_pop"),
            "perc_informal_from_pop":   rec.get("perc_informal_from_pop"),
            "avg_hours_vlntrs":         rec.get("avg_hours_vlntrs"),
            "avg_hours_formal":         rec.get("avg_hours_formal"),
            "avg_hours_informal":       rec.get("avg_hours_informal"),
            "median_hours_vlntrs":      rec.get("median_hours_vlntrs"),
            "median_hours_formal":      rec.get("median_hours_formal"),
            "median_hours_informal":    rec.get("median_hours_informal"),
            "25_hrs_vlntrs":            rec.get("25_hrs_vlntrs"),
            "75_hrs_vlntrs":            rec.get("75_hrs_vlntrs"),
            "25_hrs_formal":            rec.get("25_hrs_formal"),
            "75_hrs_formal":            rec.get("75_hrs_formal"),
            "25_hrs_informal":          rec.get("25_hrs_informal"),
            "75_hrs_informal":          rec.get("75_hrs_informal"),
        })

    _write("geo_regions.csv", rows)


def load_gender_comparison():
    """
    Convert gender_comparison_data_multiyear.json → gender_comparison.csv rows
    for 2006, 2012, 2016.

    Schema produced:
      year, vol_type, dimension, category, men_count, men_perc, women_count, women_perc

    Notes:
    - Formal_TaskTypes uses the 3-category structure (Leadership/Core tasks/Support tasks)
      valid for 2022 and assumed equivalent for synthetic years.
    - For 2025 this dimension is absent from the schema (task categories restructured).
    """
    with open(os.path.join(ASSETS, "gender_comparison_data_multiyear.json")) as f:
        raw = json.load(f)

    rows = []
    for yr_str, dim_data in raw.items():
        year = int(yr_str)
        if year not in SYNTHETIC_YEARS:
            continue

        for dim_key, records in dim_data.items():
            if not isinstance(records, list):
                continue

            # Determine vol_type from dimension key
            vol_type = "Formal" if dim_key.startswith("Formal") else "Informal"

            for rec in records:
                # Each record has different key names per dimension
                cat = (rec.get("area") or rec.get("task") or
                       rec.get("num_orgs") or rec.get("hours_range/week") or "?")
                rows.append({
                    "year":        year,
                    "vol_type":    vol_type,
                    "dimension":   dim_key,
                    "category":    cat,
                    "men_count":   rec.get("men_count"),
                    "men_perc":    rec.get("men_perc"),
                    "women_count": rec.get("women_count"),
                    "women_perc":  rec.get("women_perc"),
                })

    _write("gender_comparison.csv", rows)


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading synthetic years:", SYNTHETIC_YEARS)
    print()

    print("volunteering_trends...")
    load_volunteering_trends()

    print("formal_areas...")
    load_areas("formal")

    print("informal_areas...")
    load_areas("informal")

    print("motivations / barriers...")
    load_motivations_barriers()

    print("time_distribution...")
    load_time_distribution()

    print("geo_regions...")
    load_geo_regions()

    print("gender_comparison...")
    load_gender_comparison()

    print("\nDone.")
