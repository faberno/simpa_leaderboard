# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps import db
import random

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

class TeamTotalpointCheckpoint(db.Model):
    point_calculation_id = db.Column(db.Integer, db.ForeignKey(PointCalculation.id), primary_key=True)
    team_name = db.Column(db.Integer, db.ForeignKey(Team.name), primary_key=True)
    points = db.Column(db.Integer, nullable=False)

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
    team = db.Column(db.String, db.ForeignKey('team.name'), primary_key=True)
    point_calculation_id = db.Column(db.Integer, db.ForeignKey(PointCalculation.id), primary_key=True)
    achievement_type = db.Column(db.String, db.ForeignKey(AchievementType.name), nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    permanent = db.Column(db.Boolean, nullable=False)


def fill_static_tables():
    if len(AchievementType.query.all()) == 0:
        db.session.add(AchievementType(name="Issue"))
        db.session.add(AchievementType(name="PullRequest"))
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

# class Achievement(db.Model):
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     type = db.Column(db.String, nullable=False)
#     points = db.Column(db.Integer, nullable=False)
