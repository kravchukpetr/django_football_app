from django.core.management.base import BaseCommand
from football_app.models import Season


class Command(BaseCommand):
    help = 'Set 2025/2026 as the current season'

    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=str,
            default='2025/2026',
            help='Season to set as current (default: 2025/2026)'
        )

    def handle(self, *args, **options):
        season_name = options['season']
        
        try:
            # Parse season name to get start and end years
            start_year, end_year = season_name.split('/')
            start_year = int(start_year)
            end_year = int(end_year)
            
            # Find the season
            season = Season.objects.get(start_year=start_year, end_year=end_year)
            
            # Set all seasons as not current
            Season.objects.all().update(is_current=False)
            
            # Set the specified season as current
            season.is_current = True
            season.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully set {season.name} as the current season!')
            )
            
        except Season.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Season {season_name} not found!')
            )
        except ValueError:
            self.stdout.write(
                self.style.ERROR(f'Invalid season format. Use YYYY/YYYY format (e.g., 2025/2026)')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
