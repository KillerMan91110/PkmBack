from django.core.management.base import BaseCommand
from game.models import Move, PokemonSpecies, PokemonMove
import requests

class Command(BaseCommand):
    help = "Importa los movimientos y sus datos desde la PokéAPI"

    def handle(self, *args, **kwargs):
        base_url = "https://pokeapi.co/api/v2/move/"
        for move_id in range(1, 920):  # hasta la gen 9
            res = requests.get(f"{base_url}{move_id}/")
            if res.status_code != 200:
                continue
            data = res.json()
            Move.objects.update_or_create(
                id=data["id"],
                defaults={
                    "name": data["name"],
                    "type": data["type"]["name"],
                    "category": data["damage_class"]["name"],
                    "power": data.get("power"),
                    "accuracy": data.get("accuracy"),
                    "pp": data.get("pp"),
                    "description": next(
                        (d["short_effect"] for d in data["effect_entries"] if d["language"]["name"] == "en"), ""
                    ),
                    "api_url": f"{base_url}{move_id}/",
                },
            )
            self.stdout.write(self.style.SUCCESS(f"✅ {data['name']} importado"))
