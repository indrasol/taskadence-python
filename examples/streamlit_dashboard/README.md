# Streamlit dashboard

A one-file dashboard over the `taskadence` SDK: pick an organization (from `tm.me()`), see its tasks as a table
(`tm.tasks.list(...).to_dataframe()`, every page), status and priority charts, a project drill-down, and your open tasks.

**Configuration: `TASKADENCE_TOKEN` only** (plus `TASKADENCE_API_URL` when you are not using the default server).

```bash
cd examples/streamlit_dashboard
pip install -e "../..[pandas]"        # until taskadence is on PyPI; afterwards the next line is enough
pip install -r requirements.txt
export TASKADENCE_TOKEN=tkd_live_…       # Taskadence → Developers → Tokens; tasks:read + projects:read are enough
export TASKADENCE_API_URL=http://localhost:8000   # optional
streamlit run app.py
```

![The dashboard at 1280 px, against dev org O0020](../../../docs/images/4.5/streamlit-1280.png)

_(The screenshot lives in the Taskadence umbrella docs, `docs/images/4.5/streamlit-1280.png`; charts and projects tabs
beside it.)_

What it shows, and the SDK call behind each part:

| Part | Call |
|---|---|
| Organization picker, "signed in as" | `tm.me()` |
| KPIs, tasks table, filters, "My open tasks" | `tm.tasks.list(org_id=…, limit=1000).to_dataframe()` — follows `next_cursor` through every page |
| Status / priority charts | the same DataFrame, counted in workflow order |
| Projects and drill-down | `tm.projects.list(org_id).to_dataframe()` |

Data is cached for 60 s per organization (the **Refresh** button clears it). The token never leaves the server process:
Streamlit renders only data, and the SDK never logs the token.
