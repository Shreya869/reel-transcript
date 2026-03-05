import streamlit as st
import yt_dlp
import os
import tempfile
from groq import Groq

st.set_page_config(
    page_title="reel transcript",
    page_icon="🎙️",
    layout="centered",
)

st.markdown("""
<style>
    .main { max-width: 700px; }
    h1 { font-size: 1.8rem; font-weight: 700; }
    .subtitle { color: #888; font-size: 0.95rem; margin-top: -10px; margin-bottom: 30px; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🎙️ reel transcript")
st.markdown('<p class="subtitle">paste any instagram reel link → get the transcript</p>', unsafe_allow_html=True)


def get_groq_client():
    # check streamlit secrets first (for cloud deployment), then env, then nothing
    api_key = st.secrets.get("GROQ_API_KEY", None) if hasattr(st, "secrets") else None
    if not api_key:
        api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


with st.expander("💡 tip: if it fails on a private reel"):
    st.markdown("""
    instagram blocks downloads on private accounts. if that happens:

    1. open instagram in chrome, log in
    2. install the **cookies.txt** chrome extension
    3. export cookies and upload the file below
    """)

cookie_file = st.file_uploader("upload cookies.txt (optional — only needed for private reels)", type=["txt"])

reel_url = st.text_input(
    "instagram reel url",
    placeholder="https://www.instagram.com/reel/abc123/",
)

if st.button("get transcript", type="primary", use_container_width=True):
    if not reel_url.strip():
        st.error("please paste a reel url first")
    else:
        client = get_groq_client()
        if not client:
            st.error("groq api key not configured. contact the app owner.")
            st.stop()

        with tempfile.TemporaryDirectory() as tmpdir:
            # step 1: download
            with st.status("downloading reel...") as status:
                try:
                    ydl_opts = {
                        "format": "bestaudio/best",
                        "outtmpl": os.path.join(tmpdir, "audio.%(ext)s"),
                        "quiet": True,
                        "no_warnings": True,
                        "postprocessors": [{
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "128",
                        }],
                    }

                    if cookie_file:
                        cookie_path = os.path.join(tmpdir, "cookies.txt")
                        with open(cookie_path, "wb") as f:
                            f.write(cookie_file.read())
                        ydl_opts["cookiefile"] = cookie_path

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([reel_url.strip()])

                    # find the downloaded audio file
                    audio_path = os.path.join(tmpdir, "audio.mp3")
                    if not os.path.exists(audio_path):
                        files = [f for f in os.listdir(tmpdir) if f.startswith("audio")]
                        if not files:
                            raise Exception("no audio downloaded — reel may be private or url is wrong")
                        audio_path = os.path.join(tmpdir, files[0])

                    status.update(label="download complete ✓", state="complete")
                except Exception as e:
                    st.error(f"download failed: {e}")
                    st.stop()

            # step 2: transcribe via groq
            with st.status("transcribing...") as status:
                try:
                    with open(audio_path, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            file=(os.path.basename(audio_path), audio_file.read()),
                            model="whisper-large-v3",
                            response_format="verbose_json",
                        )
                    transcript = transcription.text.strip()
                    detected_language = getattr(transcription, "language", "unknown")
                    status.update(label="transcription complete ✓", state="complete")
                except Exception as e:
                    st.error(f"transcription failed: {e}")
                    st.stop()

        # show results
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("words", len(transcript.split()))
        with col2:
            st.metric("language detected", detected_language)

        st.markdown("### transcript")
        st.text_area("", transcript, height=300)

        st.markdown("---")
        st.download_button(
            "download as .txt",
            transcript,
            file_name="transcript.txt",
            mime="text/plain",
            use_container_width=True,
        )
