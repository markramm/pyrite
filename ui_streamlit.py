import os

import requests
import streamlit as st

API = f"http://{os.getenv('ZK_HOST','127.0.0.1')}:{os.getenv('ZK_PORT','8088')}"
SUMMARY_MAX_LENGTH = int(os.getenv("ZK_SUMMARY_MAX_LENGTH", "280"))

st.title("🧠 Zettelkasten Assistant")

tab1, tab2, tab3 = st.tabs(["Create / Edit", "Search", "Links & CEQRC"])

with tab1:
    st.header("Create Note")
    title = st.text_input("Title")
    body = st.text_area("Body", height=200)

    # Summary field with character counter and auto-generation
    col1, col2 = st.columns([3, 1])
    with col1:
        summary = st.text_area(
            "Summary (optional - will auto-generate if empty)",
            height=80,
            max_chars=SUMMARY_MAX_LENGTH,
        )
    with col2:
        char_count = len(summary) if summary else 0
        color = "red" if char_count > SUMMARY_MAX_LENGTH else "green"
        st.markdown(
            f"<p style='color: {color}; font-size: 12px;'>{char_count}/{SUMMARY_MAX_LENGTH} chars</p>",
            unsafe_allow_html=True,
        )

        if st.button("🤖 Generate Summary", help="Auto-generate summary from body text"):
            if body.strip():
                r = requests.post(f"{API}/generate-summary", json={"text": body})
                if r.ok:
                    summary = r.json()["summary"]
                    st.rerun()

    tags = st.text_input("Tags (comma-separated)")

    if st.button("Create"):
        note_data = {
            "title": title,
            "body": body,
            "summary": summary,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
        }
        r = requests.post(f"{API}/notes", json=note_data)
        if r.ok:
            st.success(f"Created note {r.json()['id']}")
        else:
            st.error(r.text)

    st.header("Load / Update")
    nid = st.text_input("Note ID", key="nid_load")
    if st.button("Load"):
        r = requests.get(f"{API}/notes/{nid}")
        if r.ok:
            data = r.json()
            st.session_state["loaded_note"] = data
        else:
            st.error("Not found")
    if "loaded_note" in st.session_state:
        data = st.session_state["loaded_note"]
        new_title = st.text_input("Edit Title", value=data["title"])
        new_body = st.text_area("Edit Body", value=data["body"], height=200)

        # Summary editing with character counter
        col1, col2 = st.columns([3, 1])
        with col1:
            new_summary = st.text_area(
                "Edit Summary",
                value=data.get("summary", ""),
                height=80,
                max_chars=SUMMARY_MAX_LENGTH,
            )
        with col2:
            char_count = len(new_summary) if new_summary else 0
            color = "red" if char_count > SUMMARY_MAX_LENGTH else "green"
            st.markdown(
                f"<p style='color: {color}; font-size: 12px;'>{char_count}/{SUMMARY_MAX_LENGTH} chars</p>",
                unsafe_allow_html=True,
            )

            if st.button(
                "🤖 Regenerate Summary",
                key="regen_summary",
                help="Auto-generate summary from current body text",
            ):
                if new_body.strip():
                    r = requests.post(f"{API}/generate-summary", json={"text": new_body})
                    if r.ok:
                        new_summary = r.json()["summary"]
                        st.rerun()

        new_tags = st.text_input("Edit Tags", value=", ".join(data["tags"]))

        if st.button("Save Changes"):
            update_data = {
                "title": new_title,
                "body": new_body,
                "summary": new_summary,
                "tags": [t.strip() for t in new_tags.split(",") if t.strip()],
            }
            r = requests.put(f"{API}/notes/{data['id']}", json=update_data)
            st.success("Saved" if r.ok else r.text)

with tab2:
    st.header("Search")
    q = st.text_input("Query (FTS5 syntax)", value="*")
    tag = st.text_input("Tag filter (optional)")
    if st.button("Search"):
        params = {"q": q}
        if tag.strip():
            params["tag"] = tag.strip()
        r = requests.get(f"{API}/search", params=params)
        if r.ok:
            for item in r.json():
                st.markdown(f"**{item['id']}** — {item['title']}")
                if "snippet" in item:
                    st.markdown(item["snippet"], unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.error(r.text)

with tab3:
    st.header("Backlinks & CEQRC")
    nid2 = st.text_input("Note ID", key="nid_bk")
    if st.button("Show Backlinks"):
        r = requests.get(f"{API}/notes/{nid2}/backlinks")
        st.write(r.json())
    if st.button("Run CEQRC (probe → crystallize → connect)"):
        r = requests.post(f"{API}/notes/{nid2}/ceqrc")
        st.write(r.json())
