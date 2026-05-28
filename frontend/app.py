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
    [data-testid="stSidebar"] .sidebar-preview {
        margin-top: 1rem;
        padding-top: 0.5rem;
        border-top: 1px solid #e5e7eb;
    }
    [data-testid="stSidebar"] .sidebar-preview [data-testid="stChatMessage"] {
        background: transparent;
        padding: 0.35rem 0;
    }
    [data-testid="stSidebar"] .sidebar-preview [data-testid="stMarkdownContainer"] p {
        font-size: 0.9rem;
        line-height: 1.45;
        margin-bottom: 0.35rem;
    }
    [data-testid="stSidebar"] .sidebar-preview [data-testid="stCaptionContainer"] p {
        font-size: 0.75rem;
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
    [data-testid="stSidebar"] .sidebar-demo-footnote {
        font-size: 0.75rem;
        color: #6b7280;
        font-style: italic;
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
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
if "chat_query" not in st.session_state:
    st.session_state.chat_query = ""


def process_question(prompt: str) -> None:
    """Fetch insight and append to session history (no extra widgets)."""
    prompt = prompt.strip()
    if not prompt:
        return

    st.session_state.chat_query = prompt
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        response = httpx.get(
            f"{BACKEND_URL}/stocks/insight",
            params={"question": prompt},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": data["summary"],
                "symbols": data.get("symbols", []),
            }
        )
    except httpx.TimeoutException:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "Request timed out — the backend took too long to respond.",
            }
        )
    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", "Unknown error")
        st.session_state.messages.append(
            {"role": "assistant", "content": f"Error: {detail}"}
        )
    except httpx.ConnectError:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "Could not connect to the backend. Is the server running?",
            }
        )


def queue_question(prompt: str) -> None:
    st.session_state.chat_query = prompt
    st.session_state.run_query = prompt
    st.rerun()


def _latest_exchange() -> tuple[dict, dict | None] | None:
    messages = st.session_state.messages
    last_user_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i]["role"] == "user":
            last_user_idx = i
            break
    if last_user_idx is None:
        return None

    user = messages[last_user_idx]
    assistant = None
    if (
        last_user_idx + 1 < len(messages)
        and messages[last_user_idx + 1]["role"] == "assistant"
    ):
        assistant = messages[last_user_idx + 1]
    return user, assistant


def render_sidebar_preview() -> None:
    """Latest Q&A under example buttons (matches mockup sidebar)."""
    exchange = _latest_exchange()
    if exchange is None:
        return

    user, assistant = exchange
    st.markdown('<div class="sidebar-preview"></div>', unsafe_allow_html=True)

    with st.chat_message("user"):
        st.write(user["content"])

    if assistant is not None:
        with st.chat_message("assistant"):
            st.write(assistant["content"])
            if assistant.get("symbols"):
                st.caption(f"Stocks analysed: {', '.join(assistant['symbols'])}")

        if DEMO_MODE:
            st.markdown(
                '<p class="sidebar-demo-footnote">Demo data — replace API keys in '
                "<code>.env</code> for live quotes.</p>",
                unsafe_allow_html=True,
            )


# --- Process queued questions first (before any chat UI) ---
if run_prompt := st.session_state.pop("run_query", None):
    with st.spinner("Fetching data..."):
        process_question(run_prompt)


with st.sidebar:
    st.markdown("## Example questions")
    for i, question in enumerate(st.session_state.example_questions):
        if st.button(question, key=f"example_{i}", use_container_width=True):
            queue_question(question)

    render_sidebar_preview()

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

chat_history = st.container(height=520, border=False)
with chat_history:
    if not st.session_state.messages:
        st.caption("Ask a question below or pick an example on the left.")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message.get("symbols"):
                st.caption(f"Stocks analysed: {', '.join(message['symbols'])}")

    if DEMO_MODE and st.session_state.messages:
        st.caption(
            "Demo data — replace API keys in `.env` for live quotes."
        )


def render_search_bar() -> None:
    """Pinned search bar — must stay the last UI on the page."""
    input_col, send_col = st.columns([12, 1])
    with input_col:
        st.text_input(
            "Ask about stocks",
            key="chat_query",
            label_visibility="collapsed",
            placeholder="Ask about stocks...",
        )
    with send_col:
        if st.button("↑", key="send_query", use_container_width=True):
            if st.session_state.chat_query.strip():
                queue_question(st.session_state.chat_query)


if hasattr(st, "bottom"):
    with st.bottom():
        render_search_bar()
else:
    if chat_prompt := st.chat_input("Ask about stocks..."):
        queue_question(chat_prompt)
