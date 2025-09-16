from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime

class Country(models.Model):
    """Model representing a country"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, blank=True, null=True, help_text="ISO 2-letter country code")
    flag_image = models.URLField(blank=True, null=True, help_text="URL to country flag image")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_major = models.BooleanField(default=False, help_text="Flag to identify major countries")

    class Meta:
        verbose_name_plural = "Countries"
        ordering = ['name']

    def __str__(self):
        return self.name


class League(models.Model):
    """Model representing a football league"""
    name = models.CharField(max_length=150)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='leagues')
    level = models.PositiveIntegerField(default=2, blank=True, null=True, help_text="League level (1 = top tier)")
    type = models.CharField(max_length=150, blank=True, null=True)
    logo_image = models.URLField(blank=True, null=True, help_text="URL to league logo")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['country__name', 'level', 'name']
        unique_together = ['name', 'country']

    def __str__(self):
        return f"{self.name} ({self.country.name})"


class Season(models.Model):
    """Model representing a football season"""
    name = models.CharField(max_length=100, help_text="e.g., 2023/2024")
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='seasons', blank=True, null=True)
    start_year = models.PositiveIntegerField(help_text="Starting year of the season")
    end_year = models.PositiveIntegerField(help_text="Ending year of the season", blank=True, null=True)
    start_date = models.DateField(blank=True, null=True, help_text="Season start date")
    end_date = models.DateField(blank=True, null=True, help_text="Season end date")
    is_current = models.BooleanField(default=False, help_text="Is this the current active season?")
    is_active = models.BooleanField(default=True, help_text="Is this season available for predictions?")
    
    # Coverage attributes
    coverage_fixtures_events = models.BooleanField(default=False, help_text="Coverage for fixtures events")
    coverage_fixtures_lineups = models.BooleanField(default=False, help_text="Coverage for fixtures lineups")
    coverage_fixtures_statistics_fixtures = models.BooleanField(default=False, help_text="Coverage for fixtures statistics")
    coverage_fixtures_statistics_players = models.BooleanField(default=False, help_text="Coverage for player statistics")
    coverage_standings = models.BooleanField(default=False, help_text="Coverage for standings")
    coverage_players = models.BooleanField(default=False, help_text="Coverage for players")
    coverage_top_scorers = models.BooleanField(default=False, help_text="Coverage for top scorers")
    coverage_top_assists = models.BooleanField(default=False, help_text="Coverage for top assists")
    coverage_top_cards = models.BooleanField(default=False, help_text="Coverage for top cards")
    coverage_injuries = models.BooleanField(default=False, help_text="Coverage for injuries")
    coverage_predictions = models.BooleanField(default=False, help_text="Coverage for predictions")
    coverage_odds = models.BooleanField(default=False, help_text="Coverage for odds")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_year']
        unique_together = ['league', 'start_year', 'end_year']

    def __str__(self):
        return f"{self.name} ({self.league.name})"

    def save(self, *args, **kwargs):
        # Ensure only one season can be current at a time
        if self.is_current:
            Season.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current_season(cls, league=None):
        """Get the current active season for a specific league or any league"""
        try:
            if league:
                return cls.objects.get(is_current=True, league=league)
            else:
                return cls.objects.get(is_current=True)
        except cls.DoesNotExist:
            # If no current season is set, return the most recent one
            if league:
                return cls.objects.filter(is_active=True, league=league).first()
            else:
                return cls.objects.filter(is_active=True).first()

    @property
    def is_finished(self):
        """Check if the season has ended"""
        return timezone.now().date() > self.end_date

    @property
    def is_upcoming(self):
        """Check if the season hasn't started yet"""
        return timezone.now().date() < self.start_date

    @property
    def is_ongoing(self):
        """Check if the season is currently ongoing"""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date


class Team(models.Model):
    """Model representing a football team"""
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name='teams')
    founded_year = models.PositiveIntegerField(blank=True, null=True)
    code = models.CharField(max_length=20, blank=True)
    national = models.BooleanField(default=False)
    logo_image = models.URLField(blank=True, null=True, help_text="URL to team logo")   
    venue_id = models.PositiveIntegerField(blank=True, null=True)
    venue_name = models.CharField(max_length=100, blank=True, null=True)
    venue_address = models.CharField(max_length=100, blank=True, null=True)
    venue_city = models.CharField(max_length=100, blank=True, null=True)
    venue_capacity = models.PositiveIntegerField(blank=True, null=True)
    venue_surface = models.CharField(max_length=100, blank=True, null=True)
    venue_image = models.URLField(blank=True, null=True, help_text="URL to venue image")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'country']

    def __str__(self):
        return self.name


