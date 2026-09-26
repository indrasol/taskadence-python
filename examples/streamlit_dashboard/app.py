"""TasksMate dashboard — a Streamlit example of the `tasksmate` SDK.

    export TASKSMATE_TOKEN=tm_live_…                 # an access token with tasks:read + projects:read
    export TASKSMATE_API_URL=http://localhost:8000   # optional; default: the SDK's server
    streamlit run examples/streamlit_dashboard/app.py

No other configuration: the organizations come from `tm.me()`, everything else from the API.
"""

from __future__ import annotations

import datetime as dt
import os

import altair as alt
import pandas as pd
import streamlit as st

from tasksmate import APIError, TasksMate, TasksMateError

st.set_page_config(page_title="TasksMate dashboard", page_icon="✅", layout="wide")

DONE = {"completed", "archived"}
STATUS_ORDER = ["backlog", "not_started", "in_progress", "blocked", "on_hold", "completed", "archived"]
PRIORITY_ORDER = ["critical", "high", "medium", "low", "none"]


if not os.environ.get("TASKSMATE_TOKEN"):
    st.error(
        "Set **TASKSMATE_TOKEN** to a TasksMate access token (`tm_live_…`) and restart: "
        "`TASKSMATE_TOKEN=tm_live_… streamlit run app.py`. Mint one in TasksMate → Developers → Tokens."
    )
    st.stop()


@st.cache_resource
def client() -> TasksMate:
    return TasksMate()  # token from TASKSMATE_TOKEN, base URL from TASKSMATE_API_URL or the SDK default


@st.cache_data(ttl=60, show_spinner=False)
def whoami() -> tuple[str, list[tuple[str, str]]]:
    me = client().me()
    orgs = [(o.org_id, o.name if isinstance(o.name, str) and o.name else o.org_id) for o in me.organizations or []]
    return str(getattr(me.principal, "username", "") or ""), orgs


@st.cache_data(ttl=60, show_spinner="Loading tasks…")
def tasks_frame(org_id: str) -> pd.DataFrame:
    frame = client().tasks.list(org_id=org_id, limit=1000).to_dataframe()  # every page
    if frame.empty:
        return frame
    today = dt.date.today()
    due = frame["due_date"] if "due_date" in frame else pd.Series([None] * len(frame))
    frame["overdue"] = [
        isinstance(d, dt.date) and d < today and s not in DONE for d, s in zip(due, frame["status"], strict=True)
    ]
    return frame


@st.cache_data(ttl=60, show_spinner="Loading projects…")
def projects_frame(org_id: str) -> pd.DataFrame:
    return client().projects.list(org_id).to_dataframe()


def bars(frame: pd.DataFrame, column: str, order: list[str], color: str) -> alt.Chart:
    """Task counts per value, in the workflow's order (not alphabetical)."""
    series = frame[column].fillna("none").value_counts()
    ordered = [k for k in order if k in series.index] + [k for k in series.index if k not in order]
    data = pd.DataFrame({column: ordered, "tasks": [int(series[k]) for k in ordered]})
    return (
        alt.Chart(data)
        .mark_bar(color=color, cornerRadiusEnd=3)
        .encode(
            x=alt.X("tasks:Q", title="tasks"),
            y=alt.Y(f"{column}:N", sort=ordered, title=None),
            tooltip=[column, "tasks"],
        )
        .properties(height=alt.Step(30))
    )


COLUMNS = ["task_id", "title", "status", "priority", "assignee", "due_date", "project_id", "task_type", "overdue"]


def show(frame: pd.DataFrame) -> None:
    cols = [c for c in COLUMNS if c in frame.columns]
    st.dataframe(
        frame[cols],
        hide_index=True,
        use_container_width=True,
        column_config={
            "overdue": st.column_config.CheckboxColumn("overdue"),
            "due_date": st.column_config.DateColumn("due"),
        },
    )


try:
    username, orgs = whoami()
except (TasksMateError, APIError) as exc:
    st.error(f"The TasksMate API refused the request: {exc}")
    st.stop()

with st.sidebar:
    st.title("TasksMate")
    st.caption(f"Signed in as **{username or 'a service account'}** · {client().base_url}")
    if not orgs:
        st.warning("This token belongs to no organization.")
        st.stop()
    org_id = st.selectbox("Organization", [o for o, _ in orgs], format_func=dict(orgs).get)
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
    st.caption("Data is read with your token and cached for 60 s.")

try:
    tasks = tasks_frame(org_id)
    projects = projects_frame(org_id)
except (TasksMateError, APIError) as exc:
    st.error(f"{exc}")
    st.stop()

st.header(dict(orgs)[org_id])
if tasks.empty:
    st.info("No tasks you can read in this organization yet.")
    st.stop()

open_tasks = tasks[~tasks["status"].isin(DONE)]
done_share = 100 * (tasks["status"] == "completed").mean()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Tasks", len(tasks))
k2.metric("Open", len(open_tasks))
k3.metric("Overdue", int(tasks["overdue"].sum()))
k4.metric("Completed", f"{done_share:.0f}%")

tab_all, tab_charts, tab_projects, tab_mine = st.tabs(["All tasks", "Status & priority", "Projects", "My open tasks"])

with tab_all:
    f1, f2 = st.columns(2)
    statuses = f1.multiselect("Status", [s for s in STATUS_ORDER if s in set(tasks["status"])])
    priorities = f2.multiselect("Priority", [p for p in PRIORITY_ORDER if p in set(tasks["priority"].fillna("none"))])
    view = tasks
    if statuses:
        view = view[view["status"].isin(statuses)]
    if priorities:
        view = view[view["priority"].fillna("none").isin(priorities)]
    show(view)

with tab_charts:
    c1, c2 = st.columns(2)
    c1.subheader("By status")
    c1.altair_chart(bars(tasks, "status", STATUS_ORDER, "#0f766e"), use_container_width=True)
    c2.subheader("By priority")
    c2.altair_chart(bars(tasks, "priority", PRIORITY_ORDER, "#b45309"), use_container_width=True)

with tab_projects:
    if projects.empty:
        st.info("No projects you can read.")
    else:
        projects = projects.sort_values(["tasks_total", "name"], ascending=[False, True])
        names = dict(zip(projects["project_id"], projects["name"], strict=True))
        summary = projects[
            ["project_id", "name", "status", "tasks_completed", "tasks_total", "progress_percent"]
        ].copy()
        summary["progress_percent"] = pd.to_numeric(summary["progress_percent"], errors="coerce")  # sent as a string
        st.dataframe(
            summary,
            hide_index=True,
            use_container_width=True,
            column_config={
                "progress_percent": st.column_config.ProgressColumn(
                    "progress", min_value=0, max_value=100, format="%.0f%%"
                )
            },
        )
        chosen = st.selectbox("Drill into a project", list(names), format_func=names.get)
        mine = tasks[tasks["project_id"] == chosen]
        st.caption(f"{len(mine)} task(s) in **{names[chosen]}**")
        show(mine)

with tab_mine:
    mine = open_tasks[open_tasks["assignee"] == username] if "assignee" in open_tasks else open_tasks.iloc[0:0]
    st.caption(f"Open tasks assigned to **{username}**, soonest due first.")
    show(mine.sort_values("due_date", na_position="last"))
