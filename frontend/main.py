import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
from transformers import pipeline
import os
import requests
import anthropic
import json
import numpy as np


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


def call_build():
    url = "http://localhost:5000/build"

    data = st.session_state.get("build_data")
    try:
        response = requests.post(url, json=data)  # Make the POST request
        if response.status_code == 200:
            data = response.json()
            st.session_state["api_data"] = data  # Store the result in session state
            num_blocks = data.get("blocks")
            st.success(f"Build call successful! Blocks placed: {num_blocks}")
        else:
            st.error(f"Build call failed with status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred: {e}")


def call_analyzer(img, img_bytes, depth_str=None):
    load_dotenv()
    claude_key = os.getenv("ANTHROPIC_API_KEY")

    client = anthropic.Anthropic()

    with open("prompt.txt", "r", encoding="utf-8") as f:
        prompt = f.read()

    if depth_str:
        prompt = f"""{prompt}
        ---
        Depth information (16x16 grid, normalized: 0 = far, 1 = near):

        {depth_str}

        Use this depth grid to reason about vertical structure, height changes,
        and relative block placement.
        """

    image_data = client.beta.files.upload(
        file=(img.name, img_bytes.getvalue(), img.type)
    )
    print("Image id: ", image_data.id)

    message = client.beta.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=20000,
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


def resize_img(img):
    w, h = img.size
    longer_edge = w if w > h else h
    if longer_edge > 1568:
        max_size = (1568, 1568)
        img.thumbnail(max_size, Image.LANCZOS)

    return img


def normalize_depth(grid):
    grid = grid.astype("float32")

    min = grid.min()
    max = grid.max()

    if max > min:
        return (grid - min) / (max - min)
    else:
        return np.zeros_like(grid)


@st.cache_resource
def load_depth_model():
    return pipeline(
        task="depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf"
    )


def main():
    model = load_depth_model()
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

    if "build_data" not in st.session_state:
        st.session_state.build_data = None

    use_depth = st.toggle("Use Depth Model")
    depth_str = None

    uploaded_img = st.file_uploader("Choose an image")
    if uploaded_img is not None:
        img = Image.open(uploaded_img)
        img = resize_img(img)

        if use_depth:
            depth = model(img)["depth"]
            depth = depth.resize(
                (16, 16), Image.BILINEAR
            )  # TODO: mess with low-res grid size (16x16 currently)
            depth_np = np.array(depth)
            depth_grid = normalize_depth(depth_np)
            depth_list = depth_grid.round(3).tolist()
            depth_str = json.dumps(depth_list)

            # Display depth
            st.subheader("Depth Grid (16×16, normalized)")

            st.text("\n".join(" ".join(f"{v:0.2f}" for v in row) for row in depth_grid))

        st.image(img)
        print(img.size)

        if st.button("Analyze Image"):
            # Convert img to bytes
            buf = BytesIO()
            img.save(buf, format=img.format)
            buf.seek(0)
            img_bytes = buf

            st.session_state.build_data = call_analyzer(
                uploaded_img, img_bytes, depth_str
            )
    if st.session_state.build_data is not None:
        st.code(st.session_state.build_data, language="json")

        if st.button("BUILD"):
            call_build()


if __name__ == "__main__":
    main()
