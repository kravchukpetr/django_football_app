from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # League URLs
    path('leagues/', views.league_list, name='league_list'),
    path('leagues/<int:league_id>/', views.league_detail, name='league_detail'),
    path('leagues/<int:league_id>/results/', views.league_season_results, name='league_season_results'),
    
    # Team URLs
    path('teams/<int:team_id>/', views.team_detail, name='team_detail'),
    
    # User URLs
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('profile/', views.user_profile, name='user_profile'),
    
    # Group URLs
    path('groups/', views.group_list, name='group_list'),
    path('groups/<int:group_id>/', views.group_detail, name='group_detail'),
    path('my-groups/', views.my_groups, name='my_groups'),
    
    # Prediction URLs
    path('predictions/', views.prediction_center, name='prediction_center'),
    path('predictions/make/<int:match_id>/', views.make_prediction, name='make_prediction'),
    path('predictions/bulk/', views.bulk_predictions, name='bulk_predictions'),
    path('predictions/my/', views.my_predictions, name='my_predictions'),
]
