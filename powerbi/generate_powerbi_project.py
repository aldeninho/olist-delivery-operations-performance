"""Generate the Olist Delivery Operations Power BI project (PbixProj format).

Usage: python powerbi/generate_powerbi_project.py
Produces powerbi/olist_delivery_operations/ ready to be compiled with pbi-tools.
"""
import json
import os
import shutil

ROOT = r"C:\Users\Asus\OneDrive\Documents\2nd data analayst project"
OUT = os.path.join(ROOT, "powerbi", "olist_delivery_operations")
DATA = os.path.join(ROOT, "data", "processed").replace("\\", "/")
TEMPLATE = os.path.join(os.environ["LOCALAPPDATA"], "Temp", "opencode", "adventureworksdw2020-pbix", "pbix")

FACT_ORDERS_COLUMNS = [
    ("order_id", "text", "text"),
    ("order_status", "text", "text"),
    ("order_purchase_timestamp", "datetime", "datetime"),
    ("order_approved_at", "datetime", "datetime"),
    ("order_delivered_carrier_date", "datetime", "datetime"),
    ("order_delivered_customer_date", "datetime", "datetime"),
    ("order_estimated_delivery_date", "datetime", "datetime"),
    ("purchase_month", "text", "text"),
    ("customer_city", "text", "text"),
    ("customer_state", "text", "text"),
    ("order_value_brl", "number", "number"),
    ("freight_cost_brl", "number", "number"),
    ("item_count", "number", "number"),
    ("seller_count", "number", "number"),
    ("primary_category", "text", "text"),
    ("review_score", "number", "number"),
    ("delivery_days", "number", "number"),
    ("estimated_delivery_days", "number", "number"),
    ("late_delivery_days", "number", "number"),
    ("sla_breach", "text", "text"),
    ("data_quality_flag", "text", "text"),
]

SELLER_COLUMNS = [
    ("seller_id", "text", "text"),
    ("total_orders", "Int64.Type", "int64"),
    ("delivered_orders", "Int64.Type", "int64"),
    ("cancelled_orders", "Int64.Type", "int64"),
    ("on_time_delivery_pct", "type number", "number"),
    ("sla_breach_pct", "type number", "number"),
    ("avg_delivery_days", "type number", "number"),
    ("freight_cost_per_delivered_order_brl", "type number", "number"),
    ("avg_review_score", "type number", "number"),
]

SEGMENTS_COLUMNS = [
    ("segment_type", "text", "text"),
    ("segment", "text", "text"),
    ("delivered_orders", "Int64.Type", "int64"),
    ("late_orders", "Int64.Type", "int64"),
    ("avg_late_days", "type number", "number"),
    ("avg_freight_brl", "type number", "number"),
    ("late_delivery_rate", "type number", "number"),
    ("excess_late_orders_vs_baseline", "type number", "number"),
]

FACT_MEASURES = [
    ("Total Orders", "COUNTROWS('Fact Orders')", "0"),
    ("Delivered Orders", "CALCULATE([Total Orders], 'Fact Orders'[order_status] = \"delivered\")", "0"),
    ("Cancelled Orders", "CALCULATE([Total Orders], 'Fact Orders'[order_status] = \"canceled\")", "0"),
    ("Cancellation Rate", "DIVIDE([Cancelled Orders], [Total Orders])", "0.0%"),
    ("On-Time Deliveries", "CALCULATE([Delivered Orders], 'Fact Orders'[sla_breach] = \"No\")", "0"),
    ("On-Time Delivery %", "DIVIDE([On-Time Deliveries], [Delivered Orders])", "0.0%"),
    ("SLA Breaches", "CALCULATE([Delivered Orders], 'Fact Orders'[sla_breach] = \"Yes\")", "0"),
    ("SLA Breach Rate", "DIVIDE([SLA Breaches], [Delivered Orders])", "0.0%"),
    ("Average Delivery Days", "AVERAGEX(FILTER('Fact Orders', 'Fact Orders'[order_status] = \"delivered\"), 'Fact Orders'[delivery_days])", "0.0"),
    ("Freight Cost per Delivered Order", "DIVIDE(CALCULATE(SUM('Fact Orders'[freight_cost_brl]), 'Fact Orders'[order_status] = \"delivered\"), [Delivered Orders])", "0.00"),
]

