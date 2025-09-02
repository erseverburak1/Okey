"""
Fizz Daily Ticket Report Generator (Email layout per attachment)

This script queries Jira Cloud and produces an HTML email that matches the
provided attachment layout:

- Created Ticket table
- Resolved Ticket table
- SLA Success (Met/Breached by Support Group)
- SLA Breached (Priority split by Category)
- SLA Breached: Problem linked vs linkless (Etiya, Etiya-OCS)
- Breached Priority - Etiya-OCS (P3*, P3, P4)

Set REPORT_STDOUT=1 to emit the HTML to stdout for mailers; otherwise, the
report is saved to a local HTML file and opened in a browser.
"""

import os
import datetime
import requests
import pandas as pd  # noqa: F401  (kept for compatibility; not used directly in final layout)


# Flowede çalışsın diye global variable'a passledik
flowe_html = ""


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
JIRA_URL = "https://fizzetiya.atlassian.net/"
USERNAME = os.getenv("JIRA_USERNAME", "burak.ersever@etiya.com")
API_TOKEN = os.getenv(
    "JIRA_API_TOKEN",
    "ATATT3xFfGF0KTNrbYrkrb_tn42Duot2qJ-jwfmcH1sIRIOELmSjOrOGk0Kz_I2ECV77TV9Om4QXaqfByyqVgRbccOO3uGMuDLqFb1H6gE_1GnfrlNbm3NFMzdhURffesagBIWJa8LgjjgStsETU8spVet2QmtxMeOYHOwyXrCdv_XYPfihyY0o=97A5DD1A",
)

SUPPORT_GROUP_FIELD = "customfield_10032"
SLA_TARGET_FIELD = "customfield_10052"


# ----------------------------------------------------------------------------
# User groups
# ----------------------------------------------------------------------------
LEVEL1_USERS = [
    "63eca53607df05aa827622ed",
    "712020:e3530b74-5edb-4a2d-9011-e3d8ed649f43",
    "712020:146e9332-389f-42d1-b900-6c81b3535701",
    "6400641f4d5e4b44e231e6d6",
    "712020:e17b7b12-deb1-4371-acd0-8f6fa5d5cb66",
    "712020:e14e9e85-aaf1-4b91-844b-979866c82c44",
    "62b1734b99eafa602d8843d3",
    "712020:0eeebd68-1158-4c18-bd47-2a86ad73a3ee",
    "640835b27655a3223a24da5c",
    "712020:dfb2ce1d-4a60-4396-be3f-c3a2b389043a",
    "712020:78b50d3a-5f6a-44a3-ace8-31572d5bf859",
    "5dc9411dbb355b0ddbd15add",
    "616e9a785800630069f91241",
    "63bbdbf9c52a63dcda827b5a",
]

LEVEL2_USERS = [
    "62209c609c3cce00694b94be",
    "5d7f7fe41fcbda0da133dc9c",
    "5fd9c86add5eb501080328ad",
    "60b799d024eedc006d301422",
    "6124fe64129802006ad7d4e8",
    "6165957f64ff010071c1f5ca",
    "629e12009f5d480069c82c76",
    "712020:355d7404-048e-4567-98a1-94e7a5070103",
    "62267d364160640069c945d7",
    "61e1329649f1950069c25284",
    "626a642ba32183006f251807",
    "62c442f6efb17d6ce62edba5",
]

I2I_USER = "712020:ea416182-6ac7-4c75-ad78-fca8a4011205"


# ----------------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------------
def _parse_jira_datetime(value):
    """Parse Jira datetime into naive UTC datetime (or None)."""
    if not value:
        return None
    try:
        dt = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
        return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    except Exception:
        try:
            return datetime.datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            try:
                return datetime.datetime.strptime(value[:10], "%Y-%m-%d")
            except Exception:
                return None


def get_date_range():
    """Return today's local day window label used in the email header."""
    today = datetime.date.today()
    return f"{today.strftime('%Y-%m-%d')} 00:00-23:59"


