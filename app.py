from flask import Flask, render_template, current_app, Blueprint, url_for, redirect
from flask_gravatar import Gravatar
from flask_login import LoginManager
from markupsafe import Markup
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from datetime import date
from forms import CreatePostForm, RegisterForm
from flask_login import UserMixin


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap(app)

ckeditor = CKEditor(app)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

#  CONFIGURE TABLE
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

class User(db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)


with app.app_context():
    db.create_all()

# Register new user
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(
            email = form.email.data,
            password = form.password.data,
            name = form.name.data
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('get_all_posts'))
    return render_template('register.html', form=form)
@app.route('/')
def get_all_posts():
    # Query the database for all the posts. Convert the data to a python list.
    result = db.session.execute(db.select(BlogPost).order_by(BlogPost.date))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)

@app.route('/post/<int:post_id>')
def show_post(post_id):
    #  Retrieve a BlogPost from the database based on the post_id.
    requested_post = db.get_or_404(BlogPost, post_id)
    return render_template("post.html", post=requested_post)

@app.route('/new-post', methods=['GET', 'POST'])
def add_new_post():
    form = CreatePostForm
    if form.validate_on_submit():
        new_post = BlogPost(
            title = form.title.data,
            subtitle = form.subtitle.data,
            body = form.body.data,
            img_url=form.img_url.data,
            author = form.author.data,
            date = date.today().strftime("%B %d, %Y"),
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('get_all_posts'))
    return render_template("make-post.html", form=form)

# Editing an existing post
@app.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body,
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_post.img_url.data
        post.author = edit_post.author.data
        post.body = edit_form.body.data

        db.session.commit()
        return redirect(url_for('show_post', post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)

# Delete post
@app.route('/delete/<int:post_id>')
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == "__main__":
    app.run(debug=True)