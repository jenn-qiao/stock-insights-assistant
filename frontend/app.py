import os
import random

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in ("1", "true", "yes")

EXAMPLE_QUESTION_POOL = [
    "How is AAPL doing today?",
    "How is Apple doing today?",
    "Compare TSLA and F",
    "Compare Tesla and Ford",
    "What are the top gainers in tech?",
    "How is Microsoft performing?",
    "How is MSFT doing today?",
    "Compare AAPL and MSFT",
    "What sector is NVDA in?",
    "How is GOOGL performing?",
    "What's happening with Amazon stock?",
    "Compare META and GOOGL",
    "How is NVIDIA doing today?",
    "Tell me about Berkshire Hathaway",
    "How is JPMorgan doing?",
    "Compare AMD and INTC",
    "What is Tesla's P/E ratio?",
    "How is Netflix performing?",
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
        padding-top: 1.5rem;
    }
    [data-testid="stSidebar"] h2 {
        font-size: 1.1rem;
        font-weight: 700;
        color: #374151;
        margin-bottom: 0.75rem;
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
        transition: border-color 0.15s ease, background-color 0.15s ease;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #f9fafb;
        border-color: #d1d5db;
        color: #111827;
    }
    [data-testid="stSidebar"] .stButton > button:active,
    [data-testid="stSidebar"] .stButton > button:focus {
        background-color: #ffffff;
        border-color: #9ca3af;
        color: #111827;
        box-shadow: none;
    }
    [data-testid="stSidebar"] .sidebar-note {
        font-size: 0.8rem;
        color: #6b7280;
        font-style: italic;
        margin-top: 1.5rem;
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
if "example_questions" not in st.session_state:
    st.session_state.example_questions = random.sample(
        EXAMPLE_QUESTION_POOL,
        min(4, len(EXAMPLE_QUESTION_POOL)),
    )


def handle_question(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Fetching data..."):
            try:
                response = httpx.get(
                    f"{BACKEND_URL}/stocks/insight",
                    params={"question": prompt},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                summary = data["summary"]
                symbols = data.get("symbols", [])

                st.write(summary)
                if symbols:
                    st.caption(f"Stocks analysed: {', '.join(symbols)}")

                st.session_state.messages.append(
                    {"role": "assistant", "content": summary, "symbols": symbols}
                )

            except httpx.TimeoutException:
                st.error("Request timed out — the backend took too long to respond.")
            except httpx.HTTPStatusError as e:
                detail = e.response.json().get("detail", "Unknown error")
                st.error(f"Error: {detail}")
            except httpx.ConnectError:
                st.error("Could not connect to the backend. Is the server running?")


with st.sidebar:
    st.markdown("## Example questions")
    for i, question in enumerate(st.session_state.example_questions):
        if st.button(question, key=f"example_{i}", use_container_width=True):
            st.session_state.pending_prompt = question
            st.rerun()

    st.markdown(
        '<p class="sidebar-note">Demo data — replace API keys in '
        "<code>.env</code> for live quotes.</p>",
        unsafe_allow_html=True,
    )

st.title("📈 Stock Insights Assistant")
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

prompt = st.session_state.pop("pending_prompt", None)
if prompt is None:
    prompt = st.chat_input("Ask about stocks...")

if prompt:
    handle_question(prompt)
