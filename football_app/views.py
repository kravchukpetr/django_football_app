from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Q, Avg, Sum, F
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import (
    League, Country, Team, MatchResult, MatchPredict, 
    UserGroup, GroupMembership, UserProfile, Season, GroupInvitation
)
from .forms import MatchPredictionForm, UserSignInForm, UserSignUpForm, CreateGroupForm, GroupInvitationForm


def home(request):
    """Home page with overview of recent matches and predictions"""
    # Get current seasons for all leagues
    current_seasons = Season.objects.filter(is_current=True).select_related('league', 'league__country')
    
    recent_matches = MatchResult.objects.filter(
        status='finished',
        season__in=current_seasons
    ).select_related('home_team', 'away_team', 'league', 'league__country', 'season').order_by('-match_date')[:20]
    
    upcoming_matches = MatchResult.objects.filter(
        status='scheduled',
        match_date__gte=timezone.now(),
        season__in=current_seasons
    ).select_related('home_team', 'away_team', 'league', 'league__country', 'season').order_by('match_date')[:20]
    
    # Group recent matches by league
    recent_matches_by_league = {}
    for match in recent_matches:
        if match.league not in recent_matches_by_league:
            recent_matches_by_league[match.league] = []
        recent_matches_by_league[match.league].append(match)
    
    # Limit to 5 matches per league
    for league in recent_matches_by_league:
        recent_matches_by_league[league] = recent_matches_by_league[league][:5]
    
    # Group upcoming matches by league
    upcoming_matches_by_league = {}
    for match in upcoming_matches:
        if match.league not in upcoming_matches_by_league:
            upcoming_matches_by_league[match.league] = []
        upcoming_matches_by_league[match.league].append(match)
    
    # Limit to 5 matches per league
    for league in upcoming_matches_by_league:
        upcoming_matches_by_league[league] = upcoming_matches_by_league[league][:5]
    
    context = {
        'recent_matches_by_league': recent_matches_by_league,
        'upcoming_matches_by_league': upcoming_matches_by_league,
        'current_seasons': current_seasons,
    }
    return render(request, 'football_app/home.html', context)


# League Views
def league_list(request):
    """List all leagues grouped by country"""
    # Get additional countries from GET parameters
    additional_country_ids = request.GET.getlist('countries')
    
    # Start with major countries by default
    countries = Country.objects.prefetch_related('leagues').filter(
        leagues__isnull=False,
        is_major=True
    ).distinct().order_by('name')
    
    # Add additional countries if specified
    if additional_country_ids:
        try:
            additional_country_ids = [int(cid) for cid in additional_country_ids]
            additional_countries = Country.objects.prefetch_related('leagues').filter(
                id__in=additional_country_ids,
                leagues__isnull=False
            ).distinct().order_by('name')
            # Combine and deduplicate
            all_country_ids = set(countries.values_list('id', flat=True)) | set(additional_countries.values_list('id', flat=True))
            countries = Country.objects.prefetch_related('leagues').filter(
                id__in=all_country_ids,
                leagues__isnull=False
            ).distinct().order_by('name')
        except (ValueError, TypeError):
            # If invalid IDs provided, just use major countries
            pass
    
    # Get all available countries for the dropdown (excluding already selected major countries)
    available_countries = Country.objects.filter(
        leagues__isnull=False,
        is_major=False
    ).distinct().order_by('name')
    
    context = {
        'countries': countries,
        'available_countries': available_countries,
        'selected_country_ids': additional_country_ids,
    }
    return render(request, 'football_app/league_list.html', context)


