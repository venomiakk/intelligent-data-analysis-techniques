import os
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf

class SpeechThread(QThread):
    """Klasa do rozpoznawania mowy w osobnym wątku, aby nie blokować interfejsu"""
    finished = pyqtSignal(str, str)  # tekst, wykryty język
    progress = pyqtSignal(int)  # postęp przetwarzania
    error = pyqtSignal(str)
    
    def __init__(self, mode='record', file_path=None, model=None, forced_language=None):
        super().__init__()
        self.mode = mode  # 'record' lub 'file'
        self.file_path = file_path
        self.model = model
        self.forced_language = forced_language 
        self.sample_rate = 16000 
        self.recording = False
        self.audio_data = []
        
    def run(self):
        try:
            if not self.model:
                raise Exception("Model Whisper nie został przekazany!")
            
            self.progress.emit(30)
            
            # Nagrywanie lub wczytywanie audio
            if self.mode == 'record':
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                temp_filename = temp_file.name
                temp_file.close()
                
                print("Rozpoczynam nagrywanie, naciśnij przycisk stop aby zakończyć...")
                self.recording = True
                self.audio_data = []
                
                with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=self._audio_callback):
                    while self.recording:
                        sd.sleep(100)
                
                if len(self.audio_data) > 0:
                    audio_array = np.concatenate(self.audio_data, axis=0)
                    if np.max(np.abs(audio_array)) > 0:
                        audio_array = audio_array / np.max(np.abs(audio_array))
                    
                    sf.write(temp_filename, audio_array, self.sample_rate)
                    audio_path = temp_filename
                else:
                    raise Exception("Brak nagranych danych audio")
                    
            else:
                audio_path = self.file_path
            
            self.progress.emit(50)
            
            self.progress.emit(70)

            transcribe_options = {"verbose": True}
            if self.forced_language:
                transcribe_options["language"] = self.forced_language
                print(f"Wymuszono język: {self.forced_language}")
            
            result = self.model.transcribe(audio_path, **transcribe_options)
            text = result["text"]
            detected_lang = result["language"]
            print(f"Pełny wynik Whisper: {result}")
            print(f"Wykryty/wymuszone język: {detected_lang}")
            
            if self.mode == 'record' and os.path.exists(temp_filename):
                os.unlink(temp_filename)
                
            self.progress.emit(100)
            self.finished.emit(text, detected_lang)
            
        except Exception as e:
            self.error.emit(f"Błąd: {str(e)}")
            if self.mode == 'record' and 'temp_filename' in locals() and os.path.exists(temp_filename):
                os.unlink(temp_filename)
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback do zbierania danych audio"""
        if status:
            print(f"Status: {status}")
        if self.recording:
            self.audio_data.append(indata.copy())
    
    def stop(self):
        """Zatrzymaj nagrywanie"""
        self.recording = False