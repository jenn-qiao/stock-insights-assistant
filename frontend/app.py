import os

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Stock Insights Assistant", page_icon="📈")
st.title("📈 Stock Insights Assistant")
st.caption("Ask any question about stocks or companies.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message.get("symbols"):
            st.caption(f"Stocks analysed: {', '.join(message['symbols'])}")

if prompt := st.chat_input("e.g. How is Apple doing today? Compare Tesla and Ford."):
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
