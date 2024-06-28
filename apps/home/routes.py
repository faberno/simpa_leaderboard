# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""
import random
import os
import re

from apps.home import blueprint
from flask import render_template, redirect, request, url_for, flash, current_app
from jinja2 import TemplateNotFound

from apps.models import Team, Member, HackathonStats, PointCalculation, ReachedAchievement, Issue #TeamTotalpointCheckpoint, ReachedAchievement, AchievementType
from apps import db, hackathon_start, github_token, repo_name, tz, date_after_start
import github
from datetime import datetime
import pytz

achievement_points = {'Issue': 10, 'PullRequest': 20, 'Review':5}
priority_points = {0: 5, 1: 10, 2:15}
difficulty_points = {0: 5, 1: 10, 2:15}

onetime_challenges = {
    'Create your first Issue': 15,
    'Create your first PR': 15,
    'Create your first Review': 15,
    'Fix a bug': 10,
    'Fix 3 bugs': 20,
    'Implement a feature': 10,
    'Implement 3 features': 20,
    'Improve the documentation': 10,
    'Improve the documentation x3': 20
}

eastereggs = {
    'Time Traveler': 'Resolve the oldest issue',
    'Complaint Champion': 'Open most issues',
    'Pull Request Power House': 'Open most PRs',
    'LOC Lunatic': 'Most LOC added',
    'Code Cleaner': 'Most LOC removed',
    'Doc Dynamo': 'Best Documentation',
    'Test Titan': 'Most Tests added',
    'Mega Merger': 'Largest PR',
    'Slip-up Sleuth': 'Most embarrassing bug found',
    'Beer Pong Baron': 'Best efforts in the Beer Pong Tournament',
    'Rage Cage Mage': 'Win Rage Cage',
    'Looping Louie Legend': 'Best efforts in the Looping Louie Tournament',
    'Team Title Titans': 'Best team name',
    'Issue Improviser': 'Create PR for Issue that is not part of the hacking week',
    'Max Verstappen': 'Fastest team to score any points',
    'FIXME Fixer': 'Fix a FIXME',
    'TODO Doner': 'Do a TODO',
    'Off-By-One Obliterator': 'Finally and forever fix "off-by-one-error"',
    'Commit Message Maestro': 'Most typos in the commit messages'
}


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
        team_name = request.form['team_name'].strip()
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
    achievements = sum([ReachedAchievement.query.filter_by(member=member.name).all() for member in team.members], [])
    return render_template('home/team_info.html', segment='team_info', team=team, achievements=achievements)

@blueprint.route('/issues')
def issues():
    issues = Issue.query.filter_by(issue_state='open').all()
    return render_template('home/issues.html', segment='issues', issues=issues)

@blueprint.route('/challenges')
def challenges():
    easteregg_ach = ReachedAchievement.query.filter_by(achievement_type='Easter Egg').all()
    easteregg_ach = [a.title.split(':')[0] for a in easteregg_ach]
    display_eastereggs = dict()
    for title, descr in eastereggs.items():
        if title in easteregg_ach:
            display_eastereggs[title] = descr
        else:
            display_eastereggs[title] = ""
    return render_template('home/challenges.html', segment='challenges', onetime_challenges=onetime_challenges, eastereggs=display_eastereggs)


def get_issue_creation_date(issue):
    if issue is None:
        return datetime.now(tz=tz)
    g = github.Github(auth=github.Auth.Token(github_token))
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(int(issue))
    return issue.created_at


def argmax(iterable):
    return max(enumerate(iterable), key=lambda x: x[1])[0]

def argmin(iterable):
    return min(enumerate(iterable), key=lambda x: x[1])[0]

def get_team_from_issue(issue):
    creator = issue.user.login
    creator = Member.query.get(creator)
    if creator is not None:
        return creator.team_name
    return None


def get_pr_data(nr):
    with github.Github(auth=github.Auth.Token(github_token)) as g:
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(nr)
    return pr

def get_pr_stats(pr):
    member = Member.query.get(pr.user.login)
    if member is None:
        return None
    pr_data = get_pr_data(pr.number)
    stats = dict()
    stats['pr_name'] = pr.title
    stats['deletions'] = pr_data.deletions
    stats['additions'] = pr_data.additions
    stats['fixed_issue_creation'] = get_issue_creation_date(get_linked_issue(pr.body))
    stats['creator'] = pr.user.login
    stats['creator_team'] = Member.query.get(pr.user.login).team_name
    return stats


