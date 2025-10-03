from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import MatchPredict, Fixture, UserGroup, UserProfile, League, GroupInvitation, GroupMembership


class MatchPredictionForm(forms.ModelForm):
    """Form for making match predictions"""
    
    class Meta:
        model = MatchPredict
        fields = ['predicted_result', 'predicted_home_score', 'predicted_away_score', 'confidence_level']
        widgets = {
            'predicted_result': forms.Select(
                attrs={'class': 'form-select'},
                choices=MatchPredict.PREDICTION_CHOICES
            ),
            'predicted_home_score': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '0',
                    'max': '20',
                    'placeholder': 'Home score'
                }
            ),
            'predicted_away_score': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '0',
                    'max': '20',
                    'placeholder': 'Away score'
                }
            ),
            'confidence_level': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '1',
                    'max': '100',
                    'value': '50',
                    'type': 'range'
                }
            ),
        }
        labels = {
            'predicted_result': 'Match Result',
            'predicted_home_score': 'Home Team Score',
            'predicted_away_score': 'Away Team Score',
            'confidence_level': 'Confidence Level',
        }
        help_texts = {
            'predicted_result': 'Select the expected match outcome',
            'predicted_home_score': 'Predict the home team score (optional)',
            'predicted_away_score': 'Predict the away team score (optional)',
            'confidence_level': 'How confident are you in this prediction? (1-100)',
        }

    def __init__(self, *args, **kwargs):
        self.match = kwargs.pop('match', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add some JavaScript for automatic result calculation
        self.fields['predicted_home_score'].widget.attrs.update({
            'onchange': 'updatePredictedResult()'
        })
        self.fields['predicted_away_score'].widget.attrs.update({
            'onchange': 'updatePredictedResult()'
        })

    def clean(self):
        cleaned_data = super().clean()
        predicted_home_score = cleaned_data.get('predicted_home_score')
        predicted_away_score = cleaned_data.get('predicted_away_score')
        predicted_result = cleaned_data.get('predicted_result')

        # Validate that both scores are provided if one is provided
        if (predicted_home_score is not None) != (predicted_away_score is not None):
            raise ValidationError("Please provide both home and away scores, or leave both blank.")

        # Auto-calculate result if scores are provided
        if predicted_home_score is not None and predicted_away_score is not None:
            if predicted_home_score > predicted_away_score:
                auto_result = 'H'
            elif predicted_away_score > predicted_home_score:
                auto_result = 'A'
            else:
                auto_result = 'D'
            
            # Check if the provided result matches the calculated result
            if predicted_result != auto_result:
                cleaned_data['predicted_result'] = auto_result

        # Validate that match is still open for predictions
        if self.match:
            if self.match.status_long in ['Match Finished', 'In Progress', 'First Half, Kick Off', 'Second Half, 2nd Half Started', 'Extra Time', 'Penalty In Progress']:
                raise ValidationError("Cannot make predictions for finished or live matches.")
            
            # Check if prediction deadline has passed (e.g., 1 hour before match)
            if self.match.date <= timezone.now():
                raise ValidationError("Prediction deadline has passed for this match.")

        return cleaned_data

    def save(self, commit=True):
        prediction = super().save(commit=False)
        if self.match:
            prediction.match = self.match
        if self.user:
            prediction.user = self.user
        
        if commit:
            prediction.save()
        return prediction


class BulkPredictionForm(forms.Form):
    """Form for making predictions on multiple matches at once"""
    
    def __init__(self, *args, **kwargs):
        matches = kwargs.pop('matches', [])
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.matches = matches
        self.user = user
        
        # Create fields for each match
        for match in matches:
            field_prefix = f'match_{match.id}'
            
            # Result field
            self.fields[f'{field_prefix}_result'] = forms.ChoiceField(
                choices=[('', 'Select Result')] + MatchPredict.PREDICTION_CHOICES,
                required=False,
                widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
            )
            
            # Home score field
            self.fields[f'{field_prefix}_home_score'] = forms.IntegerField(
                required=False,
                min_value=0,
                max_value=20,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': '0'
                })
            )
            
            # Away score field
            self.fields[f'{field_prefix}_away_score'] = forms.IntegerField(
                required=False,
                min_value=0,
                max_value=20,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': '0'
                })
            )
            
            # Check if user already has a prediction for this match
            if user:
                try:
                    existing_prediction = MatchPredict.objects.get(user=user, match=match)
                    self.fields[f'{field_prefix}_result'].initial = existing_prediction.predicted_result
                    self.fields[f'{field_prefix}_home_score'].initial = existing_prediction.predicted_home_score
                    self.fields[f'{field_prefix}_away_score'].initial = existing_prediction.predicted_away_score
                except MatchPredict.DoesNotExist:
                    pass

    def clean(self):
        cleaned_data = super().clean()
        
        for match in self.matches:
            field_prefix = f'match_{match.id}'
            result = cleaned_data.get(f'{field_prefix}_result')
            home_score = cleaned_data.get(f'{field_prefix}_home_score')
            away_score = cleaned_data.get(f'{field_prefix}_away_score')
            
            # Skip validation if no prediction is made for this match
            if not result and home_score is None and away_score is None:
                continue
            
            # Validate that match is still open for predictions
            if match.status_long in ['Match Finished', 'In Progress', 'First Half, Kick Off', 'Second Half, 2nd Half Started', 'Extra Time', 'Penalty In Progress']:
                raise ValidationError(f"Cannot make predictions for {match} - match is {match.get_status_display().lower()}.")
            
            if match.date <= timezone.now():
                raise ValidationError(f"Prediction deadline has passed for {match}.")
            
            # If result is provided, it's required
            if not result:
                raise ValidationError(f"Please select a result for {match}.")
            
            # Validate score consistency if both scores are provided
            if home_score is not None and away_score is not None:
                if home_score > away_score and result != 'H':
                    cleaned_data[f'{field_prefix}_result'] = 'H'
                elif away_score > home_score and result != 'A':
                    cleaned_data[f'{field_prefix}_result'] = 'A'
                elif home_score == away_score and result != 'D':
                    cleaned_data[f'{field_prefix}_result'] = 'D'

        return cleaned_data

    def save(self):
        """Save all predictions"""
        predictions_created = 0
        predictions_updated = 0
        
        for match in self.matches:
            field_prefix = f'match_{match.id}'
            result = self.cleaned_data.get(f'{field_prefix}_result')
            home_score = self.cleaned_data.get(f'{field_prefix}_home_score')
            away_score = self.cleaned_data.get(f'{field_prefix}_away_score')
            
            # Skip if no prediction is made
            if not result:
                continue
            
            # Create or update prediction
            prediction, created = MatchPredict.objects.update_or_create(
                user=self.user,
                match=match,
                defaults={
                    'predicted_result': result,
                    'predicted_home_score': home_score,
                    'predicted_away_score': away_score,
                    'confidence_level': 50,  # Default confidence
                }
            )
            
            if created:
                predictions_created += 1
            else:
                predictions_updated += 1
        
        return predictions_created, predictions_updated


