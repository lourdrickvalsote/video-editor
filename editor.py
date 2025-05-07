import streamlit as st
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, video
import tempfile
import os
import zipfile
import random
from pathlib import Path
import time

st.set_page_config(page_title="🎬 Auto Video Editor", layout="centered")
st.title("🎥 Auto Video Editor")

# Track how many upload groups there are
if "upload_group_count" not in st.session_state:
    st.session_state.upload_group_count = 2

if st.button("➕ Add More Upload Groups"):
    st.session_state.upload_group_count += 1

if "cancel_generation" not in st.session_state:
    st.session_state.cancel_generation = False

# Set number of output videos
num_videos_to_generate = st.number_input("How many combined videos do you want to generate?", min_value=1, max_value=100, value=3, step=1)

# Upload videos dynamically
video_inputs = []
for i in range(st.session_state.upload_group_count):
    label = f"Group {i+1}"
    files = st.file_uploader(f"Upload one or more videos for {label}", type=["mp4", "mov", "avi", "mkv"], accept_multiple_files=True, key=f"uploader_{i}")
    video_inputs.append((label, files))

video_params = {}

for label, files in video_inputs:
    if files:
        temp_paths = []
        durations = []
        for file in files:
            file.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_vid:
                temp_vid.write(file.read())
                temp_paths.append(temp_vid.name)
                clip = VideoFileClip(temp_vid.name)
                durations.append(clip.duration)
                clip.close()

        key_prefix = f"{label.lower()}_"

        if key_prefix + "clip_timings_text" not in st.session_state or len(st.session_state[key_prefix + "clip_timings_text"].splitlines()) != num_videos_to_generate:
            duration = random.choice(durations)
            timings = []
            for _ in range(num_videos_to_generate):
                start = round(random.uniform(0, duration - 1), 2)
                end = round(random.uniform(start + 0.5, duration), 2)
                timings.append(f"{start}, {end}")
            st.session_state[key_prefix + "clip_timings_text"] = "\n".join(timings)

        st.markdown(f"### 📋 {label} Clip Timings")
        clip_timings_text = st.text_area(f"{label} Clip Timings", value=st.session_state[key_prefix + "clip_timings_text"], key=key_prefix + "timings")

        if st.button(f"🎲 Randomize {label} Timings"):
            randomized = []
            duration = random.choice(durations)
            for _ in range(num_videos_to_generate):
                start = round(random.uniform(0, duration - 1), 2)
                end = round(random.uniform(start + 0.5, duration), 2)
                randomized.append(f"{start}, {end}")
            st.session_state[key_prefix + "clip_timings_text"] = "\n".join(randomized)

        if key_prefix + "speed_multipliers_text" not in st.session_state or len(st.session_state[key_prefix + "speed_multipliers_text"].splitlines()) != num_videos_to_generate:
            st.session_state[key_prefix + "speed_multipliers_text"] = "\n".join(["1.0"] * num_videos_to_generate)

        st.markdown(f"### ⏩ {label} Speed Multipliers")
        speed_multipliers_text = st.text_area(f"{label} Speed Multipliers", value=st.session_state[key_prefix + "speed_multipliers_text"], key=key_prefix + "speeds")

        if st.button(f"🎲 Randomize {label} Speeds"):
            randomized = []
            for _ in range(num_videos_to_generate):
                speed = round(random.weibullvariate(1.6, 2), 2)
                randomized.append(f"{speed}")
            st.session_state[key_prefix + "speed_multipliers_text"] = "\n".join(randomized)

        if key_prefix + "overlay_texts" not in st.session_state or len(st.session_state[key_prefix + "overlay_texts"].splitlines()) != num_videos_to_generate:
            st.session_state[key_prefix + "overlay_texts"] = "\n".join([f"Clip {i+1}" for i in range(num_videos_to_generate)])

        st.markdown(f"### 🖋️ {label} Overlay Texts")
        overlay_texts_text = st.text_area(f"{label} Overlay Texts Per Clip", value=st.session_state[key_prefix + "overlay_texts"], key=key_prefix + "overlay")

        video_params[label] = {
            "paths": temp_paths,
            "durations": durations,
            "timings": clip_timings_text,
            "speeds": speed_multipliers_text,
            "texts": [x.strip() for x in overlay_texts_text.splitlines()]
        }

