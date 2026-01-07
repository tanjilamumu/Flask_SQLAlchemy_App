from flask import Flask, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# SECRET KEY for login session
app.config['SECRET_KEY'] = 'secret123'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:abc12345.@database-1.c7224ew0aex5.us-east-2.rds.amazonaws.com/tasks'

db = SQLAlchemy(app)

# ------------------ MODEL ------------------
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)


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

    return render_template('index.html', tasks=tasks)


@app.route('/add', methods=['POST'])
def add_task():
    if 'user' not in session:
        return redirect('/login')

    task = request.form.get('task')
    if task:
        new_task = Task(title=task)
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