import os
import json
import sys

import dash
from dash import dcc, html, ctx, dash_table
from dash.dependencies import Output, Input, State
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.colors as pc
import dash_bootstrap_components as dbc

sys.path.insert(0, os.path.dirname(__file__))
from schema.schema_loader import get_available_years, get_available_filters

# ── data loading ──────────────────────────────────────────────────────────────
geo_df           = pd.read_csv("assets/data/geo_regions.csv")
trend_df         = pd.read_csv("assets/data/volunteering_trends.csv")
motiv_df         = pd.read_csv("assets/data/motivations.csv")
barriers_df      = pd.read_csv("assets/data/barriers.csv")
formal_areas_df  = pd.read_csv("assets/data/formal_areas.csv")
informal_areas_df= pd.read_csv("assets/data/informal_areas.csv")
time_dist_df     = pd.read_csv("assets/data/time_distribution.csv")
gender_comp_df   = pd.read_csv("assets/data/gender_comparison.csv")
mb_df            = pd.concat([motiv_df, barriers_df], ignore_index=True)

with open("assets/laender_999_geo.json", "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

years   = sorted(get_available_years())
regions = sorted(geo_df["region"].unique())

# ── label maps ────────────────────────────────────────────────────────────────
CATEGORY_LABELS = {
    "male": "Men", "female": "Women", "all": "All",
    "under_30": "Under 30", "age_30_39": "30–39", "age_40_49": "40–49",
    "age_50_59": "50–59", "age_60_69": "60–69", "age_70_79": "70–79", "age_80_plus": "80+",
    "compulsory_max": "Compulsory/less", "apprenticeship_voc": "Apprenticeship/BMS",
    "matura": "Matura", "university": "University",
    "first_generation": "1st generation", "second_generation": "2nd generation",
    "no_migration": "No migration background",
    "employed": "Employed", "retired": "Retired", "other_employment": "Other",
    "in_training": "In training", "homemaker": "Homemaker",
    "up_to_2500": "≤2,500", "up_to_10000": "≤10,000",
    "up_to_100000": "≤100,000", "over_100000": ">100,000",
    "burgenland": "Burgenland", "kaernten": "Kärnten",
    "niederoesterreich": "Niederösterreich", "oberoesterreich": "Oberösterreich",
    "salzburg": "Salzburg", "steiermark": "Steiermark",
    "tirol": "Tirol", "vorarlberg": "Vorarlberg", "wien": "Wien",
    "leadership": "Leadership", "core_tasks": "Core tasks", "support_tasks": "Support tasks",
    "lt_1h": "<1 hour", "1_4h": "1–4 hours", "5_9h": "5–9 hours",
    "10_19h": "10–19 hours", "20plus_h": "20+ hours",
    "disaster_rescue": "Disaster & Rescue", "arts_culture": "Arts & Culture",
    "environment_nature": "Environment & Nature", "religion_church": "Religion & Church",
    "social_health": "Social & Health", "politics_advocacy": "Politics & Advocacy",
    "civic_community": "Civic & Community", "education": "Education",
    "sports": "Sports", "refugee_aid": "Refugee Aid", "other_area": "Other Area",
    "household_tasks": "Household tasks", "repairs_crafts": "Repairs & Crafts",
    "garden_support": "Gardening", "visit_services": "Visiting care recipients",
    "care_dependent": "Care for dependents", "transport_services": "Transport",
    "disaster_aid": "Disaster aid", "admin_paperwork": "Admin & Paperwork",
    "tutoring": "Tutoring", "childcare": "Childcare",
    "refugee_support": "Refugee support", "other_informal": "Other",
    "enjoy_work": "Enjoy the work", "common_good": "Contribute to common good",
    "help_others": "Help others", "career_benefit": "Career benefit",
    "use_skills": "Use my skills", "social_connection": "Meet people",
    "social_recognition": "Social recognition", "stay_active": "Stay active",
    "share_experience": "Share experience", "learning": "Learn/develop",
    "find_job": "Find a job", "reciprocity": "Expect help in return",
    "important_cause": "Important cause",
    "never_asked": "Never been asked", "never_thought": "Never thought about it",
    "family_burden": "Family responsibilities", "illness_disability": "Illness/disability",
    "financial": "Financial reasons", "work_incompatible": "Incompatible with work",
    "bad_experience": "Bad experiences", "no_contribution": "Feel unable to contribute",
    "wrong_age": "Wrong age", "lack_information": "Lack of information",
    "nothing_nearby": "Nothing nearby",
    "weekly": "Weekly", "monthly": "Monthly", "yearly": "Yearly", "never": "Never",
}

DEMOGRAPHIC_LABELS = {
    "gender": "Gender", "age_group": "Age", "age": "Age",
    "education": "Education",
    "migration_background": "Migration Background", "migration": "Migration Background",
    "employment": "Employment", "employment_type": "Employment type",
    "municipality_size": "Municipality Size",
    "municipality size classes": "Municipality Size",
    "region": "Region",
    "freq_of_volunteering": "Frequency of Volunteering",
    "task_type": "Task Type", "total": "Total",
    "citizenship": "Citizenship", "birth_country": "Country of Birth",
    "household_size": "Household Size", "household size": "Household Size",
    "occupation": "Occupation",
    "single-person households": "Single-Person Households",
    "multi-person households": "Multi-Person Households",
}

DIM_LABELS = {
    "Formal_NumberOfOrgs": "Number of Organizations",
    "Formal_TaskTypes":    "Task Types",
    "Formal_Areas":        "Activity Areas",
    "Formal_Time/week":    "Time per week",
    "Informal_Areas":      "Activity Areas",
    "Informal_Time/week":  "Time per week",
}

VOL_TYPE_DISPLAY = {
    "any": "Any", "formal": "Formal", "informal": "Informal",
    "both_formal_informal": "Formal and Informal",
    "formal_only": "Formal Only", "informal_only": "Informal Only",
    "Total": "Any", "Formal": "Formal", "Informal": "Informal",
}

MAP_COLUMN_LABELS = {
    "perc_volunteers_from_pop": "Any (%)",
    "perc_formal_from_pop":    "Formal (%)",
    "perc_informal_from_pop":  "Informal (%)",
    "avg_hours_vlntrs":        "Avg hrs (Any)",
    "avg_hours_formal":        "Avg hrs (Formal)",
    "avg_hours_informal":      "Avg hrs (Informal)",
    "median_hours_vlntrs":     "Median hrs (Any)",
    "median_hours_formal":     "Median hrs (Formal)",
    "median_hours_informal":   "Median hrs (Informal)",
}


def cat_label(cat_id):
    return CATEGORY_LABELS.get(str(cat_id), str(cat_id).replace("_", " ").capitalize())


def demo_label(demo_id):
    return DEMOGRAPHIC_LABELS.get(str(demo_id), str(demo_id).replace("_", " ").capitalize())


def _ts_demographic_options():
    manifest_years = set(get_available_years())
    all_demos = sorted(trend_df[trend_df["year"].isin(manifest_years)]["demographic"].unique())
    return [{"label": demo_label(d), "value": d} for d in all_demos]


# ── Dash app ──────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, 
    title="Statistics of Volunteering in Austria",
    index_string="""<!DOCTYPE html>
<html lang="en">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>""")
server = app.server

