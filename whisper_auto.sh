#!/bin/bash
set -e

ENV_DIR="$HOME/whisper-env"

# Prefer Python 3.11 if available
if command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="python3.11"
else
  PYTHON_BIN="python3"
fi

# Create venv if missing
if [ ! -d "$ENV_DIR" ]; then
  echo "Creating virtual environment..."
  "$PYTHON_BIN" -m venv "$ENV_DIR"
fi

# Activate venv
# shellcheck disable=SC1090
source "$ENV_DIR/bin/activate"

# Upgrade pip quietly
pip install -U pip >/dev/null 2>&1 || true

# Install Whisper if missing
if ! command -v whisper >/dev/null 2>&1; then
  echo "Installing Whisper (first time setup)..."
  pip install -U openai-whisper
fi

# Check if torch is available, install if not
python - <<'EOF'
import sys
try:
    import torch  # noqa: F401
    sys.exit(0)
except Exception:
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
  echo "Installing PyTorch (first time setup)..."
  pip install torch torchvision torchaudio
fi

# Check ffmpeg
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "✗ FFmpeg not found. Please install it with: brew install ffmpeg"
  exit 1
fi

# -----------------------
# Select input file
# -----------------------

# Parse arguments: $1 = video path, $2 = language code, $3 = model
if [ -z "$1" ]; then
  echo "No input file passed, opening file picker..."
  input_video=$(osascript <<'EOF'
set f to choose file with prompt "Select a video or audio file to transcribe:" of type {"public.movie","public.audio"}
POSIX path of f
EOF
) || true

  if [ -z "$input_video" ]; then
    echo "No file selected, exiting."
    exit 1
  fi
else
  input_video="$1"
fi

# Get language code (default to "en" if not provided)
lang_code="${2:-en}"

# Get model (default to "turbo" if not provided)
model="${3:-turbo}"

# Normalize paths
input_video_dir=$(dirname "$input_video")
input_basename=$(basename "$input_video")
filename_no_ext="${input_basename%.*}"

# -----------------------
# Auto rename outputs
# -----------------------

audio_stem="${filename_no_ext}_converted"
audio_path="$input_video_dir/${audio_stem}.wav"

# If any files with this stem already exist, find a free suffix
if ls "$input_video_dir/${audio_stem}"* >/dev/null 2>&1; then
  n=1
  while ls "$input_video_dir/${audio_stem}_${n}"* >/dev/null 2>&1; do
    n=$((n+1))
  done
  audio_stem="${audio_stem}_${n}"
  audio_path="$input_video_dir/${audio_stem}.wav"
  echo "Existing outputs found, using new stem: $audio_stem"
fi

# Language and model info is already logged by Python GUI, so we skip those echo statements
# to avoid duplicate logging in the GUI output

echo "Extracting and normalizing audio..."
# Suppress FFmpeg verbose output (version info, stream details), only show warnings/errors
ffmpeg -i "$input_video" -ac 1 -ar 16000 -c:a pcm_s16le -af dynaudnorm "$audio_path" -loglevel warning -hide_banner 2>&1 || true

echo "Transcribing with Whisper..."
# Build whisper command, omit --language if auto-detect
# Using optimized settings for best SRT quality:
# - beam_size 5 (default)
# - word_timestamps: Refines timestamps for more accurate subtitle timing
# - max_line_width 42: Typical subtitle width (~2 lines, readable)
# - max_line_count 2: Maximum 2 lines per subtitle (standard)
# - condition_on_previous_text: Uses context from previous segments (default True)
# - patience 1.0: Standard beam search patience (default)
if [ "$lang_code" = "auto" ]; then
  whisper "$audio_path" \
    --model "$model" \
    --fp16 False \
    --output_format srt \
    --beam_size 5 \
    --word_timestamps True \
    --max_line_width 42 \
    --max_line_count 2 \
    --condition_on_previous_text True \
    --patience 1.0 \
    --output_dir "$input_video_dir"
else
  whisper "$audio_path" \
    --model "$model" \
    --language "$lang_code" \
    --fp16 False \
    --output_format srt \
    --beam_size 5 \
    --word_timestamps True \
    --max_line_width 42 \
    --max_line_count 2 \
    --condition_on_previous_text True \
    --patience 1.0 \
    --output_dir "$input_video_dir"
fi

# Rename SRT file to match input video filename
whisper_srt="$input_video_dir/${audio_stem}.srt"
final_srt="$input_video_dir/${filename_no_ext}.srt"

# Handle case where SRT already exists (add number suffix)
if [ -f "$final_srt" ]; then
  n=1
  while [ -f "$input_video_dir/${filename_no_ext}_${n}.srt" ]; do
    n=$((n+1))
  done
  final_srt="$input_video_dir/${filename_no_ext}_${n}.srt"
fi

if [ -f "$whisper_srt" ]; then
  mv "$whisper_srt" "$final_srt"
  # Clean up temporary audio file used for transcription
  if [ -f "$audio_path" ]; then
    rm "$audio_path"
  fi
fi

# Completion message is handled by Python GUI

