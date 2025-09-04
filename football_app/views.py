from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Q, Avg, Sum, F
from django.utils import timezone
from datetime import timedelta
from .models import (
    League, Country, Team, MatchResult, MatchPredict, 
    UserGroup, GroupMembership, UserProfile, Season
)
from .forms import MatchPredictionForm


def home(request):
    """Home page with overview of recent matches and predictions"""
    current_season = Season.get_current_season()
    
    recent_matches = MatchResult.objects.filter(
        status='finished',
        season=current_season
    ).select_related('home_team', 'away_team', 'league', 'league__country', 'season').order_by('-match_date')[:20]
    
    upcoming_matches = MatchResult.objects.filter(
        status='scheduled',
        match_date__gte=timezone.now(),
        season=current_season
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
        'current_season': current_season,
    }
    return render(request, 'football_app/home.html', context)


# League Views
def league_list(request):
    """List all leagues grouped by country"""
    countries = Country.objects.prefetch_related('leagues').filter(
        leagues__isnull=False
    ).distinct().order_by('name')
    
    context = {
        'countries': countries,
    }
    return render(request, 'football_app/league_list.html', context)


def league_detail(request, league_id):
    """League detail with matches and standings"""
    league = get_object_or_404(League, id=league_id)
    
    # Get selected season (default to current)
    season_id = request.GET.get('season')
    if season_id:
        try:
            selected_season = Season.objects.get(id=season_id)
        except Season.DoesNotExist:
            selected_season = Season.get_current_season()
    else:
        selected_season = Season.get_current_season()
    
    # Get all seasons for the dropdown
    available_seasons = Season.objects.filter(
        matches__league=league
    ).distinct().order_by('-start_year')
    
    # If no seasons have matches for this league, show all active seasons
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
    
    # Get selected season (default to current)
    season_id = request.GET.get('season')
    if season_id:
        try:
            selected_season = Season.objects.get(id=season_id)
        except Season.DoesNotExist:
            selected_season = Season.get_current_season()
    else:
        selected_season = Season.get_current_season()
    
    # Get all seasons for this league for the dropdown
    available_seasons = Season.objects.filter(
        matches__league=league
    ).distinct().order_by('-start_year')
    
    # If no seasons have matches for this league, show all active seasons
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
    
    # Get selected season (default to current)
    season_id = request.GET.get('season')
    if season_id:
        try:
            selected_season = Season.objects.get(id=season_id)
        except Season.DoesNotExist:
            selected_season = Season.get_current_season()
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
    
    context = {
        'memberships': memberships,
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
    ).order_by('-start_year')
    
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
    ).distinct().order_by('-start_year')
    
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
