import whisper
import pyaudio
import wave
import os

model = whisper.load_model("base")

def record_audio(seconds=5, filename="/tmp/jarvis_input.wav"):
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1,
                    rate=16000, input=True, frames_per_buffer=1024)
    print("[JARVIS] Listening...")
    frames = [stream.read(1024) for _ in range(int(16000/1024 * seconds))]
    stream.stop_stream()
    stream.close()
    p.terminate()
    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000)
    wf.writeframes(b''.join(frames))
    wf.close()
    return filename

def listen():
    filename = record_audio()
    result = model.transcribe(filename)
    os.remove(filename)
    return result["text"]
