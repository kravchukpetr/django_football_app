from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Country, League, Team, Fixture, MatchPredict, 
    UserGroup, GroupMembership, GroupInvitation, UserProfile, Season,
    GroupLeagueRound, GroupDateSelection
)


# Custom admin filters
class ActiveLeagueFilter(admin.SimpleListFilter):
    title = 'league'
    parameter_name = 'league'

    def lookups(self, request, model_admin):
        """Return only active leagues"""
        active_leagues = League.objects.filter(is_active=True).order_by('name')
        return [(league.id, str(league)) for league in active_leagues]

    def queryset(self, request, queryset):
        """Filter queryset based on selected league"""
        if self.value():
            return queryset.filter(league__id=self.value())
        return queryset


class ActiveLeagueSeasonFilter(admin.SimpleListFilter):
    title = 'season'
    parameter_name = 'season'

    def lookups(self, request, model_admin):
        """Return only seasons from active leagues"""
        active_league_seasons = Season.objects.filter(league__is_active=True).order_by('-start_year', 'league__name')
        return [(season.id, str(season)) for season in active_league_seasons]

    def queryset(self, request, queryset):
        """Filter queryset based on selected season"""
        if self.value():
            return queryset.filter(season__id=self.value())
        return queryset


# Inline admin classes
class LeagueInline(admin.TabularInline):
    model = League
    extra = 1
    fields = ('name', 'level', 'is_active')


class SeasonInline(admin.TabularInline):
    model = Season
    extra = 1
    fields = ('name', 'start_year', 'end_year', 'is_current', 'is_active')


class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 1
    fields = ('user', 'role', 'total_points', 'is_active')
    readonly_fields = ('total_points',)


class MatchPredictInline(admin.TabularInline):
    model = MatchPredict
    extra = 0
    fields = ('user', 'predicted_result', 'predicted_home_score', 'predicted_away_score', 'points_earned')
    readonly_fields = ('points_earned',)


