"""
recognizer.py
Handles Vosk speech recognition setup and pyaudio audio processing.
"""
import json
import pyaudio
from vosk import Model, KaldiRecognizer

# Import configuration settings
from config import (
    MODEL_LOCATION,
    AUDIO_FORMAT,
    AUDIO_CHANNELS,
    AUDIO_RATE,
    AUDIO_BUFFER_SIZE
)

def initialize_speech_recognition():
    """Initializes the Vosk model and recognizer."""
    try:
        model = Model(MODEL_LOCATION)
        rec = KaldiRecognizer(model, AUDIO_RATE)
        return model, rec
    
    # General exception handling
    except Exception as e:
        print(f"Error initializing Vosk model: {e}")
        raise

def initialize_audio_stream():
    """Initializes PyAudio audio input stream."""
    try:
        p = pyaudio.PyAudio()
        stream = p.open(
            format=getattr(pyaudio, AUDIO_FORMAT),
            channels=AUDIO_CHANNELS,
            rate=AUDIO_RATE,
            input=True,
            frames_per_buffer=AUDIO_BUFFER_SIZE,
            input_device_index=None,
        )
        stream.start_stream()
        return p, stream
    
    # General exception handling
    except Exception as e:
        print(f"Error initializing audio stream: {e}")
        raise

def process_audio(rec, data):
    """
    Process audio data through recognizer and convert it to text.
    Args:
        rec: KaldiRecognizer instance
        data: Audio data
    """
    try:
        if rec.AcceptWaveform(data):
            result = rec.Result()
            text = json.loads(result).get("text", "")
            return text if text else None
    
    # General exception handling
    except Exception as e:
        print(f"Error processing audio: {e}")
    return None

def cleanup_audio(p, stream):
    """
    Cleans up and closes the audio stream and PyAudio instance.
    Args:
        p: PyAudio instance
        stream: PyAudio stream instance
    """
    try:
        if stream:
            stream.stop_stream()
            stream.close()
        if p:
            p.terminate()
    
    # General exception handling
    except Exception as e:
        print(f"Error cleaning up audio resources: {e}")