SELLER_MEASURES = [
    ("Total Seller Orders", "SUM('Seller Performance'[total_orders])", "0"),
    ("Seller On-Time Rate", "AVERAGE('Seller Performance'[on_time_delivery_pct])", "0.0%"),
    ("Seller SLA Breach Rate", "AVERAGE('Seller Performance'[sla_breach_pct])", "0.0%"),
    ("Seller Avg Delivery Days", "AVERAGE('Seller Performance'[avg_delivery_days])", "0.0"),
    ("Seller Avg Review Score", "AVERAGE('Seller Performance'[avg_review_score])", "0.00"),
]


def column_tmdl(name, ttype, infer, indent="\t"):
    lines = [f"{indent}column {q(name)}", f"{indent}\tdataType: {ttype}", f"{indent}\tsummarizeBy: {'sum' if ttype != 'text' else 'none'}"]
    if ttype == "text":
        lines[2] = f"{indent}\tsummarizeBy: none"
    lines.append(f"{indent}\tsourceColumn: {name}")
    lines.append(f"{indent}\tannotation SummarizationSetBy = Automatic")
    lines.append("")
    return "\n".join(lines)


def q(name):
    if " " in name or name[:1].isdigit():
        return f"'{name}'"
    return name


def m_partition(csv_name, columns, extra_add_columns=None):
    tcols = ", ".join('{"%s", %s}' % (c[0], "Text.Type" if c[2] == "text" else ('Int64.Type' if c[2] == "int64" else ('type datetime' if c[2] == "datetime" else "type number"))) if False else '{"' + c[0] + '", ' + ('type text' if c[2] == 'text' else (c[1] if c[1].startswith('Int64') or c[1] == 'type number' or c[1] == 'type text' or c[1] == 'datetime' or c[1] == 'number' else c[1])) + '}' for c in columns)
    tcols = ", ".join('{"' + c[0] + '", ' + column_type_m(c) + '}' for c in columns)
    rows = [
        "\tpartition default = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        f'\t\t\t\t    Source = Csv.Document(File.Contents("{DATA}/{csv_name}"),[Delimiter=",", Columns={len(columns)}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        '\t\t\t\t    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
        f'\t\t\t\t    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{{tcols}}})' + (',' if extra_add_columns else ''),
    ]
    if extra_add_columns:
        for expr, newcol in extra_add_columns:
            rows.append(f'\t\t\t\t    #"Added {newcol}" = Table.AddColumn(#"Changed Type", "{newcol}", each {expr}, type number)')
        rows.append("\t\t\t\tin")
        rows.append('\t\t\t\t    #"Added ' + extra_add_columns[-1][1] + '"')
    else:
        rows.append("\t\t\t\tin")
        rows.append('\t\t\t\t    #"Changed Type"')
    rows.append("")
    rows.append("\tannotation PBI_ResultType = Table")
    return "\n".join(rows) + "\n"


def column_type_m(c):
    t = c[2]
    if t == "text":
        return "type text"
    if t == "int64":
        return "Int64.Type"
    if t == "datetime":
        return "type datetime"
    return "type number"


def write_table(path, table_name, columns, csv_name, measures, extra_add_columns=None, datetime_cols_unused=None):
    lines = [f"table {q(table_name)}", ""]
    for name, mtype, ttype in columns:
        d = ttype if ttype != "number" else "double"
        d = "double" if ttype == "number" else ("int64" if ttype == "int64" else ("dateTime" if ttype == "datetime" else "string"))
        lines.append(f"\tcolumn {q(name)}")
        lines.append(f"\t\tdataType: {d}")
        if d in ("double", "int64"):
            lines.append("\t\tsummarizeBy: sum")
        else:
            lines.append("\t\tsummarizeBy: none")
        lines.append(f"\t\tsourceColumn: {name}")
        lines.append("\t\tannotation SummarizationSetBy = Automatic")
        lines.append("")
    if extra_add_columns:
        # add the bucket column mapping to the M-added column
        new_cols = extra_add_columns
        lines.append("\tcolumn delivery_days_bucket")
        lines.append("\t\tdataType: double")
        lines.append("\t\tsummarizeBy: none")
        lines.append("\t\tsourceColumn: delivery_days_bucket")
        lines.append("\t\tannotation SummarizationSetBy = Automatic")
        lines.append("")
    lines.append(m_partition(csv_name, columns, extra_add_columns=extra_add_columns))
    for name, expr, fmt in measures:
        lines.append(f"\tmeasure {q(name)} = {expr}")
        lines.append(f"\t\tformatString: {fmt}")
        lines.append(f"\t\tannotation PBI_FormatHint = {{\"$$$\"}}".replace('{"$$$"}', "{}"))
        lines.pop()
        lines.append("")
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, f"{table_name}.tmdl"), "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines))


