import streamlit as st
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, video
import tempfile
import os
import zipfile

st.set_page_config(page_title="🎬 Batch Video Editor with Effects", layout="centered")
st.title("🎥 Upload, Paste Parameters, Auto-Generate Clips (MoviePy 2.1.2)")

video_file = st.file_uploader("Upload a video", type=["mp4", "mov", "avi", "mkv"])

if video_file:
    st.video(video_file)

    st.markdown("### 📋 Paste Clip Timings")
    st.markdown("Each line: `start_time,end_time` (seconds)")
    st.code("0, 5\n10, 15\n20, 25")
    clip_timings_text = st.text_area("Clip Timings", value="1, 5\n0, 5\n0, 5")

    st.markdown("### ⏩ Paste Speed Multipliers (Optional)")
    st.markdown("Each line: `1.0` (normal), `2.0` (2x faster), `0.5` (half speed)")
    st.code("1.0\n2.0\n0.5")
    speed_multipliers_text = st.text_area("Speed Multipliers", value="1.0\n1.5\n1.0")

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

            # subclip = subclip.with_effects([video.fx.Resize(1080,1920)])

            # Add overlay text if needed
            if overlay_text.strip() != "":
                try:
                    txt_clip = TextClip(font="Mark Simonson - Proxima Nova Semibold-webfont", text=overlay_texts[i], font_size=80, color='white', stroke_color="black", stroke_width=5, duration=subclip.duration, margin=(5,5), method='caption', size=(round(subclip.size[0] * 0.8), None), text_align='center').with_position(("center", "center"))
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