class PredictionFilterForm(forms.Form):
    """Form for filtering predictions by league, date, etc."""
    
    league = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    # status = forms.MultipleChoiceField(
    #     choices=Fixture.MATCH_STATUS_CHOICES,
    #     required=False,
    #     widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    # )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    show_only_unpredicted = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        user_groups = kwargs.pop('user_groups', None)
        super().__init__(*args, **kwargs)
        
        # Set league choices based on user's groups - only show active leagues
        if user_groups:
            from .models import League
            leagues = League.objects.filter(
                prediction_groups__in=user_groups,
                is_active=True
            ).distinct()
            self.fields['league'].queryset = leagues
        else:
            from .models import League
            self.fields['league'].queryset = League.objects.filter(is_active=True)


class UserSignUpForm(UserCreationForm):
    """Form for user registration with profile information"""
    
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    
    birthday = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'birthday')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update password field widgets
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email
    
    def clean_birthday(self):
        birthday = self.cleaned_data.get('birthday')
        if birthday:
            from datetime import date
            today = date.today()
            age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
            if age < 13:
                raise ValidationError("You must be at least 13 years old to register.")
            if age > 120:
                raise ValidationError("Please enter a valid birth date.")
        return birthday
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create user profile
            UserProfile.objects.create(
                user=user,
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                birthday=self.cleaned_data['birthday']
            )
        return user


