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
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def call_starter(username):
    url = "http://localhost:5000/bot"  # TODO: this will have to change once deployed

    params = {"username": username}
    try:
        response = requests.get(url, params=params)  # Make the GET request
        if response.status_code == 200:
            data = response.json()
            st.session_state["api_data"] = data  # Store the result in session state
            st.success("API call successful!")
        else:
            st.error(f"API call failed with status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred: {e}")


def call_build(button=False):
    url = "http://localhost:5000/build"

    data = st.session_state.get("build_data")
    try:
        response = requests.post(url, json=data)  # Make the POST request
        if response.status_code == 200:
            data = response.json()
            st.session_state["api_data"] = data  # Store the result in session state
            num_blocks = data.get("blocks")
            if button:
                st.success(f"Build call successful! Blocks placed: {num_blocks}")
        else:
            st.error(f"Build call failed with status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred: {e}")


def call_analyzer(img, img_bytes, depth_str=None):
    load_dotenv()
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    tokens = int(os.getenv("TOKENS"))

    client = anthropic.Anthropic()

    prompt_path = BASE_DIR / "prompt.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
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

    message = ""
    buffer = ""

    with client.beta.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=tokens,
        betas=["files-api-2025-04-14"],
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
    ) as stream:
        for event in stream:
            if event.type == "content_block_delta":
                delta = event.delta

                if delta.type == "text_delta":
                    text = delta.text
                    message += text
                    buffer += text

                    while True:
                        # Find potential object boundaries
                        start = buffer.find('{"block_type"')
                        if start == -1:
                            break

                        # Look for the closing brace
                        end = buffer.find("}", start)
                        if end == -1:
                            break  # Not complete yet

                        # Extract and try to parse
                        potential_obj = buffer[start : end + 1]
                        try:
                            block_obj = json.loads(potential_obj)
                            # Valid block object found
                            if all(
                                k in block_obj for k in ["block_type", "x", "y", "z"]
                            ):
                                yield {"type": "block", "data": block_obj}

                            # Remove processed part from buffer
                            buffer = buffer[end + 1 :]
                        except json.JSONDecodeError:
                            # Not valid JSON, move past this opening brace
                            buffer = buffer[start + 1 :]

            elif event.type == "content_block_stop":
                break  # message is done coming in

    json_str = message.strip()

    # clean markdown response
    if json_str.startswith("```json"):
        json_str = json_str[7:]
    if json_str.startswith("```"):
        json_str = json_str[3:]
    if json_str.endswith("```"):
        json_str = json_str[:-3]

    try:
        data = json.loads(json_str)
        yield {"type": "complete", "data": data}
    except json.JSONDecodeError as e:
        print(f"Final parse error: {e}")
        yield {"type": "error", "data": json_str}


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
    username = st.text_input("Enter Minecraft username:")

    with header:
        st.title("Minecraft Project v2")

    if "api_data" not in st.session_state:
        st.session_state["api_data"] = None

    if username:
        if st.button("Start Bot"):
            call_starter(username)

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

        if st.button("Analyze Image"):
            # Convert img to bytes
            buf = BytesIO()
            img.save(buf, format=img.format)
            buf.seek(0)
            img_bytes = buf

            blocks_built = []
            status_placeholder = st.empty()
            error_placeholder = st.empty()

            for result in call_analyzer(uploaded_img, img_bytes, depth_str):
                if result["type"] == "block":
                    block = result["data"]
                    blocks_built.append(block)

                    # Build incrementally
                    build_payload = {
                        "schematic_name": "streaming_build",
                        "blocks": blocks_built,
                    }
                    st.session_state.build_data = build_payload

                    # Call build endpoint
                    call_build()

                    status_placeholder.text(
                        f"Built {len(blocks_built)} blocks so far..."
                    )

                elif result["type"] == "complete":
                    st.session_state.build_data = result["data"]
                    status_placeholder.success(
                        f"Complete! Total blocks: {len(result['data'].get('blocks', []))}"
                    )

                elif result["type"] == "error":
                    error_placeholder.error(
                        "Parsing error occurred. Build probably incomplete"
                    )
    if st.session_state.build_data is not None:
        st.code(st.session_state.build_data, language="json")

        if st.button("BUILD"):
            call_build(True)


if __name__ == "__main__":
    main()
