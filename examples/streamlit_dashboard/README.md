# Streamlit dashboard

A one-file dashboard over the `taskadence` SDK: pick an organization (from `tm.me()`), see its tasks as a table
(`tm.tasks.list(...).to_dataframe()`, every page), status and priority charts, a project drill-down, and your open tasks.

**Configuration: `TASKADENCE_TOKEN` only** (plus `TASKADENCE_API_URL` when you are not using the default server).

```bash
cd examples/streamlit_dashboard
pip install -r requirements.txt        # taskadence[pandas] and streamlit
export TASKADENCE_TOKEN=tkd_live_…       # TasKadence Settings > Developers; tasks:read + projects:read are enough
streamlit run app.py
```

What it shows, and the SDK call behind each part:

| Part | Call |
|---|---|
| Organization picker, "signed in as" | `tm.me()` |
| KPIs, tasks table, filters, "My open tasks" | `tm.tasks.list(org_id=…, limit=1000).to_dataframe()`, which follows `next_cursor` through every page |
| Status / priority charts | the same DataFrame, counted in workflow order |
| Projects and drill-down | `tm.projects.list(org_id).to_dataframe()` |

Data is cached for 60 s per organization (the **Refresh** button clears it). The token never leaves the server process:
Streamlit renders only data, and the SDK never logs the token.