def find_team_with_best_stats(data, stat, func=max):
    from collections import defaultdict
    team_stats = defaultdict(int)

    # Aggregate additions for each team
    for entry in data.values():
        team_name = entry["creator_team"]
        stat_val = entry[stat]
        team_stats[team_name] += stat_val

    # Find the team with the maximum sum of additions
    max_team = func(team_stats, key=team_stats.get)
    return max_team, team_stats[max_team]

def find_team_with_most_prs(data, perma):
    from collections import defaultdict
    team_stats = defaultdict(int)

    # Aggregate additions for each team
    for entry in data.values():
        team_name = entry["creator_team"]
        team_stats[team_name] += 1

    max_team = max(team_stats.values())
    for team, val in team_stats.items():
        if val == max_team:
            member  = Member.query.filter_by(team_name=team).first()
            achieve = ReachedAchievement(title=f"Pull Request Power House: Open most PRs ({max_team})",
                                         member=member.name,
                                         point_calculation_id=27,
                                         achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
                                         points=15, labels='', permanent=perma)
            db.session.add(achieve)
            db.session.flush()
    return max_team, team_stats[max_team]

@blueprint.route('/make_eastereggs/<perma>')
def make_eastereggs(perma):
    ReachedAchievement.query.filter_by(permanent=False).delete()

    perma = perma.lower() == 'true'
    g = github.Github(auth=github.Auth.Token(github_token))
    repo = g.get_repo(repo_name)
    issues_and_prs = repo.get_issues(since=hackathon_start, sort='created', direction='asc', state='all', labels=['hacking week'])
    issues_and_prs = list(filter(lambda i: date_after_start(i.created_at), issues_and_prs))
    g.close()

    all_issues = [i for i in issues_and_prs if i.pull_request is None]
    all_prs = [i for i in issues_and_prs if i.pull_request is not None]

    pr_stats = {pr: stats for pr in all_prs if (stats := get_pr_stats(pr)) is not None}

    largest_pr = max(pr_stats, key=lambda k: pr_stats[k]['additions'])
    largest_pr_stats = pr_stats[largest_pr]
    achieve = ReachedAchievement(title=f"Mega Merger: Largest PR", member=largest_pr.user.login,
                       point_calculation_id=27,
                       achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
                       points=15, labels='', permanent=perma)
    db.session.add(achieve)
    db.session.flush()

    # ------------------------------------------
    oldest_issue_fixed = min(pr_stats, key=lambda k: pr_stats[k].get('fixed_issue_creation', datetime.now(tz=tz)))
    achieve = ReachedAchievement(title=f"Time Traveler: Resolve the oldest issue", member=oldest_issue_fixed.user.login,
                       point_calculation_id=27,
                       achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
                       points=15, labels='', permanent=perma)
    db.session.add(achieve)
    db.session.flush()

    # ------------------------------------------

    max_addition_team = find_team_with_best_stats(pr_stats, 'additions', max)
    member = Member.query.filter_by(team_name=max_addition_team[0]).first()
    achieve = ReachedAchievement(title=f"LOC Lunatic: Most LOC added ({max_addition_team[1]})", member=member.name,
                       point_calculation_id=27,
                       achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
                       points=15, labels='', permanent=perma)
    db.session.add(achieve)
    db.session.flush()

    # ------------------------------------------

    max_deletions_team  = find_team_with_best_stats(pr_stats, 'deletions', max)
    member = Member.query.filter_by(team_name=max_deletions_team[0]).first()
    achieve = ReachedAchievement(title=f"Code Cleaner: Most LOC removed ({max_deletions_team[1]})", member=member.name,
                       point_calculation_id=27,
                       achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
                       points=15, labels='', permanent=perma)
    db.session.add(achieve)
    db.session.flush()

    # ------------------------------------------

    max_deletions_team  = find_team_with_most_prs(pr_stats, perma)

    # -----------------------
    from collections import Counter
    issue_teams = [get_team_from_issue(i) for i in all_issues]
    issue_count = Counter(issue_teams)
    if None in issue_count:
        del issue_count[None]
    max_issues = max(issue_count.values())
    for team in issue_count.keys():
        if team is not None and issue_count[team] == max_issues:
            member = Member.query.filter_by(team_name=team).first()
            achieve = ReachedAchievement(title=f"Complaint Champion: Open most issues ({max_issues})", member=member.name,
                               point_calculation_id=27,
                               achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
                               points=15, labels='', permanent=perma)
            db.session.add(achieve)
            db.session.commit()

    # -----------------------
    # achieve = ReachedAchievement(title=f"Team Title Titans: Best team name", member='seitela',
    #                              point_calculation_id=27,
    #                              achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
    #                              points=15, labels='', permanent=perma)
    # db.session.add(achieve)
    # db.session.commit()
    #
    # # -----------------------
    # achieve = ReachedAchievement(title=f"Doc Dynamo: Best Documentation", member='frisograce',
    #                              point_calculation_id=27,
    #                              achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
    #                              points=15, labels='', permanent=perma)
    # db.session.add(achieve)
    # db.session.commit()
    #
    # # -----------------------
    # achieve = ReachedAchievement(title=f"Commit Message Maestro: Most typos in the commit messages", member='jnoelke',
    #                              point_calculation_id=27,
    #                              achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
    #                              points=15, labels='', permanent=perma)
    # db.session.add(achieve)
    # db.session.commit()
    # # -----------------------
    # achieve = ReachedAchievement(title=f"Test Titan: Most Tests added", member='TomTomRixRix',
    #                              point_calculation_id=27,
    #                              achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
    #                              points=15, labels='', permanent=perma)
    # db.session.add(achieve)
    # db.session.commit()
    # # -----------------------
    # achieve = ReachedAchievement(title=f"Rage Cage Mage: Win Rage Cage", member='seitela',
    #                              point_calculation_id=27,
    #                              achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
    #                              points=15, labels='', permanent=perma)
    # db.session.add(achieve)
    # db.session.commit()
    # # -----------------------
    # achieve = ReachedAchievement(title=f"Beer Pong Baron: Best efforts in the Beer Pong Tournament", member='jnoelke',
    #                              point_calculation_id=27,
    #                              achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
    #                              points=20, labels='', permanent=perma)
    # db.session.add(achieve)
    # db.session.commit()
    # # # -----------------------
    # achieve = ReachedAchievement(title=f"Looping Louie Legend: Best efforts in the Looping Louie Tournament", member='marcelmknopp',
    #                              point_calculation_id=27,
    #                              achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
    #                              points=10, labels='', permanent=perma)
    # db.session.add(achieve)
    # db.session.commit()
    # # # -----------------------
    # achieve = ReachedAchievement(title=f"Issue Improviser: Create PR for Issue that is not part of the hacking week", member='jnoelke',
    #                              point_calculation_id=27,
    #                              achievement_type="Easter Egg", creation_date=datetime.now(tz=tz),
    #                              points=15, labels='', permanent=perma)
    # db.session.add(achieve)
    # db.session.commit()

    return redirect(url_for('home_blueprint.default'))


