import streamlit as st
import yt_dlp
import whisper
import os
import tempfile
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

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
    .transcript-box {
        background: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        font-size: 1rem;
        line-height: 1.7;
        border: 1px solid #e0e0e0;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🎙️ reel transcript")
st.markdown('<p class="subtitle">paste any instagram reel link → get the transcript</p>', unsafe_allow_html=True)

# tip for private reels
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

model_size = st.select_slider(
    "transcription quality",
    options=["tiny", "base", "small"],
    value="tiny",
    help="tiny = fastest (30s), base = balanced (1min), small = most accurate (2min)"
)

if st.button("get transcript", type="primary", use_container_width=True):
    if not reel_url.strip():
        st.error("please paste a reel url first")
    else:
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

                    audio_path = os.path.join(tmpdir, "audio.mp3")
                    if not os.path.exists(audio_path):
                        # find whatever audio file was downloaded
                        files = os.listdir(tmpdir)
                        audio_files = [f for f in files if f.startswith("audio")]
                        if not audio_files:
                            raise Exception("no audio file downloaded — the reel may be private or the url is wrong")
                        audio_path = os.path.join(tmpdir, audio_files[0])

                    status.update(label="download complete ✓", state="complete")
                except Exception as e:
                    st.error(f"download failed: {e}")
                    st.stop()

            # step 2: transcribe
            with st.status(f"transcribing with whisper ({model_size})...") as status:
                try:
                    model = whisper.load_model(model_size)
                    result = model.transcribe(audio_path, fp16=False)
                    transcript = result["text"].strip()
                    detected_language = result.get("language", "unknown")
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
        st.markdown(f'<div class="transcript-box">{transcript}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.download_button(
            "download as .txt",
            transcript,
            file_name="transcript.txt",
            mime="text/plain",
            use_container_width=True,
        )

        # copy helper
        st.text_area("or copy from here", transcript, height=200)
