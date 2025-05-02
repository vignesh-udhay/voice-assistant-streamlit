# Voice Assistant with Groq AI

A Streamlit-based voice assistant application that uses Groq AI for text generation and speech processing.

## Deployment on Hugging Face Spaces

1. Create a new Space on Hugging Face:

   - Go to <https://huggingface.co/spaces>
   - Click "Create new Space"
   - Choose "Docker" as the SDK
   - Name your space and set it to public/private as desired

2. Configure your Space:

   - In your Space's settings, add the following environment variables:
     - `GROQ_API_KEY`: Your Groq API key

3. Push your code:

   - Clone your Space's repository
   - Copy all the files from this repository into your Space's repository
   - Push the changes to Hugging Face

4. The Space will automatically build and deploy your application

## Local Development

1. Clone the repository
2. Create a `.env` file with your Groq API key:

   ```env
   GROQ_API_KEY=your_api_key_here
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:

   ```bash
   streamlit run src/streamlit_app.py
   ```

## Features

- Voice recording and transcription
- AI-powered responses using Groq's LLaMa 3.3 70B model
- Text-to-speech conversion
- Conversation history
- Support for multiple audio formats

## Requirements

- Python 3.10+
- FFmpeg
- Groq API key
