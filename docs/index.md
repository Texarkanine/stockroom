# stockroom

A local, faithful, searchable warehouse of your agentic-coding history.

Stockroom captures prompts, responses, and tool inputs from supported agentic coding harnesses into a single-file [DuckDB](https://duckdb.org/) warehouse with local embeddings so you can use SQL queries when you know exactly what you're looking for, and semantic searches when you don't.

It includes a dashboard that gives an at-a-glance visual overview of your coding habits and history...

![Stockroom Dashboard](img/stockroom-dashboard-top-light.png){ width="400"}

... along with the ability to drill into and reconstruct past conversations:

![Stockroom Conversation Reconstruction](img/stockroom-dashboard-convo-light.png){ width="400"}

It can be used **fully offline** and **without AI** once it's set up: after installation, nothing else needs to be downloaded from the internet. Dependencies are fully locked so what you see on GitHub is *exactly* what you get, and you can query the warehouse with local `stockroom` and `duckdb` CLIs - no need to use any AI tool:

![Querying the Warehouse with DuckDB CLI](img/stockroom-duckdb-query.png)

Of course, you *can* use AI tools: day-to-day use is expected to go through the `/sr-search` skill & its companions in your agent harness, allowing agents to intelligently assemble queries for you to find what you're looking for - or even to recall past interactions on their own while working on something for you!

## Where to Go from Here

- Want it? [Quickstart](user-guide/quickstart.md)