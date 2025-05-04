# backend/routes/auth_routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse

# Import the User model and SessionLocal for database operations
# Use '..' to go up one level from 'routes' to the parent 'backend' package
from ..models import User
from ..app import SessionLocal # SessionLocal is defined in backend/app.py

# Define the blueprint *in this file*
auth_routes = Blueprint('auth', __name__,
                        template_folder='../templates', # Specify template folder relative to this file
                        url_prefix='/auth')

@auth_routes.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        # Redirect to the main page route defined in app.py ('index')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        session = SessionLocal()
        try:
            # Check if username already exists
            existing_user = session.query(User).filter_by(username=username).first()
            if existing_user:
                flash('Username already exists. Please choose a different one.', 'warning')
                return render_template('register.html', title='Register')

            if not username or not password:
                 flash('Username and password are required.', 'danger')
                 return render_template('register.html', title='Register')

            # Create new user
            new_user = User(username=username)
            new_user.set_password(password)
            session.add(new_user)
            session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login')) # Redirect to login page after success
        except Exception as e:
            session.rollback() # Roll back changes on error
            flash(f'An error occurred during registration: {e}', 'danger')
            print(f"Registration error: {e}") # Log the error
        finally:
            SessionLocal.remove() # Ensure session is removed in all cases

    # Handle GET request: render the registration page
    return render_template('register.html', title='Register')

@auth_routes.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index')) # Redirect to main page if already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember_me') is not None # Checkbox value
        session = SessionLocal()
        try:
            user = session.query(User).filter_by(username=username).first()
            # Check if user exists and password is correct
            if user and user.check_password(password):
                login_user(user, remember=remember) # Log the user in via Flask-Login
                flash('Login successful!', 'success')
                next_page = request.args.get('next')
                # Security check: Ensure next_page is a relative path within the app
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('index') # Default redirect to index if 'next' is invalid or missing
                return redirect(next_page)
            else:
                flash('Invalid username or password.', 'danger')
        except Exception as e:
            flash(f'An error occurred during login: {e}', 'danger')
            print(f"Login error: {e}") # Log the error
        finally:
            SessionLocal.remove() # Ensure session is removed

    # Handle GET request: render the login page
    return render_template('login.html', title='Sign In')

@auth_routes.route('/logout')
@login_required # User must be logged in to log out
def logout():
    logout_user() # Log the user out via Flask-Login
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login')) # Redirect to login page after logout