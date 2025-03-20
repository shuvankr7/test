import streamlit as st
import torch
import os
import whisper
import wave
import time
from langchain_groq import ChatGroq
from streamlit_mic_recorder import mic_recorder

# Set environment variables
os.environ["USER_AGENT"] = "RAG-Chat-Assistant/1.0"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# API Key and Model Config
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEFAULT_MODEL = "llama3-70b-8192"
DEFAULT_TEMPERATURE = 0.5
DEFAULT_MAX_TOKENS = 1024

# Load Whisper model
@st.cache_resource
def load_whisper_model():
    try:
        model = whisper.load_model("base", device="cpu")
        return model
    except Exception as e:
        st.error(f"Error loading Whisper model: {e}")
        return None

# Initialize RAG System
@st.cache_resource
def initialize_rag_system():
    if not GROQ_API_KEY:
        st.error("Missing API key for Groq LLM.")
        return None
    try:
        return ChatGroq(
            api_key=GROQ_API_KEY,
            model=DEFAULT_MODEL,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=DEFAULT_MAX_TOKENS
        )
    except Exception as e:
        st.error(f"Error initializing RAG system: {e}")
        return None

# Process Transaction Message
def process_transaction_message(message, llm):
    if llm is None:
        return {"error": "RAG system is not initialized."}
    
    system_prompt = (
        "Extract structured details from this transaction message as JSON."
        " Fields: Amount, Transaction Type, Bank Name, Card Type, Paid To, Merchant, Transaction Mode,"
        " Transaction Date, Reference Number, and Tag (spending category)."
        " If data is missing, set it to null. Assume cash if mode is not mentioned."
        " Just return JSON, no extra text."
    )
    
    input_prompt = f"{system_prompt}\nMessage: {message}"
    response = llm.invoke(input_prompt)
    try:
        return response.content if hasattr(response, 'content') else response
    except Exception as e:
        return {"error": str(e)}

# Streamlit UI
st.title("Voice-Based Transaction Analyzer")
st.sidebar.header("Settings")

# Browser Mic Audio Capture
audio_bytes = mic_recorder(start_prompt="Start Recording", stop_prompt="Stop Recording", key="mic")

if audio_bytes:
    st.success("Recording complete! Processing audio...")
    temp_file_path = "temp_audio.wav"
    
    with open(temp_file_path, "wb") as f:
        f.write(audio_bytes)
    
    whisper_model = load_whisper_model()
    if whisper_model:
        result = whisper_model.transcribe(temp_file_path)
        transcription = result.get("text", "").strip()
        
        if transcription:
            st.session_state.transcription = transcription
        else:
            st.error("No transcription output.")
    else:
        st.error("Whisper model failed to load.")

# Display transcription and allow edits
if "transcription" in st.session_state:
    st.subheader("Transcription")
    text_input = st.text_area("Edit the transcription if needed", value=st.session_state.transcription, key="edited_text")
    final_text = text_input.strip()
    
    # Process extracted text
    with st.status("Processing transaction details...", expanded=True) as status:
        rag_llm = initialize_rag_system()
        processed_result = process_transaction_message(final_text, rag_llm)
        st.session_state.final_output = processed_result
        status.update(label="Processing complete!", state="complete", expanded=False)

# Display extracted transaction details
if "final_output" in st.session_state:
    st.subheader("Extracted Transaction Details")
    st.json(st.session_state.final_output)
