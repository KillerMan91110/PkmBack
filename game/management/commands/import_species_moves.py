from django.core.management.base import BaseCommand
from game.models import PokemonSpecies, Move, PokemonMove
import requests

class Command(BaseCommand):
    help = "Importa los movimientos aprendibles de cada especie Pokémon"

    def handle(self, *args, **kwargs):
        for species in PokemonSpecies.objects.all():
            url = f"https://pokeapi.co/api/v2/pokemon/{species.name.lower()}/"
            res = requests.get(url)
            if res.status_code != 200:
                continue
            data = res.json()
            for m in data["moves"]:
                move_name = m["move"]["name"]
                move, _ = Move.objects.get_or_create(name=move_name)
                details = m["version_group_details"][0]
                PokemonMove.objects.update_or_create(
                    species=species,
                    move=move,
                    defaults={
                        "level_learned_at": details["level_learned_at"],
                        "learn_method": details["move_learn_method"]["name"],
                    },
                )
            self.stdout.write(self.style.SUCCESS(f"📦 Movimientos cargados para {species.name}"))
