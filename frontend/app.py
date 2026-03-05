import streamlit as st
import requests

st.set_page_config(page_title="DBdiver", page_icon="🧠")
st.title("🧠 DBdiver - AI Database Assistant")

# Sidebar for configuration
with st.sidebar:
    st.header("Settings")
    db_url = st.text_input(
        "Database URL",
        "postgresql://user:password@localhost:5432/mydb",
        type="password"  # Hide credentials
    )
    backend_url = st.text_input("Backend URL", "http://localhost:8000")


def build_query_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/query"

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
if prompt := st.chat_input("Ask a question about your database..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            if not db_url.strip():
                st.error("❌ Please enter a valid Database URL.")
                st.stop()

            with st.spinner("Analyzing database..."):
                payload = {"question": prompt, "db_url": db_url.strip()}
                response = requests.post(
                    build_query_url(backend_url.strip()),
                    json=payload,
                    timeout=30  # Prevent hanging forever
                )
                response.raise_for_status()  # Check for 404/500 errors
                data = response.json()

            if "error" in data:
                answer = f"⚠️ **Backend Error:** {data['error']}"
                st.error(answer)
            else:
                # Format the response nicely
                user_view = data.get("formatted_result") or str(data.get("result"))
                st.markdown(user_view)
                with st.expander("See Generated SQL"):
                    st.code(data['sql'], language="sql")
                
                # Save the formatted answer to history
                answer = f"{user_view}\n\n```sql\n{data['sql']}\n```"

            st.session_state.messages.append({"role": "assistant", "content": answer})

        except requests.exceptions.ConnectionError:
            st.error("❌ Could not connect to the backend server. Is it running?")
        except Exception as e:
            st.error(f"❌ An unexpected error occurred: {e}")