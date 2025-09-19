# Flexible Group Match Selection Feature

## Overview

The group system has been enhanced to support flexible match selection beyond just entire leagues. Users can now create groups that include:

1. **Entire Leagues** (original functionality)
2. **Specific League Rounds** (e.g., "Premier League rounds 1-5")
3. **Matches on Specific Dates** (e.g., "All matches on 2025-12-25")
4. **Mixed Selection** (combination of the above)

## New Models

### GroupLeagueRound
- Links a group to specific rounds of a league/season
- Fields: `group`, `league`, `season`, `round_number`
- Allows selecting individual rounds like "Round 1", "Matchday 5", "Quarter-final"

### GroupDateSelection
- Links a group to matches on specific dates
- Fields: `group`, `match_date`, `specific_leagues`, `description`
- Can include all active leagues on a date or filter by specific leagues

## Enhanced UserGroup Model

### New Method: get_all_matches()
- Returns all matches that belong to the group based on all selection criteria
- Combines matches from:
  - Entire leagues (backward compatibility)
  - League rounds
  - Date selections
- Returns a unified, deduplicated queryset

## Enhanced Forms

### CreateGroupForm
- New `selection_type` field with radio buttons:
  - `leagues`: Select entire leagues
  - `rounds`: Select specific rounds
  - `dates`: Select matches by date
  - `mixed`: Use multiple selection methods

### New Form Fields
- `round_league`: Choose league for round selection
- `round_season`: Choose season for round selection  
- `round_numbers`: Enter round numbers (supports ranges like "1-5")
- `match_dates`: Enter dates in YYYY-MM-DD format
- `date_leagues`: Optional league filter for date selection

## Enhanced Views

### AJAX Endpoints
- `get_seasons_by_league`: Get seasons for a selected league
- `get_rounds_by_league_season`: Get available rounds for league/season

### Updated Views
- `create_group_view`: Handles new form structure
- `group_detail`: Shows all selection types in group details
- `prediction_center`: Uses flexible match selection for predictions

## User Interface

### Dynamic Form Sections
- Form sections show/hide based on selection type
- Real-time league/season/round filtering via AJAX
- Intuitive interface with helpful descriptions

### Group Creation Flow
1. Select basic group info (name, description, etc.)
2. Choose match selection type
3. Configure selection based on type:
   - **Leagues**: Select countries → leagues
   - **Rounds**: Select league → season → round numbers
   - **Dates**: Enter dates → optionally filter leagues
   - **Mixed**: Use any combination

## Examples

### Example 1: Premier League Specific Rounds
- Selection Type: "Specific League Rounds"
- League: "Premier League"
- Season: "2025/26"
- Round Numbers: "1, 2, 5-10, 15"
- Result: Group includes only these specific rounds

### Example 2: Christmas Day Football
- Selection Type: "Matches on Specific Dates"
- Dates: "2025-12-25"
- Leagues: (empty = all active leagues)
- Result: All football matches on Christmas Day

### Example 3: Mixed Selection
- Selection Type: "Mixed Selection"
- Include entire "Champions League" 
- Plus "Premier League rounds 1-5"
- Plus "All matches on 2025-12-25"
- Result: Combined selection from all criteria

## Database Changes

### Migration: 0008_add_flexible_group_selections
- Creates `GroupLeagueRound` table
- Creates `GroupDateSelection` table  
- Makes `UserGroup.leagues` field optional (blank=True)

## Backward Compatibility

- Existing groups using the old league-only system continue to work
- Old groups automatically use the entire league selection
- No data migration required
- Admin interface supports both old and new group types

## Statistics and Leaderboards

- Group statistics automatically include matches from all selection types
- Leaderboards calculate points from the flexible match set
- No changes to prediction scoring system

## Admin Interface

- New admin pages for `GroupLeagueRound` and `GroupDateSelection`
- Group admin shows all selection types
- Easy management of complex group configurations

## Benefits

1. **Flexibility**: Create groups for tournaments, specific gameweeks, or special events
2. **Precision**: Include only relevant matches for specialized competitions
3. **Convenience**: Set up groups for specific dates (holidays, special events)
4. **Scalability**: Mix and match selection types as needed
5. **User Experience**: Intuitive interface guides users through options

## Technical Implementation

- Clean separation of concerns with dedicated models
- Efficient database queries using union operations
- AJAX-powered dynamic form interactions
- Comprehensive admin interface for management
- Full backward compatibility maintained
