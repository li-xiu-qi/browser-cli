#  Video Content Q&A with CAMEL-AI

An intelligent Streamlit-based application that uses the [CAMEL-AI](https://www.camel-ai.org/) framework to allow users to extract, understand, and query the contents of YouTube videos. It leverages CAMEL toolkits and OpenAI models for transcription, summarization, and natural language Q&A.

---

##  Features

- **YouTube Video Downloader**: Fetches video content directly from YouTube using CAMEL's `VideoDownloaderToolkit`.
- **Audio Transcription**: Extracts and transcribes audio with `AudioAnalysisToolkit`.
- **Summarization Agent**: Uses `ChatAgent` with GPT-4o-mini to generate concise summaries of the transcript.
- **Question Answering**: Ask any natural language questions based on the transcript — answers are grounded in the video's content.

---

##  Toolkits & Architecture

This app utilizes the following CAMEL-AI components:

- `VideoDownloaderToolkit`: For downloading YouTube videos.
- `AudioAnalysisToolkit`: For audio-to-text transcription.
- `ChatAgent`: To summarize transcripts and answer questions using OpenAI models.

---

## ️ Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/camel-ai/camel.git
   cd examples/usecases/chat_with_youtube
   ```

2. **Set Up Virtual Environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:

   Create a `.env` file and add your OpenAI API key:

   ```env
   OPENAI_API_KEY=your_openai_api_key
   ```

5. **Install ffmpeg** (for audio extraction):

   - macOS: `brew install ffmpeg`
   - Ubuntu: `sudo apt install ffmpeg`
   - Windows: [Download from ffmpeg.org](https://ffmpeg.org/download.html)

---
##  Using Authentication Cookies with yt-dlp

YouTube may require authentication for certain videos. To allow yt-dlp to access such content, you need to provide your own `cookies.txt` file.

### Exporting Cookies from Your Browser

1. **Using a Browser Extension**:

   - **Chrome**: Install [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - **Firefox**: Install [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

   After installing the extension:

   - Navigate to [YouTube](https://www.youtube.com) and log in.
   - Click the extension icon and export the cookies.
   - Save the file as `cookies.txt` in the `examples/usecases/chat_with_youtube` directory.


### Updating the Application to Use Your Cookies

In your code, specify the path to your `cookies.txt`:

```python
video_toolkit = VideoAnalysisToolkit(cookies_path="cookies.txt")
```

Ensure that this path points to your exported `cookies.txt` file.

---

## ▶️ Running the Application

Start the Streamlit server:

```bash
streamlit run app.py
```

Then, paste a YouTube link, and the app will download the video, transcribe it, summarize it, and let you chat with it.

---

##  Project Structure

```
video-qa-camel/
├── app.py                # Main Streamlit application
├── downloads/            # Temporary video/audio files
├── .env                  # Environment variables (not committed)
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

---

##  Example Usage

1. Launch the app using Streamlit.
2. Paste a YouTube video URL.
3. Wait for the download, audio extraction, and transcription to complete.
4. View the summary.
5. Ask any question based on the video's content and get an AI-generated answer.

---

##  Notes

- This app does not yet support chunked retrieval-based Q&A for long transcripts. For scalable Q&A over long-form content, consider integrating an external vector database (e.g., Milvus, Pinecone) with chunking and embedding.
- All answers are context-aware, based on the entire transcript, but may be truncated for long videos due to model token limits.


---

##  Contributing

Feel free to open pull requests, issues, or discussions for improvements, new features, or bug fixes.

---

##  Powered by

- [CAMEL-AI](https://github.com/camel-ai/camel)
- [OpenAI GPT Models](https://openai.com/)
- [Streamlit](https://streamlit.io/)
