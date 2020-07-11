from flask import Flask, request, render_template, redirect, flash, session
from flask_debugtoolbar import DebugToolbarExtension
from models import connect_db, db, User, Feedback
from forms import RegisterForm, LoginForm, FeedbackForm
from sqlalchemy.exc import IntegrityError
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgres:///auth_db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "Secret-What?")
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False

connect_db(app)
db.create_all()

toolbar = DebugToolbarExtension(app)


@app.route("/")
def index():
    """Redirect to Register page"""
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register_user():
    """Route to show user registration"""

    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data

        new_user = User.register(username, password, email, first_name, last_name)

        db.session.add(new_user)
        try:
            db.session.commit()
        except IntegrityError:
            form.username.errors.append("Username taken, please pick another")
            return render_template("/users/register.html", form=form)

        session["username"] = new_user.username
        flash("Thank you for registering", "warning")
        return redirect(f"/users/{new_user.username}")

    return render_template("/users/register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def show_login():
    """Show login form"""
    if "username" in session:
        return redirect(f"/users/{session['username']}")

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.authenticate(username, password)
        if user:
            session["username"] = user.username
            flash(f"Welcome back {user.first_name}!", "success")
            return redirect(f"/users/{user.username}")
        else:
            form.username.errors = ["Invalid username/password."]

    return render_template("users/login.html", form=form)


@app.route("/users/<username>")
def show_user(username):
    """Redirect to users page"""
    if "username" not in session or username != session["username"]:
        flash("You must be logged in to view this page", "danger")
        return redirect("/login")

    user = User.query.get_or_404(username)
    return render_template("/users/users.html", user=user)


@app.route("/logout")
def logout_user():
    """Logout user and redirect"""
    session.pop("username")
    flash("You have been logged out!", "success")
    return redirect("/")


@app.route("/users/<username>/delete", methods=["POST"])
def delete_user(username):
    """Delete a user"""

    if "username" not in session or username != session["username"]:
        flash("You do not have permission to do delete this user!", "primary")
        return redirect(f"/users/{username}")
    else:
        user = User.query.get_or_404(username)
        db.session.delete(user)
        db.session.commit()
        session.pop("username")
        flash("User has been successfully deleted", "info")
        return redirect("/login")


@app.route("/users/<username>/feedback/add", methods=["GET", "POST"])
def add_feedback(username):
    """Add feedback for specific user"""
    if "username" not in session or username != session["username"]:
        flash("Please login to leave feedback!", "danger")
        return redirect("/login")

    form = FeedbackForm()
    user = User.query.get_or_404(username)
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data

        new_feedback = Feedback(title=title, content=content, username=username)

        db.session.add(new_feedback)
        db.session.commit()
        flash("Feedback submitted!", "success")
        return redirect(f"/users/{username}")

    return render_template("/feedback/add.html", form=form, user=user)


@app.route("/feedback/<int:id>/update", methods=["GET", "POST"])
def update_feedback(id):
    """Update specific feedback message"""
    feedback = Feedback.query.get_or_404(id)

    if "username" not in session or feedback.username != session["username"]:
        flash("Please login to update your feedback!", "danger")
        return redirect("/login")

    form = FeedbackForm(obj=feedback)
    if form.validate_on_submit():
        feedback.title = form.title.data
        feedback.content = form.content.data

        db.session.commit()
        flash("Feedback Updated!", "info")
        return redirect(f"/users/{feedback.username}")

    return render_template("/feedback/update.html", form=form, feedback=feedback)


@app.route("/feedback/<int:id>/delete", methods=["POST"])
def delete_feedback(id):
    """Delete feedback"""

    feedback = Feedback.query.get_or_404(id)

    if "username" not in session or feedback.username != session["username"]:
        flash("Not allowed! You did not create this feedback", "danger")
        return redirect("/login")

    db.session.delete(feedback)
    db.session.commit()
    flash("Feedback Deleted!", "warning")
    return redirect(f"/users/{feedback.username}")


# ===================== ERROR 404 ===================== #


@app.errorhandler(404)
def page_not_found(error):
    """Show 404 ERROR page if page NOT FOUND"""

    return render_template("error.html"), 404
