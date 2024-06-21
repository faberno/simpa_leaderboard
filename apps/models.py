# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from apps import db
import random

class Team(db.Model):
    name = db.Column(db.String, primary_key=True)
    img_link = db.Column(db.String)
    points = db.Column(db.Integer)
    members = db.relationship('Member', backref='team', lazy=True)

    def __init__(self, name, img_link):
        self.name = name
        if not img_link:
            img_link = f"https://picsum.photos/id/{random.randint(0, 500)}/50/50"
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

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String, nullable=False)
    points = db.Column(db.Integer, nullable=False)
