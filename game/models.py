from django.db import models
from django.contrib.auth.models import AbstractUser

# -------------------------------
# Usuario personalizado
# -------------------------------
class User(AbstractUser):
    nickname = models.CharField(max_length=30)
    pokedollars = models.IntegerField(default=10000)
    pokediamonds = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    role = models.CharField(max_length=20, default="player")
    experience = models.IntegerField(default=0)
    experience_to_next_level = models.IntegerField(default=100)
    starter = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',
        blank=True
    )

    def __str__(self):
        return self.nickname


# -------------------------------
# Pokédex base — Datos oficiales del Pokémon
# -------------------------------
class PokemonSpecies(models.Model):
    pokedex_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=50)
    types = models.JSONField()  # ["fire", "flying"]
    stats = models.JSONField()  # {"hp": 39, "attack": 52, "defense": 43, ...}
    ability = models.CharField(max_length=50)
    hidden_ability = models.CharField(max_length=50, blank=True)
    sprite = models.CharField(max_length=200)  # ruta base: /sprites/sprites/pokemon/4.png

    # 🔹 NUEVOS CAMPOS para compatibilidad con PokéAPI
    gender_rate = models.IntegerField(null=True, blank=True)  # 0=solo macho, 8=solo hembra, -1=sin género
    has_gender_differences = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} (#{self.pokedex_id})"


def get_nature_data(nature_name):
    natures = {
        "Adamant": {"plus": "attack", "minus": "spAttack"},
        "Bashful": {"plus": None, "minus": None},
        "Bold": {"plus": "defense", "minus": "attack"},
        "Brave": {"plus": "attack", "minus": "speed"},
        "Calm": {"plus": "spDefense", "minus": "attack"},
        "Careful": {"plus": "spDefense", "minus": "spAttack"},
        "Docile": {"plus": None, "minus": None},
        "Gentle": {"plus": "spDefense", "minus": "defense"},
        "Hardy": {"plus": None, "minus": None},
        "Hasty": {"plus": "speed", "minus": "defense"},
        "Impish": {"plus": "defense", "minus": "spAttack"},
        "Jolly": {"plus": "speed", "minus": "spAttack"},
        "Lax": {"plus": "defense", "minus": "spDefense"},
        "Lonely": {"plus": "attack", "minus": "defense"},
        "Mild": {"plus": "spAttack", "minus": "defense"},
        "Modest": {"plus": "spAttack", "minus": "attack"},
        "Naive": {"plus": "speed", "minus": "spDefense"},
        "Naughty": {"plus": "attack", "minus": "spDefense"},
        "Quiet": {"plus": "spAttack", "minus": "speed"},
        "Quirky": {"plus": None, "minus": None},
        "Rash": {"plus": "spAttack", "minus": "spDefense"},
        "Relaxed": {"plus": "defense", "minus": "speed"},
        "Sassy": {"plus": "spDefense", "minus": "speed"},
        "Serious": {"plus": None, "minus": None},
        "Timid": {"plus": "speed", "minus": "attack"},
    }
    return natures.get(nature_name, {"plus": None, "minus": None})


# -------------------------------
# Pokémon del jugador — Instancia del species
# -------------------------------
class Pokemon(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('genderless', 'Genderless'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pokemons')
    species = models.ForeignKey(PokemonSpecies, on_delete=models.CASCADE, related_name='instances')
    nickname = models.CharField(max_length=50, blank=True)
    level = models.IntegerField(default=5)
    experience = models.IntegerField(default=0)
    experience_to_next_level = models.IntegerField(default=100)
    shiny = models.BooleanField(default=False)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    slot = models.PositiveSmallIntegerField(default=1)
    slot_pc = models.PositiveIntegerField(default=0, help_text="Orden del Pokémon en el PC Box")
    ivs = models.JSONField()
    nature = models.CharField(max_length=20)
    stats = models.JSONField(default=dict)
    current_hp = models.IntegerField(default=0)
    active = models.BooleanField(default=False)
    caught_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        g = f" ({self.gender})" if self.gender else ""
        return f"{self.nickname or self.species.name}{g} (Lv {self.level})"

    def calculate_stats(self):
        base = self.species.stats
        ivs = self.ivs
        nature_data = get_nature_data(self.nature)
        lvl = self.level

        # 🔧 normalizar claves del JSON (special-attack → spAttack)
        base = {
            "hp": base.get("hp"),
            "attack": base.get("attack"),
            "defense": base.get("defense"),
            "spAttack": base.get("spAttack") or base.get("special-attack"),
            "spDefense": base.get("spDefense") or base.get("special-defense"),
            "speed": base.get("speed"),
        }

        def calc(stat, base_val):
            mult = 1.0
            if nature_data["plus"] == stat:
                mult = 1.1
            elif nature_data["minus"] == stat:
                mult = 0.9
            return int((((2 * base_val + ivs.get(stat, 0)) * lvl) / 100 + 5) * mult)

        hp = int(((2 * base["hp"] + ivs.get("hp", 0)) * lvl) / 100 + lvl + 10)
        stats = {
            "hp": hp,
            "attack": calc("attack", base["attack"]),
            "defense": calc("defense", base["defense"]),
            "spAttack": calc("spAttack", base["spAttack"]),
            "spDefense": calc("spDefense", base["spDefense"]),
            "speed": calc("speed", base["speed"]),
        }

        self.stats = stats
        if not self.current_hp or self.current_hp > hp:
            self.current_hp = hp
        self.save()
        return stats

# -------------------------------
# Plantilla de ítem (modelo base)
# -------------------------------
class ItemTemplate(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    cost = models.IntegerField()
    description = models.TextField()
    sprite_path = models.CharField(max_length=255)
    api_url = models.URLField()
    is_healing = models.BooleanField(default=False, help_text="Indica si el ítem puede curar HP")
    heal_amount = models.IntegerField(default=0, help_text="Cantidad de HP que cura si aplica")
    is_equipable = models.BooleanField(default=False, help_text="Indica si puede equiparse a un Pokémon")
    capture_rate = models.FloatField(default=0.0, help_text="Multiplicador de captura si es una Poké Ball")

    
    def __str__(self):
        return self.name




# -------------------------------
# Ítems del usuario
# -------------------------------
class Item(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='items')
    template = models.ForeignKey(ItemTemplate, on_delete=models.CASCADE, related_name='instances')
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.template.name}"


# -------------------------------
# Caja de Pokémon (PC Box)
# -------------------------------
class PokemonBox(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pc_pokemons')
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE)
    box_number = models.IntegerField(default=1)
    position = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.pokemon.species.name} en caja {self.box_number} pos {self.position}"

class Shop(models.Model):
    CATEGORY_CHOICES = [
        ("pokeballs", "Poké Balls"),
        ("healing", "Medicinas"),
        ("battle_items", "Objetos de Batalla"),
        ("berries", "Berries"),
        ("evolution", "Objetos de Evolución"),
        ("key_items", "Objetos Clave"),
        ("treasures", "Tesoros"),
    ]

    item_template = models.ForeignKey(ItemTemplate, on_delete=models.CASCADE, related_name="shop_entries")
    shop_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    stock = models.IntegerField(default=9999, help_text="Stock disponible (9999 = ilimitado)")
    available = models.BooleanField(default=True)
    discount = models.FloatField(default=0.0, help_text="Porcentaje de descuento (0.1 = 10%)")

    def __str__(self):
        return f"{self.item_template.name} ({self.shop_category})"

# models.py
class Move(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=50)
    category = models.CharField(max_length=20, choices=[("physical", "Physical"), ("special", "Special"), ("status", "Status")])
    power = models.IntegerField(null=True, blank=True)
    accuracy = models.IntegerField(null=True, blank=True)
    pp = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    api_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

class PokemonMove(models.Model):
    species = models.ForeignKey(PokemonSpecies, on_delete=models.CASCADE, related_name="moves")
    move = models.ForeignKey(Move, on_delete=models.CASCADE)
    level_learned_at = models.IntegerField(default=0)
    learn_method = models.CharField(max_length=50, default="unknown")

    class Meta:
        unique_together = ("species", "move", "learn_method")

    def __str__(self):
        return f"{self.species.name} - {self.move.name} ({self.learn_method})"

class PokemonCurrentMove(models.Model):
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE, related_name="current_moves")
    move = models.ForeignKey(Move, on_delete=models.CASCADE)
    slot = models.IntegerField()  # 1 a 4
    pp_current = models.IntegerField(default=0)
    pp_max = models.IntegerField(default=0)

    class Meta:
        unique_together = ("pokemon", "slot")

    def __str__(self):
        return f"{self.pokemon.nickname} - {self.move.name}"

