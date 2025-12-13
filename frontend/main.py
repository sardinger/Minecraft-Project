import streamlit as st
from dotenv import load_dotenv
import os
from PIL import Image
import requests


def call_api():
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


def main():
    header = st.container()

    with header:
        st.title("Minecraft Project Image Upload")

    if "api_data" not in st.session_state:
        st.session_state["api_data"] = None

    if st.button("Start Bot"):
        call_api()

    if st.session_state["api_data"]:
        st.subheader("Response:")
        st.json(st.session_state["api_data"])

    uploaded_img = st.file_uploader("Choose an image")
    if uploaded_img is not None:
        img = Image.open(uploaded_img)
        st.image(img)


if __name__ == "__main__":
    main()
