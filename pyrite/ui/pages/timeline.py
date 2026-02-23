"""
Timeline Page - Browse events chronologically.
"""

from datetime import date

import streamlit as st

from pyrite.ui.data import get_timeline

st.header("Timeline")

# Filters
col1, col2, col3, col4 = st.columns(4)

with col1:
    # Default to last year
    default_from = date(2025, 1, 1)
    date_from = st.date_input("From", value=default_from)

with col2:
    default_to = date.today()
    date_to = st.date_input("To", value=default_to)

with col3:
    min_importance = st.slider("Min Importance", 1, 10, 5)

with col4:
    limit = st.selectbox("Max Events", [50, 100, 200, 500], index=1)

# Get timeline data
with st.spinner("Loading timeline..."):
    events = get_timeline(
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
        min_importance=min_importance,
        limit=limit,
    )

st.divider()
st.subheader(f"Events: {len(events)}")

if not events:
    st.info("No events found for the selected filters.")
else:
    # Group by date
    events_by_date = {}
    for event in events:
        event_date = event.get("date", "Unknown")
        if event_date not in events_by_date:
            events_by_date[event_date] = []
        events_by_date[event_date].append(event)

    # Sort by date (newest first)
    sorted_dates = sorted(events_by_date.keys(), reverse=True)

    # Display timeline
    for event_date in sorted_dates:
        day_events = events_by_date[event_date]

        # Date header
        st.markdown(f"### {event_date}")

        for event in day_events:
            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    # Clickable title
                    if st.button(
                        f"**{event['title']}**",
                        key=f"event_{event['id']}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_entry_id = event["id"]
                        st.session_state.selected_entry_kb = event.get("kb_name", "timeline")
                        st.switch_page("pages/entry.py")

                with col2:
                    # Importance badge
                    importance = event.get("importance", 5)
                    if importance >= 8:
                        st.markdown(f"**{importance}**")
                    elif importance >= 6:
                        st.markdown(f"{importance}")
                    else:
                        st.markdown(f"{importance}")

                # Tags
                if event.get("tags"):
                    tags_str = ", ".join(event["tags"][:5])
                    st.caption(f"Tags: {tags_str}")

            st.divider()
