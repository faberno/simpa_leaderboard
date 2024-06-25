# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps import db, hackathon_start, github_token, repo_name, date_after_start
import random
import github

class Team(db.Model):
    team_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    img_link = db.Column(db.String)
    points = db.Column(db.Integer)
    members = db.relationship('Member', backref='team', lazy=True)

    def __init__(self, name, img_link):
        self.name = name
        if not img_link:
            img_link = f"https://picsum.photos/id/{random.randint(0, 100)}/50"
        self.img_link = img_link
        self.points = 0

class Member(db.Model):
    name = db.Column(db.String(80), primary_key=True)
    img_link = db.Column(db.String(200))
    team_name = db.Column(db.String, db.ForeignKey('team.name'), nullable=False)

    def __init__(self, name, team_name):
        self.name = name
        self.team_name = team_name
        self.img_link = f"https://github.com/{name}.png"

class PointCalculation(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.DateTime, nullable=False)

# class TeamTotalpointCheckpoint(db.Model):
#     point_calculation_id = db.Column(db.Integer, db.ForeignKey(PointCalculation.id), primary_key=True)
#     team_name = db.Column(db.String, db.ForeignKey(Team.name), primary_key=True)
#     points = db.Column(db.Integer, nullable=False)

class HackathonStats(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.DateTime, nullable=False)
    opened_issues = db.Column(db.Integer, nullable=False)
    opened_pulls = db.Column(db.Integer, nullable=False)
    changed_loc = db.Column(db.Integer, nullable=False)


class AchievementType(db.Model):
    name = db.Column(db.String, primary_key=True)

class ReachedAchievement(db.Model):
    title = db.Column(db.String, primary_key=True)
    member = db.Column(db.String, db.ForeignKey('member.name'), primary_key=True)
    point_calculation_id = db.Column(db.Integer, db.ForeignKey(PointCalculation.id), primary_key=True)
    achievement_type = db.Column(db.String, db.ForeignKey(AchievementType.name), nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    labels = db.Column(db.String, nullable=False)
    permanent = db.Column(db.Boolean, nullable=False)

class FinalAchievement(db.Model):
    title = db.Column(db.String, primary_key=True)
    member = db.Column(db.String, db.ForeignKey('member.name'), primary_key=True)
    point_calculation_id = db.Column(db.Integer, db.ForeignKey(PointCalculation.id), primary_key=True)
    achievement_type = db.Column(db.String, db.ForeignKey(AchievementType.name), nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    permanent = db.Column(db.Boolean, nullable=False)

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    name = db.Column(db.String, nullable=False)
    priority = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)
    state = db.Column(db.String, nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.team_id'), autoincrement=False)
    team = db.relationship('Team', backref=db.backref('issue', lazy=True))


def fill_static_tables():
    if len(AchievementType.query.all()) == 0:
        db.session.add(AchievementType(name="Issue"))
        db.session.add(AchievementType(name="PullRequest"))
        db.session.add(AchievementType(name="Review"))
        db.session.commit()

    if len(Team.query.all()) == 0:
        db.session.add(Team(name="Team 1", img_link=None))
        db.session.add(Team(name="Team 2", img_link=None))
        db.session.add(Team(name="Team 3", img_link=None))
        db.session.add(Team(name="Team 4", img_link=None))
        db.session.commit()

    if len(Member.query.all()) == 0:
        db.session.add(Member(name="faberno", team_name="Team 1"))
        db.session.add(Member(name="kdreher", team_name="Team 1"))
        db.session.add(Member(name="leoyala", team_name="Team 2"))
        db.session.add(Member(name="RecurvedBow", team_name="Team 2"))
        db.session.add(Member(name="frisograce", team_name="Team 3"))
        db.session.add(Member(name="jgroehl", team_name="Team 3"))
        db.session.add(Member(name="cbender98", team_name="Team 4"))
        db.session.add(Member(name="TomTomRixRix", team_name="Team 4"))
        db.session.commit()

    if len(Issue.query.all()) == 0:

        predefined = {9: [1, 0], 29: [2, 0], 31: [1, 0], 32: [1, 1], 66: [2, 0], 75: [2, 1], 77: [2, 2], 85: [2, 0], 103: [2, 0], 105: [2, 1], 107: [2, 0], 113: [1, 1], 115: [2, 0], 129: [1, 1], 132: [2, 0], 157: [2, 0], 159: [1, 1], 160: [2, 1], 163: [2, 0], 164: [2, 0], 165: [2, 0], 172: [2, 0], 173: [2, 0], 180: [1, 0], 184: [2, 1], 192: [2, 0], 205: [2, 0], 220: [1, 1], 221: [2, 0], 222: [2, 1], 262: [2, 0], 275: [2, 0], 283: [1, 0], 299: [1, 1], 300: [2, 1], 301: [1, 1]}

        with github.Github(auth=github.Auth.Token(github_token)) as g:
            repo = g.get_repo(repo_name)
            issues = repo.get_issues(sort='created', direction='asc', labels=['hacking week'], state='all')
            issues = filter(lambda i: (i.pull_request is None), issues)
            for i in issues:
                if i.number in predefined.keys():
                    priority, difficulty = predefined.get(i.number)
                else:
                    priority, difficulty = 0, 0
                db.session.add(Issue(id=i.number, name=i.title, priority=priority, difficulty=difficulty, state=i.state))
            db.session.commit()


# class Achievement(db.Model):
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     type = db.Column(db.String, nullable=False)
#     points = db.Column(db.Integer, nullable=False)
