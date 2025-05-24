import os
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                           QHBoxLayout, QWidget, QLabel, QTextEdit, QListWidget, 
                           QFileDialog, QComboBox, QMessageBox, QProgressBar)
# httpx==0.13.3
from googletrans import Translator
from langdetect import detect
import wave
import pyaudio
import string
from PyQt5.QtWidgets import QFrame
from RecipeDatabase import RecipeDatabase  # Changed this line
from SpeechThread import SpeechThread      # Changed this line  
from WhisperModelManager import WhisperModelManager  # Changed this line






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

    def update_progress(self, value):
        """Aktualizacja paska postępu"""
        self.progress_bar.setValue(value)

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
        self.model_combo.setCurrentText("tiny")  # Domyślny model
        model_config_layout.addWidget(self.model_combo)
        
        self.change_model_button = QPushButton("Zmień model")
        self.change_model_button.clicked.connect(self.change_model)
        self.change_model_button.setEnabled(False)  # Włączy się po załadowaniu pierwszego modelu
        model_config_layout.addWidget(self.change_model_button)
        
        self.model_status_label = QLabel("Status modelu: Ładowanie...")
        model_config_layout.addWidget(self.model_status_label)
        model_config_layout.addStretch()
        
        main_layout.addLayout(model_config_layout)
        
        # Sekcja konfiguracji języka
        language_config_layout = QHBoxLayout()
        language_config_layout.addWidget(QLabel("Wykrywany język:"))
        
        self.language_detection_combo = QComboBox()
        self.language_detection_combo.addItems(["Polski", "Angielski", "Wykryj automatycznie"])
        self.language_detection_combo.setCurrentText("Polski")
        language_config_layout.addWidget(self.language_detection_combo)
        
        language_config_layout.addStretch()
        main_layout.addLayout(language_config_layout)
        
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
        
        # Status
        self.status_label = QLabel("Gotowy do rozpoznawania mowy...")
        audio_group.addWidget(self.status_label)
        # Dodaj poziomą linię oddzielającą sekcje
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        audio_group.addWidget(line)
        # Sekcja tekstu - podzielona na dwa okienka
        text_section = QHBoxLayout()
        
        # Lewy panel - oryginalny tekst
        original_text_layout = QVBoxLayout()
        original_text_layout.addWidget(QLabel("Rozpoznany tekst:"))
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumHeight(150)  # Ograniczenie wysokości
        original_text_layout.addWidget(self.text_edit)
        
        # Prawy panel - tłumaczenie
        translation_layout = QVBoxLayout()
        translation_header = QHBoxLayout()
        translation_header.addWidget(QLabel("Tłumaczenie:"))
        
        # Opcje tłumaczenia przenieś do prawego panelu
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Polski", "English", "Español", "Français", "Deutsch"])
        translation_header.addWidget(self.language_combo)
        
        self.translate_button = QPushButton("Tłumacz")
        self.translate_button.clicked.connect(self.translate_text)
        translation_header.addWidget(self.translate_button)
        
        translation_layout.addLayout(translation_header)
        
        self.translation_edit = QTextEdit()
        self.translation_edit.setReadOnly(True)
        self.translation_edit.setMaximumHeight(150)  # Ograniczenie wysokości
        self.translation_edit.setPlaceholderText("Tutaj pojawi się tłumaczenie...")
        translation_layout.addWidget(self.translation_edit)
        
        # Dodaj panele do sekcji tekstu
        text_section.addLayout(original_text_layout)
        text_section.addLayout(translation_layout)
        
        audio_group.addLayout(text_section)
        
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
        self.ingredients_list.itemDoubleClicked.connect(self.remove_ingredient_on_double_click)
        ingredients_layout.addWidget(self.ingredients_list)

        audio_group.addLayout(ingredients_layout)
        
        main_layout.addLayout(audio_group)
        
        # Sekcja przepisów - lista i składniki z tłumaczeniem
        recipe_group = QVBoxLayout()

        # Nagłówek sekcji przepisów z przyciskiem tłumaczenia
        recipe_header = QHBoxLayout()
        recipe_header.addWidget(QLabel("Znalezione przepisy"))
        recipe_header.addStretch()
        
        # Kontrolki tłumaczenia przepisów przeniesione tutaj
        recipe_header.addWidget(QLabel("Tłumacz wybrany przepis na:"))

        self.recipe_language_combo = QComboBox()
        self.recipe_language_combo.addItems(["English", "Español", "Français", "Deutsch"])
        recipe_header.addWidget(self.recipe_language_combo)

        self.translate_recipe_button = QPushButton("Tłumacz wybrany przepis")
        self.translate_recipe_button.clicked.connect(self.translate_selected_recipe)
        self.translate_recipe_button.setEnabled(False)
        recipe_header.addWidget(self.translate_recipe_button)

        # Przycisk do przywracania oryginalnej wersji przepisu
        self.restore_recipe_button = QPushButton("Przywróć oryginalną wersję")
        self.restore_recipe_button.clicked.connect(self.restore_original_recipe)
        self.restore_recipe_button.setEnabled(False)
        recipe_header.addWidget(self.restore_recipe_button)

        recipe_header.addStretch()
        recipe_group.addLayout(recipe_header)

        self.recipe_list = QListWidget()
        self.recipe_list.itemClicked.connect(self.show_recipe)
        self.recipe_list.itemSelectionChanged.connect(self.on_recipe_selection_changed)
        recipe_group.addWidget(self.recipe_list)

        # Usunięto duplikujący się kod kontrolek tłumaczenia

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
        
        # Pobierz wybrany język
        language_choice = self.language_detection_combo.currentText()
        forced_language = self.get_language_code(language_choice)
        
        self.status_label.setText(f"Nagrywanie (model: {self.current_model_size}, język: {language_choice})... Mów teraz i naciśnij 'Zatrzymaj nagrywanie' gdy skończysz")
        self.progress_bar.setValue(0)
        self.record_button.setEnabled(False)
        self.file_button.setEnabled(False)
        self.change_model_button.setEnabled(False)  # Zablokuj zmianę modelu podczas nagrywania
        self.language_detection_combo.setEnabled(False)  # Zablokuj zmianę języka podczas nagrywania
        self.stop_button.setEnabled(True)
        
        self.speech_thread = SpeechThread(mode='record', model=self.whisper_model, forced_language=forced_language)
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
            # Pobierz wybrany język
            language_choice = self.language_detection_combo.currentText()
            forced_language = self.get_language_code(language_choice)
            
            self.status_label.setText(f"Przetwarzanie pliku (model: {self.current_model_size}, język: {language_choice}): {os.path.basename(file_path)}")
            self.progress_bar.setValue(0)
            self.record_button.setEnabled(False)
            self.file_button.setEnabled(False)
            self.change_model_button.setEnabled(False)  # Zablokuj zmianę modelu podczas przetwarzania
            self.language_detection_combo.setEnabled(False)  # Zablokuj zmianę języka podczas przetwarzania
            
            self.speech_thread = SpeechThread(mode='file', file_path=file_path, model=self.whisper_model, forced_language=forced_language)
            self.speech_thread.finished.connect(self.process_speech_result)
            self.speech_thread.progress.connect(self.update_progress)
            self.speech_thread.error.connect(self.show_error)
            self.speech_thread.start()
    
    def get_language_code(self, language_choice):
        """Konwersja wyboru języka na kod języka dla Whisper"""
        language_mapping = {
            "Wykryj automatycznie": None,
            "Polski": "pl",
            "Angielski": "en"
        }
        return language_mapping.get(language_choice, None)
    
    def process_speech_result(self, text, detected_lang):
        """Przetwarzanie wyników rozpoznawania mowy"""
        self.text_edit.setText(text)
        self.status_label.setText("Rozpoznawanie zakończone")
        self.record_button.setEnabled(True)
        self.file_button.setEnabled(True)
        self.change_model_button.setEnabled(True)
        self.language_detection_combo.setEnabled(True)  # Odblokuj wybór języka
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
        
        # Ekstrakcja składników z oryginalnego tekstu
        ingredients = self.extract_ingredients(text)
        
        # Zawsze tłumacz składniki na polski dla wyświetlania i wyszukiwania
        polish_ingredients = ingredients.copy()
        if detected_lang != 'pl' and ingredients:
            self.status_label.setText("Tłumaczenie składników na polski...")
            polish_ingredients = self.translate_ingredients_to_polish(ingredients, detected_lang)
        
        # Wyświetl TYLKO polskie składniki w liście
        self.ingredients_list.clear()
        for polish_ingredient in polish_ingredients:
            self.ingredients_list.addItem(polish_ingredient)
        
        # Filtrowanie przepisów na podstawie polskich składników
        filtered_recipes = self.recipe_db.filter_recipes(polish_ingredients)
        self.display_recipes(filtered_recipes)
        
        # Wyłącz przycisk usuwania (brak zaznaczenia)
        self.remove_ingredient_button.setEnabled(False)
        
        # Zaktualizuj status
        if detected_lang != 'pl' and ingredients:
            status_msg = f"Znaleziono {len(ingredients)} składników (przetłumaczono na polski), {len(filtered_recipes)} przepisów"
        else:
            status_msg = f"Znaleziono {len(ingredients)} składników, {len(filtered_recipes)} przepisów"
        
        self.status_label.setText(status_msg)

    def search_recipes_with_current_ingredients(self, ingredients):
        """Wyszukiwanie przepisów na podstawie aktualnych składników"""
        if not ingredients:
            self.recipe_list.clear()
            self.recipe_list.addItem("Brak składników do wyszukiwania")
            self.status_label.setText("Brak składników")
            return
        
        # Składniki w liście są już zawsze w języku polskim
        # więc nie trzeba ich tłumaczyć - po prostu użyj ich bezpośrednio
        filtered_recipes = self.recipe_db.filter_recipes(ingredients)
        self.display_recipes(filtered_recipes)
        
        # Aktualizuj status
        self.status_label.setText(f"Aktualne składniki: {len(ingredients)}, znalezione przepisy: {len(filtered_recipes)}")

    def show_recipe(self, item):
        """Wyświetlanie szczegółów wybranego przepisu - uproszczona wersja"""
        recipe_name = item.text()
        if recipe_name in ["Brak przepisów spełniających kryteria", "Brak składników do wyszukiwania"]:
            return
        
        # Pobierz przepis na podstawie pozycji w liście
        current_row = self.recipe_list.row(item)
        
        # Znajdź aktualnie wyświetlane przepisy - składniki są już w języku polskim
        current_ingredients = []
        for i in range(self.ingredients_list.count()):
            ingredient = self.ingredients_list.item(i).text()
            current_ingredients.append(ingredient)
        
        if current_ingredients:
            # Składniki są już w języku polskim, więc bezpośrednio filtruj przepisy
            filtered_recipes = self.recipe_db.filter_recipes(current_ingredients)
            
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
                    # Konwertuj na małe litery i usuń ewentualne spacje na końcach
                    polish_ingredients.append(translated.lower().strip())
                    print(f"Przetłumaczono składnik: {ingredient} -> {translated}")
                except Exception as e:
                    # Jeśli nie udało się przetłumaczyć, zostaw oryginalny w małych literach
                    polish_ingredients.append(ingredient.lower().strip())
                    print(f"Nie udało się przetłumaczyć składnika: {ingredient}, błąd: {e}")
        
            return polish_ingredients
            
        except Exception as e:
            print(f"Błąd podczas tłumaczenia składników: {e}")
            return [ing.lower().strip() for ing in ingredients]  # Zwróć oryginalne składniki w małych literach
    
    def translate_text(self):
        """Tłumaczenie rozpoznanego tekstu i składników"""
        text = self.text_edit.toPlainText()
        if not text:
            QMessageBox.warning(self, "Błąd", "Brak tekstu do tłumaczenia.")
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
            self.status_label.setText(f"Tłumaczenie tekstu na język: {target_language}...")
            
            # Tłumacz główny tekst
            translated_text = self.translator.translate(text, dest=target_code).text
            
            # Pobierz składniki z listy
            ingredients = []
            for i in range(self.ingredients_list.count()):
                ingredient = self.ingredients_list.item(i).text()
                ingredients.append(ingredient)
            
            # Wyświetl przetłumaczony tekst w prawym okienku
            result_text = f"{translated_text}"
            
            #! Tłumacz składniki jeśli istnieją
            # if ingredients:
            #     translated_ingredients = []
            #     for ingredient in ingredients:
            #         try:
            #             translated_ingredient = self.translator.translate(ingredient, dest=target_code).text
            #             translated_ingredients.append(translated_ingredient)
            #         except:
            #             # Jeśli nie udało się przetłumaczyć składnika, zostaw oryginalny
            #             translated_ingredients.append(ingredient)
                
            #     result_text += f"\n\nSkładniki ({target_language}):\n{', '.join(translated_ingredients)}"
                
            #     # Zaktualizuj listę składników przetłumaczonymi wersjami
            #     self.ingredients_list.clear()
            #     for translated_ingredient in translated_ingredients:
            #         self.ingredients_list.addItem(translated_ingredient)
                
            #     # Wyszukaj przepisy ponownie z przetłumaczonymi składnikami
            #     self.search_recipes_with_current_ingredients(translated_ingredients)
            
            self.translation_edit.setText(result_text)
            self.status_label.setText(f"Tekst przetłumaczony na język: {target_language}")
            
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
        if hasattr(self, 'language_detection_combo'):
            self.language_detection_combo.setEnabled(True)  # Odblokuj wybór języka
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(0)

    def show_recipe(self, item):
        """Wyświetlanie szczegółów wybranego przepisu - uproszczona wersja"""
        recipe_name = item.text()
        if recipe_name in ["Brak przepisów spełniających kryteria", "Brak składników do wyszukiwania"]:
            return
        
        # Pobierz przepis na podstawie pozycji w liście
        current_row = self.recipe_list.row(item)
        
        # Znajdź aktualnie wyświetlane przepisy - składniki są już w języku polskim
        current_ingredients = []
        for i in range(self.ingredients_list.count()):
            ingredient = self.ingredients_list.item(i).text()
            current_ingredients.append(ingredient)
        
        if current_ingredients:
            # Składniki są już w języku polskim, więc bezpośrednio filtruj przepisy
            filtered_recipes = self.recipe_db.filter_recipes(current_ingredients)
            
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
        
        # Składniki w liście są już zawsze w języku polskim
        # więc nie trzeba ich tłumaczyć - po prostu użyj ich bezpośrednio
        filtered_recipes = self.recipe_db.filter_recipes(ingredients)
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
            "English": "en",
            "Español": "es",
            "Français": "fr",
            "Deutsch": "de"
        }
        target_code = language_codes.get(target_language, "en")
        
        
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
            # QMessageBox.information(self, "Tłumaczenie", f"Przepis '{recipe_name}' został przetłumaczony na język: {target_language}")
            
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