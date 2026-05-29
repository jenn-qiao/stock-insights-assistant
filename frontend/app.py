"""Streamlit UI for the Stock Insights Assistant."""

import os
import random

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

EXAMPLE_QUESTIONS = [
    "How is AAPL doing today?",
    "How has TSLA performed this week?",
    "How has NVDA performed this month?",
    "How is MSFT performing this year?",
    "Give me a quick summary of Amazon stock",
    "What's happening with META today?",
    "How is Apple performing lately?",
    "How is Tesla doing compared to the market?",
    "What's going on with Nvidia stock?",
    "Compare AAPL and MSFT",
    "Compare NVDA vs AMD",
    "Compare TSLA and RIVN",
    "Which stock looks stronger today: META or GOOGL?",
    "How does Amazon compare to Walmart?",
    "What sector is AAPL in?",
    "What industry is NVDA in?",
    "What is Tesla's market cap?",
    "What are Apple's key stats today?",
    "Does Google pay a dividend?",
    "What is Amazon's P/E ratio?",
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
                status = e.response.status_code
                try:
                    detail = e.response.json().get("detail", "")
                except Exception:
                    detail = ""

                if "Could not identify" in detail or "UNKNOWN" in detail:
                    msg = "I couldn't identify a stock from that — try a specific ticker or company name. e.g. \"How is Apple doing?\" or \"Compare TSLA and F\"."
                    st.warning(msg)
                elif "Did you mean" in detail:
                    # SUGGEST path — already a friendly message from the backend
                    st.warning(detail)
                    msg = detail
                elif "not found" in detail.lower() and status == 404:
                    # e.g. "Stock 'FAKE' not found" — valid ticker format but unknown symbol
                    symbol = detail.replace("Stock '", "").replace("' not found", "").strip()
                    msg = (
                        f"I couldn't find a stock with the ticker **{symbol}**. "
                        "This app covers US-listed stocks and ETFs — double-check the symbol, "
                        "try the full company name, or ask about another company."
                    )
                    st.warning(msg)
                elif "timed out" in detail.lower():
                    msg = "The market data provider is taking too long to respond. Please try again in a moment."
                    st.error(msg)
                elif "rate" in detail.lower() or status == 429:
                    msg = "Too many requests — the data provider is rate-limiting us. Please wait a few seconds and try again."
                    st.warning(msg)
                elif "not configured" in detail.lower() or "api key" in detail.lower():
                    msg = "The assistant isn't fully configured yet. Please contact support."
                    st.error(msg)
                elif "Could not extract stock tickers" in detail or "Failed to generate" in detail:
                    msg = "Something went wrong while analysing your question. Please try rephrasing it."
                    st.error(msg)
                elif "Could not reach" in detail.lower():
                    msg = "Could not reach the market data provider. Please try again in a moment."
                    st.error(msg)
                elif status == 500:
                    msg = "An unexpected error occurred on the server. Please try again."
                    st.error(msg)
                else:
                    msg = "Something went wrong. Please try again in a moment."
                    st.error(msg)

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
    st.caption("Ask questions about stocks and get AI-powered summaries.")

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
        st.markdown("Market data from [Finnhub.io](https://finnhub.io/)")
        st.caption("Summaries powered by OpenAI.")


if __name__ == "__main__":
    main()