def league_detail(request, league_id):
    """League detail with matches and standings"""
    league = get_object_or_404(League, id=league_id)
    
    # Get selected season (default to current for this league)
    season_id = request.GET.get('season')
    if season_id:
        try:
            selected_season = Season.objects.get(id=season_id, league=league)
        except Season.DoesNotExist:
            selected_season = Season.get_current_season(league=league)
    else:
        selected_season = Season.get_current_season(league=league)
    
    # Get all seasons for this league
    available_seasons = Season.objects.filter(
        league=league
    ).order_by('-start_year')
    
    # If no seasons exist for this league, show all active seasons
    if not available_seasons.exists():
        available_seasons = Season.objects.filter(is_active=True).order_by('-start_year')
    
    # Get recent and upcoming matches for the selected season
    recent_matches = MatchResult.objects.filter(
        league=league,
        season=selected_season,
        status='finished'
    ).select_related('home_team', 'away_team', 'season').order_by('-match_date')[:10]
    
    upcoming_matches = MatchResult.objects.filter(
        league=league,
        season=selected_season,
        status='scheduled',
        match_date__gte=timezone.now()
    ).select_related('home_team', 'away_team', 'season').order_by('match_date')[:10]
    
    # Calculate standings
    teams = Team.objects.filter(league=league)
    standings = []
    
    for team in teams:
        # Get finished matches for this team in the selected season
        home_matches = MatchResult.objects.filter(
            home_team=team, league=league, season=selected_season, status='finished'
        )
        away_matches = MatchResult.objects.filter(
            away_team=team, league=league, season=selected_season, status='finished'
        )
        
        played = home_matches.count() + away_matches.count()
        wins = (home_matches.filter(home_score__gt=F('away_score')).count() + 
                away_matches.filter(away_score__gt=F('home_score')).count())
        draws = (home_matches.filter(home_score=F('away_score')).count() + 
                 away_matches.filter(away_score=F('home_score')).count())
        losses = played - wins - draws
        
        # Calculate goals manually to avoid CombinedExpression issues
        goals_for = 0
        goals_against = 0
        
        # Home matches - team's goals are home_score
        for match in home_matches:
            if match.home_score is not None:
                goals_for += match.home_score
            if match.away_score is not None:
                goals_against += match.away_score
        
        # Away matches - team's goals are away_score
        for match in away_matches:
            if match.away_score is not None:
                goals_for += match.away_score
            if match.home_score is not None:
                goals_against += match.home_score
        
        goal_difference = goals_for - goals_against
        points = wins * 3 + draws
        
        # Calculate recent form (last 5 matches)
        all_team_matches = list(home_matches) + list(away_matches)
        all_team_matches.sort(key=lambda x: x.match_date, reverse=True)
        last_5_matches = all_team_matches[:5]
        
        form = []
        for match in last_5_matches:
            if match.home_team == team:
                if match.home_score > match.away_score:
                    form.append('W')
                elif match.home_score < match.away_score:
                    form.append('L')
                else:
                    form.append('D')
            else:  # away match
                if match.away_score > match.home_score:
                    form.append('W')
                elif match.away_score < match.home_score:
                    form.append('L')
                else:
                    form.append('D')
        
        standings.append({
            'team': team,
            'played': played,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'goals_for': goals_for,
            'goals_against': goals_against,
            'goal_difference': goal_difference,
            'points': points,
            'form': form,
        })
    
    # Sort by points, then goal difference, then goals for
    standings.sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))
    
    context = {
        'league': league,
        'recent_matches': recent_matches,
        'upcoming_matches': upcoming_matches,
        'standings': standings,
        'selected_season': selected_season,
        'available_seasons': available_seasons,
    }
    return render(request, 'football_app/league_detail.html', context)


def league_season_results(request, league_id):
    """View league results for a specific season grouped by tour/round"""
    league = get_object_or_404(League, id=league_id)
    
    # Get selected season (default to current for this league)
    season_id = request.GET.get('season')
    if season_id:
        try:
            selected_season = Season.objects.get(id=season_id, league=league)
        except Season.DoesNotExist:
            selected_season = Season.get_current_season(league=league)
    else:
        selected_season = Season.get_current_season(league=league)
    
    # Get all seasons for this league
    available_seasons = Season.objects.filter(
        league=league
    ).order_by('-start_year')
    
    # If no seasons exist for this league, show all active seasons
    if not available_seasons.exists():
        available_seasons = Season.objects.filter(is_active=True).order_by('-start_year')
    
    # Get all matches for this league and season
    matches = MatchResult.objects.filter(
        league=league,
        season=selected_season
    ).select_related('home_team', 'away_team').order_by('round_number', 'match_date')
    
    # Group matches by round/tour
    tours = {}
    for match in matches:
        round_num = match.round_number or 0  # Default to 0 if no round specified
        if round_num not in tours:
            tours[round_num] = {
                'round_number': round_num,
                'matches': [],
                'finished_count': 0,
                'total_count': 0
            }
        tours[round_num]['matches'].append(match)
        tours[round_num]['total_count'] += 1
        if match.status == 'finished':
            tours[round_num]['finished_count'] += 1
    
    # Sort tours by round number
    sorted_tours = sorted(tours.values(), key=lambda x: x['round_number'])
    
    # Calculate some statistics
    total_matches = matches.count()
    finished_matches = matches.filter(status='finished').count()
    scheduled_matches = matches.filter(status='scheduled').count()
    
    context = {
        'league': league,
        'selected_season': selected_season,
        'available_seasons': available_seasons,
        'tours': sorted_tours,
        'total_matches': total_matches,
        'finished_matches': finished_matches,
        'scheduled_matches': scheduled_matches,
    }
    return render(request, 'football_app/league_season_results.html', context)


