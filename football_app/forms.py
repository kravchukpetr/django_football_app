from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import MatchPredict, MatchResult, UserGroup


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
            if self.match.status in ['finished', 'live']:
                raise ValidationError("Cannot make predictions for finished or live matches.")
            
            # Check if prediction deadline has passed (e.g., 1 hour before match)
            if self.match.match_date <= timezone.now():
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
            if match.status in ['finished', 'live']:
                raise ValidationError(f"Cannot make predictions for {match} - match is {match.get_status_display().lower()}.")
            
            if match.match_date <= timezone.now():
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
    
    status = forms.MultipleChoiceField(
        choices=MatchResult.MATCH_STATUS_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
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
        
        # Set league choices based on user's groups
        if user_groups:
            from .models import League
            leagues = League.objects.filter(prediction_groups__in=user_groups).distinct()
            self.fields['league'].queryset = leagues
        else:
            from .models import League
            self.fields['league'].queryset = League.objects.all()