# Main admin classes
@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'league', 'start_year', 'end_year', 'start_date', 'end_date', 'is_current', 'is_active', 'match_count', 'created_at')
    list_filter = ('league', 'is_current', 'is_active', 'start_year')
    search_fields = ('name', 'start_year', 'end_year', 'league__name')
    list_editable = ('is_current', 'is_active')
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Season Information', {
            'fields': ('name', 'league', 'start_year', 'end_year')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Status', {
            'fields': ('is_current', 'is_active')
        }),
        ('Coverage', {
            'fields': (
                'coverage_fixtures_events', 'coverage_fixtures_lineups', 
                'coverage_fixtures_statistics_fixtures', 'coverage_fixtures_statistics_players',
                'coverage_standings', 'coverage_players', 'coverage_top_scorers',
                'coverage_top_assists', 'coverage_top_cards', 'coverage_injuries',
                'coverage_predictions', 'coverage_odds'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def match_count(self, obj):
        count = obj.matches.count()
        if count > 0:
            url = reverse('admin:football_app_fixture_changelist') + f'?season__id__exact={obj.id}'
            return format_html('<a href="{}">{} matches</a>', url, count)
        return "0"
    match_count.short_description = 'Matches'
    
    actions = ['set_as_current_season']
    
    def set_as_current_season(self, request, queryset):
        """Set selected season as current (only one per league allowed)"""
        if queryset.count() != 1:
            self.message_user(request, 'Please select exactly one season to set as current.', level='ERROR')
            return
        
        season = queryset.first()
        if season.league:
            # Set as current for this league only
            Season.objects.filter(league=season.league, is_current=True).update(is_current=False)
            season.is_current = True
            season.save()
            self.message_user(request, f'Set {season.name} as the current season for {season.league.name}.')
        else:
            # Set as current globally (for seasons without league)
            Season.objects.filter(is_current=True).update(is_current=False)
            season.is_current = True
            season.save()
            self.message_user(request, f'Set {season.name} as the current season.')
    set_as_current_season.short_description = 'Set as current season'


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'league_count', 'team_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'code')
    inlines = [LeagueInline]
    
    def league_count(self, obj):
        return obj.leagues.count()
    league_count.short_description = 'Leagues'
    
    def team_count(self, obj):
        return obj.teams.count()
    team_count.short_description = 'Teams'


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'level', 'team_count', 'season_count', 'match_count', 'is_active', 'created_at')
    list_filter = ('country', 'level', 'is_active', 'created_at')
    search_fields = ('name', 'country__name')
    list_editable = ('is_active',)
    inlines = [SeasonInline]
    
    def team_count(self, obj):
        # Count unique teams that have played in this league
        home_teams = obj.matches.values_list('home_team_id', flat=True).distinct()
        away_teams = obj.matches.values_list('away_team_id', flat=True).distinct()
        unique_teams = set(home_teams) | set(away_teams)
        return len(unique_teams)
    team_count.short_description = 'Teams'
    
    def season_count(self, obj):
        return obj.seasons.count()
    season_count.short_description = 'Seasons'
    
    def match_count(self, obj):
        return obj.matches.count()
    match_count.short_description = 'Matches'


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'country', 'founded_year', 'is_active')
    list_filter = ('country', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'country__name')
    list_editable = ('is_active',)
    list_per_page = 50


@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display = ('match_display', 'league', 'season', 'date', 'score_display', 'status_long', 'prediction_count')
    list_filter = ('league', 'season', 'status_long', 'date', 'created_at')
    search_fields = ('home_team__name', 'away_team__name', 'league__name', 'season__name')
    list_editable = ('status_long',)
    date_hierarchy = 'date'
    inlines = [MatchPredictInline]
    
    fieldsets = (
        ('Match Information', {
            'fields': ('home_team', 'away_team', 'league', 'season', 'date', 'round_number')
        }),
        ('Result', {
            'fields': ('home_goals', 'away_goals', 'home_score_fulltime', 'away_score_fulltime', 'status_long')
        }),
        ('Venue', {
            'fields': ('venue_name', 'venue_city', 'referee'),
            'classes': ('collapse',)
        }),
    )
    
    def match_display(self, obj):
        return f"{obj.home_team} vs {obj.away_team}"
    match_display.short_description = 'Match'
    
    def score_display(self, obj):
        if obj.home_goals is not None and obj.away_goals is not None:
            return f"{obj.home_goals}-{obj.away_goals}"
        return "-"
    score_display.short_description = 'Score'
    
    def prediction_count(self, obj):
        count = obj.predictions.count()
        if count > 0:
            url = reverse('admin:football_app_matchpredict_changelist') + f'?match__id__exact={obj.id}'
            return format_html('<a href="{}">{} predictions</a>', url, count)
        return "0"
    prediction_count.short_description = 'Predictions'
    
    actions = ['calculate_points_for_predictions']
    
    def calculate_points_for_predictions(self, request, queryset):
        """Calculate points for all predictions of selected matches"""
        total_updated = 0
        for match in queryset.filter(status_long='Match Finished'):
            for prediction in match.predictions.all():
                prediction.calculate_points()
                total_updated += 1
        self.message_user(request, f'Updated points for {total_updated} predictions.')
    calculate_points_for_predictions.short_description = 'Calculate points for predictions'


@admin.register(MatchPredict)
class MatchPredictAdmin(admin.ModelAdmin):
    list_display = ('user', 'match_display', 'predicted_result_display', 'actual_result', 'points_earned', 'is_correct_display', 'created_at')
    list_filter = ('predicted_result', 'match__status_long', 'match__league', 'created_at')
    search_fields = ('user__username', 'match__home_team__name', 'match__away_team__name')
    readonly_fields = ('points_earned', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Prediction', {
            'fields': ('user', 'match', 'predicted_result', 'predicted_home_score', 'predicted_away_score')
        }),
        ('Additional Info', {
            'fields': ('confidence_level', 'points_earned'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def match_display(self, obj):
        return f"{obj.match.home_team} vs {obj.match.away_team}"
    match_display.short_description = 'Match'
    
    def predicted_result_display(self, obj):
        result = obj.get_predicted_result_display()
        if obj.predicted_home_score is not None:
            result += f" ({obj.predicted_home_score}-{obj.predicted_away_score})"
        return result
    predicted_result_display.short_description = 'Prediction'
    
    def actual_result(self, obj):
        if obj.match.status_long == 'Match Finished':
            result_text = ""
            # Determine result based on goals
            if obj.match.home_goals is not None and obj.match.away_goals is not None:
                if obj.match.home_goals > obj.match.away_goals:
                    result_text = "Home Win"
                elif obj.match.away_goals > obj.match.home_goals:
                    result_text = "Away Win"
                else:
                    result_text = "Draw"
                return f"{result_text} ({obj.match.home_goals}-{obj.match.away_goals})"
            else:
                return "Unknown"
        return obj.match.status_long or "Pending"
    actual_result.short_description = 'Actual Result'
    
    def is_correct_display(self, obj):
        if obj.match.status_long == 'Match Finished':
            if obj.is_correct:
                return format_html('<span style="color: green;">✓ Correct</span>')
            else:
                return format_html('<span style="color: red;">✗ Wrong</span>')
        return "Pending"
    is_correct_display.short_description = 'Result'


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'member_count', 'league_count', 'is_private', 'join_code', 'is_active', 'created_at')
    list_filter = ('is_private', 'is_active', 'created_at')
    search_fields = ('name', 'creator__username', 'description')
    list_editable = ('is_active',)
    filter_horizontal = ('leagues',)
    inlines = [GroupMembershipInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'creator')
        }),
        ('Settings', {
            'fields': ('is_private', 'max_members', 'join_code', 'is_active')
        }),
        ('Leagues', {
            'fields': ('leagues',)
        }),
    )
    
    def member_count(self, obj):
        count = obj.members.count()
        if count > 0:
            url = reverse('admin:football_app_groupmembership_changelist') + f'?group__id__exact={obj.id}'
            return format_html('<a href="{}">{} members</a>', url, count)
        return "0"
    member_count.short_description = 'Members'
    
    def league_count(self, obj):
        return obj.leagues.count()
    league_count.short_description = 'Leagues'


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'role', 'total_points', 'accuracy_display', 'joined_at', 'is_active')
    list_filter = ('role', 'is_active', 'joined_at', 'group')
    search_fields = ('user__username', 'group__name')
    list_editable = ('role', 'is_active')
    
    fieldsets = (
        ('Membership', {
            'fields': ('user', 'group', 'role', 'is_active')
        }),
        ('Statistics', {
            'fields': ('total_points', 'total_predictions', 'correct_predictions', 'exact_predictions'),
            'classes': ('collapse',)
        }),
    )
    
    def accuracy_display(self, obj):
        return f"{obj.accuracy_percentage}%"
    accuracy_display.short_description = 'Accuracy'
    
    actions = ['update_member_stats']
    
    def update_member_stats(self, request, queryset):
        """Update statistics for selected memberships"""
        for membership in queryset:
            membership.update_stats()
        self.message_user(request, f'Updated statistics for {queryset.count()} memberships.')
    update_member_stats.short_description = 'Update member statistics'


