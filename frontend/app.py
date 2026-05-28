import os

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in ("1", "true", "yes")

EXAMPLE_QUESTIONS = [
    "How is AAPL doing today?",
    "Compare TSLA and F",
    "What are the top gainers in tech?",
    "How is Microsoft performing?",
]

st.set_page_config(
    page_title="Stock Insights Assistant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #f3f4f6;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.25rem;
    }
    [data-testid="stSidebar"] .stButton > button {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        color: #111827;
        font-weight: 400;
        padding: 0.65rem 1rem;
        text-align: left;
        width: 100%;
        box-shadow: none;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #f9fafb;
        border-color: #d1d5db;
        color: #111827;
    }
    [data-testid="stSidebar"] .sidebar-note {
        font-size: 0.8rem;
        color: #6b7280;
        font-style: italic;
        margin-top: 1rem;
        line-height: 1.4;
    }
    [data-testid="stSidebar"] .sidebar-note code {
        background-color: #ecfdf5;
        padding: 0.1rem 0.35rem;
        border-radius: 4px;
        font-size: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "sidebar_qa" not in st.session_state:
    st.session_state.sidebar_qa = None


def fetch_insight(question: str) -> tuple[str, list[str]] | str:
    """Return (summary, symbols) on success, or an error message string."""
    try:
        response = httpx.get(
            f"{BACKEND_URL}/stocks/insight",
            params={"question": question},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["summary"], data.get("symbols", [])
    except httpx.TimeoutException:
        return "Request timed out — the backend took too long to respond."
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", "Unknown error")
        except Exception:
            detail = "Unknown error"
        return f"Error: {detail}"
    except httpx.ConnectError:
        return "Could not connect to the backend. Is the server running?"


def handle_main_chat(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Fetching data..."):
            result = fetch_insight(prompt)
            if isinstance(result, str):
                st.error(result)
                return
            summary, symbols = result
            st.write(summary)
            if symbols:
                st.caption(f"Stocks analysed: {', '.join(symbols)}")
            st.session_state.messages.append(
                {"role": "assistant", "content": summary, "symbols": symbols}
            )


def load_sidebar_answer(question: str) -> None:
    with st.spinner("Fetching..."):
        result = fetch_insight(question)
    if isinstance(result, str):
        st.session_state.sidebar_qa = {
            "question": question,
            "summary": result,
            "symbols": [],
            "error": True,
        }
    else:
        summary, symbols = result
        st.session_state.sidebar_qa = {
            "question": question,
            "summary": summary,
            "symbols": symbols,
            "error": False,
        }


with st.sidebar:
    st.markdown("## Example questions")

    for i, question in enumerate(EXAMPLE_QUESTIONS):
        if st.button(question, key=f"example_{i}", use_container_width=True):
            st.session_state.pending_sidebar_question = question
            st.rerun()

    pending = st.session_state.pop("pending_sidebar_question", None)
    if pending:
        load_sidebar_answer(pending)

    if st.session_state.sidebar_qa:
        qa = st.session_state.sidebar_qa
        st.divider()
        with st.chat_message("user"):
            st.write(qa["question"])
        with st.chat_message("assistant"):
            if qa.get("error"):
                st.error(qa["summary"])
            else:
                st.write(qa["summary"])
                if qa.get("symbols"):
                    st.caption(f"Stocks analysed: {', '.join(qa['symbols'])}")

    st.markdown(
        '<p class="sidebar-note">Demo data — replace API keys in '
        "<code>.env</code> for live quotes.</p>",
        unsafe_allow_html=True,
    )

st.title("📈 Stock Insights Assistant")
st.markdown(
    "<span style='color: gray; font-size: 1.1rem;'>by Jennifer Qiao</span>",
    unsafe_allow_html=True,
)
st.caption("Ask natural language questions about stocks and get AI-powered summaries.")

if DEMO_MODE:
    st.info(
        "Demo mode — using sample data where configured. Add real API keys to "
        "`.env` and set `DEMO_MODE=false` when ready."
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message.get("symbols"):
            st.caption(f"Stocks analysed: {', '.join(message['symbols'])}")

if prompt := st.chat_input("Ask about stocks..."):
    handle_main_chat(prompt)
