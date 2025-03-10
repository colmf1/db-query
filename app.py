import streamlit as st
import pandas as pd
import base64
import os
from DB_Query import Q

if 'q' not in st.session_state:
    st.session_state.q = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'passcode_validated' not in st.session_state:
    st.session_state.passcode_validated = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'using_dummy_data' not in st.session_state:
    st.session_state.using_dummy_data = False

def validate_passcode(passcode):
    pcode = os.getenv('PASSCODE')
    return passcode == pcode

def upload_csv():
    try:
        if not validate_passcode(passcode):
            st.error("Incorrect passcode.")
            return
        else:
            st.session_state.passcode_validated = True
            if st.session_state.using_dummy_data:
                try:
                    df = pd.read_csv("export.csv")
                    if df.empty:
                        st.error("The dummy CSV file is empty.")
                        return
                    
                    st.session_state.df = df
                    st.session_state.q = Q(df)
                    st.success("Dummy data loaded successfully!")
                    
                    with st.expander("Preview Data"):
                        st.dataframe(df.head(10), use_container_width=True)
                except FileNotFoundError:
                    st.error("Dummy data file 'export.csv' not found in the current directory.")
                except Exception as e:
                    st.error(f"Error processing dummy data: {str(e)}")            
            else:
                try:
                    df = pd.read_csv(uploaded_file)
                    if df.empty:
                        st.error("The uploaded CSV file is empty.")
                        return
                    
                    st.session_state.df = df
                    st.session_state.q = Q(df, model='gpt-4o-mini')
                    st.success("CSV file uploaded successfully")
                    
                    with st.expander("Preview Data"):
                        st.dataframe(df.head(10), use_container_width=True)
                except Exception as e:
                    st.error(f"Error processing CSV: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")

def chat_with_Q():
    if st.session_state.q is None:
        st.error("Please upload a CSV file or use dummy data first.")
        return
    
    if not user_input:
        return
    
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    
    try:
        text, img = st.session_state.q.ask_Q(user_input)
        
        if not text and not img:
            reply = {"role": "assistant", "content": "I was unable to answer that question."}
        elif img:
            if text:
                reply = {"role": "assistant", "content": text, "image": img}
            else:
                reply = {"role": "assistant", "content": "", "image": img}
        else:
            reply = {"role": "assistant", "content": text}
        
        st.session_state.chat_history.append(reply)
    except Exception as e:
        st.error(f"Error processing your request: {str(e)}")

st.title("Ask Q")
st.subheader("Upload your CSV and chat with Q")

with st.sidebar:
    st.header("Setup")
    passcode = st.text_input("Enter Passcode", type="password")
    if passcode:
        st.session_state.passcode_validated == True

    use_dummy = st.checkbox("Use dummy data (export.csv)", value=st.session_state.using_dummy_data)
    st.session_state.using_dummy_data = use_dummy
    
    if not use_dummy:
        uploaded_file = st.file_uploader("Upload your CSV file", type="csv")
    else:
        uploaded_file = None
    
    upload_button_text = "Load Dummy Data" if use_dummy else "Upload and Initialize"
    upload_button = st.button(upload_button_text, use_container_width=True)
    
    if upload_button:
        upload_csv()
    
    if st.session_state.df is not None:
        data_source = "Dummy data" if st.session_state.using_dummy_data else "Uploaded CSV"
        st.success(f"{data_source} loaded successfully")
        st.metric("Rows", st.session_state.df.shape[0])
        st.metric("Columns", st.session_state.df.shape[1])

if st.session_state.passcode_validated and st.session_state.df is not None:
    st.header("Chat with your data")
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.chat_message("user").write(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(message["content"])
                    if "image" in message:
                        img_data = base64.b64decode(message["image"])
                        st.image(img_data)

    user_input = st.chat_input("Ask me something about your data... (Which brand seen the highest growth in 2024?")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        chat_with_Q()
        st.rerun()
