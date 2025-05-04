# backend/routes/injection_routes.py
import os
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required

# Define the blueprint for injection routes
injection_routes = Blueprint('injection', __name__,
                             template_folder='../templates',
                             url_prefix='/injection') # Define a URL prefix for all routes in this blueprint

# Import necessary things for later steps (e.g., service function, SessionLocal)
from ..app import SessionLocal # Needed by the service function
from ..models import Area      # Needed by the service function
from ..injection_service import process_area_file # Import the function

@injection_routes.route('/', methods=['GET', 'POST']) # Route handles both GET and POST at /injection/
@login_required
def handle_injection():
    if request.method == 'POST':
        # --- Replace POST Logic ---
        if 'area_file' not in request.files:
            flash('No file part found in the request.', 'warning')
            return redirect(request.url)

        file = request.files['area_file']

        if file.filename == '':
            flash('No selected file.', 'warning')
            return redirect(request.url)

        # Use os.path.splitext for robust extension checking
        if file and '.' in file.filename and \
           file.filename.rsplit('.', 1)[1].lower() == 'json':

            # Call the service function to process the file stream
            result = process_area_file(file.stream) # Pass the file stream

            # Use the result message for feedback
            flash_category = 'success' if result['success'] else 'danger'
            if not result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0 :
                flash_category = 'warning' # Downgrade error if only skips occurred

            flash(result['message'], flash_category)

            # Optional: Log details if needed
            # print(f"Area injection result: {result}")

            # Redirect back to the injection page
            return redirect(url_for('injection.handle_injection'))
        else:
            flash('Invalid file type or name. Please upload a .json file.', 'danger')
            return redirect(request.url)
        # --- End POST Logic Replacement ---

    # --- GET Logic ---
    # Render the injection page template for GET requests
    return render_template('injection.html', title='Data Injection')