@blueprint.route('/rate_issue/<issue_nr>/<priority>/<difficulty>')
def rate_issue(issue_nr, priority, difficulty):
    issue = Issue.query.get(int(issue_nr))
    if issue:
        issue.priority = int(priority)
        issue.difficulty = int(difficulty)
        db.session.commit()
    return redirect(url_for('home_blueprint.issues'))



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


@blueprint.route('/assign_issue/<issue_id>', methods=['POST'])
def assign_issue(issue_id):
    team_name = request.form.get(f'team_name_{issue_id}').strip()

    if team_name:
        new_team = Team.query.filter_by(name=team_name).first()
        issue = Issue.query.get(issue_id)
        if (new_team is not None) and (issue is not None):
            issue.team_id = new_team.team_id
            db.session.commit()
            flash(f"Issue '{issue.name}' has been assigned to team '{team_name}'.", "success")
        else:
            flash(f"Team '{team_name}' does not exist.", "danger")

    return redirect(url_for('home_blueprint.issues'))


@blueprint.route('/unassign_issue/<issue_id>', methods=['POST'])
def unassign_issue(issue_id):
    if not issue_id:
        return redirect(url_for('home_blueprint.issues'))

    issue = Issue.query.get(issue_id)
    if issue.team_id:
        team_name = issue.team.name
        issue.team_id = None
        db.session.commit()
        flash(f"Issue '{issue.name}' has been unassigned from team '{team_name}'.", "success")
    return redirect(url_for('home_blueprint.issues'))


def get_linked_issue(body):
    for line in body.lower().splitlines():
        if "fixes" in line and "#" in line:
            match = re.search(r'#(\d+)', line)
            if match:
                number = match.group(1)
                return number
    return None


