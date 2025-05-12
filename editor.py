import streamlit as st
import tempfile
import os
import zipfile
import random
import time
import pandas as pd
# from pathlib import Path
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, video

# === App Configuration ===
def initialize_app():
    st.set_page_config(page_title="🎨 Auto Video Editor", layout="centered")
    st.title("🎥 Auto Video Editor")
    
    # Initialize session state variables
    if "upload_group_count" not in st.session_state:
        st.session_state.upload_group_count = 2
    if "sequences_ready" not in st.session_state:
        st.session_state.sequences_ready = False
    if "cancel_generation" not in st.session_state:
        st.session_state.cancel_generation = False

# === Video Upload Handling ===
def handle_video_uploads():
    """Handle video uploads for each group"""
    st.markdown("## 📤 Step 1: Upload Videos")
    
    # Configuration for uploads
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add More Upload Groups"):
            st.session_state.upload_group_count += 1
    with col2:
        if st.button("➖ Remove Upload Group") and st.session_state.upload_group_count > 1:
            st.session_state.upload_group_count -= 1

    num_videos_to_generate = st.number_input(
        "How many combined videos do you want to generate?", 
        min_value=1, 
        max_value=100, 
        value=3, 
        step=1
    )
    
    video_inputs = []
    for i in range(st.session_state.upload_group_count):
        with st.expander(f"Group {i+1} Videos", expanded=i < 2):  # Only expand first two by default
            label = st.text_input(f"Group {i+1} Label", value=f"Group {i+1}", key=f"group_label_{i}")
            files = st.file_uploader(
                f"Upload one or more videos for {label}", 
                type=["mp4", "mov", "avi", "mkv"], 
                accept_multiple_files=True, 
                key=f"uploader_{i}"
            )
            
            if files:
                st.success(f"✅ {len(files)} video(s) uploaded for {label}")
            
            video_inputs.append((label, files))
    
    return video_inputs, num_videos_to_generate

def process_uploaded_videos(video_inputs):
    """Process uploaded videos and extract metadata"""
    video_params = {}
    
    for label, files in video_inputs:
        if not files:
            continue
            
        temp_paths = []
        durations = []
        for file in files:
            st.write(f"Uploaded: {file.name}")
            file.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_vid:
                temp_vid.write(file.read())
                original_filename = os.path.basename(file.name) if hasattr(file, 'name') else os.path.basename(temp_vid.name)
                temp_paths.append((temp_vid.name, original_filename))
                try:
                    clip = VideoFileClip(temp_vid.name)
                    durations.append(clip.duration)
                    clip.close()
                except Exception as e:
                    st.error(f"Error processing {original_filename}: {str(e)}")
                    continue
        
        video_params[label] = {
            "paths": [p[0] for p in temp_paths],
            "filenames": [os.path.basename(p[1]) for p in temp_paths],
            "durations": durations,
        }
    
    return video_params

# === Sequence Generation ===
def generate_sequences(video_params, num_videos_to_generate):
    """Generate random video sequences"""
    st.markdown("---")
    st.subheader("🌹 Step 2: Randomly Select Videos Per Sequence")
    
    # Add sequence configuration options
    col1, col2 = st.columns(2)
    with col1:
        auto_select = st.checkbox("Use smart video selection", value=True, 
                                 help="When enabled, tries to select videos with similar dimensions and aspect ratios")
    with col2:
        maintain_order = st.checkbox("Maintain group order", value=True,
                                    help="When enabled, clips will be sequenced in the same group order for each video")
    
    if st.button("🧪 Generate Sequences"):
        sequence_data = []
        generated_sequences = {}

        for i in range(num_videos_to_generate):
            row = {"Sequence #": i+1}
            for label, data in video_params.items():
                if not data["paths"]:  # Skip empty groups
                    continue
                    
                # Select a random video path
                selected_path = random.choice(data["paths"])
                try:
                    with VideoFileClip(selected_path) as clip:
                        duration = clip.duration
                except Exception as e:
                    st.error(f"Error reading video clip: {str(e)}")
                    duration = 0
                    
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
        with st.expander("🔍 View Generated Sequences", expanded=True):
            st.dataframe(st.session_state["sequences_df"])
    
    # Check if sequences are ready
    if not st.session_state.get("sequences_ready"):
        st.warning("Upload videos and click 'Generate Sequences' to continue.")
        return False
    return True

