"""Streamlit application: Negative News Scrubber
Paste any number of e‑mail addresses or business names and quickly surface
negative news coverage that matches those entities.  Share the deployed app
URL with teammates so they can run their own checks.

‣ Requires a free NewsAPI.org key (or upgrade for higher rate‑limits).
‣ Run locally with   $ streamlit run negative_news_scrubber_app.py
‣ Or deploy to Streamlit Community Cloud / internal infra and share the URL.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import List, Dict

import pandas as pd
import streamlit as st
from newsapi import NewsApiClient

###############################################################################
# CONFIGURATION
###############################################################################

DEFAULT_NEGATIVE_KEYWORDS: List[str] = [
    "scam",
    "complaint",
    "lawsuit",
    "fraud",
    "fraudulent",
    "bankruptcy",
    "chapter 11",
    "ripoff",
    "bad review",
    "negative review",
    "bbb f rating",
    "court filing",
    "fine",
    "penalty"
    "closed"
    "shut down"
    "out of business"
    "stole"
    "not answering",
]

RESULTS_PER_QUERY = 25  # NewsAPI max is 100 per call; keep modest for speed
DATE_RANGE_DAYS = 365 * 3  # look back three years by default

###############################################################################
# UI LAYOUT
###############################################################################

st.set_page_config(page_title="Negative News Scrubber", page_icon="🕵️", layout="centered")
st.title("🕵️ Negative News Scrubber")

st.info(
    "Paste one entity per line (e‑mail address or business name) below. "
    "Click *Run Search* to scan the public web for negative‑context coverage."
)

api_key = st.text_input("NewsAPI.org Key", type="password", help="Create a free key at https://newsapi.org")

names_input = st.text_area("Emails or Business Names", height=200, placeholder="e.g. complaint@example.com\nExample Ventures LLC")

custom_kw = st.text_input(
    "Additional negative keywords (comma‑separated)",
    placeholder="optional, e.g. cease and desist,shutdown",
)

col1, col2 = st.columns([1, 1])
lookback_years = col1.slider("Look‑back period (years)", 1, 10, 3)
results_limit = col2.number_input("Max articles per entity", min_value=1, max_value=100, value=RESULTS_PER_QUERY)

run_search = st.button("🔍 Run Search")

###############################################################################
# HELPER FUNCTIONS
###############################################################################

def build_query(entity: str, keywords: List[str]) -> str:
    # Quote entity to force exact match; join keywords with OR
    kws = " OR ".join(keywords)
    return f'"{entity}" AND ({kws})'


def search_entity(entity: str, client: NewsApiClient, keywords: List[str]) -> List[Dict]:
    query = build_query(entity, keywords)
    date_from = (datetime.utcnow() - timedelta(days=lookback_years * 365)).strftime("%Y-%m-%d")

    try:
        res = client.get_everything(
            q=query,
            from_param=date_from,
            language="en",
            sort_by="relevancy",
            page_size=min(results_limit, 100),
        )
        return res.get("articles", [])
    except Exception as exc:
        st.error(f"Error querying NewsAPI for {entity}: {exc}")
        return []

###############################################################################
# MAIN EXECUTION
###############################################################################

if run_search:
    if not api_key:
        st.error("Please provide a valid NewsAPI.org key to proceed.")
        st.stop()
    if not names_input.strip():
        st.error("Please enter at least one e‑mail or business name.")
        st.stop()

    negative_keywords = DEFAULT_NEGATIVE_KEYWORDS + [kw.strip() for kw in custom_kw.split(",") if kw.strip()]
    entities = [n.strip() for n in names_input.splitlines() if n.strip()]

    newsapi = NewsApiClient(api_key=api_key)
    aggregated_rows: List[Dict] = []

    progress = st.progress(0)
    for idx, entity in enumerate(entities, start=1):
        with st.spinner(f"Searching for negative news about: {entity}"):
            articles = search_entity(entity, newsapi, negative_keywords)
            for art in articles:
                aggregated_rows.append(
                    {
                        "Entity": entity,
                        "Title": art.get("title"),
                        "Source": art.get("source", {}).get("name"),
                        "Published": art.get("publishedAt")[:10] if art.get("publishedAt") else None,
                        "URL": art.get("url"),
                    }
                )
        progress.progress(idx / len(entities))

    if aggregated_rows:
        df = pd.DataFrame(aggregated_rows)
        st.subheader("⚠️ Negative Matches Found")
        st.dataframe(df, use_container_width=True)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV report", data=csv_bytes, file_name="negative_news_report.csv", mime="text/csv")
    else:
        st.success("🎉 No negative news found for any entries in the specified time window.")

###############################################################################
# FOOTER
###############################################################################

st.markdown("---")
st.markdown(
    "#### How to Share with Your Team\n"
    "1. **Deploy** this app to [Streamlit Community Cloud](https://streamlit.io/cloud) (free) or any internal server.\n"
    "2. Send your teammates the app URL—they only need the link and a NewsAPI key.\n"
    "3. Optionally hard‑code the API key in *Secrets* or environment variables for a turnkey experience.\n"
)
