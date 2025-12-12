"""
recognizer.py
Handles Vosk speech recognition setup and pyaudio audio processing.
"""
import json
import pyaudio
import numpy as np
from vosk import Model, KaldiRecognizer

# Import configuration settings
from config import (
    MODEL_LOCATION,
    AUDIO_FORMAT,
    AUDIO_CHANNELS,
    AUDIO_RATE,
    AUDIO_BUFFER_SIZE,
    NOISE_TESTING,
    SNR_DB
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

def add_gaussian_noise_snr(audioData, snrDb):
    """
    Add Gaussian noise to achieve target SNR (for testing purposes).
    Args:
        audioData: Raw audio data bytes
        snrDb: Desired Signal-to-Noise Ratio in dB (higher is cleaner)
    Returns:
        Audio data with added noise as bytes
    """
    # Convert byte data to numpy array
    audio = np.frombuffer(audioData, dtype=np.int16).astype(np.float32)
    if audio.size == 0:
        return audioData
    
    # Compute signal power
    signalPower = np.mean(audio ** 2)
    if signalPower <= 1e-8:
        return audioData
    
    # Compute noise power for desired SNR
    snrLinear = 10.0 ** (snrDb / 10.0)
    noisePower = signalPower / snrLinear
    noiseStD = np.sqrt(noisePower)

    # Generate and add Gaussian noise
    noise = np.random.normal(0.0, noiseStD, audio.shape)
    noisy = audio + noise
    noisy = np.clip(noisy, -32768, 32767).astype(np.int16)

    return noisy.tobytes()

def process_audio(rec, data):
    """
    Process audio data through recognizer and convert it to text.
    Args:
        rec: KaldiRecognizer instance
        data: Audio data
    """
    try:
        # Add Gaussian noise if NOISE_TESTING is enabled
        if NOISE_TESTING and data:
            data = add_gaussian_noise_snr(data, SNR_DB)
        
        # Otherwise, process audio normally
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