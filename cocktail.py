class Cocktail:
    """Represents a cocktail with its ingredients and preparation steps."""

    def __init__(self, name, ingredients, steps):
        self.name = name
        self.ingredients = ingredients
        self.steps = steps

    def show(self):
        """Display cocktail details."""
        print(f"Cocktail: {self.name}")
        print("Ingredients:")
        for ingredient, details in self.ingredients.items():
            print(f"  {ingredient}: {details['quantity']}ml")  # at {details['optimal_temp_C']}°C"
        print()

    def to_dict(self):
        """Convert the Cocktail object to a dictionary for JSON storage."""
        return {
            "name": self.name,
            "ingredients": self.ingredients
        }