# === Clip Edit Settings ===
def setup_clip_settings(video_inputs, video_params, num_videos_to_generate):
    """Set up timing, speed, and overlay text settings for each group"""
    st.markdown("---")
    st.subheader("🎛️ Step 3: Configure Clip Settings")
    
    for label, files in video_inputs:
        if not files:
            continue

        key_prefix = f"{label.lower()}_"
        durations = [d for _, d in st.session_state["generated_sequences"].get(label, [])]
        
        # Initialize all settings before expanding
        initialize_timings(key_prefix, durations, num_videos_to_generate)
        initialize_speed_settings(key_prefix, num_videos_to_generate)
        initialize_overlay_text(key_prefix, num_videos_to_generate)
        
        # Create expander for this group's settings
        with st.expander(f"⚙️ {label} Settings", expanded=False):
            # Timing settings
            st.markdown(f"#### 📋 Clip Timings")
            clip_timings_text = st.text_area(
                f"Start time, End time (in seconds)", 
                value=st.session_state[key_prefix + "clip_timings_text"], 
                key=key_prefix + "timings",
                help="Format: start_time, end_time (one pair per line)"
            )
            
            # Add buttons for randomizing or using full length
            timing_buttons(key_prefix, label, durations)
            
            st.markdown("---")
            
            # Speed settings
            st.markdown(f"#### ⏩ Speed Multipliers")
            speed_multipliers_text = st.text_area(
                f"Speed multiplier for each clip", 
                value=st.session_state[key_prefix + "speed_multipliers_text"], 
                key=key_prefix + "speeds",
                help="One speed value per line (e.g., 1.0 = normal speed, 2.0 = double speed)"
            )
            
            # Add button for randomizing speeds
            if st.button(f"🎲 Randomize {label} Speeds"):
                randomized = [str(round(random.weibullvariate(1.6, 2), 2)) for _ in durations]
                st.session_state[key_prefix + "speed_multipliers_text"] = "\n".join(randomized)
            
            st.markdown("---")
            
            # Overlay text settings
            st.markdown(f"#### 🖋️ Overlay Texts")
            overlay_texts_text = st.text_area(
                f"Text overlay for each clip", 
                value=st.session_state[key_prefix + "overlay_texts"], 
                key=key_prefix + "overlay",
                help="One text overlay per line (leave blank for no text)"
            )
            st.session_state[key_prefix + "overlay_texts"] = overlay_texts_text
        
        # Display a summary outside the expander
        st.caption(f"{label}: {len(durations)} clips configured")
        
        # Update video parameters
        if label in video_params:
            video_params[label]["timings"] = clip_timings_text
            video_params[label]["speeds"] = speed_multipliers_text
            video_params[label]["texts"] = [line.strip() for line in overlay_texts_text.splitlines()]

def initialize_timings(key_prefix, durations, num_videos_to_generate):
    """Initialize random timing values if not already set"""
    if (key_prefix + "clip_timings_text" not in st.session_state or 
            len(st.session_state[key_prefix + "clip_timings_text"].splitlines()) != num_videos_to_generate):
        timings = []
        for duration in durations:
            if duration > 1:
                start = round(random.uniform(0, duration - 1), 2)
                end = round(random.uniform(start + 0.5, duration), 2)
            else:
                start = 0
                end = duration
            timings.append(f"{start}, {end}")
        st.session_state[key_prefix + "clip_timings_text"] = "\n".join(timings)

def timing_buttons(key_prefix, label, durations):
    """Add buttons for timing operations"""
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"🎲 Randomize {label} Timings"):
            randomized = []
            for duration in durations:
                if duration > 1:
                    start = round(random.uniform(0, duration - 1), 2)
                    end = round(random.uniform(start + 0.5, duration), 2)
                else:
                    start = 0
                    end = duration
                randomized.append(f"{start}, {end}")
            st.session_state[key_prefix + "clip_timings_text"] = "\n".join(randomized)
    with col2:
        if st.button(f"📏 Full-Length {label} Timings"):
            full_timings = [f"0.0, {duration}" for duration in durations]
            st.session_state[key_prefix + "clip_timings_text"] = "\n".join(full_timings)

