"""
ctf/vision.py — Multimodal Image Analysis for CTF
Uses Ollama llava/bakllava for visual CTF challenges:
  - Steganography (hidden text in images)
  - QR codes and barcodes
  - Screenshots with flag/hint visible
  - Spectrogram analysis hints
  - Visual puzzles and encoded images
Drop into ~/jarvis/ctf/vision.py

Requires: ollama pull llava  OR  ollama pull bakllava
"""

import os
import base64
import subprocess
import re
from pathlib import Path

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


VISION_MODEL = os.getenv("JARVIS_VISION_MODEL", "llava")

SUPPORTED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
SUPPORTED_AUDIO_TYPES = {".wav", ".mp3", ".ogg", ".flac"}


# ═══════════════════════════════════════════════════════════════
#  IMAGE ANALYSIS
# ═══════════════════════════════════════════════════════════════

def encode_image_b64(filepath: str) -> str:
    """Encode image as base64 for Ollama vision API."""
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image(filepath: str, question: str = "") -> str:
    """
    Analyze an image using llava multimodal model.
    Returns description/analysis including any visible text, flags, patterns.
    """
    if not OLLAMA_AVAILABLE:
        return "[ERROR] Ollama not installed"

    if not os.path.exists(filepath):
        return f"[ERROR] File not found: {filepath}"

    ext = Path(filepath).suffix.lower()
    if ext not in SUPPORTED_IMAGE_TYPES:
        return f"[SKIP] Not an image file: {ext}"

    # Build analysis prompt
    if not question:
        question = """Analyze this image for CTF challenge clues. Look for:
1. Any visible text, flags, or encoded strings (flag{...}, CTF{...}, etc.)
2. Hidden text in unusual colors or very small font
3. Patterns that might indicate steganography
4. QR codes, barcodes, or other encoded symbols
5. Morse code or binary patterns
6. Unusual pixels or artifacts at borders
7. Any metadata or watermarks visible
8. Mathematical or cipher-like patterns

Report EVERYTHING you see, especially anything that looks encoded or hidden."""

    try:
        img_b64 = encode_image_b64(filepath)
        response = ollama.chat(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": question,
                "images": [img_b64]
            }]
        )
        return response["message"]["content"]
    except Exception as e:
        if "model not found" in str(e).lower():
            return f"[ERROR] Vision model not installed. Run: ollama pull {VISION_MODEL}"
        return f"[ERROR] Vision analysis failed: {e}"


