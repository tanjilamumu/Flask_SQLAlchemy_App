from flask import Flask, json, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
import boto3
import logging


app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


# SECRET KEY for login session hjh
app.config['SECRET_KEY'] = 'secret123'

basedir = os.path.abspath(os.path.dirname(__file__))
db_name = 'tasks.db'

def get_db_secret(secret_name, region_name='us-east-2'):
    client = boto3.client('secretsmanager', region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except Exception as e:
        logging.error(f"Error retrieving secret {secret_name}: {e}")
        return None
    
    
secret = get_db_secret('prod/rds/mydb')

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{secret['username']}:{secret['password']}@{secret['host']}/{secret['dbname']}"
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
    s3_url = db.Column(db.String(500) , nullable=True)  # S3 URI for the uploaded file

with app.app_context():
   db.create_all()

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

#add task route
@app.route('/add', methods=['POST'])
def add_task():
    task = request.form.get('task')
    new_task = Task(title=task)
    file = request.files.get('file')

    if file:
        logging.info(f"Received file: {file.filename}")
        file_path = os.path.join(basedir, file.filename)
        file.save(file_path)

        
        upload_file_to_s3(file_path, file.filename)
        os.remove(file_path)  # Clean up the local file after upload
        new_task.s3_url = f"s3://{BUCKET_NAME}/{file.filename}"

        db.session.add(new_task)
        db.session.commit()

    return redirect('/')



#Delete task route
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