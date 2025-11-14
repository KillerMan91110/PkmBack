# game/management/commands/populate_gacha_boxes.py

from django.core.management.base import BaseCommand
from game.models import PokemonSpecies, GachaBox, GachaPool

# Rangos estándar de generaciones (puedes ajustarlos si tu Pokédex varía)
GEN_RANGES = {
    1: (1, 151),
    2: (152, 251),
    3: (252, 386),
    4: (387, 493),
    5: (494, 649),
    6: (650, 721),
    7: (722, 809),
    8: (810, 898),
    9: (899, 1000),  # incluye Gholdengo (#1000) y más
}

class Command(BaseCommand):
    help = "Crea GachaBox y GachaPool por generación usando PokemonSpecies"

    def handle(self, *args, **options):
        created_boxes = 0
        created_entries = 0

        for gen, (start_id, end_id) in GEN_RANGES.items():
            species_qs = PokemonSpecies.objects.filter(
                pokedex_id__gte=start_id,
                pokedex_id__lte=end_id,
            ).order_by("pokedex_id")

            count = species_qs.count()
            if count == 0:
                self.stdout.write(self.style.WARNING(f"Gen {gen} sin Species, se omite."))
                continue

            # Crea la caja si no existe
            box_name = f"Gen {gen} – Gacha"
            box, created = GachaBox.objects.get_or_create(
                name=box_name,
                defaults={
                    "price": 60 + (gen - 1) * 10,  # precio sube un poco por gen
                    "description": f"Cofre con Pokémon de la Generación {gen}.",
                    "banner": f"/imgs/gacha/gen{gen}.png",  # puedes cambiar los paths
                    "category": f"Gen {gen}",
                    "available": True,
                }
            )
            if created:
                created_boxes += 1
                self.stdout.write(self.style.SUCCESS(f"Creado GachaBox: {box_name}"))
            else:
                self.stdout.write(f"GachaBox ya existe: {box_name}")

            # Limpia el pool anterior para esa box (opcional)
            box.pool.all().delete()

            # Probabilidad uniforme: total = 100
            base_prob = 100.0 / count
            prob_acum = 0.0

            species_list = list(species_qs)
            for i, sp in enumerate(species_list):
                # Para que sume exactamente 100, al último le ajustamos el resto
                if i == len(species_list) - 1:
                    prob = max(0.0, 100.0 - prob_acum)
                else:
                    prob = round(base_prob, 2)
                    prob_acum += prob

                GachaPool.objects.create(
                    box=box,
                    species=sp,
                    rarity="common",      # TODO: si quieres luego, ajustas rarezas a mano
                    shiny_chance=0.01,    # 1% por defecto
                    probability=prob,
                )
                created_entries += 1

        self.stdout.write(self.style.SUCCESS(
            f"Listo. Boxes creados: {created_boxes}, entradas de pool creadas: {created_entries}"
        ))
