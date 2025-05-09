import streamlit as st
import streamlit as st
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, video
import tempfile
import os
import zipfile
import random
from pathlib import Path
import pandas as pd
import time

st.set_page_config(page_title="🎨 Auto Video Editor", layout="centered")
st.title("🎥 Auto Video Editor")

if "upload_group_count" not in st.session_state:
    st.session_state.upload_group_count = 2

if st.button("➕ Add More Upload Groups"):
    st.session_state.upload_group_count += 1

num_videos_to_generate = st.number_input("How many combined videos do you want to generate?", min_value=1, max_value=100, value=3, step=1)

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
            st.write(f"Uploaded: {file.name}")
            file.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_vid:
                temp_vid.write(file.read())
                original_filename = os.path.basename(file.name) if hasattr(file, 'name') else os.path.basename(temp_vid.name)
                temp_paths.append((temp_vid.name, os.path.basename(original_filename)))
                clip = VideoFileClip(temp_vid.name)
                durations.append(clip.duration)
                clip.close()
        video_params[label] = {
        "paths": [p[0] for p in temp_paths],
        "filenames": [os.path.basename(p[1]) for p in temp_paths],
            "durations": durations,
        }

# Step 2: Generate sequences
st.markdown("---")
st.subheader("🌹 Step 2: Randomly Select Videos Per Sequence")

if st.button("🧪 Generate Sequences"):
    sequence_data = []
    generated_sequences = {}

    for i in range(num_videos_to_generate):
        row = {"Sequence #": i+1}
        for label, data in video_params.items():
            selected_path = random.choice(data["paths"])
            duration = VideoFileClip(selected_path).duration
            index = data["paths"].index(selected_path)
            row[f"{label} File"] = data["filenames"][index]
            row[f"{label} Duration"] = round(duration, 2)
            generated_sequences.setdefault(label, []).append((selected_path, duration))
        sequence_data.append(row)

    df_sequences = pd.DataFrame(sequence_data)
    st.session_state["sequences_df"] = df_sequences
    st.session_state["generated_sequences"] = generated_sequences
    st.session_state["sequences_ready"] = True

if "sequences_df" in st.session_state:
    st.dataframe(st.session_state["sequences_df"])

# Stop if sequences aren't ready
if not st.session_state.get("sequences_ready"):
    st.warning("Upload videos and click 'Generate Sequences' to continue.")
    st.stop()

