import json

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

        ingredients = [ing.lower() for ing in ingredients]
        
        for recipe in self.recipes:
            recipe_ingredients = [ing.lower() for ing in recipe["ingredients"]]

            if all(any(ingredient in recipe_ing or recipe_ing in ingredient 
                      for recipe_ing in recipe_ingredients) 
                  for ingredient in ingredients):
                filtered.append(recipe)
                
        return filtered