app.layout = dbc.Container([
    html.H1("Statistics of volunteering in Austria",
            className="text-center my-4 fw-bold"),

    html.Div([
        dbc.Button("☰", id="open-offcanvas", n_clicks=0, color="light",
                   style={"position": "fixed", "top": "20px", "left": "20px",
                          "zIndex": 9999, "fontSize": "24px"}),
        dbc.Offcanvas([
            html.H2("Contents", className="h5 my-3"),
            dbc.Nav([
                dbc.NavLink("Geographic Distribution", href="#choropleth-card", external_link=True),
                dbc.NavLink("Time-Series Trends (demographic comparison)", href="#timeseries-card", external_link=True),
                dbc.NavLink("Time-Series Trends (volunteering type comparison)", href="#ts2-time-series-card", external_link=True),
                dbc.NavLink("Motivations and Barriers", href="#motivation-barrier-card", external_link=True),
                dbc.NavLink("Volunteer Activity by Demographic", href="#activity-bar-card", external_link=True),
                dbc.NavLink("Gender Comparison", href="#gender-comparison-card", external_link=True),
                dbc.NavLink("Volunteer Time Distribution", href="#errorBar-card", external_link=True),
            ], vertical=True),
        ], id="offcanvas", is_open=False, placement="start", backdrop=True,
           style={"width": "250px", "backgroundColor": "white"}),
    ]),

    # ── Geographic Distribution ──────────────────────────────────────────────
    dbc.Card([dbc.CardBody([
        html.H2("Geographic Distribution of Volunteering",
                className="mb-4 mt-2 text-center fw-semibold"),
        dbc.Row([
            dbc.Col([
                html.Label("Type of Volunteering", className="mb-1", htmlFor="metric-dropdown"),
                dbc.Select(id="metric-dropdown", options=[
                    {"label": "Any", "value": "perc_volunteers_from_pop"},
                    {"label": "Formal", "value": "perc_formal_from_pop"},
                    {"label": "Informal", "value": "perc_informal_from_pop"},
                ], value="perc_volunteers_from_pop"),
            ], width=2),
            dbc.Col([
                html.Fieldset([
                    html.Legend("Statistic", className="mb-1"),
                    dcc.RadioItems(id="stat-type-radio", options=[
                        {"label": "Percentage", "value": "perc"},
                        {"label": "Avg Hours/week", "value": "avg_hours"},
                        {"label": "Median Hours", "value": "median_hours"},
                    ], value="perc", labelStyle={"marginRight": "15px"}),
                ], style={"border": "none", "padding": 0, "margin": 0}),
            ], width=2, style={"paddingTop": 30}),
            dbc.Col([
                html.Label("Year", className="mb-1", htmlFor="year-dropdown"),
                dbc.Select(id="year-dropdown",
                           options=[{"label": str(y), "value": str(y)} for y in years],
                           value=str(max(years))),
            ], width=2),
            dbc.Col([
                dbc.Button("Reset to Austria", id="reset-button",
                           color="primary", className="mt-3"),
            ], width=2, style={"textAlign": "right"}),
        ], className="mb-4", align="center", justify="center"),
        dbc.Row([
            dbc.Col(html.Figure(dcc.Graph(id="austria-map", config={"displaylogo": False}), **{"aria-describedby": "desc-choropleth"}, style={"margin": 0}), width=6),
            dbc.Col(html.Figure(dcc.Graph(id="region-boxplot",config={"displaylogo": False}), **{"aria-describedby": "desc-choropleth"}, style={"margin": 0}), width=6),
        ]),
        dbc.Row([dbc.Col(html.Div(id="data-insights", className="data-insights"), width=12)]),
        dbc.Alert([
            html.P("Graph description", className="fw-bold mb-1"),
            html.P("The above graph shows the distribution of volunteers across Austrian regions. "
                   "Percentages represent the proportion of people who participated in the selected "
                   "volunteering type during the selected year from the total population above 15 years of age in the region."),
        ], id="desc-choropleth", color="light", style={"border": "1px solid #ccc", "marginTop": "10px"}),
    ])], id="choropleth-card", className="mb-5 shadow-sm border-0",
       style={"backgroundColor": "#f8f9fa"}),

    # ── Time Series (demographic comparison) ─────────────────────────────────
    dbc.Card([dbc.CardBody([
        html.H2("Time-series trends of Volunteering across demographic categories",
                className="mb-4 mt-2 text-center fw-semibold"),
        dbc.Row([
            dbc.Col([
                html.Label("Type of Volunteering", className="mb-1", htmlFor="ts-type-dropdown"),
                dbc.Select(id="ts-type-dropdown", options=[
                    {"label": "Any", "value": "any"},
                    {"label": "Formal", "value": "formal"},
                    {"label": "Informal", "value": "informal"},
                    {"label": "Formal and Informal", "value": "both_formal_informal"},
                    {"label": "Formal Only", "value": "formal_only"},
                    {"label": "Informal Only", "value": "informal_only"},
                ], value="any"),
            ], width=2),
            dbc.Col([
                html.Label("Demographic", className="mb-1", htmlFor="ts-demographic-dropdown"),
                dbc.Select(id="ts-demographic-dropdown",
                           options=_ts_demographic_options(),
                           value="total"),
            ], width=2),
            dbc.Col([
                html.Fieldset([
                    html.Legend("Statistic", className="mb-1"),
                    dcc.RadioItems(id="ts-radio", options=[
                        {"label": "Percentage", "value": "perc"},
                        {"label": "Count", "value": "count"},
                    ], value="perc", labelStyle={"marginRight": "15px"}),
                ], style={"border": "none", "padding": 0, "margin": 0}),
            ], width=2, style={"paddingTop": 8}),
            dbc.Col([
                html.Div("Year Range", className="mb-1"),
                dcc.RangeSlider(
                    id="ts-year-slider",
                    min=int(min(years)), max=int(max(years)),
                    value=[int(min(years)), int(max(years))],
                    marks={int(y): str(y) for y in years},
                    step=None,
                ),
            ], width=4, style={"paddingTop": 12}),
        ], className="mb-4", align="center", justify="center"),
        html.Figure(dcc.Graph(id="ts-line-graph", config={"displaylogo": False}), **{"aria-describedby": "desc-ts"}, style={"margin": 0}),
        dbc.Alert([
            html.P("Graph description", className="fw-bold mb-1"),
            html.P([
                "The above graph shows time series trends of volunteering across demographic categories. ",
                "For Any/Formal/Informal, the percentage is from all residents above 15 years of age in the selected demographic group. ",
                html.Br(), html.Br(),
                "For Formal and Informal/Formal Only/Informal Only, the percentage is from all volunteers "
                "in the selected demographic group (i.e. what share of volunteers fall into each overlap category).",
            ]),
        ], id="desc-ts", color="light", style={"border": "1px solid #ccc", "marginTop": "10px"}),
    ])], id="timeseries-card", className="mb-5 shadow-sm border-0",
       style={"backgroundColor": "#f8f9fa"}),

    # ── Time Series (volunteering type comparison) ────────────────────────────
    dbc.Card([dbc.CardBody([
        html.H2("Time-series trends of Volunteering across volunteering types",
                className="mb-4 mt-2 text-center fw-semibold"),
        dbc.Row([
            dbc.Col([
                html.Label("Demographic Dimension", className="mb-1", htmlFor="ts2-demographic-dropdown"),
                dbc.Select(id="ts2-demographic-dropdown",
                           options=_ts_demographic_options(),
                           value="total"),
            ], width=2),
            dbc.Col([
                html.Label("Demographic Category", className="mb-1", htmlFor="ts2-category-dropdown"),
                dbc.Select(id="ts2-category-dropdown", options=[], value=""),
            ], width=2),
            dbc.Col([
                html.Fieldset([
                    html.Legend("Statistic", className="mb-1"),
                    dcc.RadioItems(id="ts2-radio", options=[
                        {"label": "Percentage", "value": "perc"},
                        {"label": "Count", "value": "count"},
                    ], value="perc", labelStyle={"marginRight": "15px"}),
                ], style={"border": "none", "padding": 0, "margin": 0}),
            ], width=2, style={"paddingTop": 8}),
            dbc.Col([
                html.Div("Year Range", className="mb-1"),
                dcc.RangeSlider(
                    id="ts2-year-slider",
                    min=min(years), max=max(years),
                    value=[min(years), max(years)],
                    marks={y: str(y) for y in years},
                    step=None,
                ),
            ], width=4, style={"paddingTop": 12}),
        ], align="center", justify="center", className="mb-4"),
        html.Figure(dcc.Graph(id="ts2-line-graph", config={"displaylogo": False}), **{"aria-describedby": "desc-ts2"}, style={"margin": 0}),
        dbc.Alert([
            html.P("Graph description", className="fw-bold mb-1"),
            html.P([
                "The above graph compares all volunteering type trends for a fixed demographic category across survey years. "
            ,
            ]),
        ], id="desc-ts2", color="light", style={"border": "1px solid #ccc", "marginTop": "10px"}),
    ])], id="ts2-time-series-card", className="mb-5 shadow-sm border-0",
       style={"backgroundColor": "#f8f9fa"}),

    # ── Motivations and Barriers ──────────────────────────────────────────────
    dbc.Card([dbc.CardBody([
        html.H2("Motivations and Barriers to Volunteering",
                className="mb-4 mt-2 text-center fw-semibold"),
        dbc.Row([
            dbc.Col([
                html.Fieldset([
                    html.Legend("Type", className="mb-1"),
                    dcc.RadioItems(id="mb-type-radio", options=[
                        {"label": "Motivations", "value": "motivation"},
                        {"label": "Barriers", "value": "barrier"},
                    ], value="motivation", labelStyle={"marginRight": "15px"}),
                ], style={"border": "none", "padding": 0, "margin": 0}),
            ], width=2),
            dbc.Col([
                html.Label("Gender", className="mb-1", htmlFor="mb-gender-dropdown"),
                dbc.Select(id="mb-gender-dropdown",
                           options=[{"label": g.capitalize(), "value": g}
                                    for g in sorted(mb_df["gender"].unique())],
                           value="all"),
            ], width=2),
            dbc.Col([
                html.Label("Year", className="mb-1", htmlFor="mb-year-dropdown"),
                dbc.Select(id="mb-year-dropdown",
                           options=[{"label": str(y), "value": str(y)} for y in years],
                           value=str(max(years))),
            ], width=2),
        ], align="center", justify="center", className="mb-4"),
        html.Figure(dcc.Graph(id="mb-diverging-bar", config={"displaylogo": False}), **{"aria-describedby": "desc-mb"}, style={"margin": 0}),
        dbc.Alert([
            html.P("Graph description", className="fw-bold mb-1"),
            html.P("The above graph shows reasons that motivated volunteers and barriers faced by non-volunteers "
                   "in the selected year for each gender, sorted by 'strongly agree'."),
        ], id="desc-mb", color="light", style={"border": "1px solid #ccc", "marginTop": "10px"}),
    ])], id="motivation-barrier-card", className="mb-5 shadow-sm border-0",
       style={"backgroundColor": "#f8f9fa"}),

    # ── Volunteer Activity by Demographic ─────────────────────────────────────
    dbc.Card([dbc.CardBody([
        html.H2("Volunteer Activity by Demographic Group",
                className="mb-4 mt-2 text-center fw-semibold"),
        dbc.Row([
            dbc.Col([
                html.Label("Type of Volunteering", className="mb-1", htmlFor="activity-type-dropdown"),
                dbc.Select(id="activity-type-dropdown", options=[
                    {"label": "Formal", "value": "formal"},
                    {"label": "Informal", "value": "informal"},
                ], value="formal"),
            ], width=2),
            dbc.Col([
                html.Label("Demographic", className="mb-1", htmlFor="activity-demographic-dropdown"),
                dbc.Select(id="activity-demographic-dropdown", options=[], value="all"),
            ], width=2),
            dbc.Col([
                html.Fieldset([
                    html.Legend("Statistic", className="mb-1"),
                    dcc.RadioItems(id="activity-display-mode", options=[
                        {"label": "Percentage", "value": "percent"},
                        {"label": "Count", "value": "count"},
                    ], value="percent", labelStyle={"marginRight": "15px"}),
                ], style={"border": "none", "padding": 0, "margin": 0}),
            ], width=2),
            dbc.Col([
                html.Label("Year", className="mb-1", htmlFor="activity-year-dropdown"),
                dbc.Select(id="activity-year-dropdown",
                           options=[{"label": str(y), "value": str(y)} for y in years],
                           value=str(max(years))),
            ], width=2),
        ], align="center", justify="center", className="mb-4"),
        html.Figure(dcc.Graph(id="activity-stacked-bar", config={"displaylogo": False}), **{"aria-describedby": "desc-activity"}, style={"margin": 0}),
        dbc.Alert([
            html.P("Graph description", className="fw-bold mb-1"),
            html.P([
                "The above graph shows the distribution of formal/informal volunteers across volunteering activities. ",
                html.Br(),
                "Each bar shows the percentage of volunteers who do each activity from all volunteers "
                "of the selected volunteeringtype in the selected year. ",

            ]),
        ], id="desc-activity", color="light", style={"border": "1px solid #ccc", "marginTop": "10px"}),
    ])], id="activity-bar-card", className="mb-5 shadow-sm border-0",
       style={"backgroundColor": "#f8f9fa"}),

    # ── Gender Comparison ─────────────────────────────────────────────────────
    dbc.Card([dbc.CardBody([
        html.H2("Gender Comparison in Volunteering",
                className="mb-4 mt-2 text-center fw-semibold"),
        dbc.Row([
            dbc.Col([
                html.Label("Type of Volunteering", className="mb-1",
                           htmlFor="gender-type-select"),
                dbc.Select(id="gender-type-select", options=[
                    {"label": "Formal", "value": "Formal"},
                    {"label": "Informal", "value": "Informal"},
                ], value="Formal"),
            ], width=2),
            dbc.Col([
                html.Label("Dimension", className="mb-1",
                           htmlFor="gender-dimension-select"),
                dbc.Select(id="gender-dimension-select", options=[], value=""),
            ], width=2),
            dbc.Col([
                html.Fieldset([
                    html.Legend("Statistic", className="mb-1"),
                    dcc.RadioItems(id="gender-display-mode", options=[
                        {"label": "Percentage", "value": "percent"},
                        {"label": "Count", "value": "count"},
                    ], value="percent", labelStyle={"marginRight": "15px"}),
                ], style={"border": "none", "padding": 0, "margin": 0}),
            ], width=2),
            dbc.Col([
                html.Label("Year", className="mb-1", htmlFor="gender-year-select"),
                dbc.Select(id="gender-year-select",
                           options=[{"label": str(y), "value": str(y)} for y in years],
                           value=str(max(years))),
            ], width=2),
        ], align="center", justify="center", className="mb-4"),
        html.Figure(dcc.Graph(id="gender-comparison-bar", config={"displaylogo": False}), **{"aria-describedby": "desc-gender"}, style={"margin": 0}),
        html.Div(id="gender-live-summary",
                 className="visually-hidden",
                 **{"aria-live": "polite", "aria-atomic": "true"}),
        html.Div(
            id="gender-comparison-table",
            tabIndex=0,
            role="region",
            **{"aria-label": "Gender comparison data table"},
            style={"marginTop": "16px", "overflowX": "auto"},
        ),
        dbc.Alert([
            html.P("Graph description", className="fw-bold mb-1"),
            html.P([
                "The above graph compares different participation dimensions of men vs women in volunteering. ",

            ]),
        ], id="desc-gender", color="light", style={"border": "1px solid #ccc", "marginTop": "10px"}),
    ])], id="gender-comparison-card", className="mb-5 shadow-sm border-0",
       style={"backgroundColor": "#f8f9fa"}),

    # ── Error Bar / Time Distribution ─────────────────────────────────────────
    dbc.Card([dbc.CardBody([
        html.H2("Volunteer Time Distribution",
                className="mb-4 mt-2 text-center fw-semibold"),
        dbc.Row([
            dbc.Col([
                html.Label("Type of Volunteering", className="mb-1", htmlFor="errorBar-voltype-dropdown"),
                dbc.Select(id="errorBar-voltype-dropdown", options=[
                    {"label": "Any", "value": "Total"},
                    {"label": "Formal", "value": "Formal"},
                    {"label": "Informal", "value": "Informal"},
                ], value="Total"),
            ], width=2),
            dbc.Col([
                html.Label("Demographic", className="mb-1", htmlFor="errorBar-demographic-dropdown"),
                dbc.Select(id="errorBar-demographic-dropdown", options=[], value="total"),
            ], width=2),
            dbc.Col([
                html.Label("Year", className="mb-1", htmlFor="errorBar-year-dropdown"),
                dbc.Select(id="errorBar-year-dropdown",
                           options=[{"label": str(y), "value": str(y)} for y in years],
                           value=str(max(years))),
            ], width=2),
        ], align="center", justify="center", className="mb-4"),
        html.Figure(dcc.Graph(id="errorBar-figure",config={"displaylogo": False}), **{"aria-describedby": "desc-errorbar"}, style={"margin": 0}),
        dbc.Alert([
            html.P("Graph description", className="fw-bold mb-1"),
            html.P("The above graph compares weekly time spent on volunteering by demographic category. "
                   "Bar height = median; diamond marker = mean; error bars = interquartile range (P25–P75). "
                   ),
        ], id="desc-errorbar", color="light", style={"border": "1px solid #ccc", "marginTop": "10px"}),
    ])], id="errorBar-card", className="mb-5 shadow-sm border-0",
       style={"backgroundColor": "#f8f9fa"}),

    dcc.Store(id="selected-region", data=regions[0]),
    dcc.Interval(id="a11y-radio-init", interval=200, max_intervals=1),
    html.Div(id="other-sections-placeholder"),
], fluid=True)

