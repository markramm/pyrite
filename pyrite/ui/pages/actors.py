"""
People Page - Browse person entries.

This page was previously the "Actors" page tied to the journalism-specific
EntryActor table. It now shows person-type entries from the knowledge bases.
"""

import streamlit as st

from pyrite.ui.data import search

st.header("People")

# Search filter
person_search = st.text_input("Search people", placeholder="Type to search...")

st.divider()

if person_search:
    results = search(
        query=person_search,
        entry_type="person",
        limit=50,
    )
else:
    results = search(
        query="*",
        entry_type="person",
        limit=50,
    )

st.subheader(f"People: {len(results)}")

if not results:
    st.info("No person entries found. Create person entries with pyrite or pyrite-admin.")
else:
    # Display as grid
    cols_per_row = 3
    for i in range(0, len(results), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < len(results):
                person = results[i + j]
                with col:
                    with st.container():
                        st.markdown(f"### {person['title']}")
                        if person.get("snippet"):
                            st.caption(person["snippet"][:100])

                        if st.button("View Profile", key=f"person_{person['id']}"):
                            st.session_state.selected_entry_id = person["id"]
                            st.session_state.selected_entry_kb = person["kb_name"]
                            st.switch_page("pages/entry.py")

                    st.divider()