FACT_COLS_MAPPED = [(c[0], column_type_m(c) if False else c[2], c[2]) for c in FACT_ORDERS_COLUMNS]


def build_model():
    model_dir = os.path.join(OUT, "Model")
    os.makedirs(os.path.join(model_dir, "tables"), exist_ok=True)
    os.makedirs(os.path.join(model_dir, "cultures"), exist_ok=True)
    shutil.copy(os.path.join(TEMPLATE, "Model", "cultures", "en-US.tmdl"), os.path.join(model_dir, "cultures", "en-US.tmdl"))
    # database.tmdl
    with open(os.path.join(model_dir, "database.tmdl"), "w", encoding="utf-8", newline="") as f:
        f.write("database 'Olist Delivery Operations'\n\tcompatibilityLevel: 1550\n")
    # model.tmdl
    with open(os.path.join(model_dir, "model.tmdl"), "w", encoding="utf-8", newline="") as f:
        f.write(
            "model Model\n"
            "\tculture: en-US\n"
            "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
            "\tsourceQueryCulture: en-US\n"
            "\tdataAccessOptions\n"
            "\t\tlegacyRedirects\n"
            "\t\treturnErrorValuesAsNull\n"
            "\n"
            "annotation __PBI_TimeIntelligenceEnabled = 0\n"
            "annotation PBIDesktopVersion = 2.158.1177.0 (26.09)\n"
            'annotation PBI_QueryOrder = ["Fact Orders", "Vendor Performance", "Priority Segments"]\n\n'
            "ref table 'Fact Orders'\n"
            "ref table 'Vendor Performance'\n"
            "ref table 'Priority Segments'\n"
        )
    # tables
    write_table(
        os.path.join(model_dir, "tables"),
        "Fact Orders",
        FACT_ORDERS_COLUMNS,
        "fact_orders.csv",
        FACT_MEASURES,
        extra_add_columns=[('try Number.Floor([delivery_days]/5)*5 otherwise null', "delivery_days_bucket")],
    )
    write_table(os.path.join(model_dir, "tables"), "Seller Performance", SELLER_COLUMNS, "seller_performance.csv", SELLER_MEASURES)
    write_table(os.path.join(model_dir, "tables"), "Priority Segments", SEGMENTS_COLUMNS, "priority_segments.csv", [])


# ---------- Report JSON builders ----------

def query_ref(table, member, is_measure):
    return f"{table}.{member}"


def select_for(table, alias, member, is_measure, col_type=None):
    if is_measure:
        return {"Measure": {"Expression": {"SourceRef": {"Source": alias}}, "Property": member}, "Name": f"{table}.{member}"}
    return {"Column": {"Expression": {"SourceRef": {"Source": alias}}, "Property": member}, "Name": f"{table}.{member}"}


def alias_for(table):
    return "f" if table.startswith("Fact") else ("v" if table.startswith("Vendor") else "p")


def make_query(table, members):
    """members: list of (member, is_measure). Returns prototypeQuery and query.json bodies."""
    alias = alias_for(table)
    selects = [select_for(table, alias, m, is_m) for m, is_m in members]
    pq = {
        "Version": 2,
        "From": [{"Name": alias, "Entity": table, "Type": 0}],
        "Select": selects,
    }
    query = {
        "Commands": [
            {
                "SemanticQueryDataShapeCommand": {
                    "Query": {
                        "Version": 2,
                        "From": [{"Name": alias, "Entity": table, "Type": 0}],
                        "Select": selects,
                    },
                    "Binding": {
                        "Primary": {"Groupings": [{"Projections": list(range(len(members)))}]},
                        "DataReduction": {"DataVolume": 4, "Primary": {"Window": {"Count": 1000}}},
                        "Version": 1,
                    },
                }
            }
        ]
    }
    return pq, query


