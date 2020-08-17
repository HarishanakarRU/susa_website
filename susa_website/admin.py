# This includes all views that are involved with the admin panel, as well
# as the login page
from flask import render_template, request, url_for, flash, redirect, abort

from flask_login import UserMixin, LoginManager, login_required
from flask_login.utils import current_user, login_user, logout_user

from flask_admin import Admin, BaseView, expose, AdminIndexView
from flask_admin.menu import MenuLink
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.fileadmin import FileAdmin

from flask_wtf import FlaskForm
from wtforms.fields import StringField, TextAreaField, SelectField
from wtforms.fields.html5 import DateField, IntegerField
from wtforms.validators import DataRequired, NumberRange

import os.path as op

from . import secrets, app, db
from .schema import Events, Team, Resources, ResourcesMapping, Contents

# Flask-login init
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    pass

@login_manager.user_loader
def user_loader(username):
    if username != secrets['username']:
        return

    user = User()
    user.id = username
    print("user loaded")
    return user

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    if username != secrets['username']:
        return

    user = User()
    user.id = username

    return user


app.config['FLASK_ADMIN_SWATCH'] = 'darkly'

class AdminIndex(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super(AdminIndex, self).index()

    @expose('/login', methods=('GET', 'POST'))
    def login_view(self):
        error = None
        if current_user.is_authenticated:
            # This is weird, but you won't touch the login page after logging again
            user = User()
            user.id = secrets['username']
            login_user(user)
            flash("You were logged in.")
            return super(AdminIndex, self).index()

        if request.method == 'POST':
            if request.form['username'] != secrets['username'] or request.form['password'] != secrets['password']:
                error = 'Invalid username and/or password.'
            else:
                user = User()
                user.id = secrets['username']
                login_user(user)
                flash("You were logged in.")
                return super(AdminIndex, self).index()
        return render_template('admin/login.html', error=error)

    @expose('/logout')
    def logout_view(self):
        logout_user()
        flash("You were logged out.")
        return redirect(url_for('.login_view'))

class AdminView(ModelView):
    edit_template = 'admin/model/susa_edit.html'
    create_template = 'admin/model/susa_create.html'
    def is_accessible(self):
        return current_user.is_authenticated
    def inaccessible_callback(self,name, **kwargs):
        abort(403)

class OpStringField(StringField):
    pass

class StringField(StringField):
    validators = [DataRequired()]

class TextAreaField(TextAreaField):
    validators = [DataRequired()]

class PositionField(IntegerField):
    validators = [DataRequired(), NumberRange(min=1)]

class DateField(DateField):
    validators = [DataRequired()]

class ResourcesForm(FlaskForm):
    category = StringField("Category")
    label = StringField("Label for the link")
    link = StringField("Link", description="If adding a file hosted by us, give the relative directory to /static/resources/\nOtherwise, use a http... link")
    position = PositionField("Position within Category")

class ResourcesView(AdminView):
    column_filters = ['category']
    column_searchable_list = ['label']
    column_editable_list = ['link', 'position', 'label']
    create_form = edit_form = ResourcesForm

class ResourcesMappingForm(FlaskForm):
    category = StringField("Category")
    group_position = PositionField("Category position within Type")
    type = SelectField('Type',
    choices=[
    (1, 'Courses'),
    (2, 'Useful Links'),
    (3, 'Other Links'),
    (4, 'Removed')
    ], coerce=int)

class ResourcesMappingView(AdminView):
    column_filters = ['type', 'category']
    column_editable_list = ['group_position']
    create_form = edit_form = ResourcesMappingForm

class EventsForm(FlaskForm):
    event_date = DateField("Event Date")
    event_name = StringField("Event Name")
    description = OpStringField("Event Description")
    fb_link = OpStringField("Facebook Link")
    location = OpStringField("Location")
    resources = OpStringField("Resources", description="Format is Resource 1 label: link, Resource 2 label: link, ....")

class EventsView(AdminView):
    column_searchable_list = ['event_date', 'event_name', 'location']
    column_editable_list = ['event_date', 'event_name', 'fb_link', 'location', 'description']
    create_form = edit_form = EventsForm

class TeamForm(FlaskForm):
    name = StringField("Officer name")
    role = StringField("Officer role")
    year = StringField("Current year", description="ex. Second; First, Fifth")
    major = StringField("Major(s)", description="ex. Statistics and Computer Science; Economics; EECS")
    origin = StringField("From", description="ex. Paris, Texas; Beijing, China; Berlin, Germany")
    classes = TextAreaField("Current classes", description="ex. Stat 153, CS 61a, Data 8")
    past_classes = TextAreaField("Past classes")
    summary = TextAreaField("Give a short intro", description="You can (and should!) use HTML tags.")
    portrait = StringField("Portrait Path", description="Relative path in /static/portraits/ to officer&#39;s portrait")
    semester = StringField("Last semester active")
    position = PositionField("Position", description="With 1 being the first person displayed on the team page")

class TeamView(AdminView):
    column_searchable_list = ['role', 'name']
    column_filters = ['role']
    column_editable_list = ['position', 'role', 'summary', 'portrait', 'major', 'year', 'classes', 'past_classes']
    create_form = edit_form = TeamForm

class ContentsForm(FlaskForm):
    area = SelectField('Type',
    choices=[
    ('home_text', 'Homepage text'),
    ('about_team', 'Team page text&mdash;description about our structure'),
    ('apply_info', 'Team page text&mdash;description about how to apply to our team'),
    ('about_events', 'Event page text'),
    ('footer_emails', 'Emails in the footer of each page'),
    ('removed', 'Removed')
    ])
    text = TextAreaField("Content to include", description='You can (and should!) use HTML tags for most of the contents with the exception of the footer emails.<br>For footer emails, follow the format: "role: email@berkeley.edu, role: ......"')

class ContentsView(AdminView):
    column_searchable_list = ['area']
    column_editable_list = ['area', 'text']
    create_form = edit_form = ContentsForm

class Files(FileAdmin):
    def is_accessible(self):
        return current_user.is_authenticated
    def inaccessible_callback(self,name, **kwargs):
        abort(403)
    upload_template = mkdir_template = rename_template = edit_template = 'admin/file/susa_form.html'

path = op.join(op.dirname(__file__), 'static')

admin = Admin(app, name='SUSA', template_mode='bootstrap3', index_view=AdminIndex())
admin.add_view(ResourcesView(Resources, db.session, category="Resources", name="Links"))
admin.add_view(ResourcesMappingView(ResourcesMapping, db.session, category="Resources"))
admin.add_view(EventsView(Events, db.session))
admin.add_view(TeamView(Team, db.session))
admin.add_view(ContentsView(Contents, db.session))
admin.add_view(Files(path, name='Files'))
admin.add_link(MenuLink(name='Logout', category='', url='/admin/logout'))
admin.add_link(MenuLink(name='Exit', category='', url='/'))
