
from smartender import Smartender

if __name__ == "__main__":
    smartender = Smartender(r'/Users/lapodalessandris/Desktop/IoT Project/cocktails.json')
    smartender.show_cocktails(smartender.available_cocktails)
    smartender.configure()

    action = input("Press R to run, T to test\t")
    if action.lower() == "r":

        while True:
            smartender.show_cocktails(smartender.selected_cocktails)
            smartender.make_cocktail()

    else:
        if smartender.selected_cocktails:
            cocktail_name = smartender.selected_cocktails[0].name

        for _ in range(20):
            print(f"\nPreparing {cocktail_name} ({_+1}/10)...")
            smartender.make_cocktail(cocktail_name)