class UserSignInForm(forms.Form):
    """Form for user sign in"""
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class CreateGroupForm(forms.ModelForm):
    """Form for creating a new user group with flexible match selection"""
    
    # Match selection type
    SELECTION_TYPE_CHOICES = [
        ('leagues', 'Entire Leagues'),
        ('rounds', 'Specific League Rounds'),
        ('dates', 'Matches on Specific Dates'),
        ('mixed', 'Mixed Selection'),
    ]
    
    selection_type = forms.ChoiceField(
        choices=SELECTION_TYPE_CHOICES,
        initial='leagues',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
            'onchange': 'toggleSelectionSections()'
        }),
        label='Match Selection Type',
        help_text='Choose how you want to select matches for this group'
    )
    
    # Add separate country field for cascading dropdown
    countries = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'id': 'id_countries',
            'size': '5'
        }),
        label='Countries',
        help_text='Select countries first, then choose leagues from selected countries'
    )
    
    class Meta:
        model = UserGroup
        fields = ['name', 'description', 'is_private', 'max_members']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter group name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe your group (optional)'
            }),
            'is_private': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'max_members': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '2',
                'max': '100',
                'value': '50'
            })
        }
        labels = {
            'name': 'Group Name',
            'description': 'Description',
            'is_private': 'Private Group',
            'max_members': 'Maximum Members'
        }
        help_texts = {
            'name': 'Choose a unique name for your group',
            'description': 'Optional description of your group',
            'is_private': 'Private groups require invitation to join',
            'max_members': 'Maximum number of members allowed (2-100)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set countries queryset - only show countries that have active leagues
        from .models import Country, League, Season
        self.fields['countries'].queryset = Country.objects.filter(
            leagues__is_active=True
        ).distinct().order_by('name')
        
        # Add leagues field (for backward compatibility and mixed selection)
        self.fields['leagues'] = forms.ModelMultipleChoiceField(
            queryset=League.objects.none(),  # Start with empty queryset
            required=False,
            widget=forms.SelectMultiple(attrs={
                'class': 'form-select',
                'id': 'id_leagues',
                'size': '8'
            }),
            label='Leagues to Predict',
            help_text='Select countries first, then choose leagues from selected countries'
        )
        
        # Add round selection fields
        self.fields['round_league'] = forms.ModelChoiceField(
            queryset=League.objects.filter(is_active=True),
            required=False,
            widget=forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_round_league',
                'onchange': 'updateSeasons()'
            }),
            label='League for Round Selection',
            help_text='Select a league to choose specific rounds from'
        )
        
        self.fields['round_season'] = forms.ModelChoiceField(
            queryset=Season.objects.filter(is_active=True),
            required=False,
            widget=forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_round_season',
                'onchange': 'updateRounds()'
            }),
            label='Season',
            help_text='Select the season for round selection'
        )
        
        self.fields['round_numbers'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_round_numbers',
                'placeholder': 'e.g., 1, 2, 5-10, Matchday 1, Quarter-final'
            }),
            label='Round Numbers',
            help_text='Enter round numbers (comma-separated, ranges allowed)'
        )
        
        # Add date selection fields
        self.fields['match_dates'] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_match_dates',
                'placeholder': 'YYYY-MM-DD, YYYY-MM-DD, ...'
            }),
            label='Match Dates',
            help_text='Enter dates in YYYY-MM-DD format (comma-separated)'
        )
        
        self.fields['date_leagues'] = forms.ModelMultipleChoiceField(
            queryset=League.objects.filter(is_active=True),
            required=False,
            widget=forms.SelectMultiple(attrs={
                'class': 'form-select',
                'id': 'id_date_leagues',
                'size': '6'
            }),
            label='Leagues for Date Selection',
            help_text='Leave empty to include all active leagues on selected dates'
        )
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name and UserGroup.objects.filter(name=name).exists():
            raise ValidationError("A group with this name already exists.")
        return name
    
    def clean_max_members(self):
        max_members = self.cleaned_data.get('max_members')
        if max_members and (max_members < 2 or max_members > 100):
            raise ValidationError("Maximum members must be between 2 and 100.")
        return max_members
    
    def clean(self):
        cleaned_data = super().clean()
        selection_type = cleaned_data.get('selection_type')
        leagues = cleaned_data.get('leagues')
        round_league = cleaned_data.get('round_league')
        round_season = cleaned_data.get('round_season')
        round_numbers = cleaned_data.get('round_numbers')
        match_dates = cleaned_data.get('match_dates')
        
        # Validate based on selection type
        if selection_type == 'leagues':
            if not leagues:
                raise ValidationError("Please select at least one league for league-based selection.")
        elif selection_type == 'rounds':
            if not round_league:
                raise ValidationError("Please select a league for round-based selection.")
            if not round_season:
                raise ValidationError("Please select a season for round-based selection.")
            if not round_numbers:
                raise ValidationError("Please enter round numbers for round-based selection.")
        elif selection_type == 'dates':
            if not match_dates:
                raise ValidationError("Please enter match dates for date-based selection.")
            # Validate date format
            try:
                from datetime import datetime
                dates = [date.strip() for date in match_dates.split(',')]
                for date_str in dates:
                    datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                raise ValidationError("Please enter dates in YYYY-MM-DD format.")
        elif selection_type == 'mixed':
            has_selection = leagues or (round_league and round_season and round_numbers) or match_dates
            if not has_selection:
                raise ValidationError("Please make at least one selection for mixed selection type.")
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)
        
        if commit:
            self._save_match_selections(instance)
        
        return instance
    
    def _save_match_selections(self, group):
        """Save the flexible match selections based on form data"""
        from .models import GroupLeagueRound, GroupDateSelection
        from datetime import datetime
        
        selection_type = self.cleaned_data.get('selection_type')
        all_group_leagues = set()  # Collect all leagues used in this group
        
        # Save league selections (for leagues and mixed types)
        if selection_type in ['leagues', 'mixed']:
            leagues = self.cleaned_data.get('leagues')
            if leagues:
                group.leagues.set(leagues)
                all_group_leagues.update(leagues)
        
        # Save round selections (for rounds and mixed types)
        if selection_type in ['rounds', 'mixed']:
            round_league = self.cleaned_data.get('round_league')
            round_season = self.cleaned_data.get('round_season')
            round_numbers = self.cleaned_data.get('round_numbers')
            
            if round_league and round_season and round_numbers:
                # Add the round league to the group's leagues
                all_group_leagues.add(round_league)
                
                # Parse round numbers (handle ranges and individual numbers)
                rounds = []
                for round_part in round_numbers.split(','):
                    round_part = round_part.strip()
                    if '-' in round_part and round_part.replace('-', '').isdigit():
                        # Handle ranges like "1-5"
                        start, end = map(int, round_part.split('-'))
                        rounds.extend([str(i) for i in range(start, end + 1)])
                    else:
                        # Handle individual rounds
                        rounds.append(round_part)
                
                # Create GroupLeagueRound objects
                for round_num in rounds:
                    GroupLeagueRound.objects.get_or_create(
                        group=group,
                        league=round_league,
                        season=round_season,
                        round_number=round_num.strip()
                    )
        
        # Save date selections (for dates and mixed types)
        if selection_type in ['dates', 'mixed']:
            match_dates = self.cleaned_data.get('match_dates')
            date_leagues = self.cleaned_data.get('date_leagues')
            
            if match_dates:
                dates = [date.strip() for date in match_dates.split(',')]
                for date_str in dates:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    date_selection, created = GroupDateSelection.objects.get_or_create(
                        group=group,
                        match_date=date_obj
                    )
                    if date_leagues:
                        date_selection.specific_leagues.set(date_leagues)
                        all_group_leagues.update(date_leagues)
                    # If no specific leagues selected for dates, we'll add leagues 
                    # from matches on those dates later
        
        # Update group leagues to include all leagues from all selection types
        if all_group_leagues:
            # For pure league selection, we already set it above
            # For other types, add the additional leagues
            if selection_type in ['rounds', 'dates']:
                group.leagues.set(all_group_leagues)
            elif selection_type == 'mixed':
                # For mixed, add to existing leagues
                existing_leagues = set(group.leagues.all())
                existing_leagues.update(all_group_leagues)
                group.leagues.set(existing_leagues)


