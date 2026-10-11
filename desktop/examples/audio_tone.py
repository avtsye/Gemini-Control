"""Example capability: WAV tone generator, implemented without external dependencies."""
import math
import struct
import wave
from pathlib import Path

def run(payload, output_dir):
    frequency=float(payload.get("frequency",440))
    seconds=float(payload.get("seconds",2))
    if not 40 <= frequency <= 3000 or not 0.1 <= seconds <= 20:
        raise ValueError("frequency (40-3000) or seconds (0.1-20) out of range")
    rate=22050
    output=Path(output_dir)/"generated_tone.wav"
    with wave.open(str(output),"wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        frames=bytearray()
        for index in range(int(rate*seconds)):
            sample=int(0.25*32767*math.sin(2*math.pi*frequency*index/rate))
            frames.extend(struct.pack("<h",sample))
        wav.writeframes(frames)
    return {"created_file":str(output),"frequency":frequency,"seconds":seconds}
