from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import User, Favourite
from met import art_info, get_artworks, get_daily_artwork
from extensions import db, login_manager
from dotenv import load_dotenv
import os
from flask_wtf.csrf import CSRFProtect

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'fallback_dev_key')



database_url = os.getenv("DATABASE_URL")
if database_url:
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url

db.init_app(app)
login_manager.init_app(app)

csrf = CSRFProtect(app)

limiter = Limiter(app=app,key_func=get_remote_address,default_limits=[])

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()


# ------------ HELPERS ------------#

def is_strong_password(password):
    return (len(password) >= 8 and
            any(c.isupper() for c in password) and
            any(c.isdigit() for c in password))


# ------------ ROUTES ------------- #

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/daily')
def daily():
    artwork = get_daily_artwork()
    return render_template('daily.html', artwork=artwork, image_url=artwork["image_url"])

@app.route('/explore/<int:page>')
def explore(page):
    artworks = get_artworks(page)
    return render_template('explore.html', artworks=artworks, page=page)

@app.route('/artwork/<int:artwork_id>')
def artwork_detail(artwork_id):
    artwork = art_info(artwork_id)
    is_fav = False
    if current_user.is_authenticated:
        is_fav = Favourite.query.filter_by(
            user_id=current_user.id, artwork_id=artwork_id).first() is not None
    return render_template('info.html', artwork=artwork, is_fav=is_fav)

@app.route('/favourites')
@login_required
def favourite():
    favs = Favourite.query.filter_by(user_id=current_user.id).all()
    artworks = []
    for fav in favs:
        try:
            artwork = art_info(fav.artwork_id)
            artworks.append(artwork)
        except:
            continue
    return render_template('favourites.html', artworks=artworks)

@app.route('/favourites/add/<int:artwork_id>', methods=['POST'])
@login_required
def add_favourite(artwork_id):
    existing = Favourite.query.filter_by(
        user_id=current_user.id, artwork_id=artwork_id).first()
    if not existing:
        fav = Favourite(user_id=current_user.id, artwork_id=artwork_id)
        db.session.add(fav)
        db.session.commit()
    return redirect(request.referrer)

@app.route('/favourites/remove/<int:artwork_id>', methods=['POST'])
@login_required
def remove_favourite(artwork_id):
    fav = Favourite.query.filter_by(
        user_id=current_user.id, artwork_id=artwork_id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
    return redirect(request.referrer)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already taken.')
            return redirect(url_for('register'))
        if not is_strong_password(password):
            flash('Password must be 8+ characters with at least one uppercase letter and one number.')
            return redirect(url_for('register'))

        user = User(email=email, username=username, is_verified=True)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome to Kalai ")
        return redirect(url_for('home'))

    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)