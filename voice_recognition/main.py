import sys
import os
import json
import tempfile
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                           QHBoxLayout, QWidget, QLabel, QTextEdit, QListWidget, 
                           QFileDialog, QComboBox, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
# httpx==0.13.3
from googletrans import Translator
from langdetect import detect
import whisper
import sounddevice as sd
import soundfile as sf
import wave
import pyaudio
import string
#before translatins
class RecipeDatabase:
    """Klasa zarządzająca bazą przepisów"""
    def __init__(self, filename="recipes.json"):
        self.filename = filename
        self.load_recipes()
        
    def load_recipes(self):
        """Ładowanie przepisów z pliku JSON"""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                self.recipes = json.load(f)
        except FileNotFoundError:
            # Domyślne przepisy, jeśli plik nie istnieje
            self.recipes = [
                {
                    "name": "Spaghetti Bolognese",
                    "ingredients": ["makaron", "mięso mielone", "pomidory", "cebula", "czosnek", "marchew", "seler"],
                    "instructions": "Przygotuj sos z mięsa i warzyw, ugotuj makaron, podawaj razem."
                },
                {
                    "name": "Omlet",
                    "ingredients": ["jajka", "ser", "szynka", "pomidory", "cebula"],
                    "instructions": "Roztrzep jajka, dodaj pozostałe składniki, smaż na patelni."
                },
                {
                    "name": "Sałatka grecka",
                    "ingredients": ["pomidory", "ogórek", "cebula", "oliwki", "ser feta", "oliwa"],
                    "instructions": "Pokrój warzywa, dodaj ser feta i oliwki, polej oliwą."
                },
                {
                    "name": "Placki ziemniaczane",
                    "ingredients": ["ziemniaki", "cebula", "jajka", "mąka", "sól", "pieprz"],
                    "instructions": "Zetrzyj ziemniaki i cebulę, dodaj pozostałe składniki, smaż na patelni."
                },
                {
                    "name": "Rosół",
                    "ingredients": ["kurczak", "marchew", "pietruszka", "seler", "cebula", "por", "makaron"],
                    "instructions": "Gotuj kurczaka z warzywami, dodaj przyprawy, podawaj z makaronem."
                }
            ]
            self.save_recipes()
    
    def save_recipes(self):
        """Zapisywanie przepisów do pliku JSON"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.recipes, f, ensure_ascii=False, indent=4)
    
    def filter_recipes(self, ingredients):
        """Filtrowanie przepisów zawierających WSZYSTKIE podane składniki"""
        if not ingredients:
            return []
        
        filtered = []
        
        # Konwersja wszystkich składników na małe litery dla łatwiejszego porównania
        ingredients = [ing.lower() for ing in ingredients]
        
        for recipe in self.recipes:
            recipe_ingredients = [ing.lower() for ing in recipe["ingredients"]]
            
            # Sprawdź czy WSZYSTKIE składniki są obecne w przepisie
            if all(any(ingredient in recipe_ing or recipe_ing in ingredient 
                      for recipe_ing in recipe_ingredients) 
                  for ingredient in ingredients):
                filtered.append(recipe)
                
        return filtered


class SpeechThread(QThread):
    """Klasa do rozpoznawania mowy w osobnym wątku, aby nie blokować interfejsu"""
    finished = pyqtSignal(str, str)  # tekst, wykryty język
    progress = pyqtSignal(int)  # postęp przetwarzania
    error = pyqtSignal(str)
    
    def __init__(self, mode='record', file_path=None, model=None):
        super().__init__()
        self.mode = mode  # 'record' lub 'file'
        self.file_path = file_path
        self.model = model  # Model zawsze musi być przekazany
        self.sample_rate = 16000  # Whisper preferuje 16kHz
        self.recording = False
        self.audio_data = []
        
    def run(self):
        try:
            # Model musi być już załadowany
            if not self.model:
                raise Exception("Model Whisper nie został przekazany!")
            
            self.progress.emit(30)
            
            # Nagrywanie lub wczytywanie audio
            if self.mode == 'record':
                # Nagrywanie dźwięku
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                temp_filename = temp_file.name
                temp_file.close()
                
                # Przygotowanie do nagrywania
                print("Rozpoczynam nagrywanie, naciśnij przycisk stop aby zakończyć...")
                self.recording = True
                self.audio_data = []
                
                # Otwarcie strumienia audio
                with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=self._audio_callback):
                    while self.recording:
                        sd.sleep(100)  # Czekaj 100ms
                
                # Konwersja zebranych danych do tablicy numpy
                if len(self.audio_data) > 0:
                    audio_array = np.concatenate(self.audio_data, axis=0)
                    # Normalizacja audio
                    if np.max(np.abs(audio_array)) > 0:
                        audio_array = audio_array / np.max(np.abs(audio_array))
                    
                    # Zapisz do pliku tymczasowego
                    sf.write(temp_filename, audio_array, self.sample_rate)
                    audio_path = temp_filename
                else:
                    raise Exception("Brak nagranych danych audio")
                    
            else:
                # Użyj wybranego pliku
                audio_path = self.file_path
            
            self.progress.emit(50)
            
            # Transkrypcja z Whisper
            self.progress.emit(70)
            result = self.model.transcribe(audio_path)
            text = result["text"]
            detected_lang = result["language"]
            print(f"Pełny wynik Whisper: {result}")
            print(f"Wykryty język: {detected_lang}")
            
            # Usuń plik tymczasowy jeśli był utworzony
            if self.mode == 'record' and os.path.exists(temp_filename):
                os.unlink(temp_filename)
                
            self.progress.emit(100)
            self.finished.emit(text, detected_lang)
            
        except Exception as e:
            self.error.emit(f"Błąd: {str(e)}")
            # Próba usunięcia pliku tymczasowego w przypadku błędu
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


class WhisperModelManager(QThread):
    """Klasa do zarządzania modelem Whisper z cachowaniem"""
    model_loaded = pyqtSignal(object)  # sygnał z załadowanym modelem
    loading_progress = pyqtSignal(str)  # sygnał z informacją o postępie
    
    def __init__(self, model_size='medium'):
        super().__init__()
        self.model_size = model_size
        self.model = None
        
    def run(self):
        try:
            self.loading_progress.emit(f"Ładowanie modelu {self.model_size}...")
            
            # Załaduj model (Whisper automatycznie pobierze go jeśli nie ma w cache)
            self.model = whisper.load_model(self.model_size)
            self.loading_progress.emit(f"Model {self.model_size} załadowany pomyślnie!")
            self.model_loaded.emit(self.model)
            
        except Exception as e:
            self.loading_progress.emit(f"Błąd ładowania modelu: {str(e)}")


class MainWindow(QMainWindow):
    """Główne okno aplikacji"""
    def __init__(self):
        super().__init__()
        self.recipe_db = RecipeDatabase()
        self.translator = Translator()
        
        # Model Whisper
        self.whisper_model = None
        self.model_loaded = False
        self.current_model_size = None  # Dodaj śledzenie aktualnego modelu
        
        self.init_ui()
        self.start_model_loading()
    
    def start_model_loading(self):
        """Rozpocznij ładowanie modelu Whisper"""
        selected_model = self.model_combo.currentText() if hasattr(self, 'model_combo') else 'medium'
        self.model_status_label.setText(f"Ładowanie modelu {selected_model}...")
        
        # Zablokuj przyciski audio i zmianę modelu
        self.set_audio_buttons_enabled(False)
        if hasattr(self, 'change_model_button'):
            self.change_model_button.setEnabled(False)
        
        # Rozpocznij ładowanie modelu
        self.model_manager = WhisperModelManager(model_size=selected_model)
        self.model_manager.model_loaded.connect(self.on_model_loaded)
        self.model_manager.loading_progress.connect(self.on_loading_progress)
        self.model_manager.start()

    def change_model(self):
        """Zmień model Whisper na wybrany z listy"""
        selected_model = self.model_combo.currentText()
        current_model_size = getattr(self, 'current_model_size', None)
        
        # Sprawdź czy wybrany model jest inny niż aktualny
        if selected_model == current_model_size:
            QMessageBox.information(self, "Informacja", f"Model {selected_model} jest już załadowany.")
            return
        
        # Potwierdź zmianę modelu
        reply = QMessageBox.question(self, "Zmiana modelu", 
                                    f"Czy na pewno chcesz zmienić model z '{current_model_size}' na '{selected_model}'?\n\n"
                                    f"To może potrwać kilka minut jeśli model nie jest w cache.",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.model_loaded = False
            self.start_model_loading()

    def on_model_loaded(self, model):
        """Callback wywoływany po załadowaniu modelu"""
        self.whisper_model = model
        self.model_loaded = True
        self.current_model_size = self.model_combo.currentText()
        
        self.model_status_label.setText(f"Model {self.current_model_size} gotowy")
        self.status_label.setText("Model Whisper gotowy do użycia")
        
        # Odblokuj przyciski audio i zmianę modelu
        self.set_audio_buttons_enabled(True)
        if hasattr(self, 'change_model_button'):
            self.change_model_button.setEnabled(True)

    def on_loading_progress(self, message):
        """Callback dla aktualizacji postępu ładowania"""
        self.model_status_label.setText(message)
        self.status_label.setText(message)

    def set_audio_buttons_enabled(self, enabled):
        """Włącz/wyłącz przyciski audio"""
        if hasattr(self, 'record_button'):
            self.record_button.setEnabled(enabled)
        if hasattr(self, 'file_button'):
            self.file_button.setEnabled(enabled)
    
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        self.setWindowTitle("Filtrowanie przepisów na podstawie mowy")
        self.setGeometry(100, 100, 800, 600)
        
        # Główny układ
        main_layout = QVBoxLayout()
        
        # Sekcja konfiguracji modelu
        model_config_layout = QHBoxLayout()
        model_config_layout.addWidget(QLabel("Model Whisper:"))
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("medium")  # Domyślny model
        model_config_layout.addWidget(self.model_combo)
        
        self.change_model_button = QPushButton("Zmień model")
        self.change_model_button.clicked.connect(self.change_model)
        self.change_model_button.setEnabled(False)  # Włączy się po załadowaniu pierwszego modelu
        model_config_layout.addWidget(self.change_model_button)
        
        self.model_status_label = QLabel("Status modelu: Ładowanie...")
        model_config_layout.addWidget(self.model_status_label)
        model_config_layout.addStretch()
        
        main_layout.addLayout(model_config_layout)
        
        # Sekcja audio
        audio_group = QVBoxLayout()
        
        # Dodaj przyciski audio z początkowo wyłączoną funkcjonalnością
        audio_buttons = QHBoxLayout()
        self.record_button = QPushButton("Rozpocznij nagrywanie")
        self.record_button.clicked.connect(self.record_audio)
        self.record_button.setEnabled(False)  # Początkowo wyłączony
        
        self.stop_button = QPushButton("Zatrzymaj nagrywanie")
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        
        self.file_button = QPushButton("Wybierz plik audio")
        self.file_button.clicked.connect(self.select_audio_file)
        self.file_button.setEnabled(False)  # Początkowo wyłączony
        
        audio_buttons.addWidget(self.record_button)
        audio_buttons.addWidget(self.stop_button)
        audio_buttons.addWidget(self.file_button)
        
        audio_group.addLayout(audio_buttons)
        
        # Pasek postępu
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        audio_group.addWidget(self.progress_bar)
        
        # Status i rozpoznany tekst
        self.status_label = QLabel("Gotowy do rozpoznawania mowy...")
        audio_group.addWidget(self.status_label)
        
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Rozpoznany tekst:"))
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        text_layout.addWidget(self.text_edit)
        audio_group.addLayout(text_layout)
        
        # Wykryty język i składniki
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Wykryty język:"))
        self.lang_label = QLabel("-")
        lang_layout.addWidget(self.lang_label)
        lang_layout.addStretch()
        audio_group.addLayout(lang_layout)
        
        # Lista wykrytych składników
        ingredients_layout = QVBoxLayout()
        ingredients_header = QHBoxLayout()
        ingredients_header.addWidget(QLabel("Wykryte składniki:"))

        # Przycisk do usuwania wybranego składnika
        self.remove_ingredient_button = QPushButton("Usuń wybrany składnik")
        self.remove_ingredient_button.clicked.connect(self.remove_ingredient)
        self.remove_ingredient_button.setEnabled(False)  # Początkowo wyłączony
        ingredients_header.addWidget(self.remove_ingredient_button)

        # Przycisk do usuwania wszystkich składników
        self.clear_ingredients_button = QPushButton("Wyczyść wszystkie")
        self.clear_ingredients_button.clicked.connect(self.clear_all_ingredients)
        ingredients_header.addWidget(self.clear_ingredients_button)
        ingredients_header.addStretch()

        ingredients_layout.addLayout(ingredients_header)

        self.ingredients_list = QListWidget()
        self.ingredients_list.itemSelectionChanged.connect(self.on_ingredient_selection_changed)
        self.ingredients_list.itemDoubleClicked.connect(self.remove_ingredient_on_double_click)  # Dodaj tę linię
        ingredients_layout.addWidget(self.ingredients_list)

        audio_group.addLayout(ingredients_layout)
        
        # Opcje tłumaczenia
        translate_layout = QHBoxLayout()
        translate_layout.addWidget(QLabel("Tłumacz na:"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Polski", "English", "Español", "Français", "Deutsch"])
        translate_layout.addWidget(self.language_combo)
        self.translate_button = QPushButton("Tłumacz")
        self.translate_button.clicked.connect(self.translate_text)
        translate_layout.addWidget(self.translate_button)
        audio_group.addLayout(translate_layout)
        
        main_layout.addLayout(audio_group)
        
        # Sekcja przepisów - lista i składniki z tłumaczeniem
        recipe_group = QVBoxLayout()

        # Nagłówek sekcji przepisów z przyciskiem tłumaczenia
        recipe_header = QHBoxLayout()
        recipe_header.addWidget(QLabel("Znalezione przepisy:"))
        recipe_header.addStretch()
        recipe_group.addLayout(recipe_header)

        self.recipe_list = QListWidget()
        self.recipe_list.itemClicked.connect(self.show_recipe)
        self.recipe_list.itemSelectionChanged.connect(self.on_recipe_selection_changed)  # Dodaj obsługę zaznaczenia
        recipe_group.addWidget(self.recipe_list)

        # Kontrolki tłumaczenia przepisów
        recipe_translate_layout = QHBoxLayout()
        recipe_translate_layout.addWidget(QLabel("Tłumacz wybrany przepis na:"))

        self.recipe_language_combo = QComboBox()
        self.recipe_language_combo.addItems(["Polski", "English", "Español", "Français", "Deutsch"])
        recipe_translate_layout.addWidget(self.recipe_language_combo)

        self.translate_recipe_button = QPushButton("Tłumacz wybrany przepis")
        self.translate_recipe_button.clicked.connect(self.translate_selected_recipe)
        self.translate_recipe_button.setEnabled(False)  # Włączy się po zaznaczeniu przepisu
        recipe_translate_layout.addWidget(self.translate_recipe_button)

        # Przycisk do przywracania oryginalnej wersji przepisu
        self.restore_recipe_button = QPushButton("Przywróć oryginalną wersję")
        self.restore_recipe_button.clicked.connect(self.restore_original_recipe)
        self.restore_recipe_button.setEnabled(False)
        recipe_translate_layout.addWidget(self.restore_recipe_button)

        recipe_translate_layout.addStretch()

        recipe_group.addLayout(recipe_translate_layout)

        recipe_details_layout = QVBoxLayout()
        self.recipe_name = QLabel("Wybierz przepis, aby zobaczyć szczegóły")
        recipe_details_layout.addWidget(self.recipe_name)
        
        self.recipe_ingredients = QTextEdit()
        self.recipe_ingredients.setReadOnly(True)
        recipe_details_layout.addWidget(QLabel("Składniki:"))
        recipe_details_layout.addWidget(self.recipe_ingredients)
        
        recipe_group.addLayout(recipe_details_layout)
        main_layout.addLayout(recipe_group)
        
        # Ustawienie głównego widgetu
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def record_audio(self):
        """Funkcja do rozpoczęcia nagrywania dźwięku z mikrofonu"""
        if not self.model_loaded:
            QMessageBox.warning(self, "Błąd", "Model Whisper nie jest jeszcze załadowany!")
            return
            
        self.status_label.setText(f"Nagrywanie (model: {self.current_model_size})... Mów teraz i naciśnij 'Zatrzymaj nagrywanie' gdy skończysz")
        self.progress_bar.setValue(0)
        self.record_button.setEnabled(False)
        self.file_button.setEnabled(False)
        self.change_model_button.setEnabled(False)  # Zablokuj zmianę modelu podczas nagrywania
        self.stop_button.setEnabled(True)
        
        self.speech_thread = SpeechThread(mode='record', model=self.whisper_model)
        self.speech_thread.finished.connect(self.process_speech_result)
        self.speech_thread.progress.connect(self.update_progress)
        self.speech_thread.error.connect(self.show_error)
        self.speech_thread.start()
    
    def stop_recording(self):
        """Funkcja do zatrzymania nagrywania"""
        if hasattr(self, 'speech_thread') and self.speech_thread.isRunning():
            self.status_label.setText("Zatrzymywanie nagrywania...")
            self.speech_thread.stop()
            self.stop_button.setEnabled(False)
    
    def select_audio_file(self):
        """Funkcja do wyboru pliku audio"""
        if not self.model_loaded:
            QMessageBox.warning(self, "Błąd", "Model Whisper nie jest jeszcze załadowany!")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik audio", "", "Audio Files (*.wav *.mp3 *.m4a *.ogg)")
        if file_path:
            self.status_label.setText(f"Przetwarzanie pliku (model: {self.current_model_size}): {os.path.basename(file_path)}")
            self.progress_bar.setValue(0)
            self.record_button.setEnabled(False)
            self.file_button.setEnabled(False)
            self.change_model_button.setEnabled(False)  # Zablokuj zmianę modelu podczas przetwarzania
            
            self.speech_thread = SpeechThread(mode='file', file_path=file_path, model=self.whisper_model)
            self.speech_thread.finished.connect(self.process_speech_result)
            self.speech_thread.progress.connect(self.update_progress)
            self.speech_thread.error.connect(self.show_error)
            self.speech_thread.start()
    
    def update_progress(self, value):
        """Aktualizacja paska postępu"""
        self.progress_bar.setValue(value)
    
    def process_speech_result(self, text, detected_lang):
        """Przetwarzanie wyników rozpoznawania mowy"""
        self.text_edit.setText(text)
        self.status_label.setText("Rozpoznawanie zakończone")
        self.record_button.setEnabled(True)
        self.file_button.setEnabled(True)
        self.change_model_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Wyświetlanie wykrytego języka
        lang_names = {
            'pl': 'Polski',
            'en': 'English',
            'es': 'Español',
            'fr': 'Français',
            'de': 'Deutsch'
        }
        lang_name = lang_names.get(detected_lang, detected_lang)
        self.lang_label.setText(lang_name)
        
        # Ekstrakcja składników
        ingredients = self.extract_ingredients(text)
        
        # Tłumacz składniki na polski jeśli wykryty język nie jest polski
        polish_ingredients = ingredients.copy()
        if detected_lang != 'pl' and ingredients:
            polish_ingredients = self.translate_ingredients_to_polish(ingredients, detected_lang)
        
        # Wyświetl oryginalne składniki
        self.ingredients_list.clear()
        for ingredient in ingredients:
            self.ingredients_list.addItem(ingredient)
        
        # Filtrowanie przepisów na podstawie polskich składników
        filtered_recipes = self.recipe_db.filter_recipes(polish_ingredients)
        self.display_recipes(filtered_recipes)
        
        # Wyłącz przycisk usuwania (brak zaznaczenia)
        self.remove_ingredient_button.setEnabled(False)
        
        # Dodaj informację o tłumaczeniu jeśli było potrzebne
        if detected_lang != 'pl' and ingredients:
            status_msg = f"Znaleziono {len(ingredients)} składników (przetłumaczono na polski), {len(filtered_recipes)} przepisów"
        else:
            status_msg = f"Znaleziono {len(ingredients)} składników, {len(filtered_recipes)} przepisów"
        
        self.status_label.setText(status_msg)
    
    def translate_ingredients_to_polish(self, ingredients, source_lang):
        """Tłumaczenie składników na język polski do wyszukiwania przepisów"""
        if not ingredients:
            return []
        
        polish_ingredients = []
        
        try:
            for ingredient in ingredients:
                try:
                    # Tłumacz każdy składnik na polski
                    translated = self.translator.translate(ingredient, src=source_lang, dest='pl').text
                    polish_ingredients.append(translated.lower())
                    print(f"Przetłumaczono składnik: {ingredient} -> {translated}")
                except Exception as e:
                    # Jeśli nie udało się przetłumaczyć, zostaw oryginalny
                    polish_ingredients.append(ingredient.lower())
                    print(f"Nie udało się przetłumaczyć składnika: {ingredient}, błąd: {e}")
        
            return polish_ingredients
            
        except Exception as e:
            print(f"Błąd podczas tłumaczenia składników: {e}")
            return [ing.lower() for ing in ingredients]  # Zwróć oryginalne składniki w małych literach
    
    def translate_text(self):
        """Tłumaczenie rozpoznanego tekstu i składników"""
        text = self.text_edit.toPlainText()
        if not text:
            return
        
        target_language = self.language_combo.currentText()
        language_codes = {
            "Polski": "pl",
            "English": "en",
            "Español": "es",
            "Français": "fr",
            "Deutsch": "de"
        }
        target_code = language_codes.get(target_language, "en")
        
        try:
            # Sprawdź czy tekst zawiera już tłumaczenie
            if "Tłumaczenie tekstu:" in text:
                # Wyciągnij tylko oryginalny tekst (pierwsza linia przed "Tłumaczenie tekstu:")
                original_text = text.split("\n\nTłumaczenie tekstu:")[0]
            else:
                original_text = text
            
            # Tłumacz główny tekst
            translated_text = self.translator.translate(original_text, dest=target_code).text
            
            # Pobierz składniki z listy
            ingredients = []
            for i in range(self.ingredients_list.count()):
                ingredient = self.ingredients_list.item(i).text()
                ingredients.append(ingredient)
            
            # Tłumacz składniki jeśli istnieją
            translated_ingredients = []
            if ingredients:
                for ingredient in ingredients:
                    try:
                        translated_ingredient = self.translator.translate(ingredient, dest=target_code).text
                        translated_ingredients.append(translated_ingredient)
                    except:
                        # Jeśli nie udało się przetłumaczyć składnika, zostaw oryginalny
                        translated_ingredients.append(ingredient)
            
            # Wyświetl wyniki
            result_text = f"Oryginalny tekst:\n{original_text}\n\nTłumaczenie tekstu:\n{translated_text}"
            
            if translated_ingredients:
                result_text += f"\n\nTłumaczenie składników:\n{', '.join(translated_ingredients)}"
                
                # Zaktualizuj listę składników przetłumaczonymi wersjami
                self.ingredients_list.clear()
                for translated_ingredient in translated_ingredients:
                    self.ingredients_list.addItem(translated_ingredient)
            
            self.text_edit.setText(result_text)
            
        except Exception as e:
            self.show_error(f"Błąd tłumaczenia: {str(e)}")
    
    def extract_ingredients(self, text):
        """Ekstrakcja składników z tekstu - prosta implementacja z usuwaniem interpunkcji i duplikatów"""
        if not text:
            return []
        
        # Konwertuj na małe litery i usuń interpunkcję
        text = text.lower()
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        ingredients = []
        
        # Podziel po separatorach
        for separator in [' i ', ' and ', ' oraz ', ' z ', ' ze ']:
            if separator in text:
                ingredients = [item.strip() for item in text.split(separator) if item.strip()]
                break
        
        # Jeśli nie znaleziono separatorów, dzielimy po spacjach
        if not ingredients:
            ingredients = [word.strip() for word in text.split() if word.strip()]
        
        # Usuń duplikaty zachowując kolejność
        unique_ingredients = []
        for ingredient in ingredients:
            if ingredient not in unique_ingredients:
                unique_ingredients.append(ingredient)
        
        return unique_ingredients

    def display_recipes(self, recipes):
        """Wyświetlanie przefiltrowanych przepisów"""
        self.recipe_list.clear()
        if not recipes:
            self.recipe_list.addItem("Brak przepisów spełniających kryteria")
            self.translate_recipe_button.setEnabled(False)  # Zmień z translate_recipes_button
            return
        
        for recipe in recipes:
            self.recipe_list.addItem(recipe["name"])
        
        # Wyłącz przycisk tłumaczenia (nie ma jeszcze zaznaczenia)
        self.translate_recipe_button.setEnabled(False)

    def show_error(self, message):
        """Wyświetlanie błędów"""
        QMessageBox.critical(self, "Błąd", message)
        # Przywróć stan przycisków po błędzie
        self.record_button.setEnabled(True)
        self.file_button.setEnabled(True)
        if hasattr(self, 'change_model_button'):
            self.change_model_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(0)

    def show_recipe(self, item):
        """Wyświetlanie szczegółów wybranego przepisu - uproszczona wersja"""
        recipe_name = item.text()
        if recipe_name in ["Brak przepisów spełniających kryteria", "Brak składników do wyszukiwania"]:
            return
        
        # Pobierz przepis na podstawie pozycji w liście
        current_row = self.recipe_list.row(item)
        
        # Znajdź aktualnie wyświetlane przepisy
        current_ingredients = []
        for i in range(self.ingredients_list.count()):
            ingredient = self.ingredients_list.item(i).text()
            current_ingredients.append(ingredient)
        
        if current_ingredients:
            # Przefiltruj przepisy tak samo jak wcześniej
            lang_name = self.lang_label.text()
            if lang_name != 'Polski' and lang_name != '-':
                detected_lang_code = None
                for code, name in {'pl': 'Polski', 'en': 'English', 'es': 'Español', 'fr': 'Français', 'de': 'Deutsch'}.items():
                    if name == lang_name:
                        detected_lang_code = code
                        break
                
                if detected_lang_code and detected_lang_code != 'pl':
                    polish_ingredients = self.translate_ingredients_to_polish(current_ingredients, detected_lang_code)
                else:
                    polish_ingredients = current_ingredients
            else:
                polish_ingredients = current_ingredients
            
            filtered_recipes = self.recipe_db.filter_recipes(polish_ingredients)
            
            if 0 <= current_row < len(filtered_recipes):
                selected_recipe = filtered_recipes[current_row]
                self.recipe_name.setText(f"Przepis: {recipe_name}")  # Użyj nazwy z listy (może być przetłumaczona)
                self.recipe_ingredients.setText("\n".join(selected_recipe["ingredients"]))
            else:
                self.recipe_name.setText("Nie znaleziono przepisu")
                self.recipe_ingredients.setText("")
        else:
            self.recipe_name.setText("Brak składników")
            self.recipe_ingredients.setText("")

    def on_ingredient_selection_changed(self):
        """Obsługa zmiany zaznaczenia składnika"""
        selected_items = self.ingredients_list.selectedItems()
        self.remove_ingredient_button.setEnabled(len(selected_items) > 0)

    def remove_ingredient(self):
        """Usuwanie wybranego składnika i ponowne wyszukiwanie przepisów"""
        selected_items = self.ingredients_list.selectedItems()
        if not selected_items:
            return
        
        # Usuń zaznaczony składnik
        for item in selected_items:
            row = self.ingredients_list.row(item)
            self.ingredients_list.takeItem(row)
        
        # Pobierz aktualne składniki z listy
        current_ingredients = []
        for i in range(self.ingredients_list.count()):
            ingredient = self.ingredients_list.item(i).text()
            current_ingredients.append(ingredient)
        
        # Ponowne wyszukiwanie przepisów
        self.search_recipes_with_current_ingredients(current_ingredients)
        
        # Wyłącz przycisk jeśli nie ma już zaznaczenia
        self.remove_ingredient_button.setEnabled(False)

    def remove_ingredient_on_double_click(self, item):
        """Usuwanie składnika przez podwójne kliknięcie"""
        reply = QMessageBox.question(self, "Usuwanie składnika", 
                                    f"Czy na pewno chcesz usunąć składnik '{item.text()}'?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Zaznacz element i usuń
            self.ingredients_list.setCurrentItem(item)
            self.remove_ingredient()

    def search_recipes_with_current_ingredients(self, ingredients):
        """Wyszukiwanie przepisów na podstawie aktualnych składników"""
        if not ingredients:
            self.recipe_list.clear()
            self.recipe_list.addItem("Brak składników do wyszukiwania")
            self.status_label.setText("Brak składników")
            return
        
        # Sprawdź czy składniki są w języku polskim (jeśli nie, przetłumacz)
        lang_name = self.lang_label.text()
        if lang_name != 'Polski' and lang_name != '-':
            # Tłumacz składniki na polski
            detected_lang_code = None
            for code, name in {'pl': 'Polski', 'en': 'English', 'es': 'Español', 'fr': 'Français', 'de': 'Deutsch'}.items():
                if name == lang_name:
                    detected_lang_code = code
                    break
            
            if detected_lang_code and detected_lang_code != 'pl':
                polish_ingredients = self.translate_ingredients_to_polish(ingredients, detected_lang_code)
            else:
                polish_ingredients = ingredients
        else:
            polish_ingredients = ingredients
        
        # Filtrowanie przepisów
        filtered_recipes = self.recipe_db.filter_recipes(polish_ingredients)
        self.display_recipes(filtered_recipes)
        
        # Aktualizuj status
        self.status_label.setText(f"Aktualne składniki: {len(ingredients)}, znalezione przepisy: {len(filtered_recipes)}")
    
    def clear_all_ingredients(self):
        """Usuwanie wszystkich składników"""
        if self.ingredients_list.count() == 0:
            return
        
        reply = QMessageBox.question(self, "Usuwanie składników", 
                                    "Czy na pewno chcesz usunąć wszystkie składniki?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.ingredients_list.clear()
            self.recipe_list.clear()
            self.recipe_list.addItem("Brak składników do wyszukiwania")
            self.status_label.setText("Wszystkie składniki zostały usunięte")
            self.remove_ingredient_button.setEnabled(False)

    def on_recipe_selection_changed(self):
        """Obsługa zmiany zaznaczenia przepisu"""
        selected_items = self.recipe_list.selectedItems()
        has_selection = len(selected_items) > 0
        
        # Sprawdź czy zaznaczony element to rzeczywisty przepis
        if has_selection:
            recipe_name = selected_items[0].text()
            is_valid_recipe = recipe_name not in ["Brak przepisów spełniających kryteria", "Brak składników do wyszukiwania"]
            self.translate_recipe_button.setEnabled(is_valid_recipe)
            self.restore_recipe_button.setEnabled(is_valid_recipe)  # Dodaj tę linię
        else:
            self.translate_recipe_button.setEnabled(False)
            self.restore_recipe_button.setEnabled(False)  # Dodaj tę linię

    def translate_selected_recipe(self):
        """Tłumaczenie wybranego przepisu"""
        selected_items = self.recipe_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Błąd", "Nie wybrano żadnego przepisu.")
            return
        
        recipe_name = selected_items[0].text()
        if recipe_name in ["Brak przepisów spełniających kryteria", "Brak składników do wyszukiwania"]:
            QMessageBox.warning(self, "Błąd", "Wybrano nieprawidłowy element.")
            return
        
        target_language = self.recipe_language_combo.currentText()
        language_codes = {
            "Polski": "pl",
            "English": "en",
            "Español": "es",
            "Français": "fr",
            "Deutsch": "de"
        }
        target_code = language_codes.get(target_language, "en")
        
        if target_code == "pl":
            QMessageBox.information(self, "Informacja", "Przepis jest już w języku polskim.")
            return
        
        try:
            self.status_label.setText(f"Tłumaczenie przepisu na język: {target_language}...")
            
            # Tłumacz nazwę przepisu w liście
            selected_item = selected_items[0]
            try:
                translated_name = self.translator.translate(recipe_name, dest=target_code).text
                selected_item.setText(translated_name)
                
                # Zaktualizuj nazwę w sekcji szczegółów
                self.recipe_name.setText(f"Przepis: {translated_name}")
            except Exception as e:
                print(f"Nie udało się przetłumaczyć nazwy przepisu: {recipe_name}, błąd: {e}")
            
            # Tłumacz składniki aktualnie wyświetlanego przepisu
            current_ingredients = self.recipe_ingredients.toPlainText()
            if current_ingredients:
                translated_ingredients = []
                ingredients_list = current_ingredients.split('\n')
                
                for ingredient in ingredients_list:
                    if ingredient.strip():
                        try:
                            translated_ingredient = self.translator.translate(ingredient.strip(), dest=target_code).text
                            translated_ingredients.append(translated_ingredient)
                        except Exception as e:
                            translated_ingredients.append(ingredient.strip())  # Zostaw oryginalny jeśli błąd
                            print(f"Nie udało się przetłumaczyć składnika: {ingredient}, błąd: {e}")
            
            self.recipe_ingredients.setText('\n'.join(translated_ingredients))
        
            self.status_label.setText(f"Przepis przetłumaczony na język: {target_language}")
            QMessageBox.information(self, "Tłumaczenie", f"Przepis '{recipe_name}' został przetłumaczony na język: {target_language}")
            
            # Włącz przycisk przywracania oryginalnej wersji
            self.restore_recipe_button.setEnabled(True)
            
        except Exception as e:
            self.show_error(f"Błąd tłumaczenia przepisu: {str(e)}")

    def restore_original_recipe(self):
        """Przywrócenie oryginalnej wersji wybranego przepisu"""
        selected_items = self.recipe_list.selectedItems()
        if not selected_items:
            return
        
        # Znajdź oryginalny przepis i przywróć go
        current_row = self.recipe_list.currentRow()
        
        # Pobierz aktualne składniki z listy
        current_ingredients = []
        for i in range(self.ingredients_list.count()):
            ingredient = self.ingredients_list.item(i).text()
            current_ingredients.append(ingredient)
        
        if current_ingredients:
            # Przefiltruj przepisy tak samo jak wcześniej
            lang_name = self.lang_label.text()
            if lang_name != 'Polski' and lang_name != '-':
                detected_lang_code = None
                for code, name in {'pl': 'Polski', 'en': 'English', 'es': 'Español', 'fr': 'Français', 'de': 'Deutsch'}.items():
                    if name == lang_name:
                        detected_lang_code = code
                        break
                
                if detected_lang_code and detected_lang_code != 'pl':
                    polish_ingredients = self.translate_ingredients_to_polish(current_ingredients, detected_lang_code)
                else:
                    polish_ingredients = current_ingredients
            else:
                polish_ingredients = current_ingredients
            
            filtered_recipes = self.recipe_db.filter_recipes(polish_ingredients)
            
            if 0 <= current_row < len(filtered_recipes):
                original_recipe = filtered_recipes[current_row]
                
                # Przywróć oryginalną nazwę w liście
                selected_items[0].setText(original_recipe["name"])
                
                # Przywróć oryginalną nazwę i składniki w szczegółach
                self.recipe_name.setText(f"Przepis: {original_recipe['name']}")
                self.recipe_ingredients.setText("\n".join(original_recipe["ingredients"]))
                
                QMessageBox.information(self, "Przywracanie", "Przywrócono oryginalną wersję przepisu.")

def main():
    """Funkcja główna aplikacji"""
    app = QApplication(sys.argv)
    
    # Ustawienia aplikacji
    app.setApplicationName("Recipe Voice Filter")
    app.setApplicationVersion("1.0")
    
    # Utworzenie i wyświetlenie głównego okna
    window = MainWindow()
    window.show()
    
    # Uruchomienie pętli zdarzeń
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()