# Team Views
def team_detail(request, team_id):
    """Team detail with matches, stats and season selection"""
    team = get_object_or_404(Team, id=team_id)
    
    # Get selected season (default to current for this team's league)
    season_id = request.GET.get('season')
    if season_id:
        try:
            selected_season = Season.objects.get(id=season_id)
        except Season.DoesNotExist:
            # Try to get current season for team's league
            if team.league:
                selected_season = Season.get_current_season(league=team.league)
            else:
                selected_season = Season.get_current_season()
    else:
        # Try to get current season for team's league
        if team.league:
            selected_season = Season.get_current_season(league=team.league)
        else:
            selected_season = Season.get_current_season()
    
    # Get all seasons where this team has played
    available_seasons = Season.objects.filter(
        Q(matches__home_team=team) | Q(matches__away_team=team)
    ).distinct().order_by('-start_year')
    
    # If no seasons have matches for this team, show all active seasons
    if not available_seasons.exists():
        available_seasons = Season.objects.filter(is_active=True).order_by('-start_year')
    
    # Get team's matches for the selected season
    home_matches = MatchResult.objects.filter(
        home_team=team,
        season=selected_season
    ).select_related('away_team', 'league', 'season').order_by('-match_date')
    
    away_matches = MatchResult.objects.filter(
        away_team=team,
        season=selected_season
    ).select_related('home_team', 'league', 'season').order_by('-match_date')
    
    # Combine and sort all matches
    all_matches = list(home_matches) + list(away_matches)
    all_matches.sort(key=lambda x: x.match_date, reverse=True)
    
    # Calculate team statistics for the selected season
    finished_home_matches = home_matches.filter(status='finished')
    finished_away_matches = away_matches.filter(status='finished')
    
    total_matches = finished_home_matches.count() + finished_away_matches.count()
    
    # Calculate wins, draws, losses
    home_wins = finished_home_matches.filter(home_score__gt=F('away_score')).count()
    away_wins = finished_away_matches.filter(away_score__gt=F('home_score')).count()
    total_wins = home_wins + away_wins
    
    home_draws = finished_home_matches.filter(home_score=F('away_score')).count()
    away_draws = finished_away_matches.filter(away_score=F('home_score')).count()
    total_draws = home_draws + away_draws
    
    total_losses = total_matches - total_wins - total_draws
    
    # Calculate goals
    goals_for = 0
    goals_against = 0
    
    # Home matches - team's goals are home_score
    for match in finished_home_matches:
        if match.home_score is not None:
            goals_for += match.home_score
        if match.away_score is not None:
            goals_against += match.away_score
    
    # Away matches - team's goals are away_score
    for match in finished_away_matches:
        if match.away_score is not None:
            goals_for += match.away_score
        if match.home_score is not None:
            goals_against += match.home_score
    
    goal_difference = goals_for - goals_against
    points = total_wins * 3 + total_draws
    
    # Get recent matches (last 10)
    recent_matches = [match for match in all_matches if match.status == 'finished'][:10]
    
    # Get upcoming matches
    upcoming_matches = [match for match in all_matches if match.status == 'scheduled' and match.match_date >= timezone.now()][:10]
    
    # Calculate form (last 5 matches)
    last_5_matches = recent_matches[:5]
    form = []
    for match in last_5_matches:
        if match.home_team == team:
            if match.home_score > match.away_score:
                form.append('W')
            elif match.home_score < match.away_score:
                form.append('L')
            else:
                form.append('D')
        else:  # away match
            if match.away_score > match.home_score:
                form.append('W')
            elif match.away_score < match.home_score:
                form.append('L')
            else:
                form.append('D')
    
    # Calculate averages
    goals_for_avg = (goals_for / total_matches) if total_matches > 0 else 0
    goals_against_avg = (goals_against / total_matches) if total_matches > 0 else 0
    
    stats = {
        'matches_played': total_matches,
        'wins': total_wins,
        'draws': total_draws,
        'losses': total_losses,
        'goals_for': goals_for,
        'goals_against': goals_against,
        'goal_difference': goal_difference,
        'points': points,
        'goals_for_avg': goals_for_avg,
        'goals_against_avg': goals_against_avg,
        'form': form,
    }
    
    context = {
        'team': team,
        'selected_season': selected_season,
        'available_seasons': available_seasons,
        'all_matches': all_matches[:20],  # Limit to 20 most recent matches
        'recent_matches': recent_matches,
        'upcoming_matches': upcoming_matches,
        'stats': stats,
    }
    return render(request, 'football_app/team_detail.html', context)