def calculate_ongoing_challenges(issues_and_prs, repo, calculation_entry):
    n_issues_opened = 0
    n_prs_opened = 0
    loc_changed = 0

    for issue in issues_and_prs:

        additional_points = 0
        labels = ''
        user = Member.query.get(issue.user.login)
        if not user:
            continue
        if issue.pull_request is None: # is Issue
            achievement_type = 'Issue'
            n_issues_opened += 1
            labels = ','.join(l.name for l in issue.labels)
        else:
            achievement_type = 'PullRequest'
            n_prs_opened += 1
            pr_data = repo.get_pull(issue.number)
            loc_changed += (pr_data.additions + pr_data.deletions)
            labels = ','.join(l.name for l in issue.labels)

            # get linked issue
            linked_issue_nr = get_linked_issue(issue.body)
            if linked_issue_nr is not None:
                linked_issue = Issue.query.get(int(linked_issue_nr))
                if linked_issue is None:
                    additional_points = priority_points[0] + difficulty_points[0]
                else:
                    additional_points = priority_points[linked_issue.priority] + difficulty_points[linked_issue.difficulty]
                github_issue = repo.get_issue(int(linked_issue_nr))
                labels = labels + "," + ','.join(l.name for l in github_issue.labels)


            # check reviews
            team_members = [member.name for member in user.team.members]
            reviews = pr_data.get_reviews()
            all_reviewers = []
            for review in reviews:
                if review.user.login not in team_members:
                    points = achievement_points['Review']
                    review_user = Member.query.get(review.user.login)
                    if (review_user is not None) and (review_user.name not in all_reviewers):
                        all_reviewers.append(review_user.name)
                        achievement = ReachedAchievement(title=f"Review for '{issue.title}'", member=review_user.name,
                                                         point_calculation_id=calculation_entry.id,
                                                         achievement_type="Review", creation_date=review.submitted_at,
                                                         points=points, labels='', permanent=False)
                        db.session.add(achievement)
                        db.session.flush()

        points = achievement_points[achievement_type] + additional_points
        achievement = ReachedAchievement(title=issue.title, member=user.name, point_calculation_id=calculation_entry.id,
                                         achievement_type=achievement_type, creation_date=issue.created_at, labels=labels, points=points, permanent=False)

        db.session.add(achievement)
        db.session.flush()
    db.session.commit()

    stats = {'n_issues_opened': n_issues_opened, 'n_prs_opened': n_prs_opened, 'loc_changed': loc_changed}
    return stats


