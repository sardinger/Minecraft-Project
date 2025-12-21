import streamlit as st
from dotenv import load_dotenv
import os
from PIL import Image
import requests
import anthropic
import json


def call_starter():
    url = "http://localhost:5000/bot"  # TODO: this will have to change once deployed
    try:
        response = requests.get(url)  # Make the GET request
        if response.status_code == 200:
            data = response.json()
            st.session_state["api_data"] = data  # Store the result in session state
            st.success("API call successful!")
        else:
            st.error(f"API call failed with status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred: {e}")


def call_analyzer(img):
    load_dotenv()
    claude_key = os.getenv("ANTHROPIC_API_KEY")

    client = anthropic.Anthropic()

    with open("prompt.txt", "r", encoding="utf-8") as f:
        prompt = f.read()

    image_data = client.beta.files.upload(file=(img.name, img.getvalue(), img.type))
    print("Image id: ", image_data.id)

    message = client.beta.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        betas=["files-api-2025-04-14", "structured-outputs-2025-11-13"],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "file", "file_id": image_data.id},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        output_format={
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "schematic_name": {"type": "string"},
                    "blocks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "block_type": {"type": "string"},
                                "x": {"type": "integer"},
                                "y": {"type": "integer"},
                                "z": {"type": "integer"},
                            },
                            "required": ["block_type", "x", "y", "z"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["schematic_name", "blocks"],
                "additionalProperties": False,
            },
        },
    )

    json_str = message.content[0].text.strip()
    if not json_str.endswith("}"):
        return json_str
    else:
        data = json.loads(json_str)
        return data


def main():
    header = st.container()

    with header:
        st.title("Minecraft Project Image Upload")

    if "api_data" not in st.session_state:
        st.session_state["api_data"] = None

    if st.button("Start Bot"):
        call_starter()

    if st.session_state["api_data"]:
        st.subheader("Response:")
        st.json(st.session_state["api_data"])

    uploaded_img = st.file_uploader("Choose an image")
    if uploaded_img is not None:
        img = Image.open(uploaded_img)
        st.image(img)

        if st.button("Analyze Image"):
            data = call_analyzer(uploaded_img)
            st.code(data, language="json")


if __name__ == "__main__":
    main()
