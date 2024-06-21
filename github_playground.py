import datetime
import pytz

from github import Github
from datetime import datetime
pytz.timezone("Europe/Berlin")
hackathon_start = datetime(year=2024, month=6, day=17, tzinfo=pytz.timezone("Europe/Berlin"))

# Public Web Github
with Github() as g:
    repo_name = 'IMSY-DKFZ/simpa'
    repo = g.get_repo(repo_name)

    issues = repo.get_issues(since=hackathon_start)
    print()