# Combine all clips in order across all groups
if st.button("🚀 Generate All Combined Clips"):
    if st.session_state.get("cancel_generation", False):
        st.warning("🚫 Generation canceled.")
    else:
        if st.button("🛑 Cancel Generation"):
            st.session_state.cancel_generation = True

    status_text = st.empty()
    eta_text = st.empty()
    progress_bar = st.progress(0)
    start_time = time.time()

    def parse_clips(data):
        timings = []
        for line in data["timings"].splitlines():
            try:
                start_str, end_str = line.split(",")
                timings.append((float(start_str.strip()), float(end_str.strip())))
            except:
                pass
        speeds = [float(x.strip()) for x in data["speeds"].splitlines() if x.strip()]
        texts = data["texts"]
        return timings, speeds, texts

    combined_output_files = []

    group_clips = {}
    for label, data in video_params.items():
        timings, speeds, texts = parse_clips(data)
        group_clips[label] = {
            "timings": timings,
            "speeds": speeds,
            "texts": texts
        }

    for i in range(num_videos_to_generate):

        status_text.markdown(f"⏳ Generating video {i+1} of {num_videos_to_generate}...")
        clips_for_this_round = []

        if st.session_state.get("cancel_generation", False):
            status_text.error("🚫 Canceled by user.")

        elapsed = time.time() - start_time
        avg_time = elapsed / (i + 1)
        remaining = avg_time * (num_videos_to_generate - (i + 1))

        eta_text.markdown(f"⏱️ Estimated time remaining: **{int(remaining)}s**")
        progress_bar.progress(i / num_videos_to_generate)
        status_text.markdown(f"⏳ Generating video {i+1} of {num_videos_to_generate}...")

        for label, data in video_params.items():
            status_text.markdown(f"🎬 Generating Video #{i+1}")
            params = group_clips[label]
            paths = data["paths"]
            timing = params["timings"][i]
            speed = params["speeds"][i]
            text = params["texts"][i] if i < len(params["texts"]) else ""

            selected_path = random.choice(paths)
            clip = VideoFileClip(selected_path).subclipped(*timing).with_effects([video.fx.Resize([1080,1920])])
            if speed != 1.0:
                clip = clip.with_duration(clip.duration / speed)
            if text:
                txt_overlay = TextClip(
                    font="Mark Simonson - Proxima Nova Semibold-webfont",
                    text=text,
                    font_size=80,
                    color='white',
                    stroke_color="black",
                    stroke_width=5,
                    duration=clip.duration,
                    margin=(5,5),
                    method='caption',
                    size=(round(clip.size[0] * 0.8), None),
                    text_align='center'
                ).with_position(("center", "center"))
                clip = CompositeVideoClip([clip, txt_overlay])
            clips_for_this_round.append(clip)

        final_combined = video.compositing.CompositeVideoClip.concatenate_videoclips(clips_for_this_round)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_combined_{i+1}.mp4") as temp_output:
            final_combined.write_videofile(temp_output.name, codec="libx264", audio_codec="aac")
            combined_output_files.append(temp_output.name)

    if combined_output_files:
        zip_path = tempfile.NamedTemporaryFile(delete=False, suffix=".zip").name
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in combined_output_files:
                zipf.write(file_path, arcname=os.path.basename(file_path))

        with open(zip_path, "rb") as f:
            st.download_button(
                label="⬇️ Download All Combined Clips (ZIP)",
                data=f,
                file_name="combined_clips.zip",
                mime="application/zip"
            )

        progress_bar.progress(1.0)
        st.success(f"✅ Successfully generated {len(combined_output_files)} combined clip(s)!")
        st.session_state.cancel_generation = False