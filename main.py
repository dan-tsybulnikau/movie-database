from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# API settings for Movie DB
movie_db_api_key = os.environ.get('MOVIE_DB_API_KEY')
movie_db_endpoint = 'https://api.themoviedb.org/3'
# Starting up Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_TOKEN')
# Connecting Bootstrap
Bootstrap(app)
# Connecting SQLAlchemy DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Creating blueprint for records in DB
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(250), nullable=True)
    rating = db.Column(db.String(250), nullable=True)
    ranking = db.Column(db.String(250), nullable=True)
    review = db.Column(db.String(250), nullable=True)
    img_url = db.Column(db.String(250), nullable=True)


# Creating table in DB
db.create_all()


# Creating WTForm for movie updating
class UpdateForm(FlaskForm):
    new_rating = StringField('Your rating out of 10, eg. 7.5', validators=[DataRequired()])
    new_review = StringField('Your review', validators=[DataRequired()])
    submit = SubmitField('Done')


# Creating WTForm for movie adding
class AddForm(FlaskForm):
    movie_title = StringField('Movie Title', validators=[DataRequired()])
    submit = SubmitField('Add movie')


# Ordering movie DB by rating, changing movie ranking relatively to its rating
# Saving current ranking scheme to the DB and passing it render in index.html
@app.route("/")
def home():
    # Sorting db on homepage (by default it is sorted by id from oldest to newest)
    sorting_scheme = {
        'rating': Movie.query.order_by(Movie.rating).all(),
        'date': Movie.query.order_by(Movie.id).all(),
        'year': Movie.query.order_by(Movie.year).all(),
        'alphabet': Movie.query.order_by(Movie.title).all(),
    }
    try:
        type_of_sort = request.args['sorted']
    except KeyError:
        type_of_sort = 'date'
    finally:
        ordered_db = sorting_scheme[type_of_sort]
        for i in range(len(ordered_db)):
            ordered_db[i].ranking = len(ordered_db) - i
        db.session.commit()
        return render_template("index.html", database=ordered_db, sorted_by=type_of_sort.title())


# Editing records
@app.route('/edit', methods=['GET', 'POST'])
def edit():
    # Receiving movie id from index.html href (/edit?id=X)
    movie_id = request.args['id']
    movie_to_update = Movie.query.get(movie_id)
    movie_form = UpdateForm()
    # If request method is 'POST' (submitting the Update Form with no errors)
    if movie_form.validate_on_submit():
        movie_to_update.rating = movie_form.new_rating.data
        movie_to_update.review = movie_form.new_review.data
        db.session.commit()
        return redirect(url_for('home'))
    else:
        # If request method is 'GET' (simple opening of the url /edit.html)
        # Sending Update Form and particular movie to render
        return render_template('edit.html', form=movie_form, movie=movie_to_update)


# Deleting record
@app.route('/delete')
def delete():
    # Receiving movie id from index.html href (/delete?id=X)
    movie_id = request.args['id']
    movie_to_delete = Movie.query.get(movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/add', methods=['GET', 'POST'])
def add():
    add_form = AddForm()
    # If request method is 'POST' (submitting the Update Form with no errors)
    if add_form.validate_on_submit():
        new_movie_title = add_form.movie_title.data
        # Sending request to Movie DB in order to receive a list of movies
        # Containing specified title from Add form
        response = requests.get(url=f'{movie_db_endpoint}/search/movie', params={
            'api_key': movie_db_api_key,
            'query': new_movie_title,
            'include_adult': True,
        })
        movie_list = response.json()['results']
        return render_template('select.html', movies=movie_list)
    else:
        # If request method is 'GET' (simple opening of the url /add.html)
        # Sending Add Form and particular movie to render
        return render_template('add.html', form=add_form)


@app.route('/upload')
def upload_movie():
    # Receiving movie_db_id from index.html href (/upload_movie?movie_db_id=X)
    movie_db_id = request.args['movie_db_id']
    # Sending request to Movie DB in order to receive movie information
    response = requests.get(url=f'{movie_db_endpoint}/movie/{movie_db_id}', params={
        'api_key': movie_db_api_key,
    })
    movie_data = response.json()
    # Creating new record in DB from response
    new_movie = Movie(
        title=movie_data['title'],
        year=movie_data['release_date'][:4],
        description=movie_data['overview'],
        rating=None,
        ranking=None,
        review=None,
        img_url=f'https://image.tmdb.org/t/p/w500/{movie_data["poster_path"]}'
    )
    db.session.add(new_movie)
    db.session.commit()
    movie_form = UpdateForm()
    # Applying edit function to newly added movie
    return render_template('edit.html', form=movie_form, movie=new_movie)


if __name__ == '__main__':
    app.run(debug=True)
