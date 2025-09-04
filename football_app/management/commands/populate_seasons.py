from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from football_app.models import Season


class Command(BaseCommand):
    help = 'Populate seasons from 2010/2011 to 2025/2026'

    def handle(self, *args, **options):
        self.stdout.write('Creating seasons from 2010/2011 to 2025/2026...')
        
        seasons_data = [
            # Past seasons
            {'start_year': 2010, 'end_year': 2011, 'start_date': date(2010, 8, 1), 'end_date': date(2011, 5, 31)},
            {'start_year': 2011, 'end_year': 2012, 'start_date': date(2011, 8, 1), 'end_date': date(2012, 5, 31)},
            {'start_year': 2012, 'end_year': 2013, 'start_date': date(2012, 8, 1), 'end_date': date(2013, 5, 31)},
            {'start_year': 2013, 'end_year': 2014, 'start_date': date(2013, 8, 1), 'end_date': date(2014, 5, 31)},
            {'start_year': 2014, 'end_year': 2015, 'start_date': date(2014, 8, 1), 'end_date': date(2015, 5, 31)},
            {'start_year': 2015, 'end_year': 2016, 'start_date': date(2015, 8, 1), 'end_date': date(2016, 5, 31)},
            {'start_year': 2016, 'end_year': 2017, 'start_date': date(2016, 8, 1), 'end_date': date(2017, 5, 31)},
            {'start_year': 2017, 'end_year': 2018, 'start_date': date(2017, 8, 1), 'end_date': date(2018, 5, 31)},
            {'start_year': 2018, 'end_year': 2019, 'start_date': date(2018, 8, 1), 'end_date': date(2019, 5, 31)},
            {'start_year': 2019, 'end_year': 2020, 'start_date': date(2019, 8, 1), 'end_date': date(2020, 7, 31)},  # Extended due to COVID
            {'start_year': 2020, 'end_year': 2021, 'start_date': date(2020, 9, 1), 'end_date': date(2021, 5, 31)},
            {'start_year': 2021, 'end_year': 2022, 'start_date': date(2021, 8, 1), 'end_date': date(2022, 5, 31)},
            {'start_year': 2022, 'end_year': 2023, 'start_date': date(2022, 8, 1), 'end_date': date(2023, 5, 31)},
            {'start_year': 2023, 'end_year': 2024, 'start_date': date(2023, 8, 1), 'end_date': date(2024, 5, 31)},
            
            # Current season (2024/2025)
            {'start_year': 2024, 'end_year': 2025, 'start_date': date(2024, 8, 1), 'end_date': date(2025, 5, 31), 'is_current': True},
            
            # Future season
            {'start_year': 2025, 'end_year': 2026, 'start_date': date(2025, 8, 1), 'end_date': date(2026, 5, 31)},
        ]
        
        created_count = 0
        
        for season_data in seasons_data:
            season_name = f"{season_data['start_year']}/{season_data['end_year']}"
            
            season, created = Season.objects.get_or_create(
                start_year=season_data['start_year'],
                end_year=season_data['end_year'],
                defaults={
                    'name': season_name,
                    'start_date': season_data['start_date'],
                    'end_date': season_data['end_date'],
                    'is_current': season_data.get('is_current', False),
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
                status = "created"
                if season.is_current:
                    status += " (CURRENT)"
            else:
                status = "already exists"
            
            self.stdout.write(f"  Season {season_name}: {status}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} seasons!')
        )
        
        # Set 2024/2025 as current season if not already set
        current_season = Season.objects.filter(is_current=True).first()
        if not current_season:
            try:
                season_2024_25 = Season.objects.get(start_year=2024, end_year=2025)
                season_2024_25.is_current = True
                season_2024_25.save()
                self.stdout.write(
                    self.style.SUCCESS('Set 2024/2025 as the current season.')
                )
            except Season.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING('Could not find 2024/2025 season to set as current.')
                )
        else:
            self.stdout.write(f'Current season: {current_season.name}')
