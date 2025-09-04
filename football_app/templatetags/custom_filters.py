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
