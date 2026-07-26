from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField

class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("SIGN UP")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("LOG IN")

class CreateTravelStoryForm(FlaskForm):
    country = StringField("Country", validators=[DataRequired()])
    city = StringField("City", validators=[DataRequired()])
    title = StringField("Title", validators=[DataRequired()])
    story = CKEditorField("Story", validators=[DataRequired()])
    main_image = StringField("Story Image URL", validators=[DataRequired(), URL()])
    submit = SubmitField("Publish Story")

class CommentForm(FlaskForm):
    comment_text = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")