def make_projections(members):
    out = {}
    for i, (m, is_m, role) in enumerate(members):
        out.setdefault(role, []).append({"queryRef": m[0], "active": True} if False else {"queryRef": m[0]} )
    return out


def visual_json(name, vtype, entity_table, members, position, title=None, extra_objects=None, projection_roles=None, display=None):
    role_map = projection_roles or {}
    projections = {}
    for role in role_map:
        projections[role] = []
    # members entries: (ref, table, member, is_measure, role)
    for ref, table, member, is_m, role in members:
        projections.setdefault(role, []).append({"queryRef": ref})
    pq, query = make_query(entity_table, [(m, is_m) for _, _, m, is_m, _ in members])
    single = {
        "visualType": vtype,
        "projections": projections,
        "prototypeQuery": pq,
        "drillFilterOtherVisuals": True,
    }
    if display:
        single["display"] = display
    vc = {}
    if title:
        vc["title"] = [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "text": {"expr": {"Literal": {"Value": f"'{title}'"}}}}}]
        single["vcObjects"] = vc
    if extra_objects:
        single["objects"] = extra_objects
    return {
        "name": name,
        "layouts": [{"id": 0, "position": position}],
        "singleVisual": single,
    }, query


def textbox_json(name, x, y, w, h, paragraphs):
    return {
        "name": name,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 1000, "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "textbox",
            "drillFilterOtherVisuals": True,
            "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": [r if isinstance(r, dict) else {"value": r} for r in para]} for para in paragraphs]}}]},
        },
    }


def slicer_json(name, table, member, position):
    alias = alias_for(table)
    proto = {
        "Version": 2,
        "From": [{"Name": alias, "Entity": table, "Type": 0}],
        "Select": [select_for(table, alias, member, False)],
    }
    return {
        "name": name,
        "layouts": [{"id": 0, "position": position}],
        "singleVisual": {
            "visualType": "slicer",
            "projections": {"Values": [{"queryRef": f"{table}.{member}"}]},
            "prototypeQuery": proto,
            "display": {"mode": "hidden"},
            "drillFilterOtherVisuals": True,
            "objects": {"data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Basic'"}}}}}]},
        },
    }


def aligned(meas_refs, table, alias):
    return [(f"{table}.{m}", table, m, True, "Y") for m, _ in meas_refs]


def col_ref(table, member):
    return (f"{table}.{member}", table, member, False, "Category")


