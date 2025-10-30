import os
import requests
from django.core.management.base import BaseCommand
from game.models import ItemTemplate


class Command(BaseCommand):
    help = "Importa items desde la PokeAPI basándose en los sprites locales del frontend React"

    def handle(self, *args, **kwargs):
        # 📁 Carpeta local solo para saber qué sprites hay (no se guardará la ruta absoluta)
        sprite_folder = r"C:\Users\meroc\Documents\Practicas\PKMReact\pokemon-idle-rpg\public\sprites\sprites\items"
        base_url = "https://pokeapi.co/api/v2/item/"

        if not os.path.exists(sprite_folder):
            self.stderr.write(f"❌ Carpeta no encontrada: {sprite_folder}")
            return

        archivos = [f for f in os.listdir(sprite_folder) if f.endswith(".png")]
        total = len(archivos)
        self.stdout.write(f"🔹 Encontrados {total} sprites locales de items")

        for archivo in archivos:
            nombre = archivo.replace(".png", "")
            url_api = f"{base_url}{nombre}/"

            try:
                response = requests.get(url_api, timeout=10)
                if response.status_code != 200:
                    self.stderr.write(f"⚠️ No encontrado en PokeAPI: {nombre}")
                    continue

                data = response.json()
                categoria = data["category"]["name"]
                costo = data.get("cost", 0)
                descripcion = ""

                for entry in data.get("effect_entries", []):
                    if entry["language"]["name"] in ["es", "en"]:
                        descripcion = entry["short_effect"]
                        break

                # ⚡ Usamos ruta pública (visible desde React)
                sprite_path = f"/sprites/sprites/items/{archivo}"

                ItemTemplate.objects.update_or_create(
                    id=data["id"],
                    defaults={
                        "name": nombre,
                        "category": categoria,
                        "cost": costo,
                        "description": descripcion,
                        "sprite_path": sprite_path,
                        "api_url": url_api,
                    },
                )

                self.stdout.write(self.style.SUCCESS(f"✅ Importado {nombre}"))
            except Exception as e:
                self.stderr.write(f"❌ Error con {nombre}: {e}")

        self.stdout.write(self.style.SUCCESS("🎉 Importación finalizada"))
