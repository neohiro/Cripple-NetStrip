import math
import struct
import io
import wave
import threading
import logging

try:
    import winsound
except ImportError:
    winsound = None

logger = logging.getLogger(__name__)

class SoundManager:
    """Manages procedural audio generation and asynchronous playback."""
    
    def __init__(self):
        self.muted = False
        
        # Pre-generate wav buffers for instant playback
        self._notification_wav = self._generate_sine_wave(freq=600, duration_ms=150, volume=0.3, envelope_ms=20)
        self._alert_wav = self._generate_sine_wave(freq=150, duration_ms=200, volume=0.4, envelope_ms=50)
        self._click_wav = self._generate_sine_wave(freq=1200, duration_ms=10, volume=0.1, envelope_ms=2)

    def set_muted(self, muted: bool):
        self.muted = muted

    def play_notification(self):
        """Soft ping for new apps/connections."""
        self._play_async(self._notification_wav)

    def play_alert(self):
        """Dull thud for blocked connections."""
        self._play_async(self._alert_wav)

    def play_click(self):
        """Subtle tick for UI interactions."""
        self._play_async(self._click_wav)

    def play_intro(self):
        """Bright complex sound for startup."""
        if self.muted or not winsound:
            return
            
        def _play():
            try:
                winsound.Beep(523, 150) # C5
                winsound.Beep(659, 150) # E5
                winsound.Beep(784, 150) # G5
                winsound.Beep(1046, 400) # C6
            except Exception as e:
                logger.error(f"Error playing intro sound: {e}")
                
        threading.Thread(target=_play, daemon=True).start()

    def _play_async(self, wav_data: bytes):
        if self.muted or not winsound or not wav_data:
            return
            
        def _play():
            try:
                winsound.PlaySound(wav_data, winsound.SND_MEMORY | winsound.SND_NODEFAULT)
            except Exception as e:
                logger.error(f"Error playing sound: {e}")
                
        threading.Thread(target=_play, daemon=True).start()

    def _generate_sine_wave(self, freq: int, duration_ms: int, volume: float = 0.5, sample_rate: int = 44100, envelope_ms: int = 10) -> bytes:
        """Generate a RIFF WAVE formatted byte string containing a sine wave."""
        num_samples = int(sample_rate * (duration_ms / 1000.0))
        envelope_samples = int(sample_rate * (envelope_ms / 1000.0))
        
        audio_data = bytearray()
        
        for i in range(num_samples):
            # Apply fade in/out envelope to prevent clicking/popping
            envelope = 1.0
            if i < envelope_samples:
                envelope = i / envelope_samples
            elif i > num_samples - envelope_samples:
                envelope = (num_samples - i) / envelope_samples
                
            value = int(volume * envelope * 32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            audio_data.extend(struct.pack('<h', value))
            
        # Write to in-memory wave file
        out = io.BytesIO()
        with wave.open(out, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframesraw(audio_data)
            
        return out.getvalue()

# Global sound manager instance
sound_manager = SoundManager()
