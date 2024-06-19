# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps.home import blueprint
from flask import render_template, redirect, request, url_for, flash
from jinja2 import TemplateNotFound

from apps.models import Team, Member
from apps import db
import requests

@blueprint.route('/')
def default():

    # team1 = Team("TeamGen1", "https://github.com/faberno.png")
    # db.session.add(team1)
    # team2 = Team("TeamGen2", "https://github.com/faberno.png")
    # db.session.add(team2)
    # db.session.commit()
    return render_template('home/index.html', segment='index')

@blueprint.route('/index')
def index():
    return render_template('home/index.html', segment='index')


@blueprint.route('/teams', methods=['GET', 'POST'])
def teams():
    if request.method == 'POST':
        team_name = request.form['team_name']
        img_url = request.form['img_url']

        if team_name:
            new_team = Team(name=team_name, img_link=img_url)
            db.session.add(new_team)
            db.session.commit()
            return redirect(url_for('home_blueprint.teams'))

    teams = Team.query.all()
    return render_template('home/teams.html', segment='teams', teams=teams)


@blueprint.route('/add_member/<team_name>', methods=['POST'])
def add_member(team_name):
    member_name = request.form.get(f'member_name_{team_name}')

    if member_name:
        github_user_url = f"https://api.github.com/users/{member_name}"
        response = requests.get(github_user_url)

        if response.status_code == 200:
            existing_member = Member.query.get(member_name)
            if existing_member:
                if existing_member.team_name != team_name:
                    existing_member.team_name = team_name
                    db.session.commit()
                    flash(f"Member '{member_name}' has been moved to team '{team_name}'.", "success")
                else:
                    flash(f"Member '{member_name}' is already in team '{team_name}'.", "info")
            else:
                new_member = Member(name=member_name, team_name=team_name)
                db.session.add(new_member)
                db.session.commit()
                flash(f"Member '{member_name}' has been added to team '{team_name}'.", "success")
        else:
            flash(f"GitHub user '{member_name}' does not exist.", "danger")

    return redirect(url_for('home_blueprint.teams'))

# @blueprint.route('/<template>')
# def route_template(template):
#
#     try:
#
#         if not template.endswith('.html'):
#             template += '.html'
#
#         # Detect the current page
#         segment = get_segment(request)
#
#         # Serve the file (if exists) from app/templates/home/FILE.html
#         return render_template("home/" + template, segment=segment)
#
#     except TemplateNotFound:
#         return render_template('home/page-404.html'), 404
#
#     except:
#         return render_template('home/page-500.html'), 500


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None
