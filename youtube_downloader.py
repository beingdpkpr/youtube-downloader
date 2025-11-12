import streamlit as st
import yt_dlp
import os
from pathlib import Path
import zipfile


class YouTubeDownloader:
    def __init__(self, download_path="downloads"):
        """Initialize downloader with a download directory."""
        self.download_path = Path(download_path)
        self.download_path.mkdir(exist_ok=True)

    def progress_hook(self, d, progress_bar=None, status_text=None):
        """Hook for download progress."""
        if d['status'] == 'downloading':
            if progress_bar and 'downloaded_bytes' in d and 'total_bytes' in d:
                percent = d['downloaded_bytes'] / d['total_bytes']
                progress_bar.progress(percent)
            if status_text:
                status_text.text(f"Downloading: {d.get('_percent_str', 'N/A')} at {d.get('_speed_str', 'N/A')}")
        elif d['status'] == 'finished':
            if status_text:
                status_text.text("Download complete, processing...")

    def download_video(self, url, quality="best"):
        """Download video with audio."""
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best' if quality == 'best' else f'bestvideo[height<={quality[:-1]}]+bestaudio/best',
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
        }

        try:
            print(f"Downloading Video: {self.download_path}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return True, info['title'], filename
        except Exception as e:
            return False, str(e), None

    def download_audio(self, url, format="mp3"):
        """Download only audio from video."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format,
                'preferredquality': '192',
            }],
        }

        try:
            print(f"Downloading Audio: {self.download_path}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = str(self.download_path / f"{info['title']}.{format}")
                return True, info['title'], filename
        except Exception as e:
            return False, str(e), None

    def download_playlist(self, url, download_type="video", quality="best", audio_format="mp3"):
        """Download entire playlist."""
        if download_type == "video":
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best' if quality == 'best' else f'bestvideo[height<={quality[:-1]}]+bestaudio/best',
                'outtmpl': str(self.download_path / '%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'ignoreerrors': True,  # Continue on errors
            }
        else:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(self.download_path / '%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_format,
                    'preferredquality': '192',
                }],
                'ignoreerrors': True,
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                playlist_title = info.get('title', 'playlist')
                video_count = len(info.get('entries', []))
                playlist_folder = self.download_path / playlist_title
                return True, playlist_title, video_count, str(playlist_folder)
        except Exception as e:
            return False, str(e), 0, None

    def get_video_info(self, url):
        """Get video information without downloading."""
        ydl_opts = {'quiet': True}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                duration_min = info.get('duration', 0) // 60
                duration_sec = info.get('duration', 0) % 60

                return {
                    'title': info.get('title'),
                    'duration': f"{duration_min}:{duration_sec:02d}",
                    'uploader': info.get('uploader'),
                    'views': info.get('view_count', 0),
                    'thumbnail': info.get('thumbnail'),
                    'description': info.get('description', '')[:300] + '...' if len(
                        info.get('description', '')) > 300 else info.get('description', '')
                }
        except Exception as e:
            return None

    def get_playlist_info(self, url):
        """Get playlist information without downloading."""
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # Don't download, just get info
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if 'entries' in info:
                    return {
                        'title': info.get('title'),
                        'uploader': info.get('uploader'),
                        'video_count': len(info['entries']),
                        'videos': [{'title': entry.get('title'), 'duration': entry.get('duration')}
                                   for entry in info['entries'][:10]]  # First 10 videos
                    }
                return None
        except Exception as e:
            return None

    def create_zip(self, folder_path, zip_name):
        """Create a zip file from a folder."""
        zip_path = self.download_path / f"{zip_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            folder = Path(folder_path)
            for file in folder.rglob('*'):
                if file.is_file():
                    zipf.write(file, file.relative_to(folder.parent))
        return str(zip_path)


def main():
    st.set_page_config(
        page_title="YouTube Downloader",
        page_icon="🎬",
        layout="wide"
    )

    # Custom CSS
    st.markdown("""
        <style>
        .main {
            padding: 2rem;
        }
        .stButton>button {
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header
    st.title("🎬 YouTube Video & Audio Downloader")
    st.markdown("---")

    # Initialize downloader
    downloader = YouTubeDownloader()

    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")

        content_type = st.radio(
            "Content Type",
            ["Single Video", "Playlist"],
            help="Choose to download a single video or entire playlist"
        )

        download_type = st.radio(
            "Download Type",
            ["Video", "Audio Only"],
            help="Choose whether to download video or just audio"
        )

        if download_type == "Video":
            quality = st.selectbox(
                "Video Quality",
                ["best", "1080p", "720p", "480p", "360p"],
                help="Select video quality"
            )
        else:
            audio_format = st.selectbox(
                "Audio Format",
                ["mp3", "m4a", "wav", "opus"],
                help="Select audio format"
            )

        st.markdown("---")
        st.markdown("### 📝 Instructions")
        if content_type == "Single Video":
            st.markdown("""
            1. Paste a YouTube URL
            2. Preview video info (optional)
            3. Select download options
            4. Click Download
            """)
        else:
            st.markdown("""
            1. Paste a YouTube Playlist URL
            2. Preview playlist info (optional)
            3. Select download options
            4. Click Download Playlist
            5. Wait for all videos to download
            """)

        st.markdown("---")
        st.warning("⚠️ Only download content you have permission to download.")

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        if content_type == "Single Video":
            url = st.text_input(
                "YouTube Video URL",
                placeholder="https://www.youtube.com/watch?v=...",
                help="Paste the YouTube video URL here"
            )
        else:
            url = st.text_input(
                "YouTube Playlist URL",
                placeholder="https://www.youtube.com/playlist?list=...",
                help="Paste the YouTube playlist URL here"
            )

    with col2:
        st.write("")
        st.write("")
        preview_btn = st.button("🔍 Preview Info", use_container_width=True)

    # Preview section
    if preview_btn and url:
        with st.spinner("Fetching information..."):
            if content_type == "Single Video":
                info = downloader.get_video_info(url)

                if info:
                    st.success("✅ Video found!")

                    col1, col2 = st.columns([1, 2])

                    with col1:
                        if info['thumbnail']:
                            st.image(info['thumbnail'], use_container_width=True)

                    with col2:
                        st.subheader(info['title'])
                        st.write(f"**Uploader:** {info['uploader']}")
                        st.write(f"**Duration:** {info['duration']}")
                        st.write(f"**Views:** {info['views']:,}")

                    with st.expander("📄 Description"):
                        st.write(info['description'])
                else:
                    st.error("❌ Could not fetch video information. Please check the URL.")
            else:
                info = downloader.get_playlist_info(url)

                if info:
                    st.success("✅ Playlist found!")

                    st.subheader(info['title'])
                    st.write(f"**Uploader:** {info['uploader']}")
                    st.write(f"**Total Videos:** {info['video_count']}")

                    with st.expander(f"📋 First {len(info['videos'])} Videos"):
                        for i, video in enumerate(info['videos'], 1):
                            duration = video['duration']
                            if duration:
                                mins = duration // 60
                                secs = duration % 60
                                st.write(f"{i}. {video['title']} ({mins}:{secs:02d})")
                            else:
                                st.write(f"{i}. {video['title']}")
                else:
                    st.error("❌ Could not fetch playlist information. Please check the URL.")

    # Download section
    st.markdown("---")

    download_col1, download_col2, download_col3 = st.columns([1, 1, 1])

    with download_col2:
        if content_type == "Single Video":
            download_btn = st.button(
                f"⬇️ Download {download_type}",
                type="primary",
                use_container_width=True
            )
        else:
            download_btn = st.button(
                f"⬇️ Download Playlist ({download_type})",
                type="primary",
                use_container_width=True
            )

    if download_btn:
        if not url:
            st.error("⚠️ Please enter a YouTube URL first!")
        else:
            if content_type == "Single Video":
                progress_bar = st.progress(0)
                status_text = st.empty()

                status_text.text("Starting download...")

                if download_type == "Video":
                    success, result, filename = downloader.download_video(url, quality)
                else:
                    success, result, filename = downloader.download_audio(url, audio_format)

                progress_bar.progress(100)

                if success:
                    status_text.empty()
                    st.success(f"✅ Successfully downloaded: **{result}**")
                    st.info(f"📁 Saved to: `{filename}`")

                    # Provide download button
                    if filename and os.path.exists(filename):
                        with open(filename, 'rb') as file:
                            btn = st.download_button(
                                label="💾 Download File",
                                data=file,
                                file_name=os.path.basename(filename),
                                mime='application/octet-stream'
                            )
                else:
                    status_text.empty()
                    st.error(f"❌ Download failed: {result}")
            else:
                # Playlist download
                progress_bar = st.progress(0)
                status_text = st.empty()

                status_text.text("Starting playlist download... This may take a while.")
                progress_bar.progress(10)

                if download_type == "Video":
                    success, result, count, folder = downloader.download_playlist(
                        url, "video", quality
                    )
                else:
                    success, result, count, folder = downloader.download_playlist(
                        url, "audio", audio_format=audio_format
                    )

                progress_bar.progress(90)

                if success:
                    progress_bar.progress(100)
                    status_text.empty()
                    st.success(f"✅ Successfully downloaded playlist: **{result}**")
                    st.info(f"📁 Downloaded {count} videos to: `{folder}`")

                    # Create zip file
                    if folder and os.path.exists(folder):
                        with st.spinner("Creating zip file..."):
                            zip_path = downloader.create_zip(folder, result)

                        if os.path.exists(zip_path):
                            with open(zip_path, 'rb') as file:
                                btn = st.download_button(
                                    label="📦 Download Playlist as ZIP",
                                    data=file,
                                    file_name=os.path.basename(zip_path),
                                    mime='application/zip'
                                )
                else:
                    status_text.empty()
                    st.error(f"❌ Playlist download failed: {result}")

    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: gray;'>Made with ❤️ using Streamlit and yt-dlp</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()