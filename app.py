from flask import Flask, render_template, current_app, Blueprint, url_for, redirect, request, flash, abort
from flask_gravatar import Gravatar
from markupsafe import Markup
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, ForeignKey, Boolean
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

from forms import CreateTravelStoryForm, RegisterForm, LoginForm, CommentForm
from flask_login import UserMixin, LoginManager, login_user, login_required, current_user
from functools import wraps



app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///travel_stories.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

#  CONFIGURE TABLE
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    #  The "author" refers a List of BlogPost objects attached to each User
    stories = relationship("TravelStory", back_populates="author")

class TravelStory(db.Model):
    __tablename__ = "stories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #  Geography
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    #  Main information
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    story: Mapped[str] = mapped_column(Text, nullable=False)
    # Photo
    main_image: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    #  Create Foreign Key, "users.id" the users refers to the tablename of User
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    #  Create reference to the User object. the "posts" refers to the posts property in the User class
    author = relationship("User", back_populates="stories")


with app.app_context():
    db.create_all()

# Register new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        #  Check if user email is already present in the database
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if user:
            #  User already exists
            flash("You've already signed up with that email, log in instead")
            return redirect(url_for('login'))

        # Hashing and Salting the password entered by user
        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            name=form.name.data,
            email = form.email.data,
            password = hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        #  Authenticate the user with Flask-Login
        login_user(new_user)
        return redirect(url_for('get_all_stories'))
    return render_template('register.html', form=form, current_user=current_user)

# Retrieve a user from the database based on their email
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == email))
        # Email in db is unique so will only have one result.
        user = result.scalar()
        #  Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        #  Password incorrect
        elif not check_password_hash(user.password, password):
            flash("Password incorrect, please try again.")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_stories'))

    return render_template("login.html", form=form, current_user=current_user)

@app.route('/logout')
def logout():
    return redirect(url_for('get_all_stories'))

@app.route('/')
def get_all_stories():
    # Query the database for all the stories. Convert the data to a python list.
    result = db.session.execute(db.select(TravelStory).order_by(TravelStory.date))
    stories = result.scalars().all()
    return render_template("index.html", all_stories=stories, current_user=current_user)

@app.route('/story/<int:story_id>')
def show_story(story_id):
    #  Retrieve a BlogPost from the database based on the post_id.
    requested_story = db.get_or_404(TravelStory, story_id)
    #  Add the CommentForm to the route
    comment_form = CommentForm()
    return render_template("story.html", story=requested_story, current_user=current_user, form=comment_form)

#  Admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return abort(403)
        # If is_admin is false then return abort with 403 error
        if not current_user.is_admin:
            return abort(403)
        #  Otherwise continue with the rote function
        return f(*args, **kwargs)
    return decorated_function

@app.route('/new-story', methods=['GET', 'POST'])
@login_required
def add_new_story():
    form = CreateTravelStoryForm()
    if form.validate_on_submit():
        new_story = TravelStory(
            country=form.country.data,
            city=form.city.data,
            title = form.title.data,
            story = form.story.data,
            main_image=form.main_image.data,
            author = current_user,
            date = date.today().strftime("%B %d, %Y"),
        )
        db.session.add(new_story)
        db.session.commit()
        return redirect(url_for('get_all_stories'))
    return render_template("edit-story.html", form=form, current_user=current_user)

# Editing an existing story
@app.route('/edit-story/<int:story_id>', methods=['GET', 'POST'])
@admin_only
def edit_story(story_id):
    story = db.get_or_404(TravelStory, story_id)
    edit_form = CreateTravelStoryForm(
        country=story.country,
        city=story.city,
        title=story.title,
        story=story.story,
        main_image=story.main_image,
    )
    if edit_form.validate_on_submit():
        story.country = edit_form.country.data
        story.city = edit_form.city.data
        story.title = edit_form.title.data
        story.story = edit_form.story.data
        story.main_image = edit_form.main_image.data

        db.session.commit()
        return redirect(url_for('show_story', story_id=story.id))
    return render_template("edit-story.html", form=edit_form, is_edit=True, current_user=current_user)

# Delete story
@app.route('/delete/<int:story_id>')
@admin_only
def delete_story(story_id):
    story_to_delete = db.get_or_404(TravelStory, story_id)
    db.session.delete(story_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_stories'))


@app.route('/about')
def about():
    return render_template('about.html', current_user=current_user)

@app.route('/contact')
def contact():
    return render_template('contact.html', current_user=current_user)
@app.route('/admin')
@admin_only
def admin_panel():
    pass

if __name__ == "__main__":
    app.run(debug=True)