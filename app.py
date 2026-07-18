from flask import Flask, render_template
import requests


posts = requests.get("https://api.npoint.io/9ebec3d8cc424259a72").json()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/post/<int:index>')
def get_posts(index):
    requested_post = None
    for blog_post in post_objects:
        if blog_post.post_id == index:
            requested_post = blog_post
    return render_template("post.html", post=requested_post)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == "__main__":
    app.run(debug=True)