# User Views
def user_list(request):
    """List all users with their prediction statistics"""
    users = User.objects.select_related('profile').annotate(
        total_predictions=Count('predictions'),
        correct_predictions=Count('predictions', filter=Q(
            predictions__match__status='finished'
        ))
    ).order_by('-profile__total_points')[:50]  # Top 50 users
    
    context = {
        'users': users,
    }
    return render(request, 'football_app/user_list.html', context)


def user_detail(request, user_id):
    """User detail with predictions, groups, and statistics"""
    user = get_object_or_404(User, id=user_id)
    
    # Get user profile or create if doesn't exist
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    # Recent predictions
    recent_predictions = MatchPredict.objects.filter(
        user=user
    ).select_related('match__home_team', 'match__away_team', 'match__league').order_by('-created_at')[:20]
    
    # Group memberships
    group_memberships = GroupMembership.objects.filter(
        user=user, is_active=True
    ).select_related('group').order_by('-total_points')
    
    # Statistics by league
    league_stats = {}
    for prediction in MatchPredict.objects.filter(user=user, match__status='finished'):
        league = prediction.match.league
        if league not in league_stats:
            league_stats[league] = {
                'total': 0,
                'correct': 0,
                'exact': 0,
                'points': 0
            }
        
        league_stats[league]['total'] += 1
        league_stats[league]['points'] += prediction.points_earned
        
        if prediction.is_correct:
            league_stats[league]['correct'] += 1
        
        if (prediction.predicted_home_score == prediction.match.home_score and 
            prediction.predicted_away_score == prediction.match.away_score):
            league_stats[league]['exact'] += 1
    
    # Calculate accuracy for each league
    for league, stats in league_stats.items():
        stats['accuracy'] = round((stats['correct'] / stats['total']) * 100, 2) if stats['total'] > 0 else 0
        stats['exact_percentage'] = round((stats['exact'] / stats['total']) * 100, 2) if stats['total'] > 0 else 0
    
    context = {
        'profile_user': user,
        'profile': profile,
        'recent_predictions': recent_predictions,
        'group_memberships': group_memberships,
        'league_stats': league_stats,
    }
    return render(request, 'football_app/user_detail.html', context)


@login_required
def user_profile(request):
    """Current user's profile page"""
    return user_detail(request, request.user.id)


# User Group Views
def group_list(request):
    """List all public user groups"""
    groups = UserGroup.objects.filter(
        is_active=True, is_private=False
    ).prefetch_related('members', 'leagues').order_by('-created_at')
    
    context = {
        'groups': groups,
    }
    return render(request, 'football_app/group_list.html', context)