class GroupInvitationForm(forms.ModelForm):
    """Form for sending group invitations"""
    
    invitee_username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username or email'
        }),
        help_text="Enter the username or email of the person you want to invite"
    )
    
    class Meta:
        model = GroupInvitation
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional message to include with the invitation'
            })
        }
        labels = {
            'message': 'Invitation Message'
        }
        help_texts = {
            'message': 'Optional personal message to include with the invitation'
        }
    
    def clean_invitee_username(self):
        invitee_username = self.cleaned_data.get('invitee_username')
        if invitee_username:
            # Try to find user by username or email
            try:
                user = User.objects.get(username=invitee_username)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=invitee_username)
                except User.DoesNotExist:
                    raise ValidationError("User not found. Please check the username or email.")
            
            # Check if user is already a member
            group = self.instance.group if self.instance.pk else None
            if group and GroupMembership.objects.filter(user=user, group=group).exists():
                raise ValidationError("This user is already a member of the group.")
            
            # Check if there's already a pending invitation
            if group and GroupInvitation.objects.filter(
                group=group, 
                invitee=user, 
                status='pending'
            ).exists():
                raise ValidationError("This user already has a pending invitation to this group.")
            
            return user
        return None
    
    def save(self, commit=True):
        invitation = super().save(commit=False)
        invitation.invitee = self.cleaned_data['invitee_username']
        if commit:
            invitation.save()
        return invitation
