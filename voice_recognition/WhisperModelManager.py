import whisper
from PyQt5.QtCore import QThread, pyqtSignal

class WhisperModelManager(QThread):
    """Klasa do zarządzania modelem Whisper z cachowaniem"""
    model_loaded = pyqtSignal(object)
    loading_progress = pyqtSignal(str)
    
    def __init__(self, model_size='medium'):
        super().__init__()
        self.model_size = model_size
        self.model = None
        
    def run(self):
        try:
            self.loading_progress.emit(f"Ładowanie modelu {self.model_size}...")
            
            self.model = whisper.load_model(self.model_size)
            self.loading_progress.emit(f"Model {self.model_size} załadowany pomyślnie!")
            self.model_loaded.emit(self.model)
            
        except Exception as e:
            self.loading_progress.emit(f"Błąd ładowania modelu: {str(e)}")