def group_detail(request, group_id):
    """Group detail with leaderboard and leagues"""
    group = get_object_or_404(UserGroup, id=group_id)
    
    # Check if user is a member
    is_member = False
    user_membership = None
    if request.user.is_authenticated:
        try:
            user_membership = GroupMembership.objects.get(user=request.user, group=group)
            is_member = True
        except GroupMembership.DoesNotExist:
            pass
    
    # Get leaderboard
    leaderboard = GroupMembership.objects.filter(
        group=group, is_active=True
    ).select_related('user').order_by('-total_points', '-correct_predictions')
    
    # Update stats for all members (this could be optimized with background tasks)
    for membership in leaderboard:
        membership.update_stats()
    
    # Refresh leaderboard after stats update
    leaderboard = GroupMembership.objects.filter(
        group=group, is_active=True
    ).select_related('user').order_by('-total_points', '-correct_predictions')
    
    # Get group leagues
    leagues = group.leagues.all().order_by('country__name', 'name')
    
    # Recent group activity (predictions in group leagues)
    recent_predictions = MatchPredict.objects.filter(
        match__league__in=leagues,
        user__in=group.members.all()
    ).select_related(
        'user', 'match__home_team', 'match__away_team', 'match__league'
    ).order_by('-created_at')[:20]
    
    context = {
        'group': group,
        'is_member': is_member,
        'user_membership': user_membership,
        'leaderboard': leaderboard,
        'leagues': leagues,
        'recent_predictions': recent_predictions,
    }
    return render(request, 'football_app/group_detail.html', context)


@login_required
def my_groups(request):
    """Current user's groups"""
    memberships = GroupMembership.objects.filter(
        user=request.user, is_active=True
    ).select_related('group').order_by('-total_points')
    
    # Get pending invitations
    pending_invitations = GroupInvitation.objects.filter(
        invitee=request.user, status='pending'
    ).select_related('group', 'inviter').order_by('-created_at')
    
    context = {
        'memberships': memberships,
        'pending_invitations': pending_invitations,
    }
    return render(request, 'football_app/my_groups.html', context)


# Prediction Views
@login_required
def prediction_center(request):
    """Main prediction center with upcoming matches"""
    # Get selected season (default to current)
    season_id = request.GET.get('season')
    if season_id:
        try:
            selected_season = Season.objects.get(id=season_id)
        except Season.DoesNotExist:
            selected_season = Season.get_current_season()
    else:
        selected_season = Season.get_current_season()
    
    # Get all available seasons for the dropdown
    available_seasons = Season.objects.filter(
        is_active=True
    ).select_related('league', 'league__country').order_by('-start_year')
    
    # Get user's groups to filter relevant matches
    user_groups = UserGroup.objects.filter(members=request.user)
    
    # Get leagues from user's groups
    if user_groups.exists():
        leagues = League.objects.filter(prediction_groups__in=user_groups).distinct()
        matches = MatchResult.objects.filter(
            league__in=leagues,
            season=selected_season,
            status='scheduled',
            match_date__gte=timezone.now()
        ).select_related('home_team', 'away_team', 'league', 'season').order_by('match_date')[:20]
    else:
        # If user is not in any groups, show all upcoming matches
        matches = MatchResult.objects.filter(
            season=selected_season,
            status='scheduled',
            match_date__gte=timezone.now()
        ).select_related('home_team', 'away_team', 'league', 'season').order_by('match_date')[:20]
    
    # Get existing predictions for these matches
    existing_predictions = MatchPredict.objects.filter(
        user=request.user,
        match__in=matches
    ).select_related('match')
    
    # Create a dictionary for easy lookup
    predictions_dict = {pred.match.id: pred for pred in existing_predictions}
    
    # Add prediction info to matches
    for match in matches:
        match.user_prediction = predictions_dict.get(match.id)
        match.can_predict = (
            match.status == 'scheduled' and 
            match.match_date > timezone.now()
        )
    
    context = {
        'matches': matches,
        'user_groups': user_groups,
        'total_predictions': MatchPredict.objects.filter(user=request.user).count(),
        'selected_season': selected_season,
        'available_seasons': available_seasons,
    }
    return render(request, 'football_app/prediction_center.html', context)