def initialize_speed_settings(key_prefix, num_videos_to_generate):
    """Initialize speed multiplier values if not already set"""
    if (key_prefix + "speed_multipliers_text" not in st.session_state or 
            len(st.session_state[key_prefix + "speed_multipliers_text"].splitlines()) != num_videos_to_generate):
        st.session_state[key_prefix + "speed_multipliers_text"] = "\n".join(["1.0"] * num_videos_to_generate)

def initialize_overlay_text(key_prefix, num_videos_to_generate):
    """Initialize overlay text values if not already set"""
    if key_prefix + "overlay_texts" not in st.session_state:
        st.session_state[key_prefix + "overlay_texts"] = "\n".join([f"Clip {i+1}" for i in range(num_videos_to_generate)])
    elif len(st.session_state[key_prefix + "overlay_texts"].splitlines()) != num_videos_to_generate:
        existing_lines = st.session_state[key_prefix + "overlay_texts"].splitlines()
        filled_lines = (existing_lines + [f"Clip {i+1}" for i in range(len(existing_lines), num_videos_to_generate)])[:num_videos_to_generate]
        st.session_state[key_prefix + "overlay_texts"] = "\n".join(filled_lines)

# === Video Generation ===
def generate_videos(video_params, num_videos_to_generate):
    """Generate the final video clips"""
    st.markdown("---")
    st.subheader("🎬 Step 4: Generate Videos")
    
    if st.button("🚀 Generate All Combined Clips"):
        if st.session_state.get("cancel_generation", False):
            st.warning("🚫 Generation canceled.")
            return
            
        cancel_button = st.button("🛑 Cancel Generation")
        if cancel_button:
            st.session_state.cancel_generation = True
            return

        # Set up progress tracking
        status_text = st.empty()
        eta_text = st.empty()
        progress_bar = st.progress(0)
        start_time = time.time()
        
        # Parse clip settings for each group
        group_clips = parse_all_clip_settings(video_params)
        
        # Generate and combine clips
        combined_output_files = create_combined_clips(
            video_params, 
            group_clips, 
            num_videos_to_generate, 
            status_text, 
            eta_text, 
            progress_bar, 
            start_time
        )
        
        # Create downloadable zip file
        if combined_output_files:
            create_download_zip(combined_output_files)
            
            progress_bar.progress(1.0)
            st.success(f"✅ Successfully generated {len(combined_output_files)} combined clip(s)!")
            st.session_state.cancel_generation = False

def parse_all_clip_settings(video_params):
    """Parse timing, speed, and text settings for all groups"""
    group_clips = {}
    for label, data in video_params.items():
        timings, speeds, texts = parse_clip_settings(data)
        group_clips[label] = {
            "timings": timings,
            "speeds": speeds,
            "texts": texts
        }
    return group_clips

def parse_clip_settings(data):
    """Parse timing, speed, and text settings from text areas"""
    timings = []
    for line in data["timings"].splitlines():
        try:
            start_str, end_str = line.split(",")
            timings.append((float(start_str.strip()), float(end_str.strip())))
        except (ValueError, AttributeError):
            # Default to (0,0) for invalid entries
            timings.append((0.0, 0.0))
    
    speeds = []
    for x in data["speeds"].splitlines():
        try:
            speeds.append(float(x.strip()))
        except (ValueError, AttributeError):
            speeds.append(1.0)  # Default speed
    
    texts = data["texts"]
    return timings, speeds, texts

def create_combined_clips(video_params, group_clips, num_videos_to_generate, status_text, eta_text, progress_bar, start_time):
    """Create the combined video clips"""
    combined_output_files = []

    for i in range(num_videos_to_generate):
        if st.session_state.get("cancel_generation", False):
            status_text.error("🚫 Canceled by user.")
            break
            
        # Update progress indicators
        elapsed = time.time() - start_time
        avg_time = elapsed / (i + 1) if i > 0 else 0
        remaining = avg_time * (num_videos_to_generate - (i + 1))
        
        eta_text.markdown(f"⏱️ Estimated time remaining: **{int(remaining)}s**")
        progress_bar.progress(i / num_videos_to_generate)
        status_text.markdown(f"⏳ Generating video {i+1} of {num_videos_to_generate}...")
        
        # Process clips for this round
        clips_for_this_round = process_clips_for_round(i, video_params, group_clips)
        
        if not clips_for_this_round:
            st.error(f"No valid clips found for round {i+1}")
            continue
            
        # Combine clips and save
        try:
            final_combined = video.compositing.CompositeVideoClip.concatenate_videoclips(clips_for_this_round)
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_combined_{i+1}.mp4") as temp_output:
                final_combined.write_videofile(temp_output.name, codec="libx264", audio_codec="aac")
                combined_output_files.append(temp_output.name)
        except Exception as e:
            st.error(f"Error generating combined video {i+1}: {str(e)}")
            
    return combined_output_files

