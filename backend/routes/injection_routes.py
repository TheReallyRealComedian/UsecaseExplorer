# backend/routes/injection_routes.py
import os
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required

from ..app import SessionLocal
from ..models import Area, ProcessStep
from ..injection_service import process_area_file, process_step_file

injection_routes = Blueprint('injection', __name__,
                             template_folder='../templates',
                             url_prefix='/injection')

@injection_routes.route('/', methods=['GET', 'POST'])
@login_required
def handle_injection():
    if request.method == 'POST':

        # --- Area File Processing ---
        if 'area_file' in request.files:
            file = request.files['area_file']
            if file.filename == '':
                flash('No selected file.', 'warning')
                return redirect(request.url)

            if file and '.' in file.filename and \
               file.filename.rsplit('.', 1)[1].lower() == 'json':
                result = process_area_file(file.stream)
                flash_category = 'success' if result['success'] else 'danger'
                if not result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0 :
                    flash_category = 'warning' # Downgrade error if only skips occurred
                flash(result['message'], flash_category)
                print(f"Area injection result: {result}") # Keep logging as requested
                return redirect(url_for('injection.handle_injection'))
            else:
                flash('Invalid file type or name for Areas. Please upload a .json file.', 'danger')
                return redirect(request.url)

        # --- Process Step File Processing ---
        elif 'step_file' in request.files:
            file = request.files['step_file']
            if file.filename == '':
                flash('No selected file for Process Steps.', 'warning')
                return redirect(request.url)

            if file and '.' in file.filename and \
               file.filename.rsplit('.', 1)[1].lower() == 'json':
                # Call the service function for step files
                result = process_step_file(file.stream)

                # Determine flash category based on outcome
                flash_category = 'danger' # Default to danger
                if result['success'] and result['added_count'] > 0:
                     flash_category = 'success'
                elif result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0:
                     flash_category = 'warning' # No errors, but nothing added, only skipped
                elif not result['success'] and result.get('added_count', 0) == 0 and result.get('skipped_count', 0) > 0 and 'Error:' not in result.get('message', ''):
                    # Treat cases with only skips but marked as failure (due to data validation maybe) as warning
                    flash_category = 'warning'

                flash(result['message'], flash_category)
                print(f"Step injection result: {result}") # Keep logging as requested
                return redirect(url_for('injection.handle_injection'))
            else:
                 flash('Invalid file type or name for Process Steps. Please upload a .json file.', 'danger')
                 return redirect(request.url)

        else:
            # Handle case where no known file input was found
            flash('No file submitted or unknown form field.', 'warning')
            return redirect(request.url)

    # --- GET Logic ---
    # Render the injection page template for GET requests
    return render_template('injection.html', title='Data Injection')