def calculate_onetime_challenges(calculation_entry):
    teams = Team.query.all()
    for team in teams:
        team_achievements = ReachedAchievement.query.filter(ReachedAchievement.member.in_([member.name for member in team.members])).all()

        issues = list(filter(lambda x: x.achievement_type == 'Issue', team_achievements))
        prs = list(filter(lambda x: x.achievement_type == 'PullRequest', team_achievements))
        reviews = list(filter(lambda x: x.achievement_type == 'Review', team_achievements))

        if len(issues) > 0:
            issues = sorted(issues, key=lambda x: x.creation_date)
            title = 'Create your first Issue'
            achievement = ReachedAchievement(title=f"{title}: {issues[0].title}", member=issues[0].member, point_calculation_id=calculation_entry.id,
                               achievement_type='One-Time Challenge', creation_date=issues[0].creation_date, labels='',
                               points=onetime_challenges[title], permanent=False)
            db.session.add(achievement)
            db.session.flush()
        if len(reviews) > 0:
            reviews = sorted(reviews, key=lambda x: x.creation_date)
            title = 'Create your first Review'
            achievement = ReachedAchievement(title=f"{title}: {reviews[0].title}", member=reviews[0].member, point_calculation_id=calculation_entry.id,
                               achievement_type='One-Time Challenge', creation_date=reviews[0].creation_date, labels='',
                               points=onetime_challenges[title], permanent=False)
            db.session.add(achievement)
            db.session.flush()
        if len(prs) > 0:
            prs = sorted(prs, key=lambda x: x.creation_date)
            title = 'Create your first PR'
            achievement = ReachedAchievement(title=f"{title}: {prs[0].title}", member=prs[0].member, point_calculation_id=calculation_entry.id,
                               achievement_type='One-Time Challenge', creation_date=prs[0].creation_date, labels='',
                               points=onetime_challenges[title], permanent=False)
            db.session.add(achievement)
            db.session.flush()

            pr_labels = [achievement.labels for achievement in prs]

            bug_prs = [pr for pr in prs if 'bug' in pr.labels]
            doc_prs = [pr for pr in prs if 'documentation' in pr.labels]
            feature_prs = [pr for pr in prs if 'feature' in pr.labels]

            if len(bug_prs) > 0:
                title = 'Fix a bug'
                achievement = ReachedAchievement(title=f"{title}: {bug_prs[0].title}", member=bug_prs[0].member,
                                                 point_calculation_id=calculation_entry.id,
                                                 achievement_type='One-Time Challenge',
                                                 creation_date=bug_prs[0].creation_date, labels='',
                                                 points=onetime_challenges[title], permanent=False)
                db.session.add(achievement)
                db.session.flush()

            if len(bug_prs) > 3:
                title = 'Fix 3 bugs'
                achievement = ReachedAchievement(title=title, member=bug_prs[2].member,
                                                 point_calculation_id=calculation_entry.id,
                                                 achievement_type='One-Time Challenge',
                                                 creation_date=bug_prs[2].creation_date, labels='',
                                                 points=onetime_challenges[title], permanent=False)
                db.session.add(achievement)
                db.session.flush()

            if len(feature_prs) > 0:
                title = 'Implement a feature'
                achievement = ReachedAchievement(title=f"{title}: {feature_prs[0].title}", member=feature_prs[0].member,
                                                 point_calculation_id=calculation_entry.id,
                                                 achievement_type='One-Time Challenge',
                                                 creation_date=feature_prs[0].creation_date, labels='',
                                                 points=onetime_challenges[title], permanent=False)
                db.session.add(achievement)
                db.session.flush()

            if len(feature_prs) > 3:
                title = 'Implement 3 features'
                achievement = ReachedAchievement(title=title, member=feature_prs[2].member,
                                                 point_calculation_id=calculation_entry.id,
                                                 achievement_type='One-Time Challenge',
                                                 creation_date=feature_prs[2].creation_date, labels='',
                                                 points=onetime_challenges[title], permanent=False)
                db.session.add(achievement)
                db.session.flush()

            if len(doc_prs) > 0:
                title = 'Improve the documentation'
                achievement = ReachedAchievement(title=f"{title}: {doc_prs[0].title}", member=doc_prs[0].member,
                                                 point_calculation_id=calculation_entry.id,
                                                 achievement_type='One-Time Challenge',
                                                 creation_date=doc_prs[0].creation_date, labels='',
                                                 points=onetime_challenges[title], permanent=False)
                db.session.add(achievement)
                db.session.flush()

            if len(doc_prs) > 3:
                title = 'Improve the documentation x3'
                achievement = ReachedAchievement(title=title, member=doc_prs[2].member,
                                                 point_calculation_id=calculation_entry.id,
                                                 achievement_type='One-Time Challenge',
                                                 creation_date=doc_prs[2].creation_date, labels='',
                                                 points=onetime_challenges[title], permanent=False)
                db.session.add(achievement)
                db.session.flush()
    db.session.commit()


@blueprint.route('/update')
def update():
    teams = Team.query.all()
    # team_achievements = {team: [] for team in teams}

    # init new PointCalculation entry that can be used to get the time the Points where calculated
    calculation_entry = PointCalculation(date=datetime.now(tz=tz))
    db.session.add(calculation_entry)
    db.session.flush()

    g = github.Github(auth=github.Auth.Token(github_token))
    repo = g.get_repo(repo_name)
    issues_and_prs = repo.get_issues(since=hackathon_start, sort='created', direction='asc', state='all', labels=['hacking week'])
    issues_and_prs = list(filter(lambda i: date_after_start(i.created_at), issues_and_prs))

    for issue in issues_and_prs:
        if issue.pull_request is None:
            existing_issue = Issue.query.get(issue.number)
            if existing_issue is None:
                new_issue = Issue(id=issue.number, name=issue.title, priority=0, difficulty=0, issue_state=issue.state)
                db.session.add(new_issue)
                db.session.flush()
    db.session.commit()


    # collect all point worthy achievements
    ReachedAchievement.query.filter_by(permanent=False).delete() # calculate unpermanent ones new every time

    stats = calculate_ongoing_challenges(issues_and_prs, repo, calculation_entry)
    calculate_onetime_challenges(calculation_entry)
    stats = HackathonStats(date=datetime.now(tz=tz), opened_issues=stats['n_issues_opened'], opened_pulls=stats['n_prs_opened'], changed_loc=stats['loc_changed'])
    db.session.add(stats)
    db.session.commit()

    # for each team get the achievements and sum up their points
    for team in teams:
        team_points = 0
        for member in team.members:
            member_achievements = ReachedAchievement.query.filter_by(member=member.name).all()
            for achievement in member_achievements:
                team_points += achievement.points
        team.points = team_points
        db.session.flush()
    db.session.commit()
    g.close()
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