# ── one-time: stamp unique name= on every RadioItems group so NVDA counts correctly
app.clientside_callback(
    """
    function(n) {
        var groups = [
            'stat-type-radio', 'ts-radio', 'ts2-radio',
            'mb-type-radio', 'activity-display-mode', 'gender-display-mode'
        ];
        groups.forEach(function(gid) {
            var el = document.getElementById(gid);
            if (!el) return;
            el.querySelectorAll('input[type="radio"]').forEach(function(inp) {
                inp.setAttribute('name', gid);
            });
        });

        return null;
    }
    """,
    Output("other-sections-placeholder", "children"),
    Input("a11y-radio-init", "n_intervals"),
)

# ── helpers ───────────────────────────────────────────────────────────────────
def resolve_column(metric_value, stat_type_value):
    base = {"perc_volunteers_from_pop": "vlntrs",
            "perc_formal_from_pop":    "formal",
            "perc_informal_from_pop":  "informal"}.get(metric_value, "vlntrs")
    if stat_type_value == "perc":
        return metric_value
    elif stat_type_value == "avg_hours":
        return f"avg_hours_{base}"
    elif stat_type_value == "median_hours":
        return f"median_hours_{base}"
    return metric_value


# ── callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output("offcanvas", "is_open"),
    Input("open-offcanvas", "n_clicks"),
    State("offcanvas", "is_open"),
)
def toggle_offcanvas(n, is_open):
    if n:
        return not is_open
    return is_open