@login_required
def make_prediction(request, match_id):
    """Make a prediction for a specific match"""
    match = get_object_or_404(MatchResult, id=match_id)
    
    # Check if user can make predictions for this match
    if match.status in ['finished', 'live']:
        messages.error(request, f"Cannot make predictions for {match.get_status_display().lower()} matches.")
        return redirect('prediction_center')
    
    if match.match_date <= timezone.now():
        messages.error(request, "Prediction deadline has passed for this match.")
        return redirect('prediction_center')
    
    # Get existing prediction if any
    try:
        prediction = MatchPredict.objects.get(user=request.user, match=match)
        is_update = True
    except MatchPredict.DoesNotExist:
        prediction = None
        is_update = False
    
    if request.method == 'POST':
        form = MatchPredictionForm(
            request.POST, 
            instance=prediction,
            match=match,
            user=request.user
        )
        if form.is_valid():
            prediction = form.save()
            action = "updated" if is_update else "created"
            messages.success(request, f"Prediction {action} successfully for {match}!")
            return redirect('prediction_center')
    else:
        form = MatchPredictionForm(
            instance=prediction,
            match=match,
            user=request.user
        )
    
    context = {
        'form': form,
        'match': match,
        'is_update': is_update,
        'prediction': prediction,
    }
    return render(request, 'football_app/make_prediction.html', context)


@login_required
def bulk_predictions(request):
    """Make predictions for multiple matches at once"""
    from .forms import BulkPredictionForm, PredictionFilterForm
    
    # Get user's groups to filter relevant matches
    user_groups = UserGroup.objects.filter(members=request.user)
    
    # Initialize filter form
    filter_form = PredictionFilterForm(
        request.GET or None,
        user_groups=user_groups
    )
    
    # Get base queryset
    if user_groups.exists():
        leagues = League.objects.filter(prediction_groups__in=user_groups).distinct()
        matches = MatchResult.objects.filter(
            league__in=leagues,
            status='scheduled',
            match_date__gte=timezone.now()
        )
    else:
        matches = MatchResult.objects.filter(
            status='scheduled',
            match_date__gte=timezone.now()
        )
    
    # Apply filters
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('league'):
            matches = matches.filter(league__in=filter_form.cleaned_data['league'])
        
        if filter_form.cleaned_data.get('date_from'):
            matches = matches.filter(match_date__date__gte=filter_form.cleaned_data['date_from'])
        
        if filter_form.cleaned_data.get('date_to'):
            matches = matches.filter(match_date__date__lte=filter_form.cleaned_data['date_to'])
        
        if filter_form.cleaned_data.get('show_only_unpredicted'):
            predicted_matches = MatchPredict.objects.filter(user=request.user).values_list('match_id', flat=True)
            matches = matches.exclude(id__in=predicted_matches)
    
    matches = matches.select_related('home_team', 'away_team', 'league').order_by('match_date')[:50]
    
    if request.method == 'POST':
        bulk_form = BulkPredictionForm(
            request.POST,
            matches=matches,
            user=request.user
        )
        if bulk_form.is_valid():
            created, updated = bulk_form.save()
            messages.success(
                request, 
                f"Predictions saved! {created} new predictions created, {updated} updated."
            )
            return redirect('bulk_predictions')
    else:
        bulk_form = BulkPredictionForm(
            matches=matches,
            user=request.user
        )
    
    context = {
        'bulk_form': bulk_form,
        'filter_form': filter_form,
        'matches': matches,
        'user_groups': user_groups,
    }
    return render(request, 'football_app/bulk_predictions.html', context)