@admin.register(GroupInvitation)
class GroupInvitationAdmin(admin.ModelAdmin):
    list_display = ('invitee', 'group', 'inviter', 'status', 'created_at', 'responded_at')
    list_filter = ('status', 'created_at')
    search_fields = ('invitee__username', 'inviter__username', 'group__name')
    list_editable = ('status',)
    
    fieldsets = (
        ('Invitation', {
            'fields': ('group', 'inviter', 'invitee', 'message')
        }),
        ('Status', {
            'fields': ('status', 'responded_at')
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_points', 'total_predictions', 'accuracy_display', 'favorite_team', 'created_at')
    list_filter = ('created_at', 'favorite_team')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    
    fieldsets = (
        ('Profile', {
            'fields': ('user', 'bio', 'favorite_team', 'avatar_image')
        }),
        ('Statistics', {
            'fields': ('total_points', 'total_predictions', 'correct_predictions'),
            'classes': ('collapse',)
        }),
    )
    
    def accuracy_display(self, obj):
        return f"{obj.accuracy_percentage}%"
    accuracy_display.short_description = 'Accuracy'
    
    actions = ['update_user_stats']
    
    def update_user_stats(self, request, queryset):
        """Update statistics for selected user profiles"""
        for profile in queryset:
            profile.update_stats()
        self.message_user(request, f'Updated statistics for {queryset.count()} user profiles.')
    update_user_stats.short_description = 'Update user statistics'


# Extend User admin to include profile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('bio', 'favorite_team', 'avatar_image', 'total_points', 'total_predictions', 'correct_predictions')
    readonly_fields = ('total_points', 'total_predictions', 'correct_predictions')


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(GroupLeagueRound)
class GroupLeagueRoundAdmin(admin.ModelAdmin):
    list_display = ('group', 'league', 'season', 'round_number', 'created_at')
    list_filter = (ActiveLeagueFilter, ActiveLeagueSeasonFilter, 'created_at')
    search_fields = ('group__name', 'league__name', 'round_number')
    
    fieldsets = (
        ('Round Selection', {
            'fields': ('group', 'league', 'season', 'round_number')
        }),
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter foreign key fields to show only relevant options"""
        if db_field.name == "league":
            kwargs["queryset"] = League.objects.filter(is_active=True)
        elif db_field.name == "season":
            kwargs["queryset"] = Season.objects.filter(league__is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(GroupDateSelection) 
class GroupDateSelectionAdmin(admin.ModelAdmin):
    list_display = ('group', 'match_date', 'leagues_display', 'description', 'created_at')
    list_filter = ('match_date', 'created_at')
    search_fields = ('group__name', 'description')
    filter_horizontal = ('specific_leagues',)
    
    fieldsets = (
        ('Date Selection', {
            'fields': ('group', 'match_date', 'description')
        }),
        ('League Filters', {
            'fields': ('specific_leagues',),
            'description': 'Leave empty to include all active leagues on the selected date'
        }),
    )
    
    def leagues_display(self, obj):
        if obj.specific_leagues.exists():
            count = obj.specific_leagues.count()
            if count <= 3:
                return ', '.join([league.name for league in obj.specific_leagues.all()])
            else:
                names = ', '.join([league.name for league in obj.specific_leagues.all()[:3]])
                return f"{names} and {count - 3} more"
        return "All active leagues"
    leagues_display.short_description = 'Leagues'


# Customize admin site header
admin.site.site_header = "Football Stats Administration"
admin.site.site_title = "Football Stats Admin"
admin.site.index_title = "Welcome to Football Stats Administration"