@app.callback(
    Output("region-boxplot", "figure"),
    Output("austria-map", "figure"),
    Output("selected-region", "data"),
    Input("austria-map", "clickData"),
    Input("metric-dropdown", "value"),
    Input("stat-type-radio", "value"),
    Input("year-dropdown", "value"),
    Input("reset-button", "n_clicks"),
    #Input("region-select-dropdown", "value"),
    State("selected-region", "data"),
    prevent_initial_call=False,
)

#def update_visuals(click_data, metric_value, stat_type, year, reset_clicks, region_dropdown, current_region):
def update_visuals(click_data, metric_value, stat_type, year, reset_clicks, current_region):
    triggered = ctx.triggered_id
    d_year = geo_df[geo_df["year"] == int(year)]

    if triggered == "reset-button":
        new_region = regions[0]
    #elif triggered == "region-select-dropdown" and region_dropdown:
     #   new_region = region_dropdown
    elif (triggered == "austria-map" and click_data
          and click_data.get("points")
          and "location" in click_data["points"][0]):
        new_region = click_data["points"][0]["location"]
    elif current_region in d_year["region"].values:
        new_region = current_region
    else:
        new_region = regions[0]

    if new_region not in d_year["region"].values:
        new_region = d_year["region"].iloc[0]

    prefix = {"perc_volunteers_from_pop": "vlntrs",
              "perc_formal_from_pop":    "formal",
              "perc_informal_from_pop":  "informal"}.get(metric_value, "vlntrs")

    row = d_year.loc[d_year["region"] == new_region].iloc[0]
    q1     = row[f"25_hrs_{prefix}"]
    median = row[f"median_hours_{prefix}"]
    q3     = row[f"75_hrs_{prefix}"]
    avg    = row[f"avg_hours_{prefix}"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[new_region], y=[median],
        error_y=dict(type="data", symmetric=False,
                     array=[q3 - median], arrayminus=[median - q1],
                     color="black", thickness=2, width=8),
        marker_color="#0072B2", name="Median with IQR",
        hovertemplate=f"<b>{new_region}</b><br>Q3: {q3}<br>Median: {median}<br>Q1: {q1}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[new_region], y=[avg], mode="markers",
        marker=dict(color="black", size=10, symbol="diamond"),
        name="Average",
        hovertemplate=f"<b>{new_region}</b><br>Average: {avg}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Volunteer Hours – {new_region} ({year})",
        yaxis_title="Hours per Week", xaxis_title="",
        template="plotly_white", showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.05),
    )

    column = resolve_column(metric_value, stat_type)
    value  = row[column]
    unit   = {"perc": "%", "avg_hours": "hrs", "median_hours": "hrs"}.get(stat_type, "")

    fig_map = px.choropleth(
        d_year, locations="region", geojson=geojson_data, color=column,
        color_continuous_scale="Blues", featureidkey="properties.name",
        labels={column: MAP_COLUMN_LABELS.get(column, column)},
        title=f"{new_region} {value:.1f}{unit} ({year})",
    )
    if new_region != regions[0] or triggered == "austria-map":
        selected_feat = next(
            (f for f in geojson_data["features"] if f["properties"]["name"] == new_region), None
        )
        if selected_feat:
            coords = selected_feat["geometry"]["coordinates"][0][0]
            lons, lats = zip(*coords)
            fig_map.update_geos(lonaxis_range=[min(lons), max(lons)],
                                lataxis_range=[min(lats), max(lats)], visible=False)
        else:
            fig_map.update_geos(fitbounds="locations", visible=False)
    else:
        fig_map.update_geos(fitbounds="locations", visible=False)

    fig_map.update_traces(marker_line_color="black", marker_line_width=0.5,
                          selector=dict(type="choropleth"))
    return fig, fig_map, new_region


