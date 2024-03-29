import openai
import time
import datetime
import uuid
import streamlit as st
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Coach Aidge - Virtual Life Coach")
 
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;} 
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.markdown("""
    <style>
           .block-container {
                padding-top: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
    </style>
    """, unsafe_allow_html=True)

# Function to update the run status (simulating the retrieval process)
def update_run_status():
    # Retrieving run status
    st.session_state.run = client.beta.threads.runs.retrieve(
        thread_id=st.session_state.thread.id,
        run_id=st.session_state.run.id,
    )
   
def display_results():
                        
    # If run is completed, get messages
    st.session_state.messages = client.beta.threads.messages.list(
        thread_id=st.session_state.thread.id
    )
    for message in reversed(st.session_state.messages.data):
        if message.role in ["user"]: 
            with st.chat_message('user',avatar='https://static.wixstatic.com/media/b748e0_2cdbf70f0a8e477ba01940f6f1d19ab9~mv2.png'):
                for content_part in message.content:
                    message_text = content_part.text.value
                    st.markdown(message_text)
        elif message.role in ["assistant"]: 
            with st.chat_message('assistant',avatar='https://static.wixstatic.com/media/b748e0_fb82989e216f4e15b81dc26e8c773c20~mv2.png'):
                for content_part in message.content:
                    message_text = content_part.text.value
                    st.markdown(message_text)

# Function to find next empty Google Sheets row
def find_next_empty_row(sheet):
    all_values = sheet.get_all_values()
    return len(all_values) + 1

#Use creds to create a client to interact with the Google Drive API
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
google_service_account_info = st.secrets['google_service_account']
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_service_account_info, scope)
gclient = gspread.authorize(creds)

# Initialize the client
client = OpenAI()
sheet = gclient.open(st.secrets["spreadsheet"]).sheet1
    
# Your chosen model
MODEL = "gpt-4-1106-preview"


# Initialize session state variables

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "run" not in st.session_state:
    st.session_state.run = {"status": None}

if "messages" not in st.session_state:
    st.session_state.messages = []

if "retry_error" not in st.session_state:
    st.session_state.retry_error = 0

if 'prompt' not in st.session_state:
    st.session_state.prompt = ''

if 'input_count' not in st.session_state:
    st.session_state.input_count = 0


# Step 1:  Retrieve an Assistant if not already created
# Initialize OpenAI assistant
if "assistant" not in st.session_state:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    st.session_state.assistant = openai.beta.assistants.retrieve(st.secrets["OPENAI_ASSISTANT"])
    st.session_state.thread = client.beta.threads.create(
        metadata={'session_id': st.session_state.session_id}
    )

# Get the current date and time
current_datetime = datetime.datetime.now()
formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")  # Format as desired

st.markdown("**Tell me what's on your mind and let's see if I can help!**")    

typed_input = st.chat_input("How can I help you elevate your life?")

# Check if there is typed input
if typed_input:
    st.session_state.prompt = typed_input 
    st.session_state.input_count += 1

#Chat input and message creation
if st.session_state.input_count >= 2:
        with st.spinner("Thinking ......give me a minute"):
            time.sleep(3)
        with st.chat_message('assistant', avatar='https://static.wixstatic.com/media/b748e0_fb82989e216f4e15b81dc26e8c773c20~mv2.png'):
            st.write("I'm sorry, I can only support one submission at a time. Could you please re-enter your question?")
        st.session_state.input_count = 0
elif st.session_state.prompt and (st.session_state.input_count < 2):
    with st.spinner("Thinking ......give me a minute"):
         time.sleep(3)  # Simulate immediate delay
    if st.session_state.input_count == 1:
        st.session_state.message = client.beta.threads.messages.create(
            thread_id=st.session_state.thread.id,
            role="user",
            content=st.session_state.prompt
        )

        # Step 4: Run the Assistant
        st.session_state.run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread.id,
            assistant_id=st.session_state.assistant.id
        )
        update_run_status() 
            
        # Handle run status
        # Check and handle the run status
        while st.session_state.run.status not in ["completed", "max_retries"]:
            if st.session_state.run.status == "in_progress":
                with st.spinner("Thinking ......give me a minute"):
                   time.sleep(10)  # Simulate delay
                update_run_status()  # Update the status after delay
           
            elif st.session_state.run.status == "failed":
                st.session_state.retry_error += 1
                if st.session_state.retry_error < 3:
                    st.write("Run failed, retrying ......")
                    update_run_status()
                     
                else:
                    st.error("FAILED: The OpenAI API is currently processing too many requests. Please try again later ......")

            elif st.session_state.run.status != "completed":
                # Simulate updating the run status
                update_run_status()
                if st.session_state.retry_error < 3:
                    time.sleep(2)  # Simulate delay
        display_results()

    # Find the next empty row
    next_row = find_next_empty_row(sheet)
    # Write data to the next row
    sheet.update(f"A{next_row}:B{next_row}", [[formatted_datetime, st.session_state.prompt]])

    st.session_state.input_count = 0
