# from calendar import error

from flask import Flask, render_template, url_for, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import column, false, Select
from sqlalchemy.sql.functions import current_user
from werkzeug.security import generate_password_hash,check_password_hash
from flask_login import login_user, logout_user, login_required, current_user, LoginManager, UserMixin
from datetime import datetime, timezone
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired
# import os






# ✅ SET ENVIRONMENT VARIABLES HERE:

app = Flask(__name__, instance_relative_config=True)
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']= False
# app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

app.config['SECRET_KEY'] = 'hello'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirects to login page if not logged in


class User(db.Model,UserMixin):
   id= db.Column(db.Integer,primary_key= True)
   username = db.Column(db.String(80),nullable= False,unique = True)
   email = db.Column(db.String(80), nullable=False,unique =True )
   password = db.Column(db.String(80), nullable=False ,unique =True)
   author = db.Relationship('Blog', back_populates='blog')
   likes = db.relationship('Like', backref='user', lazy='dynamic')


class Blog(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    title = db.Column(db.String(500),nullable = False, unique = True)
    content= db.Column(db.String(5000),nullable= False, unique= True)
    blog = db.Relationship('User', back_populates='author')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_posted = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    likes = db.relationship('Like', backref='blog', lazy='dynamic')
    comments = db.relationship('Comment', backref='post', lazy=True,cascade="all, delete-orphan")



class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('blog.id'), nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('blog.id'), nullable=False)

    # Relationship
    user = db.relationship('User', backref='comments')
    # post = db.relationship('Blog', backref='comments')


class CommentForm(FlaskForm):
    content = TextAreaField('', validators=[DataRequired()])
    submit = SubmitField('Post Comment',render_kw={'class': 'comment-btn'})


with app.app_context():
  db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return  User.query.get(int(user_id))


@app.route('/',methods = ['GET','POST'])
def register():
  if request.method == 'POST':
     name = request.form.get('name')
     email = request.form.get('email')
     password = request.form.get('password')
     hashed_password = generate_password_hash(password)

     new_user =User(username= name,email= email,password= hashed_password)
     db.session.add(new_user)
     db.session.commit()
     login_user(new_user)
     return redirect(url_for('blog'))
  return render_template('register.html')

@app.route('/login', methods =['GET','POST'])
def login():
 if request.method == 'POST':
     email= request.form.get('email')
     password = request.form.get('password')
     check_email = db.Select(User).where(User.email == email)
     user = db.session.execute(check_email).scalar()
     if user:
          if check_password_hash(user.password,password):
            login_user(user)
            return redirect(url_for('blog'))
          else:
            flash('Incorrect Password,Try Again','error')
     else:
         flash("Email doesn't exist",'error')
 return render_template('login.html')

@app.route('/blog')
@login_required
def blog():
    select = db.Select(Blog)
    all_posts = db.session.execute(select).scalars()
    return render_template('blog.html', current_user= current_user,post = all_posts)

@app.route('/create_post',methods=['GET','POST'])
@login_required
def create_post():
  if request.method == 'POST':
    title = request.form.get('title')
    content = request.form.get('content')
    new_blog = Blog(title = title,content = content,user_id = current_user.id)
    db.session.add(new_blog)
    db.session.commit()
    return redirect(url_for('blog'))
  return render_template('create_post.html')

@app.route('/edit_post/<edit_id>',methods = ['GET','POST'])
@login_required
def edit_post(edit_id):
    particular_post = Select(Blog).where(Blog.id == edit_id)
    edited_post= db.session.execute(particular_post).scalar()

    if edited_post.user_id != current_user.id:
        return "Forbidden", 403

    if request.method =='POST':
        my_title = request.form.get('title')
        content = request.form.get('content')
        edited_post.title = my_title
        edited_post.content = content
        db.session.commit()
        return redirect(url_for('blog'))
    return render_template('edit_post.html',post = edited_post)


@app.route('/delete_post/<post_id>')
@login_required
def delete_post(post_id):
    particular_post = Select(Blog).where(Blog.id == post_id)
    executed_post =  db.session.execute(particular_post).scalar()
    db.session.delete(executed_post)
    db.session.commit()
    return redirect(url_for('blog'))

@app.route('/read_more/<post_id>')
@login_required
def read_more(post_id):
    requested_post = db.session.execute(Select(Blog).where(Blog.id == post_id)).scalar()
    form = CommentForm()
    return render_template('read_more.html', post=requested_post,current_user= current_user, form= form)
@app.route('/log_out')
@login_required
def log_out():
    logout_user()
    flash('You have been logged out.','success')
    return redirect(url_for('register'))
@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    particular_post = Blog.query.get_or_404(post_id)
    like = Like.query.filter_by(user_id=current_user.id,post_id=particular_post.id).first()

    if like:
        # User already liked — remove like (unlike)
        db.session.delete(like)
    else:
        # User hasn't liked yet — add like
        new_like = Like(user_id=current_user.id, post_id=particular_post.id)
        db.session.add(new_like)

    db.session.commit()
    return redirect(request.referrer or url_for('blog'))  # reload page


@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def comment_post(post_id):
    form = CommentForm()
    post = Blog.query.get_or_404(post_id)

    if form.validate_on_submit():
        comment = Comment(content=form.content.data, user_id=current_user.id, post_id=post.id)
        db.session.add(comment)
        db.session.commit()


    return redirect(url_for('read_more', post_id=post.id, form=form))


if __name__ == '__main__':
  app.run(debug=True)