@app.callback(
    Output("data-insights", "children"),
    Input("metric-dropdown", "value"),
    Input("stat-type-radio", "value"),
    Input("year-dropdown", "value"),
)
def update_insights(metric_dropdown_value, stat_type_value, year):
    column = resolve_column(metric_dropdown_value, stat_type_value)
    d_year = geo_df[geo_df["year"] == int(year)]
    highest = d_year.loc[d_year[column].idxmax()]
    lowest  = d_year.loc[d_year[column].idxmin()]
    label_map = {"perc": "% of Population", "avg_hours": "Average Weekly Hours",
                 "median_hours": "Median Weekly Hours"}
    return [
        html.P([html.Strong("Highest: "), f"{highest['region']} ({highest[column]:.1f} {label_map[stat_type_value]})"], className="mb-1 mt-2"),
        html.P([html.Strong("Lowest: "), f"{lowest['region']} ({lowest[column]:.1f} {label_map[stat_type_value]})"], className="mb-1"),
    ]


@app.callback(
    Output("ts-line-graph", "figure"),
    Input("ts-demographic-dropdown", "value"),
    Input("ts-type-dropdown", "value"),
    Input("ts-radio", "value"),
    Input("ts-year-slider", "value"),
)
def update_time_series(demographic, volunteer_type, show_type, year_range):
    d = trend_df[
        (trend_df["demographic"] == demographic) &
        (trend_df["vol_type"] == volunteer_type) &
        (trend_df["year"] >= year_range[0]) &
        (trend_df["year"] <= year_range[1])
    ]
    categories = d["category"].unique()
    SAFE = px.colors.qualitative.Safe
    fig = go.Figure()
    for i, cat in enumerate(sorted(categories)):
        subset = d[d["category"] == cat].sort_values("year")
        y_col  = "percentage" if show_type == "perc" else "count_1000"
        fig.add_scatter(
            x=subset["year"], y=subset[y_col],
            mode="lines+markers", name=cat_label(cat),
            line=dict(color=SAFE[i % len(SAFE)]),
        )
    y_label = ("Percentage of Volunteers" if show_type == "perc"
                else "Number of Volunteers (thousands)")
    fig.update_layout(
        title=f"Trends in Volunteering by {demo_label(demographic)} – {VOL_TYPE_DISPLAY.get(volunteer_type, volunteer_type)}",
        xaxis_title="Year", yaxis_title=y_label,
        legend_title=demo_label(demographic),
        margin=dict(t=60, l=20, r=20, b=20), height=450, template="plotly_white",
    )
    return fig