class Fixture(models.Model):
    """Model representing a football match result"""

    FIXTURE_STATUS_CHOICES = [
    ("TBD",	"Time To Be Defined",	"Scheduled",	"Scheduled but date and time are not known"),
    ("NS",	"Not Started",	"Scheduled",	""),
    ("1H",	"First Half, Kick Off",	"In Play",	"First half in play"),
    ('HT',	'Halftime',	'In Play',	'Finished in the regular time'),
    ("2H",	"Second Half, 2nd Half Started",	"In Play",	"Second half in play"),
    ("ET",	"Extra Time",	"In Play",	"Extra time in play"),
    ("BT",	"Break Time",	"In Play",	"Break during extra time"),
    ("P",	"Penalty In Progress",	"In Play",	"Penaly played after extra time"),
    ("SUSP",	"Match Suspended",	"In Play",	"Suspended by referee's decision, may be rescheduled another day"),
    ("INT",	"Match Interrupted",	"In Play",	"Interrupted by referee's decision, should resume in a few minutes"),
    ("FT",	"Match Finished",	"Finished",	"Finished in the regular time"),
    ("AET",	"Match Finished",	"Finished",	"Finished after extra time without going to the penalty shootout"),
    ("PEN",	"Match Finished",	"Finished",	"Finished after the penalty shootout"),
    ("PST",	"Match Postponed",	"Postponed",	"Postponed to another day, once the new date and time is known the status will change to Not Started"),
    ("CANC",	"Match Cancelled",	"Cancelled",	"Cancelled, match will not be played"),
    ("ABD",	"Match Abandoned",	"Abandoned",	"Abandoned for various reasons (Bad Weather, Safety, Floodlights, Playing Staff Or Referees), Can be rescheduled or not, it depends on the competition"),
    ("AWD",	"Technical Loss",	"Not Played",	""),
    ("WO",	"WalkOver",	"Not Played",	"Victory by forfeit or absence of competitor"),
    ("LIVE",	"In Progress",	"In Play",	"Used in very rare cases. It indicates a fixture in progress but the data indicating the half-time or elapsed time are not available"),
]

    # Extract choices for status_long and status_short fields
    STATUS_LONG_CHOICES = [(choice[1], choice[1]) for choice in FIXTURE_STATUS_CHOICES]
    STATUS_SHORT_CHOICES = [(choice[0], choice[0]) for choice in FIXTURE_STATUS_CHOICES]

    date = models.DateTimeField()
    referee = models.CharField(max_length=100, blank=True, null=True)
    timezone = models.CharField(max_length=20, blank=True, null=True)
    timestamp = models.PositiveIntegerField(blank=True, null=True)
    venue_id = models.PositiveIntegerField(blank=True, null=True)
    venue_name = models.CharField(max_length=100, blank=True, null=True)
    venue_city = models.CharField(max_length=100, blank=True, null=True)
    status_long  = models.CharField(max_length=100, blank=True, null=True, choices=STATUS_LONG_CHOICES)
    status_short = models.CharField(max_length=100, blank=True, null=True, choices=STATUS_SHORT_CHOICES)
    status_elapsed = models.PositiveIntegerField(blank=True, null=True)
    status_extra = models.CharField(max_length=100, blank=True, null=True)
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='matches')
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='matches')
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='matches', null=True, blank=True)
    round_type =  models.CharField(max_length=100, blank=True, null=True, help_text="Type of round/gameweek")
    round_number = models.PositiveIntegerField(blank=True, null=True, help_text="Match round/gameweek")
    
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    home_team_winner = models.BooleanField(default=True,blank=True, null=True)
    away_team_winner = models.BooleanField(default=True, blank=True, null=True)
    
    home_goals = models.PositiveIntegerField(blank=True, null=True)
    away_goals = models.PositiveIntegerField(blank=True, null=True)
    home_score_fulltime = models.PositiveIntegerField(blank=True, null=True)
    away_score_fulltime = models.PositiveIntegerField(blank=True, null=True)
    home_score_halftime = models.PositiveIntegerField(blank=True, null=True)
    away_score_halftime = models.PositiveIntegerField(blank=True, null=True)
    home_score_extratime = models.PositiveIntegerField(blank=True, null=True)
    away_score_extratime = models.PositiveIntegerField(blank=True, null=True)
    home_score_penalty = models.PositiveIntegerField(blank=True, null=True)
    away_score_penalty = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['home_team', 'away_team', 'date', 'season']

    def __str__(self):
        if self.home_goals is not None and self.away_goals is not None:
            return f"{self.home_team} {self.home_goals}-{self.away_goals} {self.away_team}"
        return f"{self.home_team} vs {self.away_team}"

    @property
    def is_finished(self):
        return self.status_long == 'Match Finished'

    def get_status_display(self):
        """Return the display value for status_long field"""
        return self.status_long or 'Unknown'

    @property
    def result(self):
        """Returns 'H' for home win, 'A' for away win, 'D' for draw, None if not finished"""
        if not self.is_finished or self.home_goals is None or self.away_goals is None:
            return None
        if self.home_goals > self.away_goals:
            return 'H'
        elif self.away_goals > self.home_goals:
            return 'A'
        else:
            return 'D'


