import streamlit as st
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, video
import tempfile
import os
import zipfile
import random

st.set_page_config(page_title="🎬 Auto Video Editor", layout="centered")
st.title("🎥 Auto Video Editor")

# Upload video
video_file = st.file_uploader("Upload a video", type=["mp4", "mov", "avi", "mkv"])

if video_file:  # video has been uploaded
    st.video(video_file)

    # Load the video temporarily to get duration
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_vid:
        temp_vid.write(video_file.read())
        temp_video_path = temp_vid.name

    video_clip = VideoFileClip(temp_video_path)
    video_duration = video_clip.duration
    video_clip.close()

    # Initialize default clip timings in session state
    if "clip_timings_text" not in st.session_state:
        st.session_state.clip_timings_text = "0, 5\n10, 15\n20, 25"

    st.markdown("### 📋 Paste Clip Timings")
    st.markdown("Each line: `start_time,end_time` (seconds)")
    st.code("0, 5\n10, 15\n20, 25")
    clip_timings_text = st.text_area("Clip Timings", value=st.session_state.clip_timings_text)

    # Randomize timings button
    if st.button("🎲 Randomize Timings"):
        num_clips = 3  # You can change this or make it dynamic
        randomized = []
        for _ in range(num_clips):
            start = round(random.uniform(0, video_duration - 1), 2)
            end = round(random.uniform(start + 0.5, video_duration), 2)
            randomized.append(f"{start}, {end}")
        st.session_state.clip_timings_text = "\n".join(randomized)

    # Initialize default clip speeds in session state
    if "speed_multipliers_text" not in st.session_state:
        st.session_state.speed_multipliers_text = "1.0\n1.5\n2.0"

    st.markdown("### ⏩ Paste Speed Multipliers")
    st.markdown("Each line: `1.0` (normal), `2.0` (2x faster), `0.5` (half speed)")
    st.code("1.0\n2.0\n0.5")
    speed_multipliers_text = st.text_area("Speed Multipliers", value=st.session_state.speed_multipliers_text)
    
    # Randomize speeds button
    if st.button("🎲 Randomize Speeds"):
        num_clips = 3  # You can change this or make it dynamic
        randomized = []
        for _ in range(num_clips):
            speed = round(random.weibullvariate(1.6, 2), 2)
            randomized.append(f"{speed}")
        st.session_state.speed_multipliers_text = "\n".join(randomized)

    st.markdown("### 🖋️ Paste Overlay Texts")
    st.markdown("Each line = custom text for that clip.")
    st.code("First Clip\nSecond Clip\nThird Clip")
    overlay_texts_text = st.text_area("Overlay Texts Per Clip", value="Clip 1 is a test to see if captions get moved down automatically hehehehe\nClip 2\nClip 3")

    if st.button("🚀 Generate Edited Clips"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_input:
            temp_input.write(video_file.read())
            temp_input_path = temp_input.name

        # Parse clip timings
        clip_timings = []
        for line in clip_timings_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                start_str, end_str = line.split(",")
                start, end = float(start_str.strip()), float(end_str.strip())
                clip_timings.append((start, end))
            except Exception as e:
                st.warning(f"Skipping invalid timing line: '{line}'. Error: {e}")

        # Parse speed multipliers
        speed_multipliers = []
        for line in speed_multipliers_text.splitlines():
            line = line.strip()
            if line == "":
                continue
            try:
                speed = float(line)
                speed_multipliers.append(speed)
            except Exception as e:
                st.warning(f"Skipping invalid speed line: '{line}'. Error: {e}")

        # Parse overlay texts
        overlay_texts = [line.strip() for line in overlay_texts_text.splitlines()]

        output_files = []

        video_clip = VideoFileClip(temp_input_path).with_effects([video.fx.Resize([1080,1920])])
        duration = video_clip.duration
        video_clip.close()

        n = min(len(clip_timings), len(speed_multipliers))

        for i in range(n):
            start, end = clip_timings[i]
            speed = speed_multipliers[i]
            overlay_text = overlay_texts[i] if i < len(overlay_texts) else ""

            if start >= end:
                st.warning(f"Skipping clip {i+1}: Start ({start}) is not less than End ({end}).")
                continue
            if start < 0 or end > duration:
                st.warning(f"Skipping clip {i+1}: Timings out of bounds (video is {duration:.2f}s).")
                continue

            st.write(f"✂️ Processing Clip {i+1}: {start}-{end}s at {speed}x speed")

            clip = VideoFileClip(temp_input_path).with_effects([video.fx.Resize([1080,1920])])
            subclip = clip.subclipped(start, end)

            # Speed adjustment (simulate by changing duration)
            if speed != 1.0:
                subclip = subclip.with_effects([video.fx.MultiplySpeed(speed)])

            # Add overlay text if needed
            if overlay_text.strip() != "":
                try:
                    txt_clip = TextClip(
                        font="Mark Simonson - Proxima Nova Semibold-webfont",
                        text=overlay_texts[i],
                        font_size=80,
                        color='white',
                        stroke_color="black",
                        stroke_width=5,
                        duration=subclip.duration,
                        margin=(5,5),
                        method='caption',
                        size=(round(subclip.size[0] * 0.8), None),
                        text_align='center').with_position(("center", "center"))
                    subclip = CompositeVideoClip([subclip, txt_clip])
                except Exception as e:
                    st.warning(f"⚠️ Could not add text overlay for clip {i+1}: {e}")

            # Save subclip
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_start{int(start)}_end{int(end)}.mp4") as temp_output:
                subclip.write_videofile(temp_output.name, codec="libx264", audio_codec="aac")
                output_files.append(temp_output.name)

            clip.close()

        os.remove(temp_input_path)

        # Package outputs
        if output_files:
            zip_path = tempfile.NamedTemporaryFile(delete=False, suffix=".zip").name
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path in output_files:
                    zipf.write(file_path, arcname=os.path.basename(file_path))

            with open(zip_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download All Clips (ZIP)",
                    data=f,
                    file_name="edited_clips.zip",
                    mime="application/zip"
                )

            st.success(f"✅ Successfully generated {len(output_files)} clip(s)!")
        else:
            st.error("❌ No valid clips generated. Check timings and speeds.")