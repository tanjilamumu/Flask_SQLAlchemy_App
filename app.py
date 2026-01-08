from flask import Flask, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
import boto3
import logging


app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


# SECRET KEY for login session
app.config['SECRET_KEY'] = 'secret123'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:abc12345.@database-1.c7224ew0aex5.us-east-2.rds.amazonaws.com/tasks'

db = SQLAlchemy(app)

BUCKET_NAME = 'flask-sqlalchemy-s3'

def upload_file_to_s3(file_path, file_name):
    s3 = boto3.client('s3')
    try:
        s3.upload_file(file_path, BUCKET_NAME, file_name)
        logging.info(f"File {file_name} uploaded to S3 bucket {BUCKET_NAME}")
        # RETURN the S3 URI
        return f"s3://{BUCKET_NAME}/{file_name}"
    except Exception as e:
        logging.error(f"Error uploading file to S3: {e}")
        return None

    


# ------------------ MODEL ------------------
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    s3_uri = db.Column(db.String(500) , nullable=True)  # S3 URI for the uploaded file

#with app.app_context():
   # db.create_all()

# ------------------ AUTH ------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Simple hardcoded login (assignment-friendly)
        if username == 'admin' and password == 'admin':
            session['user'] = username
            return redirect('/')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')


# ------------------ TASK ROUTES ------------------
@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')

    filter_type = request.args.get('filter')

    if filter_type == 'completed':
        tasks = Task.query.filter_by(completed=True).all()
    elif filter_type == 'uncompleted':
        tasks = Task.query.filter_by(completed=False).all()
    else:
        tasks = Task.query.all()

    return render_template('index.html', tasks=tasks, BUCKET_NAME=BUCKET_NAME)


@app.route('/add', methods=['POST'])
def add_task():
    task = request.form.get('task')
    new_task = Task(title=task)
    file = request.files('file')

    if file:
        logging.info(f"Received file: {file.filename}")
        file_path = os.path.join(basedir, file.filename)
        file.save(file_path)
        upload_file_to_s3(file_path, file.filename)
        os.remove(file_path)  # Clean up the local file after upload
        new_task.s3_uri = f"s3://{BUCKET_NAME}/{file.filename}"

        db.session.add(new_task)
        db.session.commit()

    return redirect('/')




@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    if 'user' not in session:
        return redirect('/login')

    task = Task.query.get(task_id)
    if task:
        db.session.delete(task)
        db.session.commit()
    return redirect('/')

@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    if 'user' not in session:
        return redirect('/login')

    task = Task.query.get(task_id)
    if request.method == 'POST':
        new_title = request.form.get('task')
        if task and new_title:
            task.title = new_title
            db.session.commit()
            return redirect('/')
    return render_template('edit.html', task=task)


@app.route('/toggle/<int:task_id>')
def toggle_task(task_id):
    if 'user' not in session:
        return redirect('/login')

    task = Task.query.get(task_id)
    if task:
        task.completed = not task.completed
        db.session.commit()
    return redirect('/')


# ------------------ RUN ------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)