def build_report():
    sections_dir = os.path.join(OUT, "Report", "sections")
    # clean sections dir
    for d in os.listdir(sections_dir):
        shutil.rmtree(os.path.join(sections_dir, d), ignore_errors=True)
    pages = []

    # ---- Page 1 geometry (canvas 1280x720) ----
    p1_sections = {"visuals": []}
    visuals = []
    yellow_cards = [
        ("Total Orders", "Total Orders"),
        ("On-Time Delivery %", "On-Time Delivery %"),
        ("Average Delivery Days", "Average Delivery Days"),
        ("SLA Breach Rate", "SLA Breach Rate"),
        ("Cancellation Rate", "Cancellation Rate"),
        ("Freight Cost per Delivered Order", "Freight Cost per Delivered Order"),
    ]
    for i, (label, measure) in enumerate(yellow_cards):
        x = 40 + (i % 6) * 200
        visuals.append(card(f"{'P1C'+str(i)}", 40 + (i % 3) * 200, 140 + (i // 3) * 110, 185, 100, "Fact Orders", measure, label))
    line_members = [col_ref("Fact Orders", "purchase_month"), cmember if False else None]
    line_members = [col_ref("Fact Orders", "purchase_month"), meas("Fact Orders", "On-Time Delivery %")]
    visuals.append(data_visual("lineChart", "P1Monthly", 40, 420, 760, 260, "Fact Orders", line_members, title="Monthly On-Time Delivery %"))
    seller_members = [col_ref("Seller Performance", "seller_id"), meas("Seller Performance", "Seller On-Time Rate")]
    visuals.append(data_visual("clusteredBarChart", "P1Seller", 830, 420, 420, 260, "Seller Performance", seller_members, title="Seller On-Time Rate"))
    visuals.append(textbox_visual("P1Title", 40, 40, 900, 70, f"Olist Delivery Operations Performance", size=28, bold=True))
    visuals.append(textbox_visual("P1Reco", 40, 375 - 372 if False else 80, 500, 60, "Actions: investigate late routes in RJ, review carrier handoffs, audit freight anomalies.", size=12))
    pages.append(("Executive Overview", "Executive Overview", visuals))

    # ---- Page 2 ----
    visuals = []
    l2 = [
        data_visual("clusteredColumnChart", "P2State", 40, 100, 480, 280, "Fact Orders", [col_ref("Fact Orders", "customer_state"), meas("Fact Orders", "SLA Breach Rate")], title="SLA Breach Rate by Customer State"),
        data_visual("clusteredBarChart", "P2Seller", 560, 100, 460, 280, "Seller Performance", [col_ref("Seller Performance", "seller_id"), meas("Seller Performance", "Seller SLA Breach Rate")], title="SLA Breach Rate by Seller"),
        data_visual("columnChart", "P2Dist", 1060, 100, 200 if False else 200, 280, "Fact Orders", [col_ref("Fact Orders", "delivery_days_bucket"), meas("Fact Orders", "Total Orders")], title="Delivery-Day Distribution"),
    ]
    for x0, y0, w, h, vis in [(40, 100, 480, 280, None)]:
        pass
    visuals = l2
    visuals.append(slicer_visual("P2SliceMonth", "Fact Orders", "purchase_month", 40, 410, 250, 60, title="Month"))
    visuals.append(slicer_visual("P2SliceState", "Fact Orders", "customer_state", 300, 410, 250, 60, title="Customer state"))
    visuals.append(slicer_visual("P2SliceSeller", "Seller Performance", "seller_id", 560, 410, 250, 60, title="Seller"))
    visuals.append(slicer_visual("P2SliceCat", "Fact Orders", "primary_category", 820, 410, 250, 60, title="Category"))
    visuals.append(textbox_visual("P2Title", 40, 40, 900, 70, "Delivery & SLA", size=28, bold=True))
    pages.append(("Delivery & SLA", "Delivery and SLA", visuals))

    # ---- Page 3 ----
    visuals = []
    visuals.append(data_visual("clusteredBarChart", "P3StateFreight", 40, 100, 400, 260, "Fact Orders", [col_ref("Fact Orders", "customer_state"), meas("Fact Orders", "Freight Cost per Delivered Order")], title="Freight Cost per Delivered Order by Customer State"))
    visuals.append(data_visual("clusteredColumnChart", "P3CatFreight", 480, 100, 380, 260, "Fact Orders", [col_ref("Fact Orders", "primary_category"), meas("Fact Orders", "Freight Cost per Delivered Order")], title="Freight Cost per Delivered Order by Category"))
    visuals.append(data_visual("lineChart", "P3Cancelled", 900, 100, 360, 260, "Fact Orders", [col_ref("Fact Orders", "purchase_month"), meas("Fact Orders", "Cancellation Rate")], title="Cancellation Rate Trend"))
    visuals.append(table_visual("P3Segments", 40, 390, 700, 300, "Priority Segments", ["segment_type", "segment", "delivered_orders", "late_orders", "late_delivery_rate"]))
    visuals.append(textbox_visual("P3Title", 40, 40, 900, 70, "Freight & Delivery Priorities", size=28, bold=True))
    pages.append(("Freight & Priorities", "Freight & Priorities", visuals))

    sections_dir = os.path.join(OUT, "Report", "sections")
    os.makedirs(sections_dir, exist_ok=True)
    for d in list(os.listdir(sections_dir)):
        shutil.rmtree(os.path.join(sections_dir, d), ignore_errors=True)
    config = json.load(open(os.path.join(TEMPLATE, "Report", "config.json")))
    for idx, (display, folder, visuals) in enumerate(pages):
        sdir = os.path.join(sections_dir, folder)
        vdir = os.path.join(sdir, "visualContainers")
        os.makedirs(vdir, exist_ok=True)
        with open(os.path.join(sdir, "section.json"), "w", encoding="utf-8") as f:
            json.dump({"displayName": display, "displayOption": 1, "height": 720, "name": folder, "ordinal": idx, "width": 1280}, f, indent=2)
        with open(os.path.join(sdir, "config.json"), "w", encoding="utf-8") as f:
            json.dump({}, f)
        with open(os.path.join(sdir, "filters.json"), "w", encoding="utf-8") as f:
            json.dump([], f)
        for vis in visuals:
            name, files = vis
            vdir_i = os.path.join(vdir, name)
            os.makedirs(vdir_i, exist_ok=True)
            for fname, payload in files.items():
                with open(os.path.join(vdir_i, fname), "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)


# small visual builders producing (foldername, {filename: payload})
COUNTER = [0]
def fresh_id(prefix):
    import uuid
    return uuid.uuid5(uuid.NAMESPACE_DNS, prefix).hex[:20]


def meas(table, member):
    return (f"{table}.{member}", table, member, True, "Y")


def card(name, x, y, w, h, table, member, title):
    conf, query = data_visual_raw("card", name, x, y, w, h, table, [meas(table, member)], title=title, single_role="Values")
    files = {}
    for f in ["config.json", "filters.json", "visualContainer.json", "query.json", "dataTransforms.json"]:
        pass
    return (name, {"config.json": conf, "filters.json": [], "visualContainer.json": vc_json(x, y, w, h), "query.json": query, "dataTransforms.json": datatransform("card")})


def data_visual(vtype, name, x, y, w, h, table, members, title=None):
    conf, query = data_visual_raw(vtype, name, x, y, w, h, table, members, title=title)
    return (name, {"config.json": conf, "filters.json": [], "visualContainer.json": vc_json(x, y, w, h), "query.json": query, "dataTransforms.json": datatransform(vtype)})


def data_visual_raw(vtype, name, x, y, w, h, table, members, title=None, single_role=None):
    role_members = []
    for (ref, t, m, is_m, role) in members:
        is_tabular = vtype in ("card", "tableEx", "slicer")
        if is_tabular:
            projections_role = "Values"
        elif role == "Category":
            projections_role = "Category"
        else:
            projections_role = role
        role_members.append((ref, t, m, is_m, projections_role))
    projections = {}
    for ref, t, m, is_m, role in role_members:
        projections.setdefault(role, []).append({"queryRef": ref})
    alias = alias_for(table)
    selects = [select_for(table, alias, m, is_m) for _, _, m, is_m, _ in members]
    pq = {"Version": 2, "From": [{"Name": alias, "Entity": table, "Type": 0}], "Select": selects}
    query = {
        "Commands": [
            {
                "SemanticQueryDataShapeCommand": {
                    "Query": {
                        "Version": 2,
                        "From": [{"Name": alias, "Entity": table, "Type": 0}],
                        "Select": selects,
                    },
                    "Binding": {
                        "Primary": {"Groupings": [{"Projections": list(range(len(members)))}]},
                        "DataReduction": {"DataVolume": 4, "Primary": {"Window": {"Count": 1000}}},
                        "Version": 1,
                    },
                }
            }
        ]
    }
    single = {
        "visualType": vtype,
        "projections": projections,
        "prototypeQuery": pq,
        "drillFilterOtherVisuals": True,
    }
    vc = {}
    if title:
        vc["title"] = [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "text": {"expr": {"Literal": {"Value": f"'{title}'"}}}}}]
    return (
        {
            "name": name,
            "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 1000, "width": w, "height": h}}],
            "singleVisual": {**single, "vcObjects": vc},
        },
        query,
    )


def vc_json(x, y, w, h):
    return {"height": h, "width": w, "x": x, "y": y, "z": 1000}


def datatransform(vtype):
    if vtype in ("clusteredColumnChart", "columnChart", "clusteredBarChart", "barChart", "lineChart", "stackedAreaChart", "areaChart"):
        return {"objects": {"categoryAxis": [{"properties": {}}], "valueAxis": [{"properties": {}}]}}
    return {"objects": {}}


def textbox_visual(name, x, y, w, h, text, size=14, bold=False):
    fs = {"fontSize": f"{size}pt"}
    if bold:
        fs["fontWeight"] = "bold"
    para = [{"textRuns": [{"value": text, "textStyle": fs}]}]
    conf = {
        "name": name,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 1000, "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "textbox",
            "drillFilterOtherVisuals": True,
            "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": [{"value": text, "textStyle": fs}]}]}}]},
        },
    }
    return (name, {"config.json": conf, "filters.json": [], "visualContainer.json": vc_json(x, y, w, h)})


