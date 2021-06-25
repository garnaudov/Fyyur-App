# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
from sqlalchemy import func
from flask_migrate import Migrate
import dateutil.parser
import babel
import sys
from flask_sqlalchemy import SQLAlchemy
import logging
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_moment import Moment
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object("config")
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

from models import *

# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format="medium"):
    date = dateutil.parser.parse(value)
    if format == "full":
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == "medium":
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters["datetime"] = format_datetime

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route("/")
def index():
    return render_template("pages/home.html")


#  Venues
#  ----------------------------------------------------------------


@app.route("/venues")
def venues():
    locals = []
    venues = Venue.query.all()
    places = Venue.query.distinct(Venue.city, Venue.state).all()
    for place in places:
        locals.append(
            {
                "city": place.city,
                "state": place.state,
                "venues": [
                    {
                        "id": venue.id,
                        "name": venue.name,
                        "num_upcoming_shows": len(
                            [
                                show
                                for show in venue.shows
                                if show.start_time > datetime.now()
                            ]
                        ),
                    }
                    for venue in venues
                    if venue.city == place.city and venue.state == place.state
                ],
            }
        )
    return render_template("pages/venues.html", areas=locals)


@app.route("/venues/search", methods=["POST"])
def search_venues():

    search_term = request.form.get("search_term", "")
    search_result = (
        db.session.query(Venue).filter(Venue.name.ilike(f"%{search_term}%")).all()
    )
    data = []

    for result in search_result:
        data.append(
            {
                "id": result.id,
                "name": result.name,
                "num_upcoming_shows": len(
                    db.session.query(Show)
                    .filter(Show.venue_id == result.id)
                    .filter(Show.start_time > datetime.now())
                    .all()
                ),
            }
        )

    response = {"count": len(search_result), "data": data}
    return render_template(
        "pages/search_venues.html",
        results=response,
        search_term=request.form.get("search_term", ""),
    )


