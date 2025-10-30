
from rest_framework import viewsets, status,permissions
from rest_framework.decorators import api_view, permission_classes,action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate,logout
from django.views.decorators.csrf import csrf_exempt

import random
from django.db.models import Max
from django.middleware.csrf import get_token
from django.contrib.auth import login
from .models import User, Pokemon, Item, PokemonSpecies, ItemTemplate, get_nature_data, Move, PokemonMove, PokemonCurrentMove
from .serializers import (
    UserSerializer,
    PokemonSerializer,
    ItemSerializer,
    PokemonSpeciesSerializer,
    RegisterSerializer,
    ShopSerializer,
    Shop,
    MoveSerializer,
    PokemonMoveSerializer,
    PokemonCurrentMoveSerializer
)
from game import models

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Solo el dueño del Pokémon puede editarlo (PATCH, PUT, DELETE).
    Los demás solo pueden verlo (GET).
    """
    def has_object_permission(self, request, view, obj):
        # Los métodos seguros (GET, HEAD, OPTIONS) se permiten a cualquiera autenticado
        if request.method in permissions.SAFE_METHODS:
            return True
        # Solo el dueño puede modificar
        return obj.user == request.user

# --------VIEWSETS----------

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class PokemonViewSet(viewsets.ModelViewSet):
    serializer_class = PokemonSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Pokemon.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="all")
    def get_all_pokemons(self, request):
        active = request.query_params.get("active")
        qs = self.get_queryset()
        if active == "true":
            qs = qs.filter(active=True)
        elif active == "false":
            qs = qs.filter(active=False)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=["post"], url_path="swap")
    def swap_pokemons(self, request):
        """Intercambia un Pokémon del equipo con uno del PC Box."""
        user = request.user
        team_id = request.data.get("team_pokemon_id")
        box_id = request.data.get("box_pokemon_id")

        if not team_id or not box_id:
            return Response({"error": "Faltan parámetros."}, status=400)

        try:
            team_pokemon = Pokemon.objects.get(id=team_id, user=user, active=True)
            box_pokemon = Pokemon.objects.get(id=box_id, user=user, active=False)
        except Pokemon.DoesNotExist:
            return Response({"error": "Pokémon inválido o no pertenece al usuario."}, status=404)

        # Guarda sus posiciones actuales
        team_slot = team_pokemon.slot
        box_slot_pc = box_pokemon.slot_pc

        # Intercambia estados
        team_pokemon.active = False
        box_pokemon.active = True

        # Intercambia slots
        team_pokemon.slot_pc = box_slot_pc
        box_pokemon.slot = team_slot

        # Limpia los campos que no correspondan
        team_pokemon.slot = 0
        box_pokemon.slot_pc = 0

        team_pokemon.save()
        box_pokemon.save()



        return Response({
            "message": f"✅ {team_pokemon.nickname} fue enviado al PC y {box_pokemon.nickname} se unió al equipo.",
            "team_pokemon": PokemonSerializer(box_pokemon).data,
            "box_pokemon": PokemonSerializer(team_pokemon).data
        }, status=200)

    def perform_update(self, serializer):
        pokemon = self.get_object()
        if pokemon.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permiso para modificar este Pokémon.")
        serializer.save()

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

class PokemonSpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PokemonSpecies.objects.all()
    serializer_class = PokemonSpeciesSerializer
    lookup_field = 'pokedex_id'


#------- TEST-------

@api_view(['GET'])
@permission_classes([AllowAny])
def test_api(request):
    return Response({"message": "Backend funcionando"}, status=status.HTTP_200_OK)


# ------REGISTRO---------

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        data = UserSerializer(user).data
        return Response(data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#---- LOGIN----

from django.contrib.auth import login

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response({"error": "Correo y contraseña requeridos."}, status=400)

    # Buscar usuario
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "Usuario no encontrado."}, status=400)

    # Autenticar usando Django
    user = authenticate(request, username=user.email, password=password)
    if user is None:
        return Response({"error": "Credenciales inválidas."}, status=400)

    # 🔑 Crear cookie de sesión
    login(request, user)

    response = Response(UserSerializer(user).data, status=200)
    response["X-CSRFToken"] = request.META.get("CSRF_COOKIE", "")
    return response



# -----ELECCIÓN DEL STARTER-----

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def choose_starter(request):
    user = request.user
    if getattr(user, "starter", False):
        return Response({"error": "Ya has elegido tu Pokémon inicial."}, status=status.HTTP_400_BAD_REQUEST)

    pokedex_id = request.data.get("pokedex_id")
    if not pokedex_id:
        return Response({"error": "No se especificó un Pokémon."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        species = PokemonSpecies.objects.get(pokedex_id=pokedex_id)
    except PokemonSpecies.DoesNotExist:
        return Response({"error": "Pokémon no encontrado."}, status=status.HTTP_404_NOT_FOUND)

    # ---------- Asignar género según gender_rate ----------
    gender_rate = species.gender_rate
    if gender_rate == -1:  # Sin género
        gender = "genderless"
    elif gender_rate == 0:  # Solo macho
        gender = "male"
    elif gender_rate == 8:  # Solo hembra
        gender = "female"
    else:
        # Cálculo según probabilidad (PokéAPI: 0=solo macho, 8=solo hembra)
        # Cada punto = 12.5% de probabilidad de ser hembra
        female_chance = (gender_rate / 8) * 100
        gender = random.choices(["female", "male"], weights=[female_chance, 100 - female_chance], k=1)[0]

    # ---------- Crear Pokémon ----------
    ivs = {stat: random.randint(1, 31) for stat in ["hp","attack","defense","spAttack","spDefense","speed"]}
    all_natures = [
    "Adamant", "Bashful", "Bold", "Brave", "Calm", "Careful", "Docile",
    "Gentle", "Hardy", "Hasty", "Impish", "Jolly", "Lax", "Lonely",
    "Mild", "Modest", "Naive", "Naughty", "Quiet", "Quirky", "Rash",
    "Relaxed", "Sassy", "Serious", "Timid"
]
    nature = random.choice(all_natures)

    if Pokemon.objects.filter(user=user, active=True).count() >= 6:
        return Response({"error": "Tu equipo está lleno."}, status=status.HTTP_400_BAD_REQUEST)

    def get_nature_data(nature_name):
        data = {
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
        return data.get(nature_name, {"plus": None, "minus": None})
    lvl = 5
    nature_data = get_nature_data(nature)
    base = species.stats
    base = {
        "hp": base.get("hp"),
        "attack": base.get("attack"),
        "defense": base.get("defense"),
        "spAttack": base.get("spAttack") or base.get("special-attack"),
        "spDefense": base.get("spDefense") or base.get("special-defense"),
        "speed": base.get("speed"),
    }

    def calc(stat, base_val, plus=None, minus=None):
        mult = 1.0
        if plus == stat:
            mult = 1.1
        elif minus == stat:
            mult = 0.9
        return int((((2 * base_val + ivs[stat]) * lvl) / 100 + 5) * mult)

    nature_data = get_nature_data(nature)
    hp = int(((2 * base["hp"] + ivs["hp"]) * lvl) / 100 + lvl + 10)
    stats = {
        "hp": hp,
        "attack": calc("attack", base["attack"], nature_data["plus"], nature_data["minus"]),
        "defense": calc("defense", base["defense"], nature_data["plus"], nature_data["minus"]),
        "spAttack": calc("spAttack", base["spAttack"], nature_data["plus"], nature_data["minus"]),
        "spDefense": calc("spDefense", base["spDefense"], nature_data["plus"], nature_data["minus"]),
        "speed": calc("speed", base["speed"], nature_data["plus"], nature_data["minus"]),
    }

    # Crear Pokémon
    pokemon = Pokemon.objects.create(
        user=user,
        species=species,
        nickname=species.name,
        level=lvl,
        ivs=ivs,
        nature=nature,
        gender=gender,
        stats=stats,
        current_hp=stats["hp"],
        active=True,
    )

    # 🔹 Obtener movimientos aprendibles por nivel
    possible_moves = (
        PokemonMove.objects.filter(
            species=species,
            learn_method__in=["level-up"],  # Solo aprende los movimientos que se ganan al subir de nivel
            level_learned_at__lte=lvl       # Solo movimientos que puede haber aprendido a su nivel actual o inferior
        )
        .order_by('-level_learned_at')  # Primero los más cercanos a su nivel
    )

    # 🔹 Seleccionar los últimos 4 movimientos más recientes (más cercanos al nivel actual)
    selected_moves = list(possible_moves[:4])

    # 🔹 Asignar los movimientos al Pokémon
    for i, move_rel in enumerate(selected_moves, start=1):
        move = move_rel.move
        PokemonCurrentMove.objects.create(
            pokemon=pokemon,
            move=move,
            slot=i,
            pp_current=move.pp or 35,  # ✅ Usa PP base o 35 si está vacío
            pp_max=move.pp or 35
        )


    # ---------- Dar ítems y dinero ----------
    user.pokedollars += 10000
    user.starter = True
    user.save()

    def give_item(name, qty):
        try:
            template = ItemTemplate.objects.get(name__iexact=name)
            Item.objects.create(user=user, template=template, quantity=qty)
        except ItemTemplate.DoesNotExist:
            print(f"⚠️ No existe el ítem '{name}' en la base de datos")

    give_item("Poke Ball", 10)
    give_item("Super Ball", 10)
    give_item("Poción", 5)

    return Response({
        "message": f"Has recibido a {species.name} ({gender}) como tu Pokémon inicial.",
        "pokemon": PokemonSerializer(pokemon).data,
        "pokedollars": user.pokedollars
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_csrf(request):
    """
    Devuelve un token CSRF en JSON.
    """
    token = get_token(request)
    return Response({"csrfToken": token})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Devuelve la información del usuario logeado."""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    """Cerrar sesión y eliminar la cookie de sesión"""
    logout(request)

    response = Response({"message": "Sesión cerrada correctamente"}, status=200)
    response.delete_cookie("sessionid")
    response.delete_cookie("csrftoken")
    return response

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def level_up_pokemon(request, pk):
    try:
        pokemon = Pokemon.objects.get(id=pk, user=request.user)
    except Pokemon.DoesNotExist:
        return Response({"error": "Pokémon no encontrado"}, status=404)

    pokemon.level += 1
    new_stats = pokemon.calculate_stats()
    pokemon.save()

    return Response({
        "message": f"{pokemon.nickname or pokemon.species.name} subió al nivel {pokemon.level}.",
        "stats": new_stats
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_items(request, user_id=None):
    """Devuelve todos los ítems del usuario autenticado o de un ID específico (admin)."""
    user = request.user

    # Si el usuario es admin y se pasa un ID, permite revisar otros usuarios
    if user.is_superuser and user_id:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado"}, status=404)

    items = Item.objects.filter(user=user).select_related("template")
    serializer = ItemSerializer(items, many=True)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_pokemons(request):
    """
    Devuelve todos los Pokémon del usuario, incluyendo los del equipo y los del PC Box.
    Puedes filtrar con ?active=true o ?active=false
    """
    user = request.user
    active = request.query_params.get("active")

    queryset = Pokemon.objects.filter(user=user)
    if active == "true":
        queryset = queryset.filter(active=True)
    elif active == "false":
        queryset = queryset.filter(active=False)

    queryset = queryset.order_by("slot", "id")
    serializer = PokemonSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def use_item(request):
    """
    Usa un ítem curativo sobre un Pokémon del usuario autenticado.
    Espera:
    {
        "pokemon_id": 12,
        "item_id": 34
    }
    """
    user = request.user
    pokemon_id = request.data.get("pokemon_id")
    item_id = request.data.get("item_id")

    if not pokemon_id or not item_id:
        return Response({"error": "Faltan parámetros (pokemon_id, item_id)."}, status=400)

    # Obtener Pokémon
    try:
        pokemon = Pokemon.objects.get(id=pokemon_id, user=user)
    except Pokemon.DoesNotExist:
        return Response({"error": "Pokémon no encontrado o no pertenece al usuario."}, status=404)

    # Obtener ítem
    try:
        item = Item.objects.select_related("template").get(id=item_id, user=user)
    except Item.DoesNotExist:
        return Response({"error": "Ítem no encontrado o no pertenece al usuario."}, status=404)

    template = item.template

    # Validar si es curativo
    if not template.is_healing:
        return Response({"error": f"El ítem '{template.name}' no es un objeto curativo."}, status=400)

    max_hp = pokemon.stats.get("hp", 0)
    current_hp = pokemon.current_hp

    if current_hp >= max_hp:
        return Response({"message": f"{pokemon.nickname or pokemon.species.name} ya tiene la salud completa."}, status=200)

    # Calcular curación
    heal_amount = template.heal_amount or 20
    new_hp = min(max_hp, current_hp + heal_amount)

    # Actualizar Pokémon
    pokemon.current_hp = new_hp
    pokemon.save()

    # Reducir cantidad o eliminar ítem
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
    else:
        item.delete()

    return Response({
        "message": f"{pokemon.nickname or pokemon.species.name} ha sido curado.",
        "pokemon": {
            "id": pokemon.id,
            "current_hp": pokemon.current_hp,
            "max_hp": max_hp
        },
        "item_remaining": item.quantity if item.id else 0
    }, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def throw_ball(request):
    """
    Lanza una Poké Ball durante una batalla para intentar capturar al Pokémon enemigo.
    Espera:
    {
        "item_id": 34,
        "enemy": {
            "pokedex_id": 25,
            "level": 5,
            "current_hp": 10,
            "max_hp": 35,
            "gender": "male",
            "ivs": {...},
            "nature": {"plus": "attack", "minus": "spAttack"},
            "base_stats": {...}
        }
    }
    """
    user = request.user
    item_id = request.data.get("item_id")
    enemy_data = request.data.get("enemy")

    if not item_id or not enemy_data:
        return Response({"error": "Faltan parámetros (item_id, enemy)."}, status=400)

    # ---------- Obtener ítem ----------
    try:
        item = Item.objects.select_related("template").get(id=item_id, user=user)
    except Item.DoesNotExist:
        return Response({"error": "Ítem no encontrado."}, status=404)

    template = item.template
    if "ball" not in template.name.lower():
        return Response({"error": "Este ítem no es una Poké Ball."}, status=400)

    # ---------- Datos del enemigo ----------
    pokedex_id = enemy_data.get("pokedex_id")
    current_hp = enemy_data.get("current_hp")
    max_hp = enemy_data.get("max_hp")
    level = enemy_data.get("level", 5)

    try:
        species = PokemonSpecies.objects.get(pokedex_id=pokedex_id)
    except PokemonSpecies.DoesNotExist:
        return Response({"error": "Pokémon salvaje desconocido."}, status=404)

    # ---------- Cálculo de captura simplificado ----------
    a = (((3 * max_hp - 2 * current_hp) * (species.stats.get("hp", 10)) * template.capture_rate) / (3 * max_hp))
    catch_rate = min(255, max(1, a))
    success = (template.capture_rate >= 255.0) or (random.randint(0, 255) <= catch_rate)

    # Reducir cantidad del ítem
    if item.quantity > 1:
        item.quantity -= 1
        item.save(update_fields=["quantity"])
    else:
        item.delete()

    # ---------- Si falla la captura ----------
    if not success:
        return Response({
            "captured": False,
            "message": f"❌ El {species.name} se liberó de la Poké Ball."
        }, status=200)

    # ---------- Captura exitosa ----------
    ivs = enemy_data.get("ivs") or {s: random.randint(1, 31) for s in ["hp","attack","defense","spAttack","spDefense","speed"]}
    nature_data = enemy_data.get("nature") or {"plus": None, "minus": None}
    gender = enemy_data.get("gender")

    # Si el frontend no mandó género, usa el gender_rate del species
    if not gender or gender == "unknown":
        rate = species.gender_rate
        if rate == -1:
            gender = "genderless"
        elif rate == 0:
            gender = "male"
        elif rate == 8:
            gender = "female"
        else:
            female_chance = (rate / 8) * 100
            gender = random.choices(["female", "male"], weights=[female_chance, 100 - female_chance], k=1)[0]

    base_stats = enemy_data.get("base_stats") or species.stats

    def calc_stat(stat, base_val, plus=None, minus=None):
        mult = 1.0
        if plus == stat:
            mult = 1.1
        elif minus == stat:
            mult = 0.9
        return int((((2 * base_val + ivs[stat]) * level) / 100 + 5) * mult)

    hp = int(((2 * base_stats["hp"] + ivs["hp"]) * level) / 100 + level + 10)
    stats = {
        "hp": hp,
        "attack": calc_stat("attack", base_stats["attack"], nature_data["plus"], nature_data["minus"]),
        "defense": calc_stat("defense", base_stats["defense"], nature_data["plus"], nature_data["minus"]),
        "spAttack": calc_stat("spAttack", base_stats["spAttack"], nature_data["plus"], nature_data["minus"]),
        "spDefense": calc_stat("spDefense", base_stats["spDefense"], nature_data["plus"], nature_data["minus"]),
        "speed": calc_stat("speed", base_stats["speed"], nature_data["plus"], nature_data["minus"]),
    }

    team_count = Pokemon.objects.filter(user=user, active=True).count()
    if team_count < 6:
        slot = team_count + 1
        slot_pc = 0
        active = True
    else:
        slot = 0
        slot_pc = (Pokemon.objects.filter(user=user, active=False).aggregate(max_pc=Max("slot_pc"))["max_pc"] or 0) + 1
        active = False


    shiny = random.random() < 0.01  # 1% probabilidad shiny
    current_hp = min(current_hp, stats["hp"])
    pokemon = Pokemon.objects.create(
        user=user,
        species=species,
        nickname=species.name,
        level=level,
        ivs=ivs,
        nature=enemy_data.get("nature_name"),
        gender=gender,
        shiny=shiny,
        stats=stats,
        current_hp=current_hp,
        slot=slot,
        slot_pc=slot_pc,
        active=(team_count < 6)
    )
    # 🔹 Obtener movimientos aprendibles por nivel
    possible_moves = (
        PokemonMove.objects.filter(
            species=species,
            learn_method__in=["level-up"],  # Solo aprende los movimientos que se ganan al subir de nivel
            level_learned_at__lte=level       # Solo movimientos que puede haber aprendido a su nivel actual o inferior
        )
        .order_by('-level_learned_at')  # Primero los más cercanos a su nivel
    )

    # 🔹 Seleccionar los últimos 4 movimientos más recientes (más cercanos al nivel actual)
    selected_moves = list(possible_moves[:4])

    # 🔹 Asignar los movimientos al Pokémon
    for i, move_rel in enumerate(selected_moves, start=1):
        move = move_rel.move
        PokemonCurrentMove.objects.create(
            pokemon=pokemon,
            move=move,
            slot=i,
            pp_current=move.pp or 35,  # ✅ Usa PP base o 35 si está vacío
            pp_max=move.pp or 35
        )


    return Response({
        "captured": True,
        "message": f"🎉 ¡Has capturado a {species.name}!",
        "pokemon": {
            "nickname": pokemon.nickname,
            "level": pokemon.level,
            "gender": pokemon.gender,
            "nature": pokemon.nature,
            "ivs": pokemon.ivs,
            "stats": pokemon.stats,
            "slot": pokemon.slot
        }
    }, status=200)




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def buy_item(request):
    """
    Compra un ítem desde la tienda.
    Espera:
    {
        "shop_id": 1,
        "quantity": 3
    }
    """
    user = request.user
    shop_id = request.data.get("shop_id")
    quantity = int(request.data.get("quantity", 1))

    # Validar datos
    if not shop_id or quantity <= 0:
        return Response({"error": "Datos inválidos."}, status=400)

    # Buscar ítem
    try:
        shop_entry = Shop.objects.select_related("item_template").get(id=shop_id, available=True)
    except Shop.DoesNotExist:
        return Response({"error": "El ítem no está disponible en la tienda."}, status=404)

    # Calcular costo real
    base_cost = shop_entry.item_template.cost or 0
    discount = shop_entry.discount or 0.0
    total_cost = int(base_cost * quantity * (1 - discount))

    # Verificar dinero
    if user.pokedollars < total_cost:
        return Response({
            "error": "No tienes suficiente dinero.",
            "saldo_actual": user.pokedollars,
            "costo_total": total_cost
        }, status=400)

    # Verificar stock
    if shop_entry.stock != 9999 and shop_entry.stock < quantity:
        return Response({
            "error": "Stock insuficiente.",
            "stock_disponible": shop_entry.stock
        }, status=400)

    # Descontar dinero
    user.pokedollars = max(0, user.pokedollars - total_cost)
    user.save(update_fields=["pokedollars"])  # 🔥 guarda solo ese campo

    # Reducir stock
    if shop_entry.stock != 9999:
        shop_entry.stock -= quantity
        shop_entry.save(update_fields=["stock"])

    # Agregar ítem al inventario
    item, created = Item.objects.get_or_create(
        user=user,
        template=shop_entry.item_template,
        defaults={"quantity": quantity}
    )
    if not created:
        item.quantity += quantity
        item.save(update_fields=["quantity"])

    # Refrescar usuario (asegura actualización en sesión)
    user.refresh_from_db(fields=["pokedollars"])

    return Response({
        "message": f"✅ Has comprado {quantity}x {shop_entry.item_template.name}.",
        "nuevo_saldo": user.pokedollars,
        "costo_total": total_cost,
        "item": {
            "name": shop_entry.item_template.name,
            "cantidad_actual": item.quantity
        }
    }, status=200)




@api_view(["GET"])
@permission_classes([AllowAny])
def shop_items(request):
    """Lista todos los ítems disponibles en la tienda"""
    category = request.query_params.get("category")

    queryset = Shop.objects.filter(available=True)
    if category:
        queryset = queryset.filter(shop_category=category)

    serializer = ShopSerializer(queryset, many=True)
    return Response(serializer.data)

# --- VIEWSETS PARA MOVIMIENTOS ---

class MoveViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Move.objects.all()
    serializer_class = MoveSerializer
    permission_classes = [AllowAny]


class PokemonMoveViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PokemonMoveSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        species_id = self.kwargs.get("species_id")
        return PokemonMove.objects.filter(species__pokedex_id=species_id).select_related("move")


class PokemonCurrentMoveViewSet(viewsets.ModelViewSet):
    queryset = PokemonCurrentMove.objects.all()
    serializer_class = PokemonCurrentMoveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        pokemon_id = self.kwargs.get('pokemon_id') or self.request.query_params.get('pokemon')
        if pokemon_id:
            return self.queryset.filter(pokemon_id=pokemon_id)
        return self.queryset