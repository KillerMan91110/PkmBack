from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    PokemonViewSet,
    ItemViewSet,
    PokemonSpeciesViewSet,
    PokemonMoveViewSet,
    PokemonCurrentMoveViewSet,
    level_up_pokemon,
    test_api,
    register_view,
    login_view,
    choose_starter,
    current_user,
    get_csrf,
    logout_view,
    get_user_items,
    use_item,
    shop_items,
    buy_item,
    throw_ball,
    get_user_pokemons,
    
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'pokemons', PokemonViewSet, basename='pokemon') 
router.register(r'items', ItemViewSet, basename='item')
router.register(r'pokemon-species', PokemonSpeciesViewSet, basename='pokemon-species')
router.register(r'pokemon-current-moves', PokemonCurrentMoveViewSet)

urlpatterns = [
    path("users/me/", current_user, name="current-user"),
    path('', include(router.urls)),
    path('test/', test_api, name='test_api'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('choose-starter/', choose_starter, name='choose_starter'),
    path("csrf/", get_csrf, name="get-csrf"),
    path(
        'pokemon-species/<int:pokedex_id>/',
        PokemonSpeciesViewSet.as_view({'get': 'retrieve'}),
        name='pokemon-species-detail'
    ),
    path("pokemons/<int:pk>/level-up/", level_up_pokemon, name="level-up-pokemon"),

    path("user/items/", get_user_items, name="get-user-items"),
    path("user/items/<int:user_id>/", get_user_items, name="get-user-items-by-id"),
    path('use_item/', use_item, name='use_item'),
    path("shop/", shop_items, name="shop_items"),
    path("shop/buy/", buy_item, name="buy_item"),
    path("battle/throw_ball/", throw_ball, name="throw_ball"),
    path("pokemons/all/", get_user_pokemons, name="get_user_pokemons"),
    path('pokemon-species/<int:species_id>/moves/', PokemonMoveViewSet.as_view({'get': 'list'}), name='species-moves'),

    path(
        'pokemons/<int:pokemon_id>/current-moves/',
        PokemonCurrentMoveViewSet.as_view({'get': 'list'}),
        name='pokemon-current-moves-by-pokemon'
    ),

]