def slicer_visual(name, table, member, x, y, w, h, title=None):
    alias = alias_for(table)
    proto = {"Version": 2, "From": [{"Name": alias, "Entity": table, "Type": 0}], "Select": [select_for(table, alias, member, False)]}
    objects = {"data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Basic'"}}}}}]}
    conf = {
        "name": name,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 1000, "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "slicer",
            "projections": {"Values": [{"queryRef": f"{table}.{member}"}]},
            "prototypeQuery": proto,
            "display": {"mode": "hidden"},
            "drillFilterOtherVisuals": True,
            "objects": objects,
        },
    }
    if title:
        conf["singleVisual"]["vcObjects"] = {"title": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "text": {"expr": {"Literal": {"Value": f"'{title}'"}}}}}]}
    return (name, {"config.json": conf, "filters.json": [], "visualContainer.json": vc_json(x, y, w, h)})


def table_visual(name, x, y, w, h, table, members_cols):
    alias = alias_for(table)
    selects = [select_for(table, alias, m, False) for m in members_cols]
    pq = {"Version": 2, "From": [{"Name": alias, "Entity": table, "Type": 0}], "Select": selects}
    query = {"Commands": [{"SemanticQueryDataShapeCommand": {"Query": {"Version": 2, "From": [{"Name": alias, "Entity": table, "Type": 0}], "Select": selects}, "Binding": {"Primary": {"Groupings": [{"Projections": list(range(len(members_cols)))}]}, "DataReduction": {"DataVolume": 4, "Primary": {"Window": {"Count": 1000}}}, "Version": 1}}}]}
    conf = {
        "name": name,
        "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 1000, "width": w, "height": h}}],
        "singleVisual": {
            "visualType": "tableEx",
            "projections": {"Values": [{"queryRef": f"{table}.{m}"} for m in members_cols]},
            "prototypeQuery": pq,
            "drillFilterOtherVisuals": True,
        },
    }
    return (name, {"config.json": conf, "filters.json": [], "visualContainer.json": vc_json(x, y, w, h), "query.json": query})


