from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Country, League, Team, MatchResult, MatchPredict, 
    UserGroup, GroupMembership, GroupInvitation, UserProfile, Season
)


# Inline admin classes
class LeagueInline(admin.TabularInline):
    model = League
    extra = 1
    fields = ('name', 'level', 'is_active')


class TeamInline(admin.TabularInline):
    model = Team
    extra = 1
    fields = ('name', 'short_name', 'is_active')


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
            url = reverse('admin:football_app_matchresult_changelist') + f'?season__id__exact={obj.id}'
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
    inlines = [SeasonInline, TeamInline]
    
    def team_count(self, obj):
        return obj.teams.count()
    team_count.short_description = 'Teams'
    
    def season_count(self, obj):
        return obj.seasons.count()
    season_count.short_description = 'Seasons'
    
    def match_count(self, obj):
        return obj.matches.count()
    match_count.short_description = 'Matches'


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'country', 'league', 'founded_year', 'is_active')
    list_filter = ('country', 'league', 'is_active', 'created_at')
    search_fields = ('name', 'short_name', 'country__name', 'league__name')
    list_editable = ('is_active',)
    list_per_page = 50


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ('match_display', 'league', 'season', 'match_date', 'score_display', 'status', 'prediction_count')
    list_filter = ('league', 'season', 'status', 'match_date', 'created_at')
    search_fields = ('home_team__name', 'away_team__name', 'league__name', 'season__name')
    list_editable = ('status',)
    date_hierarchy = 'match_date'
    inlines = [MatchPredictInline]
    
    fieldsets = (
        ('Match Information', {
            'fields': ('home_team', 'away_team', 'league', 'season', 'match_date', 'round_number')
        }),
        ('Result', {
            'fields': ('home_score', 'away_score', 'status')
        }),
        ('Additional Info', {
            'fields': ('venue', 'attendance', 'referee'),
            'classes': ('collapse',)
        }),
    )
    
    def match_display(self, obj):
        return f"{obj.home_team} vs {obj.away_team}"
    match_display.short_description = 'Match'
    
    def score_display(self, obj):
        if obj.home_score is not None and obj.away_score is not None:
            return f"{obj.home_score}-{obj.away_score}"
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
        for match in queryset.filter(status='finished'):
            for prediction in match.predictions.all():
                prediction.calculate_points()
                total_updated += 1
        self.message_user(request, f'Updated points for {total_updated} predictions.')
    calculate_points_for_predictions.short_description = 'Calculate points for predictions'


@admin.register(MatchPredict)
class MatchPredictAdmin(admin.ModelAdmin):
    list_display = ('user', 'match_display', 'predicted_result_display', 'actual_result', 'points_earned', 'is_correct_display', 'created_at')
    list_filter = ('predicted_result', 'match__status', 'match__league', 'created_at')
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
        if obj.match.status == 'finished':
            result_text = ""
            if obj.match.result == 'H':
                result_text = "Home Win"
            elif obj.match.result == 'A':
                result_text = "Away Win"
            elif obj.match.result == 'D':
                result_text = "Draw"
            else:
                result_text = "Unknown"
            return f"{result_text} ({obj.match.home_score}-{obj.match.away_score})"
        return obj.match.get_status_display()
    actual_result.short_description = 'Actual Result'
    
    def is_correct_display(self, obj):
        if obj.match.status == 'finished':
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
    list_filter = ('created_at', 'favorite_team__league')
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

# Customize admin site header
admin.site.site_header = "Football Stats Administration"
admin.site.site_title = "Football Stats Admin"
admin.site.index_title = "Welcome to Football Stats Administration"