# Step 3: Set timings/speeds/overlay
for label, files in video_inputs:
    if not files:
        continue

    key_prefix = f"{label.lower()}_"
    durations = [d for _, d in st.session_state["generated_sequences"].get(label, [])]

    if key_prefix + "clip_timings_text" not in st.session_state or len(st.session_state[key_prefix + "clip_timings_text"].splitlines()) != num_videos_to_generate:
        timings = []
        for duration in durations:
            start = round(random.uniform(0, duration - 1), 2)
            end = round(random.uniform(start + 0.5, duration), 2)
            timings.append(f"{start}, {end}")
        st.session_state[key_prefix + "clip_timings_text"] = "\n".join(timings)
    # if key_prefix + "clip_timings_text" not in st.session_state or len(st.session_state[key_prefix + "clip_timings_text"].splitlines()) != num_videos_to_generate:
    #     full_timings = [f"0.0, {duration}" for _, duration in st.session_state["generated_sequences"].get(label, [])]
    #     st.session_state[key_prefix + "clip_timings_text"] = "\n".join(full_timings)

    st.markdown(f"### 📋 {label} Clip Timings")
    clip_timings_text = st.text_area(f"{label} Clip Timings", value=st.session_state[key_prefix + "clip_timings_text"], key=key_prefix + "timings")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"🎲 Randomize {label} Timings"):
            randomized = []
            for duration in durations:
                start = round(random.uniform(0, duration - 1), 2)
                end = round(random.uniform(start + 0.5, duration), 2)
                randomized.append(f"{start}, {end}")
            st.session_state[key_prefix + "clip_timings_text"] = "".join(randomized)
    with col2:
        if st.button(f"📏 Full-Length {label} Timings"):
            full_timings = [f"0.0, {duration}" for _, duration in st.session_state["generated_sequences"].get(label, [])]
            st.session_state[key_prefix + "clip_timings_text"] = "\n".join(full_timings)

    if key_prefix + "speed_multipliers_text" not in st.session_state or len(st.session_state[key_prefix + "speed_multipliers_text"].splitlines()) != num_videos_to_generate:
        st.session_state[key_prefix + "speed_multipliers_text"] = "\n".join(["1.0"] * num_videos_to_generate)

    st.markdown(f"### ⏩ {label} Speed Multipliers")
    speed_multipliers_text = st.text_area(f"{label} Speed Multipliers", value=st.session_state[key_prefix + "speed_multipliers_text"], key=key_prefix + "speeds")

    if st.button(f"🎲 Randomize {label} Speeds"):
        randomized = [str(round(random.weibullvariate(1.6, 2), 2)) for _ in durations]
        st.session_state[key_prefix + "speed_multipliers_text"] = "\n".join(randomized)

    if key_prefix + "overlay_texts" not in st.session_state:
        st.session_state[key_prefix + "overlay_texts"] = "\n".join([f"Clip {i+1}" for i in range(num_videos_to_generate)])
    elif len(st.session_state[key_prefix + "overlay_texts"].splitlines()) != num_videos_to_generate:
        existing_lines = st.session_state[key_prefix + "overlay_texts"].splitlines()
        filled_lines = (existing_lines + [f"Clip {i+1}" for i in range(len(existing_lines), num_videos_to_generate)])[:num_videos_to_generate]
        st.session_state[key_prefix + "overlay_texts"] = "\n".join(filled_lines)
        st.session_state[key_prefix + "overlay_texts"] = "\n".join([f"Clip {i+1}" for i in range(num_videos_to_generate)])

    st.markdown(f"### 🖋️ {label} Overlay Texts")
    overlay_texts_text = st.text_area(f"{label} Overlay Texts", value=st.session_state[key_prefix + "overlay_texts"], key=key_prefix + "overlay")
    st.session_state[key_prefix + "overlay_texts"] = overlay_texts_text

    if label in video_params:
        video_params[label]["timings"] = clip_timings_text
        video_params[label]["speeds"] = speed_multipliers_text
        video_params[label]["texts"] = [line.strip() for line in overlay_texts_text.splitlines()]

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
            params = group_clips[label]
            timing = params["timings"][i]
            speed = params["speeds"][i]
            text = params["texts"][i] if i < len(params["texts"]) else ""

            # Use selected file from sequences_df
            st.write(f"Processing: Sequence {i+1} | {label} File")
            selected_filename = st.session_state["sequences_df"].iloc[i][f"{label} File"]
            st.write(f"→ {selected_filename}")
            st.write(f"  ⤷ Timing: {timing[0]}s to {timing[1]}s")
            st.write(f"  ⤷ Speed: {speed}x")
            st.write(f"  ⤷ Text: '{text}'")
            try:
                path_index = data["filenames"].index(selected_filename)
                selected_path = data["paths"][path_index]
            except ValueError:
                st.error(f"Could not find a match for {selected_filename} in uploaded files for {label}.")
                st.stop()
            if selected_path is None:
                st.error(f"Could not find a match for {selected_filename} in uploaded files for {label}.")
                st.stop()
            clip = VideoFileClip(selected_path)
            end_time = min(timing[1], clip.duration - 0.01)
            base_clip = clip.subclipped(timing[0], end_time).with_effects([video.fx.Resize([1080,1920])])
            if speed != 1.0:
                base_clip = base_clip.with_duration(base_clip.duration / speed)

            if text.strip():
                caption = f"{label} – Clip {i+1}: {text.strip()}"
                txt_overlay = TextClip(
                    font="Mark Simonson - Proxima Nova Semibold-webfont",
                    text=text.strip(),
                    font_size=70,
                    color='white',
                    stroke_color="black",
                    stroke_width=5,
                    duration=base_clip.duration,
                    margin=(5,5),
                    method='caption',
                    size=(round(base_clip.size[0] * 0.8), None),
                    text_align='center'
                ).with_position(("center", 225))
                final_clip = CompositeVideoClip([base_clip, txt_overlay])
            else:
                final_clip = base_clip

            clips_for_this_round.append(final_clip)

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