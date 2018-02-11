from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, g
#from data import Articles
from flask_mysqldb import MySQL
from wtforms.form import Form 
from wtforms.fields import StringField, TextAreaField, PasswordField
from wtforms import validators
from passlib.hash import sha256_crypt
from functools import wraps
import pdb


app = Flask(__name__)

# config MySQL
app.config['MYSQL_HOST'] 				= 'localhost'
app.config['MYSQL_USER'] 				= 'root'
app.config['MYSQL_PASSWORD'] 		= 'Opeyemi1'
app.config['MYSQL_DB'] 					= 'flaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#Initialize MySQL
mysql = MySQL(app)

#Articles = Articles()

#Home
@app.route('/')
def index():
	return render_template('home.html')

#About
@app.route('/about')
def about():
	return render_template('about.html')

#Articles
@app.route('/articles')
def articles():
	# create a cursor
	cur = mysql.connection.cursor()

	#get articles
	results = cur.execute("SELECT * from articles")

	articles = cur.fetchall() # fetch all in dictionary form

	if results > 0:
		return render_template('articles.html', articles=articles)
	else:
		msg = 'No articles found'
		return render_template('articles.html', msg=msg)

	#close connection
	cur.close()

#Single article index
@app.route('/article/<string:id>/')
def article(id):
	# create a cursor
	cur = mysql.connection.cursor()

	#get article by id
	result = cur.execute("SELECT * from articles WHERE id = %s", [id])

	article = cur.fetchone() # fetch only one from db

	return render_template('article.html', article=article)

	#close connection
	cur.close()

# Register form class		
class RegisterForm(Form):
	name = StringField('Name', [validators.length(min=1, max=50)])
	username = StringField('Username', [validators.length(min=4, max=25)])
	email = StringField('Email', [validators.length(min=6, max=50)])
	password = PasswordField('Password', [
		validators.InputRequired(),
		validators.EqualTo('confirm', message='Passwords do not match')
	])
	confirm = PasswordField('Confirm Password')

#  User register
@app.route('/register', methods=['GET', 'POST'])   #default for route is GET, need to add POST request accpetance.
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))

		# create cursor
		cur = mysql.connection.cursor()

		# execute query
		cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

		# commit to db
		mysql.connection.commit()

		#close connection
		cur.close()

		# send flash message after registration
		flash('You are now registered and can log in', 'success')

		return redirect(url_for('index'))


	return render_template('register.html', form=form)

#User login
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		#Get form field
		username = request.form['username'] #getting dictionary instead of named tuple, wtf not used.
		password_candidate = request.form['password']

		# create a cursor
		cur = mysql.connection.cursor()

		#Get user by username
		result = cur.execute("SELECT * from users WHERE username = %s", [username])
		# does this protect against injection?

		#check result
		if result > 0:
			# Get the stored hash
			data = cur.fetchone()
			password = data['password']

			# compare the passwords
			if sha256_crypt.verify(password_candidate, password):
				#app.logger.info('PASSWORD MATCHED')
				# passed
				session['logged_in'] = True
				session['username'] = username

				flash('You are now logged_in', 'success')
				return redirect(url_for('dashboard'))

			else:
				error = 'Invalid login'
				#pdb.set_trace()
				return render_template('login.html', error=error)
				#app.logger.info('PASSWORD NOT MATCHED')
			# close connection
			cur.close()
		else:
			error = 'Username not found'
			return render_template('login.html', error=error)
			#app.logger.info('NO USER')

	return render_template('login.html')

#check if user is logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorised, Please login', 'danger')
			return redirect(url_for('login'))
	return wrap

#Logout
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out')
	return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():

	# create a cursor
	cur = mysql.connection.cursor()

	#get articles
	results = cur.execute("SELECT * from articles")

	articles = cur.fetchall() # fetch all in dictionary form

	if results > 0:
		return render_template('dashboard.html', articles=articles)
	else:
		msg = 'No articles found'
		return render_template('dashboard.html', msg=msg)

	#close connection
	cur.close()


# Article form class		
class ArticleForm(Form):
	title = StringField('Title', [validators.length(min=1, max=200)])
	body = TextAreaField('Body', [validators.length(min=30)])

# Add Article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
	form = ArticleForm(request.form)
	if request.method == 'POST' and form.validate():
		title = form.title.data
		body = form.body.data
		author = session['username']

		# create a cursor
		cur = mysql.connection.cursor()

		# execute
		cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, author))

		# commit to db
		mysql.connection.commit()

		#close connection
		cur.close()

		# send flash message after registration
		flash('Article created', 'success')

		return redirect(url_for('dashboard'))


	return render_template('add_article.html', form=form)

# edit Adticle
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
	#create cursor
	cur = mysql.connection.cursor()

	#get article by id
	result = cur.execute("SELECT * from articles WHERE id = %s", [id])

	article = cur.fetchone() # fetch only one from db

	#Get form
	form = ArticleForm(request.form)

	#Populate article form fields
	form.title.data = article['title']
	form.body.data = article['body']

	if request.method == 'POST' and form.validate():
		title = request.form['title']
		body = request.form['body']

		# create a cursor
		cur = mysql.connection.cursor()

		# update table
		cur.execute("UPDATE articles SET title = %s, body = %s WHERE id = %s", (title, body, [id]))

		# commit to db
		mysql.connection.commit()

		#close connection
		cur.close()

		# send flash message after registration
		flash('Article Updated', 'success')

		return redirect(url_for('dashboard'))


	return render_template('edit_article.html', form=form)

@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):

	# create a cursor
	cur = mysql.connection.cursor()

	# update table
	cur.execute("DELETE from articles WHERE id = %s", [id])

	# commit to db
	mysql.connection.commit()

	#close connection
	cur.close()

	# send flash message after registration
	flash('Article Deleted', 'success')
	return redirect(url_for('dashboard'))


if __name__ == '__main__':
	# if secret key error shows up, set secret key
	app.secret_key='scret123'
	app.run(debug=True)