@app.callback(
    Output("mb-diverging-bar", "figure"),
    Input("mb-type-radio", "value"),
    Input("mb-gender-dropdown", "value"),
    Input("mb-year-dropdown", "value"),
)
def update_motiv_barrier_chart(type_choice, gender_choice, selected_year):
    df = mb_df[
        (mb_df["type"] == type_choice) &
        (mb_df["gender"] == gender_choice) &
        (mb_df["year"] == int(selected_year))
    ].copy()

    if df.empty:
        return go.Figure().update_layout(title=f"No data for {type_choice} in {selected_year}")

    df["label"] = df["item_id"].map(cat_label)
    df = df.sort_values("fully_agree", ascending=True)
    categories = df["label"]

    fig = go.Figure()
    fig.add_bar(x=-df["rather_disagree"], y=categories, orientation="h",
                name="Rather disagree", marker_color="#E8A87C")
    fig.add_bar(x=-df["not_at_all"], y=categories, orientation="h",
                name="Not at all", marker_color="#D55E00")
    fig.add_bar(x=df["rather_agree"], y=categories, orientation="h",
                name="Rather agree", marker_color="#88C9A1")
    fig.add_bar(x=df["fully_agree"], y=categories, orientation="h",
                name="Fully agree", marker_color="#009E73")

    fig.update_layout(
        barmode="relative",
        title=f"{type_choice.capitalize()} – {gender_choice.capitalize()} ({selected_year})",
        xaxis_title="Level of Agreement (%)", yaxis_title="",
        legend_title="Agreement Level",
        xaxis=dict(tickmode="array",
                   tickvals=[-100, -80, -60, -40, -20, 0, 20, 40, 60, 80, 100],
                   ticktext=[str(abs(v)) for v in [-100, -80, -60, -40, -20, 0, 20, 40, 60, 80, 100]]),
        height=600, template="plotly_white",
    )
    return fig


@app.callback(
    Output("activity-demographic-dropdown", "options"),
    Output("activity-demographic-dropdown", "value"),
    Input("activity-type-dropdown", "value"),
    Input("activity-year-dropdown", "value"),
    State("activity-demographic-dropdown", "value"),
)
def update_activity_demographics(vol_type, selected_year, current_value):
    df = formal_areas_df if vol_type == "formal" else informal_areas_df
    available = set(df[df["year"] == int(selected_year)]["demographic"].unique())

    UI_DEMOS = [
        ("Total", "all"),
        ("Gender", "gender"),
        ("Age", "age_group"),
        ("Education", "education"),
        ("Frequency of Volunteering", "freq_of_volunteering"),
    ]
    options = []
    for label, csv_demo in UI_DEMOS:
        if csv_demo in available:
            options.append({"label": label, "value": csv_demo})
        else:
            options.append({"label": f"{label} (not available in {selected_year})",
                            "value": csv_demo, "disabled": True})

    valid = [d for d in [current_value, "all", "gender"] if d in available]
    return options, (valid[0] if valid else list(available)[0])


@app.callback(
    Output("activity-stacked-bar", "figure"),
    Input("activity-type-dropdown", "value"),
    Input("activity-demographic-dropdown", "value"),
    Input("activity-display-mode", "value"),
    Input("activity-year-dropdown", "value"),
)
def update_activity_stacked_bar(vol_type, csv_demo, display_mode, selected_year):
    df = formal_areas_df if vol_type == "formal" else informal_areas_df
    d = df[df["year"] == int(selected_year)].copy()

    if csv_demo == "all":
        d = d[(d["demographic"] == "all") & (d["category"] == "all")]
    else:
        d = d[d["demographic"] == csv_demo]

    if d.empty:
        return px.bar(title="No data available for selected year and demographic.")

    if display_mode == "percent":
        if d["percentage"].notna().any():
            d["value"] = d["percentage"]
        else:
            total = df[(df["year"] == int(selected_year)) &
                       (df["demographic"] == "all")]["count_1000"].sum()
            d["value"] = (d["count_1000"] / total * 100) if total else d["count_1000"]
        y_title = "Percentage of Volunteers (%)"
    else:
        d["value"] = d["count_1000"]
        y_title = "Number of Volunteers (thousands)"

    d["area_label"] = d["area_id"].map(cat_label)
    d["cat_label"]  = d["category"].map(cat_label)
    demo_display = DEMOGRAPHIC_LABELS.get(csv_demo, csv_demo.capitalize())

    if csv_demo == "all":
        fig = px.bar(d, x="area_label", y="value", color_discrete_sequence=[px.colors.qualitative.Safe[0]],
                     labels={"area_label": "Area", "value": y_title},
                     title=f"{vol_type.capitalize()} Volunteering – Total ({selected_year})",
                     template="plotly_white")
    else:
        fig = px.bar(d, x="area_label", y="value", color="cat_label",
                     color_discrete_sequence=px.colors.qualitative.Safe,
                     labels={"area_label": "Area", "value": y_title, "cat_label": demo_display},
                     title=f"{vol_type.capitalize()} Volunteering by {demo_display} ({selected_year})",
                     template="plotly_white")

    fig.update_layout(barmode="stack", xaxis_tickangle=-45, height=500)
    return fig