def get_all_issues(_jira_unused, jql, field_names):
    """Fetch all issues using Jira REST API (pagination + changelog)."""
    issues = []
    start_at = 0
    max_results = 100
    url = f"{JIRA_URL}/rest/api/3/search"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    while True:
        payload = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": field_names,
            "expand": ["changelog"],
        }
        resp = requests.post(
            url,
            auth=(USERNAME, API_TOKEN),
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("issues", [])
        if not batch:
            break
        issues.extend(batch)
        if len(batch) < max_results:
            break
        start_at += max_results
    return issues


# ----------------------------------------------------------------------------
# Queries
# ----------------------------------------------------------------------------
def get_todays_created_issues(jira):
    jql = (
        'project = "Fizz Managed Services" '
        "AND issuetype = Incident "
        "AND created >= startOfDay() AND created <= endOfDay()"
    )
    fields = [
        "created",
        "resolutiondate",
        "assignee",
        "status",
        SUPPORT_GROUP_FIELD,
        SLA_TARGET_FIELD,
        "changelog",
    ]
    return get_all_issues(jira, jql, fields)


def get_today_resolved_issues(jira):
    jql = (
        'project = "Fizz Managed Services" '
        "AND issuetype = Incident "
        "AND status in (Closed, Resolved) "
        "AND resolved >= startOfDay() AND resolved <= endOfDay()"
    )
    fields = ["resolutiondate", "assignee", SUPPORT_GROUP_FIELD, "priority"]
    return get_all_issues(jira, jql, fields)


# ----------------------------------------------------------------------------
# Computations
# ----------------------------------------------------------------------------
def aggregate_stats_for_created_issues(issues, start_dt, end_dt):
    """Aggregate created-today metrics needed by the attachment layout."""
    result = {
        "created_total": 0,
        "assign_i2i": 0,
        "assign_third": 0,
        "l1_inprogress": 0,
        "l2_inprogress": 0,
        "pending_csr": 0,
    }

    for issue in issues:
        fields = issue.get("fields", {})
        result["created_total"] += 1

        # Count in-progress by current assignee level (only unresolved)
        resolution_date = fields.get("resolutiondate")
        assignee_id = (fields.get("assignee") or {}).get("accountId")
        if not resolution_date:
            if assignee_id in LEVEL1_USERS:
                result["l1_inprogress"] += 1
            elif assignee_id in LEVEL2_USERS:
                result["l2_inprogress"] += 1

            # Pending CSR detection from status name
            status_name = ((fields.get("status") or {}).get("name") or "").lower()
            if "pending" in status_name or "csr" in status_name:
                result["pending_csr"] += 1

        # Changelog-based routing today
        was_i2i = False
        was_third = False
        histories = (issue.get("changelog") or {}).get("histories", [])
        for history in histories:
            h_created = _parse_jira_datetime(history.get("created"))
            if not h_created or not (start_dt <= h_created <= end_dt):
                continue
            for item in history.get("items", []):
                if item.get("field") == "assignee" and (
                    item.get("to") == I2I_USER or item.get("from") == I2I_USER
                ):
                    was_i2i = True
                if item.get("field") == "Support Group" or item.get("fieldId") == SUPPORT_GROUP_FIELD:
                    group_name = (item.get("toString") or "").lower()
                    if group_name and "etiya" not in group_name and "ocs" not in group_name:
                        was_third = True
            if was_i2i and was_third:
                break
        if was_i2i:
            result["assign_i2i"] += 1
        if was_third:
            result["assign_third"] += 1

    return result


def aggregate_resolved_counts(issues):
    """Compute resolved ticket counts for the day (total, L1, L2, i2i)."""
    counts = {
        "resolved_total": 0,
        "l1_resolved": 0,
        "l2_resolved": 0,
        "i2i_resolved": 0,
    }
    for issue in issues:
        fields = issue.get("fields", {})
        counts["resolved_total"] += 1
        assignee_id = (fields.get("assignee") or {}).get("accountId")
        if assignee_id in LEVEL1_USERS:
            counts["l1_resolved"] += 1
        elif assignee_id in LEVEL2_USERS:
            counts["l2_resolved"] += 1

        current_group = (fields.get(SUPPORT_GROUP_FIELD) or {}).get("value", "").lower()
        if "etiya-ocs" in current_group or "i2i" in current_group or "ocs" in current_group:
            counts["i2i_resolved"] += 1

    return counts


def compute_sla_window_stats(jira):
    """Compute SLA buckets and breakdowns in the last 24h window.

    Returns a dict containing:
      - sla_closed_notbreached, sla_closed_breached, sla_inprog_notbreached, sla_inprog_breached
      - group_sla: per-group closed met/breached counts
      - breach_* attribution counts and keys
      - prio_counts: priority breakdown for breached tickets by group
      - problem_link: {etiya|i2i: {linked, linkless}}
    """
    stats = {
        "sla_closed_notbreached": 0,
        "sla_closed_breached": 0,
        "sla_inprog_notbreached": 0,
        "sla_inprog_breached": 0,
        "sla_closed_notbreached_keys": [],
        "sla_closed_breached_keys": [],
        "sla_inprog_notbreached_keys": [],
        "sla_inprog_breached_keys": [],
        # breach attribution buckets (by current support group)
        "breach_etiya": 0,
        "breach_i2i": 0,
        "breach_third": 0,
        "breach_etiya_keys": [],
        "breach_i2i_keys": [],
        "breach_third_keys": [],
        # priority breakdown for breached tickets
        "prio_counts": {"etiya": {}, "i2i": {}, "third": {}},
        # per-group SLA met/breached for CLOSED tickets only
        "group_sla": {
            "etiya": {"met": 0, "breached": 0},
            "i2i": {"met": 0, "breached": 0},
            "etiya_ntw": {"met": 0, "breached": 0},
            "third": {"met": 0, "breached": 0},
        },
        # problem link stats for breached tickets
        "problem_link": {
            "etiya": {"linked": 0, "linkless": 0},
            "i2i": {"linked": 0, "linkless": 0},
        },
    }

    def _normalize_priority(prio_name: str) -> str:
        if not prio_name:
            return "Other"
        s = prio_name.strip().upper().replace(" ", "")
        if s.startswith("P1"):
            return "P1"
        if s.startswith("P2"):
            return "P2"
        if s.startswith("P3*") or (s.startswith("P3") and "*" in s):
            return "P3*"
        if s.startswith("P3"):
            return "P3"
        if s.startswith("P4"):
            return "P4"
        return "Other"

    def _add_prio(category: str, prio_name: str):
        prio_norm = _normalize_priority(prio_name)
        cat_counts = stats["prio_counts"].setdefault(category, {})
        cat_counts[prio_norm] = int(cat_counts.get(prio_norm, 0)) + 1

    def _group_from_support_group(group_value: str) -> str:
        s = (group_value or "").lower()
        if "etiya-ocs" in s or "i2i" in s or "ocs" in s:
            return "i2i"
        if "etiya" in s and ("ntw" in s or "network" in s):
            return "etiya_ntw"
        if "etiya" in s:
            return "etiya"
        return "third"

    # Closed last 24h
    jql_closed = (
        'project = "Fizz Managed Services" '
        "AND issuetype = Incident "
        "AND status in (Closed, Resolved) "
        "AND resolved >= -24h"
    )
    closed_issues = get_all_issues(
        jira,
        jql_closed,
        ["resolutiondate", SLA_TARGET_FIELD, SUPPORT_GROUP_FIELD, "priority", "issuelinks"],
    )
    for issue in closed_issues:
        fields = issue.get("fields", {})
        res_dt = _parse_jira_datetime(fields.get("resolutiondate"))
        sla_dt = _parse_jira_datetime(fields.get(SLA_TARGET_FIELD))
        if not res_dt or not sla_dt:
            continue
        current_group_value = (fields.get(SUPPORT_GROUP_FIELD) or {}).get("value", "")
        group_key = _group_from_support_group(current_group_value)
        prio_name = (fields.get("priority") or {}).get("name", "")
        if res_dt > sla_dt:
            stats["sla_closed_breached"] += 1
            stats["sla_closed_breached_keys"].append(issue.get("key"))
            # group-level split
            stats["group_sla"][group_key]["breached"] += 1
            # attribution buckets
            if group_key == "i2i":
                stats["breach_i2i"] += 1
                stats["breach_i2i_keys"].append(issue.get("key"))
                _add_prio("i2i", prio_name)
            elif group_key == "etiya" or group_key == "etiya_ntw":
                stats["breach_etiya"] += 1
                stats["breach_etiya_keys"].append(issue.get("key"))
                _add_prio("etiya", prio_name)
            else:
                stats["breach_third"] += 1
                stats["breach_third_keys"].append(issue.get("key"))
                _add_prio("third", prio_name)

            # problem link check
            linked = _has_problem_link(fields.get("issuelinks") or [])
            if group_key == "i2i":
                stats["problem_link"]["i2i"]["linked" if linked else "linkless"] += 1
            elif group_key in ("etiya", "etiya_ntw"):
                stats["problem_link"]["etiya"]["linked" if linked else "linkless"] += 1
        else:
            stats["sla_closed_notbreached"] += 1
            stats["sla_closed_notbreached_keys"].append(issue.get("key"))
            stats["group_sla"][group_key]["met"] += 1

    # In-progress window checks
    jql_inprog = (
        'project = "Fizz Managed Services" AND issuetype = Incident '
        "AND status not in (Closed, Resolved)"
    )
    inprog_issues = get_all_issues(
        jira,
        jql_inprog,
        [SLA_TARGET_FIELD, SUPPORT_GROUP_FIELD, "priority", "issuelinks"],
    )
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    for issue in inprog_issues:
        fields = issue.get("fields", {})
        sla_dt = _parse_jira_datetime(fields.get(SLA_TARGET_FIELD))
        if not sla_dt:
            continue
        if now >= sla_dt and (now - sla_dt).total_seconds() <= 24 * 3600:
            stats["sla_inprog_breached"] += 1
            stats["sla_inprog_breached_keys"].append(issue.get("key"))
            current_group_value = (fields.get(SUPPORT_GROUP_FIELD) or {}).get("value", "")
            group_key = _group_from_support_group(current_group_value)
            prio_name = (fields.get("priority") or {}).get("name", "")
            if group_key == "i2i":
                stats["breach_i2i"] += 1
                stats["breach_i2i_keys"].append(issue.get("key"))
                _add_prio("i2i", prio_name)
            elif group_key == "etiya" or group_key == "etiya_ntw":
                stats["breach_etiya"] += 1
                stats["breach_etiya_keys"].append(issue.get("key"))
                _add_prio("etiya", prio_name)
            else:
                stats["breach_third"] += 1
                stats["breach_third_keys"].append(issue.get("key"))
                _add_prio("third", prio_name)

            linked = _has_problem_link(fields.get("issuelinks") or [])
            if group_key == "i2i":
                stats["problem_link"]["i2i"]["linked" if linked else "linkless"] += 1
            elif group_key in ("etiya", "etiya_ntw"):
                stats["problem_link"]["etiya"]["linked" if linked else "linkless"] += 1
        elif sla_dt > now and (sla_dt - now).total_seconds() <= 24 * 3600:
            stats["sla_inprog_notbreached"] += 1
            stats["sla_inprog_notbreached_keys"].append(issue.get("key"))

    return stats


def _has_problem_link(issuelinks):
    """Best-effort detection whether an issue has a Problem-type link."""
    try:
        for link in issuelinks:
            link_type = ((link or {}).get("type") or {}).get("name") or ""
            if link_type and "problem" in link_type.lower():
                return True
            inward = (link or {}).get("inwardIssue") or {}
            outward = (link or {}).get("outwardIssue") or {}
            for side in (inward, outward):
                fields = side.get("fields") or {}
                issuetype = (fields.get("issuetype") or {}).get("name") or ""
                if issuetype and issuetype.lower() == "problem":
                    return True
    except Exception:
        return False
    return False


# ----------------------------------------------------------------------------
# HTML builder (attachment layout)
# ----------------------------------------------------------------------------
def _cell(value):
    return f"<td>{int(value) if isinstance(value, (int, float)) else value}</td>"


def create_html_report_attachment_layout(
    created_counts,
    resolved_counts,
    sla_window,
    report_label,
):
    """Render the email HTML matching the attachment layout."""
    base_css = (
        "body{font-family:Arial,sans-serif;margin:20px;}"
        "table{border-collapse:collapse;width:100%;margin:18px 0;}"
        "th,td{border:1px solid #ddd;padding:8px;text-align:left;}"
        "th{background:#f2f2f2;}"
        "h2{margin:4px 0 12px 0;}h3{margin:16px 0 8px 0;}"
    )

    # Created Ticket table
    created_html = (
        "<h3>Created Ticket</h3>"
        "<table>"
        "<tr>"
        "<th>Created ticket</th>"
        "<th>Assign i2i</th>"
        "<th>Assign 3rd party</th>"
        "<th>Level 1 Inprogress</th>"
        "<th>Level 2 Inprogress</th>"
        "<th>Pending Ticket(CSR action req)</th>"
        "</tr>"
        f"<tr>{_cell(created_counts.get('created_total',0))}"
        f"{_cell(created_counts.get('assign_i2i',0))}"
        f"{_cell(created_counts.get('assign_third',0))}"
        f"{_cell(created_counts.get('l1_inprogress',0))}"
        f"{_cell(created_counts.get('l2_inprogress',0))}"
        f"{_cell(created_counts.get('pending_csr',0))}</tr>"
        "</table>"
    )

    # Resolved Ticket table
    resolved_html = (
        "<h3>Resolved Ticket</h3>"
        "<table>"
        "<tr>"
        "<th>Resolved ticket</th>"
        "<th>Level1 Resolved</th>"
        "<th>Level2 Resolved</th>"
        "<th>i2i Resolved</th>"
        "</tr>"
        f"<tr>{_cell(resolved_counts.get('resolved_total',0))}"
        f"{_cell(resolved_counts.get('l1_resolved',0))}"
        f"{_cell(resolved_counts.get('l2_resolved',0))}"
        f"{_cell(resolved_counts.get('i2i_resolved',0))}</tr>"
        "</table>"
    )

    # SLA Success table (per group)
    g = sla_window.get("group_sla", {})
    def _row_group(name_key, label):
        d = g.get(name_key, {"breached": 0, "met": 0})
        return f"<tr><td>{label}</td>{_cell(d.get('breached',0))}{_cell(d.get('met',0))}</tr>"

    sla_success_html = (
        "<h3>SLA Success</h3>"
        "<table>"
        "<tr><th></th><th>Breached</th><th>Met</th></tr>"
        f"{_row_group('etiya','Etiya')}"
        f"{_row_group('i2i','Etiya-OCS')}"
        f"{_row_group('etiya_ntw','Etiya - NTW')}"
        f"{_row_group('third','3rd Party')}"
        "</table>"
    )

    # SLA Breached: Category vs Priority
    pr = sla_window.get("prio_counts", {"etiya": {}, "i2i": {}, "third": {}})
    def _prio_val(cat, p):
        return int((pr.get(cat) or {}).get(p, 0))

    breached_by_cat_html = (
        "<h3>SLA Breached</h3>"
        "<table>"
        "<tr><th>Category</th><th>P1</th><th>P2</th><th>P3*</th><th>P3</th><th>P4</th></tr>"
        f"<tr><td>Etiya</td>{_cell(_prio_val('etiya','P1'))}{_cell(_prio_val('etiya','P2'))}{_cell(_prio_val('etiya','P3*'))}{_cell(_prio_val('etiya','P3'))}{_cell(_prio_val('etiya','P4'))}</tr>"
        f"<tr><td>i2i</td>{_cell(_prio_val('i2i','P1'))}{_cell(_prio_val('i2i','P2'))}{_cell(_prio_val('i2i','P3*'))}{_cell(_prio_val('i2i','P3'))}{_cell(_prio_val('i2i','P4'))}</tr>"
        f"<tr><td>3rd Party</td>{_cell(_prio_val('third','P1'))}{_cell(_prio_val('third','P2'))}{_cell(_prio_val('third','P3*'))}{_cell(_prio_val('third','P3'))}{_cell(_prio_val('third','P4'))}</tr>"
        "</table>"
    )

    # SLA Breached: Problem linked vs linkless (Etiya, i2i)
    pl = sla_window.get("problem_link", {"etiya": {"linked": 0, "linkless": 0}, "i2i": {"linked": 0, "linkless": 0}})
    problem_link_html = (
        "<h3>SLA Breached</h3>"
        "<table>"
        "<tr><th></th><th>Problemle linkli</th><th>linksiz</th></tr>"
        f"<tr><td>Etiya</td>{_cell(pl.get('etiya',{}).get('linked',0))}{_cell(pl.get('etiya',{}).get('linkless',0))}</tr>"
        f"<tr><td>i2i</td>{_cell(pl.get('i2i',{}).get('linked',0))}{_cell(pl.get('i2i',{}).get('linkless',0))}</tr>"
        "</table>"
    )

    # Breached Priority - Etiya-OCS (P3*, P3, P4 only)
    i2i_prio = pr.get("i2i", {})
    breached_priority_i2i_html = (
        "<h3>Breached Priority - Etiya-OCS</h3>"
        "<table style=\"width:auto;min-width:320px\">"
        "<tr><th></th><th>ticket sayıları</th></tr>"
        f"<tr><td>P3*</td>{_cell(int(i2i_prio.get('P3*',0)))}</tr>"
        f"<tr><td>P3</td>{_cell(int(i2i_prio.get('P3',0)))}</tr>"
        f"<tr><td>P4</td>{_cell(int(i2i_prio.get('P4',0)))}</tr>"
        "</table>"
    )

    html = (
        "<html><head><meta charset='utf-8'>"
        f"<style>{base_css}</style>"
        "</head><body>"
        f"<div style='font-size:12px;color:#666;'>" + report_label + "</div>"
        "<h2>Created Ticket Report</h2>"
        + created_html
        + resolved_html
        + sla_success_html
        + breached_by_cat_html
        + problem_link_html
        + breached_priority_i2i_html
        + "</body></html>"
    )
    return html


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def generate_daily_report():
    try:
        jira = None
        # Today window for changelog filtering
        today = datetime.date.today()
        start_dt = datetime.datetime.combine(today, datetime.time.min)
        end_dt = datetime.datetime.combine(today, datetime.time.max)

        # Created today
        created_today = get_todays_created_issues(jira)
        created_counts = aggregate_stats_for_created_issues(created_today, start_dt, end_dt)

        # Resolved today
        resolved_today = get_today_resolved_issues(jira)
        resolved_counts = aggregate_resolved_counts(resolved_today)

        # SLA window (24h)
        sla_window = compute_sla_window_stats(jira)

        report_label = get_date_range()
        html = create_html_report_attachment_layout(
            created_counts=created_counts,
            resolved_counts=resolved_counts,
            sla_window=sla_window,
            report_label=report_label,
        )
        return html
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_report_to_file(html_content):
    if html_content is None:
        print("Rapor oluşturulamadı!")
        return
    today = datetime.date.today().strftime("%Y-%m-%d")
    report_path = f"/workspace/daily_report_{today}.html"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Rapor kaydedildi: {report_path}")
    try:
        import webbrowser
        webbrowser.open(report_path)
    except Exception:
        pass


if __name__ == "__main__":
    html_report = generate_daily_report()
    flowe_html = html_report or ""
    if os.getenv("REPORT_STDOUT") == "1":
        print(html_report or "", end="")
    else:
        save_report_to_file(html_report)