@login_required
def my_predictions(request):
    """View user's predictions with filtering options"""
    from .forms import PredictionFilterForm
    
    # Get selected season (default to current)
    season_id = request.GET.get('season')
    if season_id:
        try:
            selected_season = Season.objects.get(id=season_id)
        except Season.DoesNotExist:
            selected_season = Season.get_current_season()
    else:
        selected_season = Season.get_current_season()
    
    # Get all available seasons for the dropdown (seasons where user has predictions)
    available_seasons = Season.objects.filter(
        matches__predictions__user=request.user
    ).select_related('league', 'league__country').distinct().order_by('-start_year')
    
    # Get user's groups for filtering
    user_groups = UserGroup.objects.filter(members=request.user)
    
    # Initialize filter form
    filter_form = PredictionFilterForm(
        request.GET or None,
        user_groups=user_groups
    )
    
    # Base queryset - filter by user and selected season
    predictions = MatchPredict.objects.filter(
        user=request.user,
        match__season=selected_season
    ).select_related(
        'match__home_team', 'match__away_team', 'match__league', 'match__season'
    )
    
    # Apply filters
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('league'):
            predictions = predictions.filter(match__league__in=filter_form.cleaned_data['league'])
        
        if filter_form.cleaned_data.get('status'):
            predictions = predictions.filter(match__status__in=filter_form.cleaned_data['status'])
        
        if filter_form.cleaned_data.get('date_from'):
            predictions = predictions.filter(match__match_date__date__gte=filter_form.cleaned_data['date_from'])
        
        if filter_form.cleaned_data.get('date_to'):
            predictions = predictions.filter(match__match_date__date__lte=filter_form.cleaned_data['date_to'])
    
    predictions = predictions.order_by('-match__match_date')
    
    # Calculate statistics
    total_predictions = predictions.count()
    finished_predictions = predictions.filter(match__status='finished')
    # Calculate correct predictions manually since result is a property
    correct_predictions = 0
    for prediction in finished_predictions:
        if prediction.is_correct:
            correct_predictions += 1
    total_points = sum(pred.points_earned for pred in finished_predictions)
    
    accuracy = (correct_predictions / finished_predictions.count() * 100) if finished_predictions.count() > 0 else 0
    
    context = {
        'predictions': predictions,
        'filter_form': filter_form,
        'total_predictions': total_predictions,
        'correct_predictions': correct_predictions,
        'total_points': total_points,
        'accuracy': round(accuracy, 2),
        'selected_season': selected_season,
        'available_seasons': available_seasons,
    }
    return render(request, 'football_app/my_predictions.html', context)


# Authentication Views
def signin_view(request):
    """User sign in view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserSignInForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)
            
            # Try to authenticate with username or email
            user = authenticate(request, username=username, password=password)
            if user is None:
                # Try to find user by email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if user is not None:
                login(request, user)
                if not remember_me:
                    # Set session to expire when browser closes
                    request.session.set_expiry(0)
                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                return redirect('home')
            else:
                messages.error(request, "Invalid username/email or password.")
    else:
        form = UserSignInForm()
    
    return render(request, 'football_app/signin.html', {'form': form})


def signup_view(request):
    """User sign up view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Account created successfully! Welcome, {user.first_name}!")
            return redirect('signin')
    else:
        form = UserSignUpForm()
    
    return render(request, 'football_app/signup.html', {'form': form})


def signout_view(request):
    """User sign out view"""
    logout(request)
    messages.info(request, "You have been signed out successfully.")
    return redirect('home')


@login_required
def create_group_view(request):
    """Create a new user group"""
    if request.method == 'POST':
        form = CreateGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.creator = request.user
            group.save()
            form.save_m2m()  # Save many-to-many relationships (leagues)
            
            # Add creator as admin member
            GroupMembership.objects.create(
                user=request.user,
                group=group,
                role='admin'
            )
            
            messages.success(request, f"Group '{group.name}' created successfully!")
            return redirect('group_detail', group_id=group.id)
    else:
        form = CreateGroupForm()
    
    return render(request, 'football_app/create_group.html', {'form': form})


def join_group_view(request, join_code):
    """Join a group using join code"""
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to join a group.")
        return redirect('signin')
    
    try:
        group = UserGroup.objects.get(join_code=join_code)
    except UserGroup.DoesNotExist:
        messages.error(request, "Invalid join code. The group may not exist.")
        return redirect('group_list')
    
    # Check if user is already a member
    if GroupMembership.objects.filter(user=request.user, group=group).exists():
        messages.info(request, f"You are already a member of '{group.name}'.")
        return redirect('group_detail', group_id=group.id)
    
    # Check if group is full
    if group.member_count >= group.max_members:
        messages.error(request, f"Group '{group.name}' is full. It has reached its maximum capacity of {group.max_members} members.")
        return redirect('group_detail', group_id=group.id)
    
    # Check if group is private and user is not invited
    if group.is_private:
        # Check if user has a pending invitation
        from .models import GroupInvitation
        if not GroupInvitation.objects.filter(
            group=group, 
            invitee=request.user, 
            status='pending'
        ).exists():
            messages.error(request, f"Group '{group.name}' is private. You need an invitation to join.")
            return redirect('group_detail', group_id=group.id)
    
    # Join the group
    GroupMembership.objects.create(
        user=request.user,
        group=group,
        role='member'
    )
    
    messages.success(request, f"Successfully joined '{group.name}'!")
    return redirect('group_detail', group_id=group.id)