@app.callback(
    Output("gender-dimension-select", "options"),
    Output("gender-dimension-select", "value"),
    Input("gender-type-select", "value"),
    Input("gender-year-select", "value"),
    State("gender-dimension-select", "value"),
)
def update_dimension_options(vol_type, selected_year, current_dim):
    filters    = get_available_filters("gender_comparison", int(selected_year))
    avail_dims = filters.get("dimensions", {}).get(vol_type, [])

    all_possible = {
        "Formal":   ["Formal_NumberOfOrgs", "Formal_TaskTypes", "Formal_Areas", "Formal_Time/week"],
        "Informal": ["Informal_Areas", "Informal_Time/week"],
    }.get(vol_type, [])

    options = [
        {"label": DIM_LABELS.get(dim_id, dim_id), "value": dim_id}
        for dim_id in all_possible
        if dim_id in avail_dims
    ]

    default = avail_dims[0] if avail_dims else ""
    value   = current_dim if current_dim in avail_dims else default
    return options, value


@app.callback(
    Output("gender-comparison-bar", "figure"),
    Output("gender-comparison-table", "children"),
    Output("gender-live-summary", "children"),
    Input("gender-type-select", "value"),
    Input("gender-dimension-select", "value"),
    Input("gender-display-mode", "value"),
    Input("gender-year-select", "value"),
)
def update_gender_comparison(vol_type, dimension, display_mode, selected_year):
    _no_table = None

    if not dimension:
        return px.bar(title="Please select a dimension."), _no_table, "Please select a dimension."

    filters     = get_available_filters("gender_comparison", int(selected_year))
    unavail_ids = {item["id"] for item in filters.get("unavailable_dimensions", [])}
    if dimension in unavail_ids:
        msg = f"{dimension} is not available for {selected_year}."
        return (
            go.Figure().update_layout(
                title=f"{dimension} is not available for {selected_year}",
                annotations=[dict(text="This dimension was not published in the "
                                  f"{selected_year} survey release.",
                                  xref="paper", yref="paper", x=0.5, y=0.5,
                                  showarrow=False, font=dict(size=14))],
            ),
            _no_table,
            msg,
        )

    d = gender_comp_df[
        (gender_comp_df["year"] == int(selected_year)) &
        (gender_comp_df["vol_type"] == vol_type) &
        (gender_comp_df["dimension"] == dimension)
    ].copy()

    if d.empty:
        return px.bar(title="No data for selected filters."), _no_table, "No data for selected filters."

    d["cat_label"] = d["category"].map(cat_label)

    col_m  = "men_count"  if display_mode == "count" else "men_perc"
    col_w  = "women_count" if display_mode == "count" else "women_perc"
    unit   = "k"           if display_mode == "count" else "%"
    hdr_m  = f"Men ({unit})"
    hdr_w  = f"Women ({unit})"

    dim_display = DIM_LABELS.get(dimension, dimension)

    # ── aria-live summary ──────────────────────────────────────────────────────
    d_s         = d.copy()
    d_s["diff"] = d_s[col_m] - d_s[col_w]
    men_lead    = d_s[d_s["diff"] > 0].sort_values("diff", ascending=False)
    women_lead  = d_s[d_s["diff"] < 0].sort_values("diff")
    parts = [f"{vol_type} Volunteering – {dim_display} ({selected_year})."]
    if not men_lead.empty:
        r = men_lead.iloc[0]
        parts.append(f"Men lead most in {r['cat_label']} ({r[col_m]:.1f}{unit}).")
    if not women_lead.empty:
        r = women_lead.iloc[0]
        parts.append(f"Women lead most in {r['cat_label']} ({r[col_w]:.1f}{unit}).")
    if men_lead.empty and women_lead.empty:
        parts.append("No gender differences observed.")
    parts.append(f"Data table below shows all {len(d)} categories.")
    summary = " ".join(parts)

    # ── accessible html table ─────────────────────────────────────────────────
    # aria-label on the table itself names it without duplicating the live summary.
    # The wrapper div (in layout) says "region"; the table says what it contains.
    # No <caption> — the live summary already announces the current context.
    table = [
        html.Caption(f"{vol_type} Volunteering – {dim_display} ({selected_year}) ", className="visually-hidden"),
        html.Table([
            html.Thead(html.Tr([
                html.Th(dim_display, scope="col"),
                html.Th(hdr_m, scope="col"),
                html.Th(hdr_w, scope="col"),
            ])),
            html.Tbody([
                html.Tr([
                    html.Th(row["cat_label"],scope="row"),
                    html.Td(f"{row[col_m]:.1f}"),
                    html.Td(f"{row[col_w]:.1f}"),
                ]) for _, row in d.iterrows() 
            ]),
        ],
        className="table table-bordered table-hover table-sm mt-2"
       ## ,**{"aria-label": f"{vol_type} Volunteering – {dim_display} ({selected_year})"}
       ),
    ]

    # ── chart ─────────────────────────────────────────────────────────────────
    if display_mode == "count":
        df_long = pd.melt(d, id_vars=["cat_label"],
                          value_vars=["men_count", "women_count"],
                          var_name="Gender", value_name="Value")
        y_label = "Number of Volunteers (thousands)"
    else:
        df_long = pd.melt(d, id_vars=["cat_label"],
                          value_vars=["men_perc", "women_perc"],
                          var_name="Gender", value_name="Value")
        y_label = "Percentage of Volunteers (%)"

    df_long["Gender"] = df_long["Gender"].replace({
        "men_count": "Men", "women_count": "Women",
        "men_perc":  "Men", "women_perc":  "Women",
    })

    fig = px.bar(df_long, x="cat_label", y="Value", color="Gender",
                 barmode="group",
                 labels={"cat_label": dim_display, "Value": y_label},
                 color_discrete_map={"Men": "#0072B2", "Women": "#D55E00"})
    fig.update_layout(
        title=f"{vol_type} Volunteering – {dim_display} ({selected_year})",
        yaxis_title=y_label, xaxis_title="",
        template="plotly_white", height=500,
    )
    return fig, table, summary


