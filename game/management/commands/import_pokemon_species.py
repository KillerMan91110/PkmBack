from django.core.management.base import BaseCommand
from game.models import PokemonSpecies
import requests

class Command(BaseCommand):
    help = "Importa especies Pokémon desde la PokeAPI"

    def handle(self, *args, **kwargs):
        total = 1000 # Número total de especies Pokémon conocidas
        for i in range(1, total + 1):
            url = f"https://pokeapi.co/api/v2/pokemon/{i}/"
            response = requests.get(url)
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Error {i}: no encontrado"))
                continue

            data = response.json()
            name = data["name"].capitalize()
            types = [t["type"]["name"] for t in data["types"]]

            stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
            abilities = [a["ability"]["name"] for a in data["abilities"]]
            ability = abilities[0] if abilities else ""
            hidden_ability = ""
            if len(abilities) > 1:
                hidden_ability = abilities[-1]

            # Ruta del sprite local
            sprite_path = f"/sprites/sprites/pokemon/{i}.png"

            PokemonSpecies.objects.update_or_create(
                pokedex_id=i,
                defaults={
                    "name": name,
                    "types": types,
                    "stats": stats,
                    "ability": ability,
                    "hidden_ability": hidden_ability,
                    "sprite": sprite_path,
                }
            )

            self.stdout.write(self.style.SUCCESS(f"✅ Importado {i} - {name}"))