@login_required
def send_invitation_view(request, group_id):
    """Send an invitation to join a group"""
    group = get_object_or_404(UserGroup, id=group_id)
    
    # Check if user has permission to send invitations
    try:
        membership = GroupMembership.objects.get(user=request.user, group=group)
        if membership.role not in ['admin', 'moderator']:
            messages.error(request, "You don't have permission to send invitations to this group.")
            return redirect('group_detail', group_id=group.id)
    except GroupMembership.DoesNotExist:
        messages.error(request, "You are not a member of this group.")
        return redirect('group_detail', group_id=group.id)
    
    if request.method == 'POST':
        form = GroupInvitationForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.group = group
            invitation.inviter = request.user
            invitation.save()
            
            messages.success(request, f"Invitation sent to {invitation.invitee.username}!")
            return redirect('group_detail', group_id=group.id)
    else:
        form = GroupInvitationForm()
    
    return render(request, 'football_app/send_invitation.html', {
        'form': form,
        'group': group
    })


@login_required
def accept_invitation_view(request, invitation_id):
    """Accept a group invitation"""
    invitation = get_object_or_404(GroupInvitation, id=invitation_id, invitee=request.user)
    
    if invitation.status != 'pending':
        messages.error(request, "This invitation is no longer valid.")
        return redirect('my_groups')
    
    if invitation.is_expired:
        invitation.status = 'expired'
        invitation.save()
        messages.error(request, "This invitation has expired.")
        return redirect('my_groups')
    
    success, message = invitation.accept()
    if success:
        messages.success(request, f"Successfully joined '{invitation.group.name}'!")
    else:
        messages.error(request, message)
    
    return redirect('group_detail', group_id=invitation.group.id)


@login_required
def decline_invitation_view(request, invitation_id):
    """Decline a group invitation"""
    invitation = get_object_or_404(GroupInvitation, id=invitation_id, invitee=request.user)
    
    if invitation.status != 'pending':
        messages.error(request, "This invitation is no longer valid.")
        return redirect('my_groups')
    
    success, message = invitation.decline()
    if success:
        messages.info(request, f"Invitation to '{invitation.group.name}' declined.")
    else:
        messages.error(request, message)
    
    return redirect('my_groups')


@login_required
def my_invitations_view(request):
    """View user's pending invitations"""
    invitations = GroupInvitation.objects.filter(
        invitee=request.user,
        status='pending'
    ).select_related('group', 'inviter', 'group__creator').order_by('-created_at')
    
    # Filter out expired invitations
    valid_invitations = []
    for invitation in invitations:
        if not invitation.is_expired:
            valid_invitations.append(invitation)
        else:
            invitation.status = 'expired'
            invitation.save()
    
    return render(request, 'football_app/my_invitations.html', {
        'invitations': valid_invitations
    })


@require_http_methods(["GET"])
def get_leagues_by_country(request):
    """AJAX view to get leagues for selected countries"""
    country_ids = request.GET.getlist('country_ids[]')
    
    if not country_ids:
        return JsonResponse({'leagues': []})
    
    try:
        # Convert string IDs to integers
        country_ids = [int(cid) for cid in country_ids]
        
        # Get leagues for the selected countries
        leagues = League.objects.filter(
            country_id__in=country_ids,
            is_active=True
        ).select_related('country').order_by('country__name', 'name')
        
        # Format the response
        leagues_data = []
        for league in leagues:
            leagues_data.append({
                'id': league.id,
                'name': league.name,
                'country_name': league.country.name,
                'display_name': f"{league.name} ({league.country.name})"
            })
        
        return JsonResponse({'leagues': leagues_data})
    
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid country IDs'}, status=400)