def data_visual(vtype, name, x, y, w, h, table, members, title=None):
    conf, query = data_visual_raw(vtype, name, x, y, w, h, table, members, title=title)
    return (name, {"config.json": conf, "filters.json": [], "visualContainer.json": vc_json(x, y, w, h), "query.json": query, "dataTransforms.json": datatransform(vtype)})


def main():
    os.makedirs(OUT, exist_ok=True)
    # scaffold copy from template
    for item in [".pbixproj.json", "Version.txt", "DiagramLayout.json", "ReportMetadata.json", "ReportSettings.json"]:
        shutil.copy(os.path.join(TEMPLATE, item), os.path.join(OUT, item))
    for d in ["StaticResources"]:
        src_d = os.path.join(TEMPLATE, d)
        dst_d = os.path.join(OUT, d)
        if os.path.exists(src_d):
            shutil.copytree(src_d, dst_d, dirs_exist_ok=True)
    # override PBIDesktop version reference name in database is fine, keep
    os.makedirs(os.path.join(OUT, "Model", "tables"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "Model", "cultures"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "Report", "sections"), exist_ok=True)
    build_model()
    build_report()
    for f in ["config.json", "report.json"]:
        src = os.path.join(TEMPLATE, "Report", f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT, "Report", f))
    # adjust report.json: drop RegisteredResources logo package
    rp = json.load(open(os.path.join(OUT, "Report", "report.json")))
    rp["resourcePackages"] = [pkg for pkg in rp["resourcePackages"] if pkg["resourcePackage"]["name"] == "SharedResources"]
    json.dump(rp, open(os.path.join(OUT, "Report", "report.json"), "w"), indent=2)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
