# backend/utils.py
from flask import url_for # serialize_for_js needs url_for

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
            # In a real app, you might want to log this more formally.
            # For now, printing is okay for debugging.
            # Critical: Ensure url_for is called within an app context if this function
            # is ever used outside of a request context where url_for works automatically.
            # However, in this specific usage (within routes), it should be fine.
            print(f"DEBUG: url_for failed for item {obj.id} ({obj.name}) of type {item_type}: {url_error}")
            item_dict['url'] = '#' # Fallback URL
            data.append(item_dict)
    return data