def process_clips_for_round(i, video_params, group_clips):
    """Process clips from each group for this round"""
    clips_for_this_round = []
    
    # Create a status expander for detailed logs
    with st.expander(f"Processing details for video {i+1}", expanded=False):
        for label, data in video_params.items():
            if label not in group_clips:
                continue
                
            params = group_clips[label]
            
            # Skip if we don't have enough parameters
            if i >= len(params["timings"]) or i >= len(params["speeds"]):
                st.warning(f"Missing timing or speed parameters for {label} in round {i+1}")
                continue
                
            timing = params["timings"][i]
            speed = params["speeds"][i]
            text = params["texts"][i] if i < len(params["texts"]) else ""
            
            # Get selected file from sequences_df
            try:
                selected_filename = st.session_state["sequences_df"].iloc[i][f"{label} File"]
                st.write(f"Processing: Sequence {i+1} | {label} File")
                st.write(f"→ {selected_filename}")
                st.write(f"  ⤷ Timing: {timing[0]}s to {timing[1]}s")
                st.write(f"  ⤷ Speed: {speed}x")
                st.write(f"  ⤷ Text: '{text}'")
                
                path_index = data["filenames"].index(selected_filename)
                selected_path = data["paths"][path_index]
                
                clip = create_processed_clip(selected_path, timing, speed, text, label, i)
                if clip:
                    clips_for_this_round.append(clip)
                    st.success(f"✅ Successfully processed clip for {label}")
                    
            except (ValueError, IndexError, KeyError) as e:
                st.error(f"Error finding file for {label} in round {i+1}: {str(e)}")
                continue
                
    return clips_for_this_round

def create_processed_clip(video_path, timing, speed, text, label, clip_index):
    """Create a processed video clip with timing, speed, and text overlay"""
    try:
        clip = VideoFileClip(video_path)
        end_time = min(timing[1], clip.duration - 0.01)
        base_clip = clip.subclipped(timing[0], end_time).with_effects([video.fx.Resize([1080,1920])])
        
        if speed != 1.0:
            base_clip = base_clip.with_duration(base_clip.duration / speed)
        
        if text.strip():
            txt_overlay = TextClip(
                font="Mark Simonson - Proxima Nova Semibold-webfont",
                text=text.strip(),
                font_size=60,
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
            
        return final_clip
        
    except Exception as e:
        st.error(f"Error processing {label} clip {clip_index+1}: {str(e)}")
        return None

def create_download_zip(output_files):
    """Create a downloadable ZIP file with all generated videos"""
    try:
        zip_path = tempfile.NamedTemporaryFile(delete=False, suffix=".zip").name
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in output_files:
                zipf.write(file_path, arcname=os.path.basename(file_path))

        with open(zip_path, "rb") as f:
            st.download_button(
                label="⬇️ Download All Combined Clips (ZIP)",
                data=f,
                file_name="combined_clips.zip",
                mime="application/zip"
            )
    except Exception as e:
        st.error(f"Error creating ZIP file: {str(e)}")

# === Main Application ===
def main():
    initialize_app()
    
    # Step 1: Handle video uploads
    video_inputs, num_videos_to_generate = handle_video_uploads()
    video_params = process_uploaded_videos(video_inputs)
    
    # Step 2: Generate sequences
    sequences_ready = generate_sequences(video_params, num_videos_to_generate)
    if not sequences_ready:
        st.stop()
    
    # Step 3: Set up clip settings
    setup_clip_settings(video_inputs, video_params, num_videos_to_generate)
    
    # Step 4: Generate videos
    generate_videos(video_params, num_videos_to_generate)

if __name__ == "__main__":
    main()