from flask import Flask, render_template, current_app, Blueprint, url_for, redirect, request, flash, abort, session
from markupsafe import Markup
from flask_bootstrap import Bootstrap
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

from forms import CreateTravelStoryForm, RegisterForm, LoginForm, CommentForm
from flask_login import UserMixin, LoginManager, login_user, login_required, current_user, logout_user
from functools import wraps
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(dotenv_path="/home/yuliyatestlab/travel-stories-platform/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")

print("DEBUG SUPABASE_URL:", SUPABASE_URL)
print("DEBUG SUPABASE_KEY:", SUPABASE_KEY)


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY', '8BYkEfBA6O6donzWlSihBXox7C0sKR6b')

Bootstrap(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    result = supabase.table("users").select("*").eq("id", user_id).execute()
    user_data = result.data[0] if result.data else None

    if not user_data:
        return None

    #  Create user object
    return User(
        id=user_data["id"],
        name=user_data["name"],
        email=user_data["email"],
        password=user_data["password"],
        is_admin=user_data.get("is_admin", False),
    )


class User(UserMixin):
    def __init__(self, id, name, email, password, is_admin=False):
        self.id = id
        self.name = name
        self.email = email
        self.password = password
        self.is_admin = is_admin


# Register new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        #  Check if user email is already present in the Supabase
        result = supabase.table("users").select("*").eq("email", form.email.data).execute()
        user = result.data[0] if result.data else None
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
        #  Insert new user into Supabase
        insert_result = supabase.table("users").insert({
            "name": form.name.data,
            "email": form.email.data,
            "password": hash_and_salted_password
        }).execute()

        new_user_data = insert_result.data[0]
        #  Create User object for Flask-Login
        new_user = User(
            id=new_user_data["id"],
            name=new_user_data["name"],
            email=new_user_data["email"],
            password=new_user_data["password"],
            is_admin=new_user_data.get("is_admin", False)
        )

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
        #  Check if user exists in Supabase
        result = supabase.table("users").select("*").eq("email", email).execute()
        user = result.data[0] if result.data else None
        #  Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        #  Password incorrect
        elif not check_password_hash(user["password"], password):
            flash("Password incorrect, please try again.")
            return redirect(url_for('login'))
        else:
            #  Create User object for Flask-Login
            logged_user = User(
                id=user["id"],
                name=user["name"],
                email=user["email"],
                password=user["password"],
                is_admin=user.get("is_admin", False)
            )
            login_user(logged_user)
            return redirect(url_for('get_all_stories'))

    return render_template("login.html", form=form, current_user=current_user)

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('get_all_stories'))

@app.route('/')
def get_all_stories():
    # Query Supabase for all the stories. Convert the data to a python list.
    result = supabase.table("stories").select("*").order("date").execute()
    stories = result.data if result.data else []
    # Attach author name to each story
    for story in stories:
        author_result = supabase.table("users").select("name").eq("id", story["author_id"]).execute()
        story["author_name"] = author_result.data[0]["name"] if author_result.data else "Unknown"
    return render_template("index.html", all_stories=stories, current_user=current_user)

@app.route('/story/<int:story_id>', methods=["GET", "POST"])
def show_story(story_id):
    #  Retrieve a BlogPost from the database based on the post_id.
    result = supabase.table("stories").select("*").eq("id", story_id).execute()
    requested_story = result.data[0] if result.data else None

    # Attach author name
    author_result = supabase.table("users").select("name").eq("id", requested_story["author_id"]).execute()
    requested_story["author_name"] = author_result.data[0]["name"] if author_result.data else "Unknown"

    if not requested_story:
        abort(404)

    #  Add the CommentForm to the route
    comment_form = CommentForm()

    if comment_form.validate_on_submit() and current_user.is_authenticated:
        new_comment = Comment(
            comment_text=comment_form.comment_text.data,
            comment_author=current_user,
            parent_story=requested_story,
        )
        db.session.add(new_comment)
        db.session.commit()
        db.session.refresh(requested_story)
        return redirect(url_for("show_story", story_id=story_id))

    #  Download comments from DB
    comments = db.session.execute(
        db.select(Comment).where(Comment.story_id == story_id)
    ).scalars().all()
        new_comment_text = comment_form.comment_text.data
        #  Insert comment into Supabase
        insert_result = supabase.table("comments").insert({
            "comment_text": new_comment_text,
            "comment_author_id": current_user.id,
            "story_id": story_id,
        }).execute()

        return redirect(url_for("show_story", story_id=story_id))

    #  Retrieve comment for this story
    comments_result = supabase.table("comments").select("*").eq("story_id", story_id).execute()
    comments = comments_result.data if comments_result.data else []

    #  Attach author name to each comment
    for comment in comments:
        author_result = supabase.table("users").select("name").eq("id", comment["comment_author_id"]).execute()
        comment["author_name"] = author_result.data[0]["name"] if author_result.data else "Unknown"

    return render_template("story.html", story=requested_story, comments=comments, current_user=current_user, form=comment_form)

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
        #  Prepare story data
        new_story = {
            "country": form.country.data,
            "city": form.city.data,
            "title": form.title.data,
            "story": form.story.data,
            "main_image": form.main_image.data,
            "author_id": current_user.id,
            "date": date.today().strftime("%B %d, %Y"),
        }
        #  Insert story into Supabase
        result = supabase.table("stories").insert(new_story).execute()
        return redirect(url_for('get_all_stories'))

    return render_template("edit-story.html", form=form, current_user=current_user)

# Editing an existing story
@app.route('/edit-story/<int:story_id>', methods=['GET', 'POST'])
@admin_only
def edit_story(story_id):
    #  Retrieve story from Supabase
    result = supabase.table("stories").select("*").eq("id", story_id).execute()
    story = result.data[0] if result.data else None

    if not story:
        abort(404)

    #  Pre-fill form with existing story data
    edit_form = CreateTravelStoryForm(
        country=story["country"],
        city=story["city"],
        title=story["title"],
        story=story["story"],
        main_image=story["main_image"],
    )
    #  Handle form submission
    if edit_form.validate_on_submit():
        updated_story = {
            "country": edit_form.country.data,
            "city": edit_form.city.data,
            "title": edit_form.title.data,
            "story": edit_form.story.data,
            "main_image": edit_form.main_image.data,
        }

        #  Update story in Supabase
        supabase.table("stories").update(updated_story).eq("id", story_id).execute()
        return redirect(url_for('show_story', story_id=story_id))
    return render_template("edit-story.html", form=edit_form, is_edit=True, current_user=current_user)

# Delete story
@app.route('/delete/<int:story_id>')
@admin_only
def delete_story(story_id):
    #  Retrieve story from Supabase
    result = supabase.table("stories").select("*").eq("id", story_id).execute()
    story_to_delete = result.data[0] if result.data else None

    if not story_to_delete:
        abort(404)

    #  Delete story from Supabase
    supabase.table("stories").delete().eq("id", story_id).execute()
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

#  Test Db
@app.route("/supabase-select")
def supabase_select():
    try:
        response = supabase.table("stories").select("*").execute()
        return {"data": response.data}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        debug=False
    )