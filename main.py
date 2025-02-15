from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from flask_mail import Mail
import os
from werkzeug.utils import secure_filename
import math

with open('config.json', 'r') as c:
    params = json.load(c)["params"]

local_server = True

app = Flask(__name__)

app.secret_key = params['s_key']
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = 587,
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME = params["gmail_user"],
    MAIL_PASSWORD = params["gmail_password"]
)
mail = Mail(app)

if local_server:
    app.config["SQLALCHEMY_DATABASE_URI"] = params["local_uri"]
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params["prod_uri"]
  # Ensure correct DB name
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)  # Initialize database

class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(320), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)  # Use DateTime for better handling

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60), nullable=False)
    subheading = db.Column(db.String(60), nullable=False)
    content = db.Column(db.String(3000), nullable=False)
    by = db.Column(db.String(15), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)  # Use DateTime for better handling
    slug = db.Column(db.String(60), nullable=False)
    img_file = db.Column(db.String(15), nullable=True)

@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(params['no_of_posts']))
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = posts[(page-1)*int(params['no_of_posts']):(page-1)*int(params['no_of_posts'])+ int(params['no_of_posts'])]
    if page==1:
        prev = "#"
        next = "/?page="+ str(page+1)
    elif page==last:
        prev = "/?page="+ str(page-1)
        next = "#"
    else:
        prev = "/?page="+ str(page-1)
        next = "/?page="+ str(page+1)
    
    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)

@app.route("/about")
def about():
    return render_template('about.html', params=params)

@app.route("/post/<string:post_slug>", methods = ['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug = post_slug).first()
    return render_template('post.html', params=params, post = post)

@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':  # Fix conditional check
        # Retrieve form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        
        # Create entry and add to database
        entry = Contacts(name=name, email=email, phone=phone, message=message)
        db.session.add(entry)
        db.session.commit()
        mail.send_message(
            subject='New message from ' + name,
            sender=params["gmail_user"],  # ✅ Use your own Gmail as sender
            recipients=[params["gmail_user"]],  # ✅ Ensure recipients is a list
            body=f"From: {name} ({email})\n\n{message}\n\nPhone: {phone}"
        )
        flash("Thanks for submitting your details. We will get back to you soon", "success")
    return render_template('contact.html', params=params)

@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    error = None  # Initialize error message
    if 'user' in session and session['user'] == params['admin_user']:
        posts = Posts.query.all()
        return render_template('dashboard.html', params=params, posts=posts)

    if request.method == "POST":
        username = request.form.get("uname")
        userpass = request.form.get("password")

        if username == params['admin_user'] and userpass == params['admin_password']:
            session['user'] = username  # Set session variable
            posts = Posts.query.all()
            return render_template('dashboard.html', params=params, posts=posts)
        else:
            error = "Invalid username or password. Please try again."

    return render_template('login.html', params=params, error=error)


@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def edit(sno):
    if 'user' in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            box_title = request.form.get('title')
            subheading = request.form.get('subheading')
            content = request.form.get('content')
            by = request.form.get('by')
            slug = request.form.get('slug')
            img_file = request.form.get('img_file')
            date = datetime.utcnow()

            if sno=='0':
                post = Posts(title=box_title, slug=slug, content=content, by=by, subheading=subheading, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
                return redirect('/dashboard')
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = box_title
                post.subheading = subheading
                post.slug = slug
                post.content = content
                post.by = by
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/edit/'+sno)
        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post, sno=sno)
    
@app.route("/uploader" , methods=['GET', 'POST'])
def uploader():
    if "user" in session and session['user']==params['admin_user']:
        if request.method=='POST':
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "Uploaded successfully!"

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/dashboard')

@app.route("/delete/<string:sno>" , methods=['GET', 'POST'])
def delete(sno):
    if "user" in session and session['user']==params['admin_user']:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect("/dashboard")

if __name__ == "__main__":
    app.run(debug=True)
