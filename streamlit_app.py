import json, hmac
import openai
import streamlit as st

from datetime import datetime
from uuid import uuid4


SYSTEM_PROMPT = """You are a chatbot put on a gym website. You can use the following tools:

- store_snapchat_username: Store Snapchat username provided by user during chat.

Your job is to help onboard new clients and help them by providing info.
The gym is open in the city of San Francisco. You can use the following information:

Open hours: 08:00 - 22:00 Monday - Friday
Subscription fee: $5.00

If the user shows interest in joining the gym, you can provide more info,
but ask for their Snapchat username so you can send details to them."""

tools = [
    {
        "type": "function",
        "function": {
            "name": "store_snapchat_username",
            "description": "Store username provided by user during chat.",
            "parameters": {
                "type": "object",
                "properties": {"username": {"type": "string"}},
                "required": ["username"],
            },
        },
    }
]


def _store_snapchat_username(username: str):
    """Store username provided by user during chat."""
    st.warning(f"Your Snapchat username is: {username}")

    return {
        "id": uuid4().hex,
        "username": username,
        "opted_in": datetime.now().isoformat(),
        "success": True,
    }


def check_password():
    def password_entered():
        if hmac.compare_digest(
            st.session_state["password"], st.secrets["PASSWORD"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("Password incorrect")

    return False


if __name__ == "__main__":
    st.title("Snapchat Demo")
    st.caption("Streamlit app for demo purposes")

    if not check_password():
        st.stop()

    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "assistant", "content": "Hello, how can I help?"},
        ]

    for message in st.session_state["messages"]:
        info = dict(message)
        st.chat_message(info["role"]).write(info["content"])

    if prompt := st.chat_input():
        if "OPENAI_API_KEY" not in st.secrets:
            st.error("OpenAI API key is required")

        st.session_state["messages"].append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        response = (
            client.chat.completions.create(
                model="gpt-4o",
                messages=st.session_state["messages"],
                tools=tools,
            )
            .choices[0]
            .message
        )
        st.session_state["messages"].append(response)
        if response.content:
            st.chat_message("assistant").write(response.content)

        if response.tool_calls:
            for tool_call in response.tool_calls:
                fn_name = tool_call.function.name
                if fn_name == "store_snapchat_username":
                    args = json.loads(tool_call.function.arguments)
                    user = _store_snapchat_username(args["username"])
                    st.session_state["messages"].append(
                        {
                            "role": "tool",
                            "content": json.dumps(user),
                            "tool_call_id": tool_call.id,
                        }
                    )

                    new_response = (
                        client.chat.completions.create(
                            model="gpt-4o",
                            messages=st.session_state["messages"],
                        )
                        .choices[0]
                        .message
                    )
                    st.session_state["messages"].append(new_response)
                    st.chat_message("assistant").write(new_response.content)
