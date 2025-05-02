import os
import tempfile
import time
from pathlib import Path

import streamlit as st
import groq
from dotenv import load_dotenv
from pydub import AudioSegment
from audiorecorder import audiorecorder

# Load environment variables only in development
if os.getenv('ENVIRONMENT', 'development') == 'development':
    load_dotenv()

# App configuration
st.set_page_config(
    page_title="Voice Assistant with Groq AI",
    page_icon="🎤",
    layout="centered"
)

# Initialize Groq client
@st.cache_resource
def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.warning("GROQ_API_KEY is not set. Please set it in .env file or Streamlit secrets.")
    return groq.Client(api_key=api_key)

client = get_groq_client()

# Supported audio formats by Groq Whisper
SUPPORTED_FORMATS = ['flac', 'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'ogg', 'opus', 'wav', 'webm']

def safe_delete(filepath, retries=5, delay=0.1):
    """Safely delete a file with retries on Windows"""
    for i in range(retries):
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
            return
        except Exception:
            if i < retries - 1:
                time.sleep(delay)
            continue

def convert_audio_to_wav(audio_data):
    temp_orig = None
    temp_wav = None
    try:
        # Create unique temporary files
        temp_orig = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        
        # Write original audio data
        temp_orig.write(audio_data)
        temp_orig.close()  # Explicitly close the file
        
        # Convert using pydub
        audio = AudioSegment.from_file(temp_orig.name)
        audio.export(temp_wav.name, format='wav')
        
        # Read converted audio
        with open(temp_wav.name, 'rb') as wav_file:
            converted_audio = wav_file.read()
        
        return converted_audio
        
    except Exception as e:
        raise Exception(f"Error converting audio: {str(e)}")
    
    finally:
        # Clean up temporary files
        if temp_orig:
            safe_delete(temp_orig.name)
        if temp_wav:
            safe_delete(temp_wav.name)

def get_llm_response(text):
    """Get response from LLM"""
    try:
        with st.spinner("Getting AI response..."):
            completion = client.chat.completions.create(
                messages=[{
                    "role": "system",
                    "content": "You are a helpful assistant. Keep your responses concise and informative."
                }, {
                    "role": "user",
                    "content": text
                }],
                model="llama-3.3-70b-versatile",
                max_tokens=500
            )
            return completion.choices[0].message.content
    except Exception as e:
        st.error(f"LLM Error: {str(e)}")
        return f"Error getting LLM response: {str(e)}"

def text_to_speech(text):
    """Convert text to speech using PlayAI TTS model through Groq API"""
    try:
        if isinstance(text, bytes):
            text = text.decode('utf-8')
        
        with st.spinner("Converting text to speech..."):
            # Create a temporary path to save speech output
            temp_dir = tempfile.gettempdir()
            temp_filename = f"tts_output_{int(time.time())}.wav"
            temp_path = os.path.join(temp_dir, temp_filename)
            speech_file_path = Path(temp_path)
            
            # Call Groq TTS and use write_to_file method correctly
            response = client.audio.speech.create(
                model="playai-tts",
                input=text,
                voice="Atlas-PlayAI",
                response_format="wav"
            )
            
            # Use the proper write_to_file method
            response.write_to_file(speech_file_path)
            
            return str(speech_file_path)
    
    except Exception as e:
        st.error(f"TTS Error: {str(e)}")
        return None

def process_audio(audio_data):
    """Complete pipeline: Audio -> Text -> LLM -> Speech"""
    try:
        # Step 1: Transcribe audio
        with st.spinner("Transcribing audio..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                
                with open(temp_file.name, 'rb') as audio_file:
                    transcription = client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3"
                    )
                safe_delete(temp_file.name)
        
        # Step 2: Get LLM response
        llm_response = get_llm_response(transcription.text)
        
        # Step 3: Convert response to speech
        audio_response = text_to_speech(llm_response)
        
        if audio_response is None:
            st.warning("Failed to generate audio response")
            return {
                "transcription": transcription.text,
                "llm_response": llm_response,
                "audio_response": None,
                "error": "Failed to generate audio"
            }
        
        return {
            "transcription": transcription.text,
            "llm_response": llm_response,
            "audio_response": audio_response
        }
    except Exception as e:
        st.error(f"Process Audio Error: {str(e)}")
        return {
            "error": f"Error in processing: {str(e)}",
            "transcription": "",
            "llm_response": "",
            "audio_response": None
        }

# UI Components
st.title("Voice Assistant with Groq AI")
st.markdown("Speak or upload audio to get an AI response both in text and voice!")

# Session state initialization
if 'history' not in st.session_state:
    st.session_state.history = []

# Audio input selection
input_method = st.radio("Choose input method:", ["Record Audio", "Upload Audio"])

if input_method == "Record Audio":
    st.write("Click the microphone to start recording:")
    audio = audiorecorder("Click to record", "Click to stop")
    
    if len(audio) > 0:
        # Convert to bytes
        audio_bytes = audio.export().read()
        st.audio(audio_bytes, format="audio/wav")
        
        if st.button("Process Recorded Audio"):
            result = process_audio(audio_bytes)
            
            # Store results in session state
            if 'error' not in result:
                st.session_state.history.append({
                    "transcription": result["transcription"],
                    "response": result["llm_response"],
                    "audio_path": result["audio_response"]
                })
else:  # Upload Audio
    uploaded_file = st.file_uploader("Upload an audio file", type=SUPPORTED_FORMATS)
    if uploaded_file and st.button("Process Uploaded Audio"):
        audio_bytes = uploaded_file.read()
        result = process_audio(audio_bytes)
        
        # Store results in session state
        if 'error' not in result:
            st.session_state.history.append({
                "transcription": result["transcription"],
                "response": result["llm_response"],
                "audio_path": result["audio_response"]
            })

# Display conversation history
if st.session_state.history:
    st.subheader("Conversation History")
    for i, item in enumerate(st.session_state.history):
        with st.expander(f"Interaction {i+1}", expanded=(i == len(st.session_state.history)-1)):
            st.markdown("**You said:**")
            st.text(item["transcription"])
            
            st.markdown("**AI response:**")
            st.text(item["response"])
            
            if item["audio_path"]:
                st.markdown("**Audio response:**")
                with open(item["audio_path"], "rb") as audio_file:
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format="audio/wav")

# Footer
st.divider()
st.caption("Powered by Groq AI - Using LLaMa 3.3 70B Versatile, Whisper Large v3, and PlayAI TTS") 