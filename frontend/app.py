"""Streamlit UI for the Stock Insights Assistant."""

import os
import random

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

EXAMPLE_QUESTIONS = [
    "How is AAPL doing today?",
    "How is TSLA doing today?",
    "How is NVDA doing today?",
    "How is MSFT doing today?",
    "How is GOOGL doing today?",
    "How is AMZN doing today?",
    "Compare PLTR and IONQ",
    "Compare AAPL and MSFT",
    "Compare NVDA and AMD",
    "Compare GOOGL and META",
    "What sector is AAPL in?",
    "What sector is TSLA in?",
    "What is the market cap of NVDA?",
    "How is Microsoft performing?",
    "How is Apple performing?",
    "What are TSLA's key stats today?",
]


def _init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "example_questions" not in st.session_state:
        st.session_state.example_questions = random.sample(EXAMPLE_QUESTIONS, 4)
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None


def _render_assistant_reply(question: str) -> None:
    with st.chat_message("assistant"):
        with st.spinner("Fetching data and generating insights…"):
            try:
                response = httpx.get(
                    f"{BACKEND_URL}/stocks/insight",
                    params={"question": question},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                summary = data["summary"]
                symbols = data.get("symbols", [])

                st.markdown(summary)
                if symbols:
                    st.caption(f"Stocks analysed: {', '.join(symbols)}")

                st.session_state.messages.append(
                    {"role": "assistant", "content": summary, "symbols": symbols}
                )

            except httpx.TimeoutException:
                msg = "Request timed out — the backend took too long to respond."
                st.error(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
            except httpx.HTTPStatusError as e:
                detail = e.response.json().get("detail", "Unknown error")
                if "Could not identify" in detail or "UNKNOWN" in detail:
                    msg = (
                        "I need a specific stock to look up. "
                        "Try: \"How is Apple doing?\" or \"Compare TSLA and F\"."
                    )
                else:
                    msg = f"Error: {detail}"
                st.warning(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
            except httpx.ConnectError:
                msg = "Could not connect to the backend. Is the server running?"
                st.error(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})
            except Exception:
                msg = "Something went wrong. Please try again in a moment."
                st.error(msg)
                st.session_state.messages.append({"role": "assistant", "content": msg})


def _handle_question(question: str) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    _render_assistant_reply(question)


def main() -> None:
    st.set_page_config(
        page_title="Stock Insights Assistant",
        page_icon="📈",
        layout="centered",
    )

    _init_session_state()

    st.title("📈 Stock Insights Assistant")
    st.caption("Ask natural language questions about stocks and get AI-powered summaries.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("symbols"):
                st.caption(f"Stocks analysed: {', '.join(message['symbols'])}")

    # Handle sidebar question after history so it renders inline without duplication
    if st.session_state.pending_question:
        question = st.session_state.pending_question
        st.session_state.pending_question = None
        _handle_question(question)

    typed = st.chat_input("Ask about stocks…")
    if typed:
        _handle_question(typed)

    with st.sidebar:
        st.header("Example questions")
        for example in st.session_state.example_questions:
            if st.button(example, use_container_width=True, key=f"example_{example}"):
                st.session_state.pending_question = example
                st.rerun()

        st.divider()
        st.markdown(
            "Market data from [Finnhub.io](https://finnhub.io/) — "
            "quotes, volume, news, and analyst ratings."
        )
        st.caption("Summaries powered by OpenAI.")


if __name__ == "__main__":
    main()
