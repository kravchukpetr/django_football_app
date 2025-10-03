from django import template

register = template.Library()

@register.filter
def lookup_dict(form, match_id):
    """Helper filter to access dynamic form fields in bulk prediction form"""
    field_data = {}
    field_prefix = f'match_{match_id}'
    
    # Get the form fields for this match
    result_field = form.fields.get(f'{field_prefix}_result')
    home_score_field = form.fields.get(f'{field_prefix}_home_score')
    away_score_field = form.fields.get(f'{field_prefix}_away_score')
    
    if result_field:
        field_data['result'] = form[f'{field_prefix}_result']
    if home_score_field:
        field_data['home_score'] = form[f'{field_prefix}_home_score']
    if away_score_field:
        field_data['away_score'] = form[f'{field_prefix}_away_score']
    
    return field_data

@register.filter
def lookup(dictionary, key):
    """Simple lookup filter for dictionary access in templates"""
    return dictionary.get(key)

@register.filter
def sort_rounds_by_order(rounds_dict):
    """Sort rounds dictionary by predefined order"""
    # Define the order for round numbers
    round_order = [
        'Preliminary round',
        '1st Qualifying Round',
        '2nd Qualifying Round', 
        '3rd Qualifying Round',
        'Play-offs',
        'Round of 16',
        'Quarter-finals',
        'Semi-finals',
        'Final'
    ]
    
    # Create a mapping of round names to their order
    order_map = {round_name: index for index, round_name in enumerate(round_order)}
    
    # Sort the dictionary items by the predefined order
    sorted_items = sorted(rounds_dict.items(), key=lambda x: order_map.get(x[0], 999))
    
    return dict(sorted_items)

@register.filter
def sort_round_numbers_by_order(rounds_dict):
    """Sort round numbers within a round type by predefined order"""
    # Define the order for round numbers
    round_order = [
        'Preliminary round',
        '1st Qualifying Round',
        '2nd Qualifying Round', 
        '3rd Qualifying Round',
        'Play-offs',
        'Round of 16',
        'Quarter-finals',
        'Semi-finals',
        'Final'
    ]
    
    # Create a mapping of round names to their order
    order_map = {round_name: index for index, round_name in enumerate(round_order)}
    
    # Also handle variations and partial matches
    def get_order_key(round_name):
        # Try exact match first
        if round_name in order_map:
            return order_map[round_name]
        
        # Try case-insensitive match
        for ordered_round in round_order:
            if round_name.lower() == ordered_round.lower():
                return order_map[ordered_round]
        
        # Try partial match
        for ordered_round in round_order:
            if ordered_round.lower() in round_name.lower() or round_name.lower() in ordered_round.lower():
                return order_map[ordered_round]
        
        # Default to end for unknown rounds
        return 999
    
    # Sort the dictionary items by the predefined order
    sorted_items = sorted(rounds_dict.items(), key=lambda x: get_order_key(x[0]))
    
    return dict(sorted_items)

@register.filter
def should_expand_round(round_name):
    """Check if a round should be expanded by default"""
    expanded_rounds = ['Round of 16', 'Quarter-finals', 'Semi-finals', 'Final']
    return round_name in expanded_rounds
