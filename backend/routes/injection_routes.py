# backend/routes/injection_routes.py
import os
import traceback
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename
import json

# SessionLocal is not directly used here, it's used by injection_service
from ..models import Area, ProcessStep, UseCase
from ..injection_service import process_area_file, process_step_file, process_usecase_file

injection_routes = Blueprint('injection', __name__,
                             template_folder='../templates',
                             url_prefix='/injection')

@injection_routes.route('/', methods=['GET', 'POST'])
@login_required
def handle_injection():
    print("Injection route accessed") # Debug log
    if request.method == 'POST':
        print("POST request received") # Debug log
        try:
            # Check if any file was uploaded
            if 'area_file' not in request.files and \
               'step_file' not in request.files and \
               'usecase_file' not in request.files:
                flash('No file part in the request.', 'danger')
                print("No file part in the request") # Debug log
                return redirect(request.url)

            # --- Area File Processing ---
            if 'area_file' in request.files:
                print("Area file detected") # Debug log
                file = request.files['area_file']
                if file.filename == '' or not file:
                    flash('No selected file.', 'warning')
                    return redirect(request.url)

                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_area_file(file.stream)
                    flash_category = 'success' if result['success'] else 'danger'
                    if not result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0 :
                        flash_category = 'warning' # Downgrade error if only skips occurred
                    flash(result['message'], flash_category)
                    print(f"Area injection result: {result}")
                    return redirect(url_for('injection.handle_injection'))
                else:
                    flash('Invalid file type or name for Areas. Please upload a .json file.', 'danger')
                    return redirect(request.url)

            # --- Process Step File Processing ---
            elif 'step_file' in request.files:
                print("Step file detected") # Debug log
                file = request.files['step_file']
                if file.filename == '' or not file:
                    print("No selected file for Process Steps") # Debug log
                    flash('No selected file for Process Steps.', 'warning')
                    return redirect(request.url)

                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_step_file(file.stream)

                    flash_category = 'danger' # Default to danger
                    if result['success'] and result['added_count'] > 0:
                         flash_category = 'success'
                    elif result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0:
                         flash_category = 'warning' # No errors, but nothing added, only skipped
                    elif not result['success'] and result.get('added_count', 0) == 0 and \
                         result.get('skipped_count', 0) > 0 and 'Error:' not in result.get('message', ''):
                        # Treat cases with only skips but marked as failure as warning
                        flash_category = 'warning'

                    flash(result['message'], flash_category)
                    print(f"Step injection result: {result}")
                    return redirect(url_for('injection.handle_injection'))
                else:
                     flash('Invalid file type or name for Process Steps. Please upload a .json file.', 'danger')
                     return redirect(request.url)

            # --- Use Case File Processing ---
            elif 'usecase_file' in request.files:
                print("Use Case file detected") # Debug log
                file = request.files['usecase_file']
                if file.filename == '' or not file:
                    print("No selected file for Use Cases") # Debug log
                    flash('No selected file for Use Cases.', 'warning')
                    return redirect(request.url)

                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_usecase_file(file.stream)

                    flash_category = 'danger' # Default to danger
                    if result['success'] and result['added_count'] > 0:
                        flash_category = 'success'
                    elif result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0:
                        flash_category = 'warning'
                    elif not result['success'] and 'Error:' not in result.get('message', ''):
                         flash_category = 'warning' # Treat skip-only failures as warnings

                    flash(result['message'], flash_category)
                    print(f"Use Case injection result: {result}")
                    return redirect(url_for('injection.handle_injection'))
                else:
                     flash('Invalid file type or name for Use Cases. Please upload a .json file.', 'danger')
                     return redirect(request.url)
            # --- END Use Case File Processing ---

            else:
                print("No known file input found") # Debug log
                flash('No file submitted or unknown form field.', 'warning')
                return redirect(request.url)

        except Exception as e:
            print(f"Unexpected error in injection route: {str(e)}")
            traceback.print_exc()
            flash(f"An unexpected error occurred: {str(e)}", 'danger')
            return redirect(request.url)

    # --- GET Logic ---
    return render_template('injection.html', title='Data Injection')