@app.route("/venues/<int:venue_id>")
def show_venue(venue_id):

    venue = Venue.query.get_or_404(venue_id)
    upcoming_shows = []
    past_shows = []
    shows = (
        db.session.query(Show)
        .join(Venue, Venue.id == Show.venue_id)
        .filter(Venue.id == venue_id)
        .all()
    )
    for show in shows:
        temp_show = {
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M"),
        }
        if show.start_time <= datetime.now():
            past_shows.append(temp_show)
        else:
            upcoming_shows.append(temp_show)

    venue_object_with_shows = {
        "id": venue.id,
        "name": venue.name,
        "city": venue.city,
        "address": venue.address,
        "phone": venue.phone,
        "genres": venue.genres,
        "facebook_link": venue.facebook_link,
        "website_link": venue.website_link,
        "image_link": venue.image_link,
        "seeking_talent": venue.seeking_talent,
        "upcoming_shows": upcoming_shows,
        "past_shows": past_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template("pages/show_venue.html", venue=venue_object_with_shows)


#  Create Venue
#  ----------------------------------------------------------------


@app.route("/venues/create", methods=["GET"])
def create_venue_form():
    form = VenueForm()
    return render_template("forms/new_venue.html", form=form)


@app.route("/venues/create", methods=["POST"])
def create_venue_submission():
    form = VenueForm(request.form, meta={"csrf": False})
    if form.validate():
        try:
            venueObj = Venue(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                address=form.address.data,
                phone=form.phone.data,
                genres=form.genres.data,
                facebook_link=form.facebook_link.data,
                image_link=form.image_link.data,
                website_link=form.website_link.data,
                seeking_talent=form.seeking_talent.data,
                seeking_description=form.seeking_description.data,
            )
            db.session.add(venueObj)
            db.session.commit()
            flash("Venue " + form.name.data + " was successfully listed!")
        except ValueError as e:
            print(e)
            db.session.rollback()
            flash(
                "An error occurred. Venue " + form.name.data + " could not be listed."
            )
        finally:
            db.session.close()
    else:
        message = []
        for field, errors in form.errors.items():
            message.append(field + ": (" + "|".join(errors) + ")")
        flash("Entered data for the venue is not valid.")
    return render_template("pages/home.html")


@app.route("/venues/<int:venue_id>", methods=["DELETE"])
def delete_venue(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
        flash("Venue is successfully deleted!")
    except:
        db.session.rollback()
    finally:
        db.session.close()
    return None


#  Artists
#  ----------------------------------------------------------------
@app.route("/artists")
def artists():
    data = db.session.query(Artist).all()

    return render_template("pages/artists.html", artists=data)


@app.route("/artists/search", methods=["POST"])
def search_artists():
    search_term = request.form.get("search_term", "")
    search_result = (
        db.session.query(Artist).filter(Artist.name.ilike(f"%{search_term}%")).all()
    )
    data = []

    for result in search_result:
        num_upcoming_shows = len(
            db.session.query(Show)
            .filter(Show.artist_id == result.id)
            .filter(Show.start_time > datetime.now())
            .all()
        )

        data.append(
            {
                "id": result.id,
                "name": result.name,
                "num_upcoming_shows": num_upcoming_shows,
            }
        )

    responseResult = {"count": len(search_result), "data": data}
    return render_template(
        "pages/search_artists.html",
        results=responseResult,
        search_term=request.form.get("search_term", ""),
    )


@app.route("/artists/<int:artist_id>")
def show_artist(artist_id):
    artist = db.session.query(Artist).get_or_404(artist_id)
    upcoming_shows = []
    past_shows = []

    shows = (
        db.session.query(Show)
        .join(Artist, Artist.id == Show.artist_id)
        .filter(Artist.id == artist_id)
        .all()
    )

    for show in shows:
        temp_show = {
            "venue_id": show.venue_id,
            "venue_name": show.venue.name,
            "venue_image_link": show.venue.image_link,
            "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M"),
        }
        if show.start_time <= datetime.now():
            past_shows.append(temp_show)
        else:
            upcoming_shows.append(temp_show)

    atist_object_with_shows = {
        "id": artist.id,
        "name": artist.name,
        "city": artist.city,
        "phone": artist.phone,
        "genres": artist.genres,
        "facebook_link": artist.facebook_link,
        "website_link": artist.website_link,
        "image_link": artist.image_link,
        "seeking_venue": artist.seeking_venue,
        "upcoming_shows": upcoming_shows,
        "past_shows": past_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template("pages/show_artist.html", artist=atist_object_with_shows)

#  Update
#  ----------------------------------------------------------------
@app.route("/artists/<int:artist_id>/edit", methods=["GET"])
def edit_artist(artist_id):
    artist = Artist.query.filter_by(id=artist_id).first_or_404()
    form = ArtistForm(obj=artist)
    return render_template("forms/edit_artist.html", form=form, artist=artist)


@app.route("/artists/<int:artist_id>/edit", methods=["POST"])
def edit_artist_submission(artist_id):

    artistObj = Artist.query.get(artist_id)
    error = False

    try:
        artistObj.name = request.form["name"]
        artistObj.city = request.form["city"]
        artistObj.state = request.form["state"]
        artistObj.phone = request.form["phone"]
        artistObj.genres = request.form.getlist("genres")
        artistObj.image_link = request.form["image_link"]
        artistObj.facebook_link = request.form["facebook_link"]
        artistObj.website_link = request.form["website_link"]
        artistObj.seeking_venue = True if "seeking_venue" in request.form else False
        artistObj.seeking_description = request.form["seeking_description"]

        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash("[Error] The artist cannot be updated.")
    if not error:
        flash("The artist was updated successfully!")
    return redirect(url_for("show_artist", artist_id=artist_id))


@app.route("/venues/<int:venue_id>/edit", methods=["GET"])
def edit_venue(venue_id):
    venueObj = Venue.query.filter_by(id=venue_id).first_or_404()
    form = VenueForm(obj=venueObj)
    return render_template("forms/edit_venue.html", form=form, venue=venueObj)


@app.route("/venues/<int:venue_id>/edit", methods=["POST"])
def edit_venue_submission(venue_id):
    error = False
    venueObj = Venue.query.get(venue_id)

    try:
        venueObj.name = request.form["name"]
        venueObj.city = request.form["city"]
        venueObj.state = request.form["state"]
        venueObj.address = request.form["address"]
        venueObj.phone = request.form["phone"]
        venueObj.genres = request.form.getlist("genres")
        venueObj.image_link = request.form["image_link"]
        venueObj.facebook_link = request.form["facebook_link"]
        venueObj.website_link = request.form["website_link"]
        venueObj.seeking_talent = True if "seeking_talent" in request.form else False
        venueObj.seeking_description = request.form["seeking_description"]

        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        flash(f"[Error] Venue cannot be updated.")
    if not error:
        flash(f"The venue was updated successfully!")
    return redirect(url_for("show_venue", venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------


@app.route("/artists/create", methods=["GET"])
def create_artist_form():
    form = ArtistForm()
    return render_template("forms/new_artist.html", form=form)


@app.route("/artists/create", methods=["POST"])
def create_artist_submission():
    form = ArtistForm()
    error = False
    if form.validate():
        try:
            artist = Artist(
                name=form.name.data,
                city=form.city.data,
                state=form.state.data,
                phone=form.phone.data,
                genres=form.genres.data,
                website_link=form.website_link.data,
                seeking_venue=form.seeking_venue.data,
                seeking_description=form.seeking_description.data,
                image_link=form.image_link.data,
                facebook_link=form.facebook_link.data,
            )
            db.session.add(artist)
            db.session.commit()
            flash("Artist " + request.form["name"] + " was successfully listed!")
            return render_template("pages/home.html")
        except ValueError as e:
            print(e)
            db.session.rollback()
            flash("An error occurred. Artist could not be listed.")
        finally:
            db.session.close()
    else:
        message = []
        for field, errors in form.errors.items():
            message.append(field + ": (" + "|".join(errors) + ")")
        flash("Entered data for the artist is not valid.")
    return render_template("pages/home.html")


#  Shows
#  ----------------------------------------------------------------


@app.route("/shows")
def shows():
    data = []
    shows = Show.query.order_by(Show.start_time.desc()).all()
    for show in shows:
        venue = Venue.query.filter_by(id=show.venue_id).first_or_404()
        artist = Artist.query.filter_by(id=show.artist_id).first_or_404()
        data.extend(
            [
                {
                    "venue_id": venue.id,
                    "venue_name": venue.name,
                    "artist_id": artist.id,
                    "artist_name": artist.name,
                    "artist_image_link": artist.image_link,
                    "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M"),
                }
            ]
        )
    return render_template("pages/shows.html", shows=data)


@app.route("/shows/create")
def create_shows():

    form = ShowForm()
    return render_template("forms/new_show.html", form=form)


@app.route("/shows/create", methods=["POST"])
def create_show_submission():
    form = ShowForm(request.form, meta={"csrf": False})
    if form.validate():
        try:
            show = Show(
                artist_id=form.artist_id.data,
                venue_id=form.venue_id.data,
                start_time=form.start_time.data,
            )
            db.session.add(show)
            db.session.commit()
            flash("The show was successfully listed!")
        except ValueError as e:
            print(e)
            db.session.rollback()
            flash("[Error] Show could not be listed.")
        finally:
            db.session.close()
    else:
        message = []
        for field, errors in form.errors.items():
            message.append(field + ": (" + "|".join(errors) + ")")
    return render_template("pages/home.html")


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


if not app.debug:
    file_handler = FileHandler("error.log")
    file_handler.setFormatter(
        Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info("errors")

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == "__main__":
    app.run()

# Or specify port manually:
"""
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
"""
