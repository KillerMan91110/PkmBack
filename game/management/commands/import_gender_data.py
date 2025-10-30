from django.core.management.base import BaseCommand
from game.models import PokemonSpecies
import requests

class Command(BaseCommand):
    help = "Importa datos de género desde PokéAPI para las especies existentes."

    def handle(self, *args, **options):
        species_list = PokemonSpecies.objects.all()
        total = species_list.count()

        for index, species in enumerate(species_list, start=1):
            url = f"https://pokeapi.co/api/v2/pokemon-species/{species.pokedex_id}/"
            r = requests.get(url)
            if r.status_code != 200:
                self.stdout.write(self.style.WARNING(f"⚠️ No encontrado {species.name}"))
                continue

            data = r.json()
            gender_rate = data.get("gender_rate", None)
            has_diff = data.get("has_gender_differences", False)

            species.gender_rate = gender_rate
            species.has_gender_differences = has_diff
            species.save()

            self.stdout.write(self.style.SUCCESS(f"[{index}/{total}] {species.name} → rate={gender_rate}, diff={has_diff}"))

        self.stdout.write(self.style.SUCCESS("✅ Importación completada"))
