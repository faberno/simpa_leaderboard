# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import random
import os

from apps.home import blueprint
from flask import render_template, redirect, request, url_for, flash, current_app
from jinja2 import TemplateNotFound

from apps.models import Team, Member, HackathonStats, PointCalculation, ReachedAchievement #TeamTotalpointCheckpoint, ReachedAchievement, AchievementType
from apps import db
import github
from datetime import datetime
import pytz

tz = pytz.timezone("Europe/Berlin")
hackathon_start = datetime(year=2024, month=6, day=1, tzinfo=tz)

github_token = os.getenv('GITHUB_TOKEN')
repo_name = 'IMSY-DKFZ/simpa'

achievement_points = {'Issue': 10, 'PullRequest': 20}

def date_after_start(date):
    """Is date after hackathon start?"""
    return date > hackathon_start

def calculate_points_of():
    ...


@blueprint.route('/ping')
def ping():
    current_app.logger.info('Pinged!')
    return "Ping!"

@blueprint.route('/')
def default():
    teams = Team.query.order_by(Team.points.desc()).all()
    members = Member.query.all()
    stats = HackathonStats.query.order_by(HackathonStats.date.desc()).first()
    return render_template('home/index.html', segment='index', teams=teams, members=members, stats=stats)

@blueprint.route('/index')
def index():
    return default()


@blueprint.route('/teams', methods=['GET', 'POST'])
def teams():
    if request.method == 'POST':
        team_name = request.form['team_name']
        img_url = request.form['img_url']

        if team_name:
            team_exists = Team.query.filter_by(name=team_name).first() is not None
            if not team_exists:
                new_team = Team(name=team_name, img_link=img_url)
                db.session.add(new_team)
                db.session.commit()
                return redirect(url_for('home_blueprint.teams'))
            else:
                flash(f"Team '{team_name}' already exists.", "danger")
    teams = Team.query.all()
    return render_template('home/teams.html', segment='teams', teams=teams)

@blueprint.route('/teams/<id>')
def team_info(id):
    team = Team.query.get(id)
    achievements = ReachedAchievement.query.filter_by(team=team.name).all()
    return render_template('home/team_info.html', segment='team_info', team=team, achievements=achievements)


@blueprint.route('/add_member/<team_name>', methods=['POST'])
def add_member(team_name):
    current_app.logger.info(f"Received POST request to add team: {team_name}")
    member_name = request.form.get(f'member_name_{team_name}').strip()

    if member_name:
        user_exists = True
        with github.Github(auth=github.Auth.Token(github_token)) as g:
            try:
                g.get_user(member_name)
            except github.GithubException:
                user_exists = False

        if user_exists:
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

@blueprint.route('/recalculate')
def recalculate():
    teams = Team.query.all()
    team_achievements = {team: [] for team in teams}


    # init new PointCalculation entry that can be used to get the time the Points where calculated
    calculation_entry = PointCalculation(date=datetime.now(tz=tz))
    db.session.add(calculation_entry)
    db.session.flush()

    with github.Github(auth=github.Auth.Token(github_token)) as g:
        repo = g.get_repo(repo_name)
        issues_and_prs = repo.get_issues(since=hackathon_start, sort='created', direction='asc', state='all')
        issues_and_prs = list(filter(lambda i: date_after_start(i.created_at), issues_and_prs))


    # collect all point worthy achievements
    n_issues_opened = 0
    n_prs_opened = 0
    loc_changed = 0
    ReachedAchievement.query.filter_by(permanent=False).delete()
    for issue in issues_and_prs:
        user = Member.query.get(issue.user.login)
        if not user:
            continue
        if issue.pull_request is None: # is Issue
            achievement_type = 'Issue'
            n_issues_opened += 1
        else:
            achievement_type = 'PullRequest'
            n_prs_opened += 1
            pr_data = repo.get_pull(issue.number)
            loc_changed += (pr_data.additions + pr_data.deletions)

        points = achievement_points[achievement_type]
        achievement = ReachedAchievement(title=issue.title, team=user.team_name, point_calculation_id=calculation_entry.id,
                                         achievement_type=achievement_type, creation_date=issue.created_at, points=points, permanent=False)

        db.session.add(achievement)
        db.session.flush()

    stats = HackathonStats(date=datetime.now(tz=tz), opened_issues=n_issues_opened, opened_pulls=n_prs_opened, changed_loc=loc_changed)
    db.session.add(stats)
    db.session.commit()

    # for each team get the achievements and sum up their points
    for team in teams:
        team_points = 0
        team_achievements = ReachedAchievement.query.filter_by(team=team.name).all()
        for achievement in team_achievements:
            team_points += achievement.points
        team.points = team_points
        db.session.flush()
    db.session.commit()
    return redirect(url_for('home_blueprint.default'))

# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None
