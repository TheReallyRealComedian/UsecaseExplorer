# backend/routes/auth_routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse

from ..models import User
from ..db import SessionLocal # CHANGED

auth_routes = Blueprint('auth', __name__,
                        template_folder='../templates',
                        url_prefix='/auth')

@auth_routes.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        session = SessionLocal()
        try:
            existing_user = session.query(User).filter_by(username=username).first()
            if existing_user:
                flash('Username already exists. Please choose a different one.', 'warning')
                return render_template('register.html', title='Register')

            if not username or not password:
                 flash('Username and password are required.', 'danger')
                 return render_template('register.html', title='Register')

            new_user = User(username=username)
            new_user.set_password(password)
            session.add(new_user)
            session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            session.rollback()
            flash(f'An error occurred during registration: {e}', 'danger')
            print(f"Registration error: {e}")
        finally:
            SessionLocal.remove()

    return render_template('register.html', title='Register')

@auth_routes.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember_me') is not None
        session = SessionLocal()
        try:
            user = session.query(User).filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user, remember=remember)
                flash('Login successful!', 'success')
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('index')
                return redirect(next_page)
            else:
                flash('Invalid username or password.', 'danger')
        except Exception as e:
            flash(f'An error occurred during login: {e}', 'danger')
            print(f"Login error: {e}")
        finally:
            SessionLocal.remove()

    return render_template('login.html', title='Sign In')

@auth_routes.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))