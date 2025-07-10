# backend/utils.py
import markupsafe
import markdown
import json
from flask import url_for


# --- CUSTOM JINJA FILTERS ---
def nl2br(value):
    if value is None:
        return ''
    return markupsafe.Markup(markupsafe.escape(value).replace('\n', '<br>\n'))

def markdown_to_html_filter(value):
    if value is None:
        return ''
    return markupsafe.Markup(markdown.markdown(value, extensions=['fenced_code', 'tables']))

def truncate_filter(s, length=255, end='...'):
    if s is None:
        return ''
    s = str(s)
    if len(s) > length:
        return s[:length] + end
    else:
        return s

def zfill_filter(value, width):
    if value is None:
        return ''
    return str(value).zfill(width)

def htmlsafe_json_filter(value):
    return markupsafe.Markup(json.dumps(value))

def map_priority_to_benefit_filter(priority):
    if priority == 1:
        return "High"
    if priority == 2:
        return "Medium"
    if priority == 3:
        return "Low"
    return "N/A"

# --- SERIALIZATION FOR JAVASCRIPT ---
def serialize_for_js(obj_list, item_type):
    """
    Helper to convert query results to flat dicts for JavaScript.
    Now lives in utils.py to avoid circular imports.
    """
    data = []
    for obj in obj_list:
        item_dict = {
            'id': obj.id,
            'name': str(obj.name) if obj.name is not None else '',
        }
        # Add URLs dynamically based on type
        try:
            if item_type == 'area':
                item_dict['url'] = url_for('areas.view_area', area_id=obj.id)
            elif item_type == 'step':
                item_dict['area_id'] = obj.area_id
                item_dict['url'] = url_for('steps.view_step', step_id=obj.id)
            elif item_type == 'usecase':
                item_dict['step_id'] = obj.process_step_id
                item_dict['url'] = url_for('usecases.view_usecase', usecase_id=obj.id)
            data.append(item_dict)
        except Exception as url_error:
            print(f"DEBUG: url_for failed for item {obj.id} ({obj.name}) of type {item_type}: {url_error}")
            item_dict['url'] = '#' # Fallback URL
            data.append(item_dict)
    return data