def find_text_in_image(filepath: str) -> str:
    """
    Extract all text from image using multiple methods:
    1. llava visual analysis
    2. tesseract OCR (if installed)
    3. zbarimg for QR/barcodes
    """
    results = []

    # Method 1: llava
    vision_result = analyze_image(filepath, "Extract ALL text visible in this image. Include any encoded strings, flags, numbers, and symbols. Output exactly what you see.")
    if vision_result and "[ERROR]" not in vision_result:
        results.append(f"[VISION] {vision_result}")

    # Method 2: Tesseract OCR
    try:
        ocr_result = subprocess.run(
            ["tesseract", filepath, "stdout", "-l", "eng"],
            capture_output=True, text=True, timeout=30
        )
        if ocr_result.stdout.strip():
            results.append(f"[OCR] {ocr_result.stdout.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Method 3: zbarimg (QR/barcode)
    try:
        bar_result = subprocess.run(
            ["zbarimg", "--quiet", filepath],
            capture_output=True, text=True, timeout=15
        )
        if bar_result.stdout.strip():
            results.append(f"[BARCODE] {bar_result.stdout.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "\n\n".join(results) if results else "[No text found in image]"


def analyze_spectrogram_hint(audio_filepath: str) -> str:
    """
    For audio files: generate spectrogram image then analyze it visually.
    Many CTF challenges hide flags in audio spectrograms.
    Requires: sox or ffmpeg
    """
    if not os.path.exists(audio_filepath):
        return f"[ERROR] Audio file not found: {audio_filepath}"

    spectrogram_path = f"/tmp/jarvis_spectrogram.png"

    # Try to generate spectrogram with sox
    try:
        result = subprocess.run([
            "sox", audio_filepath,
            "-n", "spectrogram",
            "-o", spectrogram_path,
            "-t", "JARVIS CTF Spectrogram",
            "-c", "Frequency (Hz)"
        ], capture_output=True, text=True, timeout=30)
        if os.path.exists(spectrogram_path):
            analysis = analyze_image(spectrogram_path,
                "This is an audio spectrogram from a CTF challenge. Look carefully for:\n"
                "1. Text or letters hidden in the frequency patterns\n"
                "2. Flag format strings (flag{...}, CTF{...})\n"
                "3. Morse code patterns in the frequencies\n"
                "4. Any unusual bright spots or patterns that could encode data\n"
                "Report exactly what you see in the frequency patterns.")
            return f"[SPECTROGRAM ANALYSIS]\n{analysis}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: try ffmpeg
    try:
        subprocess.run([
            "ffmpeg", "-i", audio_filepath,
            "-lavfi", "showspectrumpic=s=1024x512:color=fire",
            spectrogram_path, "-y"
        ], capture_output=True, timeout=30)
        if os.path.exists(spectrogram_path):
            analysis = analyze_image(spectrogram_path,
                "CTF audio spectrogram — look for hidden text, flag patterns, morse code in frequencies.")
            return f"[SPECTROGRAM ANALYSIS]\n{analysis}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "[SPECTROGRAM] Could not generate — install sox or ffmpeg"


def detect_lsb_visually(filepath: str) -> str:
    """
    Ask llava to look for LSB steganography hints in an image.
    Also tries zsteg if installed for actual LSB extraction.
    """
    results = []

    # Visual analysis for LSB hints
    vision = analyze_image(filepath,
        "Look for signs of LSB (Least Significant Bit) steganography in this image:\n"
        "1. Unusual noise or graininess especially in smooth areas\n"
        "2. Slight color variations that seem out of place\n"
        "3. Patterns in the borders or specific regions\n"
        "4. Any visible data artifacts\n"
        "This is a CTF forensics challenge image.")
    if vision and "[ERROR]" not in vision:
        results.append(f"[LSB VISUAL]\n{vision}")

    # Try actual zsteg extraction
    try:
        zsteg = subprocess.run(
            ["zsteg", filepath],
            capture_output=True, text=True, timeout=30
        )
        if zsteg.stdout.strip():
            results.append(f"[ZSTEG]\n{zsteg.stdout[:2000]}")
    except FileNotFoundError:
        results.append("[ZSTEG] Not installed — run: gem install zsteg")

    return "\n\n".join(results) if results else "[No LSB data detected]"


def analyze_binary_visually(filepath: str) -> str:
    """
    For binary/executable files: analyze any embedded images or visual data.
    Also good for PDF/Office files with embedded images.
    """
    # First try to extract images from binary using binwalk
    extract_dir = f"/tmp/jarvis_extract_{Path(filepath).stem}"
    try:
        subprocess.run(
            ["binwalk", "-e", "--run-as=root", "-o", extract_dir, filepath],
            capture_output=True, timeout=60
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Analyze any extracted images
    results = []
    if os.path.exists(extract_dir):
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                fpath = os.path.join(root, f)
                ext = Path(fpath).suffix.lower()
                if ext in SUPPORTED_IMAGE_TYPES:
                    analysis = analyze_image(fpath)
                    if analysis and "[ERROR]" not in analysis:
                        results.append(f"[EMBEDDED IMAGE: {f}]\n{analysis}")

    return "\n\n".join(results) if results else "[No visual data found in binary]"


def full_visual_analysis(filepath: str) -> str:
    """
    Complete visual analysis pipeline for any file.
    Auto-detects file type and applies appropriate analysis.
    """
    ext = Path(filepath).suffix.lower()
    filename = Path(filepath).name

    if ext in SUPPORTED_IMAGE_TYPES:
        results = [
            f"[VISUAL ANALYSIS: {filename}]",
            find_text_in_image(filepath),
            "",
            "[LSB CHECK]",
            detect_lsb_visually(filepath),
        ]
        return "\n".join(results)

    elif ext in SUPPORTED_AUDIO_TYPES:
        return analyze_spectrogram_hint(filepath)

    elif ext in {".pdf", ".exe", ".bin", ".elf"}:
        return analyze_binary_visually(filepath)

    else:
        # Try image analysis anyway (file might have wrong extension)
        result = analyze_image(filepath)
        if "[ERROR]" not in result:
            return result
        return f"[VISION] Unsupported file type: {ext}"


def check_vision_model() -> bool:
    """Check if vision model is available in Ollama."""
    try:
        models = ollama.list()
        model_names = [m["name"] for m in models.get("models", [])]
        return any(VISION_MODEL in name for name in model_names)
    except Exception:
        return False


def install_vision_model() -> str:
    """Pull the vision model if not installed."""
    try:
        result = subprocess.run(
            ["ollama", "pull", VISION_MODEL],
            capture_output=True, text=True, timeout=300
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"[ERROR] Could not pull {VISION_MODEL}: {e}"
