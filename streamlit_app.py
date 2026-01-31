import os
import re
import streamlit as st

from pdf2image import convert_from_path
from PIL import Image

from config import BASE_DIR
from redis_search import keyword_file_search

st.markdown("""
<style>
/* PDF preview image styling */
div[data-testid="stImage"] img {
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 12px;
    background-color: #fafafa;
}
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "results" not in st.session_state:
    st.session_state.results = []

if "last_query" not in st.session_state:
    st.session_state.last_query = ""


# Helpers
def highlight_query(text: str, query: str) -> str:
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"**{m.group(0)}**", text)


@st.cache_data(show_spinner=False)
def load_pdf_images(file_path: str):
    """
    Convert PDF to list of PIL Images (cached).
    Works reliably across all browsers.
    """
    return convert_from_path(file_path, dpi=150)


# UI
st.set_page_config(page_title="Government Orders Search", layout="wide")
st.title("📄 Government Orders Search System")

query_text = st.text_input(
    "Enter your search query",
    placeholder="e.g. pwd"
)

# Search action (sets state only)
run_search = False

if st.button("Search"):
    run_search = True

if query_text.strip() and query_text != st.session_state.last_query:
    run_search = True

if run_search and query_text.strip():
    st.session_state.results = keyword_file_search(query_text)
    st.session_state.last_query = query_text

# Render results (persistent)
results = st.session_state.results
query = st.session_state.last_query

if results:
    st.success(f"Found {len(results)} files.")

    for res in results:
        file_path = os.path.join(BASE_DIR, res["file_location"])
        file_name = res["filename"]

        # ---- Stable session keys ----
        open_key = f"open_{file_name}"
        page_key = f"page_{file_name}"

        if open_key not in st.session_state:
            st.session_state[open_key] = False
        if page_key not in st.session_state:
            st.session_state[page_key] = 1

        # ---- Filename toggle (accordion) ----
        if st.button(f"📄 {file_name}", key=f"btn_{file_name}"):
            st.session_state[open_key] = not st.session_state[open_key]

        # ---- Matched line ----
        st.markdown(
            highlight_query(res["matched_line"], query)
        )

        # ---- Inline PDF preview (images) ----
        if st.session_state[open_key]:
            pages = load_pdf_images(file_path)
            total_pages = len(pages)

            # Clamp page number
            page = st.session_state[page_key]
            page = max(1, min(page, total_pages))
            st.session_state[page_key] = page

            # Display page
            left_pad, pdf_col, right_pad = st.columns([1, 4, 1])

            with pdf_col:
                st.image(
                    pages[page - 1],
                    width=700
                )

                st.markdown('</div>', unsafe_allow_html=True)

            # Navigation controls
            nav_left, nav_spacer, nav_right = st.columns([1, 4, 1])

            with nav_left:
                if st.button("⬅ Prev", key=f"prev_{file_name}"):
                    st.session_state[page_key] = max(1, page - 1)

            with nav_right:
                if st.button("Next ➡", key=f"next_{file_name}"):
                    st.session_state[page_key] = min(total_pages, page + 1)

            st.caption(f"Page {page} of {total_pages}")

        st.divider()

elif query_text.strip():
    st.warning("No files found.")