@app.callback(
    Output("errorBar-demographic-dropdown", "options"),
    Output("errorBar-demographic-dropdown", "value"),
    Input("errorBar-year-dropdown", "value"),
    State("errorBar-demographic-dropdown", "value"),
)
def update_errorbar_demographics(selected_year, current_value):
    d = time_dist_df[time_dist_df["year"] == int(selected_year)]
    available = set(d["demographic"].unique())

    UI_DEMOS = [
        ("Total", "total"),
        ("Gender", "gender"),
        ("Age", "age_group"),
        ("Education", "education"),
        ("Migration Background", "migration_background"),
        ("Employment", "employment"),
        ("Municipality Size", "municipality_size"),
        ("Region", "region"),
        ("Task Type", "task_type"),
    ]
    options = []
    for label, csv_demo in UI_DEMOS:
        if csv_demo in available:
            options.append({"label": label, "value": csv_demo})
        else:
            options.append({"label": f"{label} (not available in {selected_year})",
                            "value": csv_demo, "disabled": True})

    valid = [d for d in [current_value, "total", "gender"] if d in available]
    return options, (valid[0] if valid else list(available)[0])


@app.callback(
    Output("errorBar-figure", "figure"),
    Input("errorBar-voltype-dropdown", "value"),
    Input("errorBar-demographic-dropdown", "value"),
    Input("errorBar-year-dropdown", "value"),
)
def update_errorBar(vol_type, demographic, selected_year):
    d = time_dist_df[
        (time_dist_df["year"] == int(selected_year)) &
        (time_dist_df["demographic"] == demographic) &
        (time_dist_df["vol_type"] == vol_type)
    ].copy()

    if d.empty:
        return go.Figure().update_layout(
            title=f"No data for {demo_label(demographic)} in {selected_year}")

    d["cat_label"] = d["category"].map(cat_label)
    color_list = pc.qualitative.Safe
    colors = color_list * (len(d) // len(color_list) + 1)

    fig = go.Figure()
    for i, (_, row) in enumerate(d.iterrows()):
        p25 = row["p25"]
        p50 = row["p50"]
        p75 = row["p75"]
        avg = row["avg_hours"]
        lbl = row["cat_label"]
        fig.add_trace(go.Bar(
            x=[lbl], y=[p50],
            error_y=dict(type="data", symmetric=False,
                         array=[p75 - p50], arrayminus=[p50 - p25],
                         thickness=2, width=8, color="rgba(0,0,0,0.5)"),
            name=lbl, marker_color=colors[i],
            hovertemplate=f"<b>{lbl}</b><br>Q3: {p75}<br>Median: {p50}<br>Q1: {p25}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[lbl], y=[avg], mode="markers",
            marker=dict(color="black", size=10, symbol="diamond"),
            name=f"Mean ({lbl})",
            hovertemplate=f"<b>{lbl}</b><br>Mean: {avg}<extra></extra>",
            showlegend=True,
        ))

    fig.update_layout(
        title=f"Volunteer Hours/Week – {VOL_TYPE_DISPLAY.get(vol_type, vol_type)} – "
              f"{demo_label(demographic)} ({selected_year})",
        yaxis_title="Hours per Week",
        xaxis_title=demo_label(demographic) if demographic != "total" else "",
        barmode="group", template="plotly_white", height=500,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.05, title="Legend"),
    )
    return fig


@app.callback(
    Output("ts2-category-dropdown", "options"),
    Output("ts2-category-dropdown", "value"),
    Input("ts2-demographic-dropdown", "value"),
)
def update_ts2_categories(demographic):
    if not demographic:
        return [], ""
    cats = sorted(trend_df[trend_df["demographic"] == demographic]["category"].unique())
    options = [{"label": cat_label(c), "value": c} for c in cats]
    return options, (cats[0] if cats else "")


@app.callback(
    Output("ts2-line-graph", "figure"),
    Input("ts2-demographic-dropdown", "value"),
    Input("ts2-category-dropdown", "value"),
    Input("ts2-radio", "value"),
    Input("ts2-year-slider", "value"),
)
def update_ts2_graph(demographic, category, display_mode, year_range):
    if not demographic or not category:
        return px.line(title="No data available.")

    d = trend_df[
        (trend_df["demographic"] == demographic) &
        (trend_df["category"] == category) &
        (trend_df["year"] >= year_range[0]) &
        (trend_df["year"] <= year_range[1])
    ]

    vol_types = sorted(d["vol_type"].unique())

    SAFE = px.colors.qualitative.Safe

    vol_types = sorted(d["vol_type"].unique())
    fig = go.Figure()
    for i, vt in enumerate(vol_types):
        subset = d[d["vol_type"] == vt].sort_values("year")
        y_col = "percentage" if display_mode == "perc" else "count_1000"
        fig.add_scatter(
            x=subset["year"], y=subset[y_col],
            mode="lines+markers",
            name=VOL_TYPE_DISPLAY.get(vt, vt.replace("_", " ").capitalize()),
            line=dict(color=SAFE[i % len(SAFE)]),
        )

    y_label = ("Percentage of Volunteers" if display_mode == "perc"
                else "Number of Volunteers (thousands)")
    fig.update_layout(
        title=f"Volunteering Type Comparison – {cat_label(category)} ({demo_label(demographic)})",
        xaxis_title="Year", yaxis_title=y_label,
        legend_title="Type of Volunteering",
        height=500, template="plotly_white",
    )
    return fig


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
