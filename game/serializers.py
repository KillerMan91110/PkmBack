from rest_framework import serializers
from .models import User, Pokemon, Item, PokemonSpecies, get_nature_data, ItemTemplate, Shop,Move, PokemonMove, PokemonCurrentMove, GachaBox,GachaPool

# Serializer para registro de usuario
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    repeat_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['nickname', 'email', 'password', 'repeat_password']

    def validate(self, data):
        if data['password'] != data['repeat_password']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return data

    def create(self, validated_data):
        validated_data.pop('repeat_password')
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            nickname=validated_data['nickname'],
            pokedollars=0,
            pokediamonds=0,
            level=1,
            experience=0,
            experience_to_next_level=100,
            role='player',
            starter=False
        )
        return user

# Serializer normal de usuario
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'nickname', 'email',
            'pokedollars', 'pokediamonds',
            'level', 'experience', 'experience_to_next_level',
            'role', 'starter'
        ]

class ItemSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    template_description = serializers.CharField(source="template.description", read_only=True)
    template_sprite = serializers.CharField(source="template.sprite_path", read_only=True)
    template_category = serializers.CharField(source="template.category", read_only=True)
    is_healing = serializers.BooleanField(source="template.is_healing", read_only=True)
    heal_amount = serializers.IntegerField(source="template.heal_amount", read_only=True)

    class Meta:
        model = Item
        fields = '__all__'

class PokemonSpeciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = PokemonSpecies
        fields = '__all__'

class PokemonSerializer(serializers.ModelSerializer):
    species = PokemonSpeciesSerializer(read_only=True)
    nature_data = serializers.SerializerMethodField()
    class Meta:
        model = Pokemon
        fields = '__all__'
        extra_kwargs = {
            'current_hp': {'required': False}  #Asegura que sea escribible
        }

    def get_nature_data(self, obj):
        return get_nature_data(obj.nature)


class ShopSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="item_template.name", read_only=True)
    description = serializers.CharField(source="item_template.description", read_only=True)
    sprite_path = serializers.CharField(source="item_template.sprite_path", read_only=True)
    cost = serializers.IntegerField(source="item_template.cost", read_only=True)
    is_healing = serializers.BooleanField(source="item_template.is_healing", read_only=True)
    heal_amount = serializers.IntegerField(source="item_template.heal_amount", read_only=True)

    class Meta:
        model = Shop
        fields = [
            "id", "name", "description", "sprite_path",
            "cost", "is_healing", "heal_amount",
            "shop_category", "stock", "available", "discount"
        ]

# --- NUEVOS SERIALIZERS DE MOVIMIENTOS ---

from .models import Move, PokemonMove, PokemonCurrentMove

class MoveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Move
        fields = '__all__'

class PokemonMoveSerializer(serializers.ModelSerializer):
    move = MoveSerializer(read_only=True)
    class Meta:
        model = PokemonMove
        fields = ['move', 'level_learned_at', 'learn_method']

class PokemonCurrentMoveSerializer(serializers.ModelSerializer):
    move = MoveSerializer(read_only=True)
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PokemonCurrentMove
        fields = ['id',          # 👈 AGREGA ESTO
            'slot',
            'move',
            'pp_current',
            'pp_max']


# serializers.py
class GachaPoolSerializer(serializers.ModelSerializer):
    species_name = serializers.CharField(source="species.name", read_only=True)
    sprite = serializers.CharField(source="species.sprite", read_only=True)
    

    class Meta:
        model = GachaPool
        fields = ["id", "species_name", "sprite", "rarity", "shiny_chance", "probability"]



class GachaBoxSerializer(serializers.ModelSerializer):
    pool = GachaPoolSerializer(many=True, read_only=True)
    rarity_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = GachaBox
        fields = ["id", "name", "price", "description", "banner", "category", "pool", "rarity_breakdown"]

    def get_rarity_breakdown(self, obj):
        agg = {}
        for p in obj.pool.all():
            agg[p.rarity] = agg.get(p.rarity, 0) + p.probability
        # redondear a 2 decimales
        return {k: round(v, 2) for k, v in agg.items()}