class MatchPredict(models.Model):
    """Model representing a user's prediction for a match"""
    PREDICTION_CHOICES = [
        ('H', 'Home Win'),
        ('D', 'Draw'),
        ('A', 'Away Win'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions')
    match = models.ForeignKey(Fixture, on_delete=models.CASCADE, related_name='predictions')
    predicted_result = models.CharField(max_length=1, choices=PREDICTION_CHOICES)
    predicted_home_score = models.PositiveIntegerField(blank=True, null=True)
    predicted_away_score = models.PositiveIntegerField(blank=True, null=True)
    confidence_level = models.PositiveIntegerField(
        default=50, 
        help_text="Confidence level from 1-100"
    )
    points_earned = models.PositiveIntegerField(default=0, help_text="Points earned for this prediction")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'match']

    def __str__(self):
        return f"{self.user.username} predicts {self.match}"

    def save(self, *args, **kwargs):
        # Prevent predictions on finished or live matches
        if self.match.status_long in ['Match Finished', 'In Progress', 'First Half, Kick Off', 'Second Half, 2nd Half Started', 'Extra Time', 'Penalty In Progress'] and not self.pk:
            raise ValueError("Cannot create predictions for finished or live matches")
        super().save(*args, **kwargs)

    @property
    def is_correct(self):
        """Check if the prediction is correct"""
        if not self.match.is_finished:
            return None
        return self.predicted_result == self.match.result

    def calculate_points(self):
        """Calculate points based on prediction accuracy"""
        if not self.match.is_finished:
            return 0
        
        points = 0
        
        # Exact score prediction (5 points)
        if (self.predicted_home_score == self.match.home_goals and 
            self.predicted_away_score == self.match.away_goals):
            points = 5
        # Correct result prediction (2 points)
        elif self.is_correct:
            points = 2
        # No points for incorrect prediction
        else:
            points = 0
            
        self.points_earned = points
        self.save()
        return points


class UserGroup(models.Model):
    """Model representing a prediction group where users compete"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=500, blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(User, through='GroupMembership', related_name='joined_groups')
    leagues = models.ManyToManyField(League, related_name='prediction_groups', 
                                   help_text="Leagues that this group predicts")
    is_private = models.BooleanField(default=False, help_text="Private groups require invitation")
    max_members = models.PositiveIntegerField(default=50, help_text="Maximum number of members")
    join_code = models.CharField(max_length=20, unique=True, blank=True, 
                               help_text="Code for users to join the group")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.join_code:
            import secrets
            import string
            self.join_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        super().save(*args, **kwargs)

    @property
    def member_count(self):
        return self.members.count()

    def can_join(self, user):
        """Check if a user can join this group"""
        if self.member_count >= self.max_members:
            return False, "Group is full"
        if user in self.members.all():
            return False, "Already a member"
        return True, "Can join"

    def get_leaderboard(self):
        """Get group leaderboard sorted by total points"""
        memberships = self.groupmembership_set.select_related('user').order_by('-total_points')
        return memberships


class GroupMembership(models.Model):
    """Through model for UserGroup membership with statistics"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    total_points = models.PositiveIntegerField(default=0)
    total_predictions = models.PositiveIntegerField(default=0)
    correct_predictions = models.PositiveIntegerField(default=0)
    exact_predictions = models.PositiveIntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['user', 'group']
        ordering = ['-total_points', '-joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"

    @property
    def accuracy_percentage(self):
        """Calculate prediction accuracy percentage"""
        if self.total_predictions == 0:
            return 0
        return round((self.correct_predictions / self.total_predictions) * 100, 2)

    @property
    def exact_score_percentage(self):
        """Calculate exact score prediction percentage"""
        if self.total_predictions == 0:
            return 0
        return round((self.exact_predictions / self.total_predictions) * 100, 2)

    def update_stats(self):
        """Update member statistics for this group"""
        # Get all predictions for matches in this group's leagues
        group_leagues = self.group.leagues.all()
        predictions = MatchPredict.objects.filter(
            user=self.user,
            match__league__in=group_leagues,
            match__status_long='Match Finished'
        )
        
        self.total_predictions = predictions.count()
        # Calculate correct predictions manually since result is a property
        correct_count = 0
        for prediction in predictions:
            if prediction.is_correct:
                correct_count += 1
        self.correct_predictions = correct_count
        
        # Count exact score predictions
        exact_predictions = 0
        total_points = 0
        
        for prediction in predictions:
            if (prediction.predicted_home_score == prediction.match.home_goals and 
                prediction.predicted_away_score == prediction.match.away_goals):
                exact_predictions += 1
                total_points += 5  # 5 points for exact score
            elif prediction.is_correct:
                total_points += 2  # 2 points for correct outcome
        
        self.exact_predictions = exact_predictions
        self.total_points = total_points
        self.save()


class GroupInvitation(models.Model):
    """Model for group invitations"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]

    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, related_name='invitations')
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ['group', 'invitee']
        ordering = ['-created_at']

    def __str__(self):
        return f"Invitation to {self.invitee.username} for {self.group.name}"

    @property
    def is_expired(self):
        """Check if invitation is expired (30 days)"""
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > self.created_at + timedelta(days=30)

    def accept(self):
        """Accept the invitation"""
        if self.status == 'pending' and not self.is_expired:
            can_join, message = self.group.can_join(self.invitee)
            if can_join:
                GroupMembership.objects.create(user=self.invitee, group=self.group)
                self.status = 'accepted'
                self.responded_at = timezone.now()
                self.save()
                return True, "Invitation accepted"
            else:
                return False, message
        return False, "Invitation cannot be accepted"

    def decline(self):
        """Decline the invitation"""
        if self.status == 'pending':
            self.status = 'declined'
            self.responded_at = timezone.now()
            self.save()
            return True, "Invitation declined"
        return False, "Invitation cannot be declined"


class UserProfile(models.Model):
    """Extended user profile for football predictions"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    birthday = models.DateField(blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    total_points = models.PositiveIntegerField(default=0)
    total_predictions = models.PositiveIntegerField(default=0)
    correct_predictions = models.PositiveIntegerField(default=0)
    favorite_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    avatar_image = models.URLField(blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def save(self, *args, **kwargs):
        """Override save to automatically calculate age from birthday"""
        if self.birthday and not self.age:
            from datetime import date
            today = date.today()
            self.age = today.year - self.birthday.year - ((today.month, today.day) < (self.birthday.month, self.birthday.day))
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        """Return the full name of the user"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.user.username

    @property
    def accuracy_percentage(self):
        """Calculate prediction accuracy percentage"""
        if self.total_predictions == 0:
            return 0
        return round((self.correct_predictions / self.total_predictions) * 100, 2)

    def update_stats(self):
        """Update user statistics based on predictions"""
        predictions = MatchPredict.objects.filter(user=self.user, match__status_long='finished')
        self.total_predictions = predictions.count()
        # Calculate correct predictions manually since result is a property
        correct_count = 0
        for prediction in predictions:
            if prediction.is_correct:
                correct_count += 1
        self.correct_predictions = correct_count
        self.total_points = sum(prediction.points_earned for prediction in predictions)
        self.save()
