"""
Search Page - Full-text search with faceted filtering.
"""

import streamlit as st

from pyrite.ui.data import get_tags, search

st.header("🔍 Search")

# Get global search from sidebar
query = st.session_state.get("global_search", "")
selected_kb = st.session_state.get("selected_kb", "All KBs")

# Search form
with st.form("search_form"):
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        query = st.text_input(
            "Search Query",
            value=query,
            placeholder='Enter search terms (supports FTS5 syntax: AND, OR, NOT, "phrase")',
        )
    with col2:
        limit = st.selectbox("Results", [20, 50, 100, 200], index=1)
    with col3:
        search_mode = st.radio(
            "Mode",
            ["keyword", "semantic", "hybrid"],
            index=0,
            horizontal=True,
        )
        expand_query = st.checkbox("AI Expand", value=False, help="Use AI to expand search terms")

    # Filters in expander
    with st.expander("Advanced Filters", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            entry_type = st.selectbox(
                "Entry Type", ["All", "event", "actor", "organization", "theme", "scene"], index=0
            )

        with col2:
            date_from = st.date_input("From Date", value=None)

        with col3:
            date_to = st.date_input("To Date", value=None)

        # Tag filter
        tags = get_tags(selected_kb if selected_kb != "All KBs" else None, limit=50)
        tag_options = [t["name"] for t in tags]
        selected_tags = st.multiselect("Filter by Tags", tag_options)

    submitted = st.form_submit_button("Search", type="primary", use_container_width=True)

# Perform search
if query or submitted:
    if query:
        with st.spinner("Searching..."):
            results = search(
                query=query,
                kb_name=selected_kb if selected_kb != "All KBs" else None,
                entry_type=entry_type if entry_type != "All" else None,
                tags=selected_tags if selected_tags else None,
                date_from=date_from.isoformat() if date_from else None,
                date_to=date_to.isoformat() if date_to else None,
                limit=limit,
                mode=search_mode,
                expand=expand_query,
            )

        st.divider()

        # Results header
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"Results: {len(results)} found")
        with col2:
            if results:
                st.download_button(
                    "Export JSON",
                    data=str(results),
                    file_name="search_results.json",
                    mime="application/json",
                )

        # Display results
        if not results:
            st.info("No results found. Try different search terms or filters.")
        else:
            for result in results:
                with st.container():
                    # Title with link to detail
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.button(
                            f"**{result['title']}**",
                            key=f"result_{result['id']}",
                            use_container_width=True,
                        ):
                            st.session_state.selected_entry_id = result["id"]
                            st.session_state.selected_entry_kb = result["kb_name"]
                            st.switch_page("pages/entry.py")

                    with col2:
                        st.caption(f"{result['kb_name']} | {result['entry_type']}")

                    # Snippet
                    if result.get("snippet"):
                        # Convert highlight marks to markdown bold
                        snippet = result["snippet"].replace("<mark>", "**").replace("</mark>", "**")
                        st.markdown(f"...{snippet}...", unsafe_allow_html=False)

                    # Metadata row
                    meta_parts = []
                    if result.get("date"):
                        meta_parts.append(f"📅 {result['date']}")
                    if result.get("importance"):
                        meta_parts.append(f"⭐ {result['importance']}")
                    if result.get("tags"):
                        meta_parts.append(f"🏷️ {', '.join(result['tags'][:3])}")

                    if meta_parts:
                        st.caption(" | ".join(meta_parts))

                    st.divider()
    else:
        st.info("Enter a search query to find entries.")
else:
    # Show popular tags and actors when no search
    st.subheader("Explore")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Popular Tags")
        tags = get_tags(selected_kb if selected_kb != "All KBs" else None, limit=15)
        for tag in tags:
            if st.button(f"🏷️ {tag['name']} ({tag['count']})", key=f"tag_{tag['name']}"):
                st.session_state.global_search = tag["name"]
                st.rerun()

    with col2:
        st.markdown("### Recent Entries")
        recent = search(query="*", limit=15)
        for entry in recent:
            if st.button(f"{entry['title']}", key=f"recent_{entry['id']}"):
                st.session_state.selected_entry_id = entry["id"]
                st.session_state.selected_entry_kb = entry["kb_name"]
                st.switch_page("pages/entry.py")
