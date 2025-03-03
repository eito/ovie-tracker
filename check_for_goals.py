from datetime import datetime, timezone
import json
import os
import requests
import tweepy

CAPITALS_TEAM_ID = 15  # Washington Capitals team ID in the NHL API
OVECHKIN_PLAYER_ID = 8471214  # Alex Ovechkin's player ID
SCHEDULE_URL = "https://api-web.nhle.com/v1/club-schedule-season/WSH/20242025"
PLAY_BY_PLAY_FORMAT = "https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
GOALS_AT_START_OF_YEAR = 853

GOAL_STATE_FILE = "goal_state.json"
SCHEDULE_FILE = "schedule.json"

# Github API
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER")
REPO_NAME = os.getenv("REPO_NAME")
GITHUB_API_URL = f"https://api.github.com/repos/{os.getenv('REPO_OWNER')}/{os.getenv('REPO_NAME')}/issues/1/comments"

# X API Credentials from GitHub Secrets
X_API_KEY = os.getenv("X_API_KEY")
X_API_KEY_SECRET = os.getenv("X_API_KEY_SECRET")
X_API_BEARER_TOKEN = os.getenv("X_API_BEARER_TOKEN")
X_API_ACCESS_TOKEN = os.getenv("X_API_ACCESS_TOKEN")
X_API_ACCESS_TOKEN_SECRET = os.getenv("X_API_ACCESS_TOKEN_SECRET")

# X API Endpoint for posting tweets
X_API_URL = "https://api.twitter.com/2/tweets"

def x_client():
    # Authenticate with OAuth 1.0a Context (Required for `tweet.write`)
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_KEY_SECRET,
        bearer_token=X_API_BEARER_TOKEN,
        access_token=X_API_ACCESS_TOKEN,
        access_token_secret=X_API_ACCESS_TOKEN_SECRET
    )

def post_to_x(goal_number, period, goal_time):
    """Posts a tweet when Ovechkin scores."""
    tweet_text = f"🚨 Ovechkin has scored goal #{goal_number} at {goal_time} in period {period}! 🚨 #ALLCAPS #NHL"

    try:
        response = x_client().create_tweet(text=tweet_text)
        print(f"✅ Tweet posted successfully! {response.data}")
    except tweepy.TweepyException as e:
        print(f"❌ Failed to post tweet: {e}")


"""
TODO: check out to determine if a goal was disallowed and update GOAL_STATE_FILE, delete comment
- generate a GIF to post to comment that shows the goal happening?
- post notification of event to Argus so you could watch it?
- post link to goal if present: highlightClipSharingUrl
- store schedule.json since it's fixed?
"""

DEBUG=False

def read_last_goal():
    """Reads the last goal number from the state file."""
    try:
        with open(GOAL_STATE_FILE, "r") as f:
            data = json.load(f)
            return data.get("last_goal", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0

def write_last_goal(goal_number):
    """Writes the latest goal number to the state file."""    
    with open(GOAL_STATE_FILE, "w") as f:
        json.dump({"last_goal": goal_number}, f)

def post_github_comment(goal_number, period, goal_time):
    """Posts a comment on GitHub."""
    comment = f"🚨 Ovechkin has scored his **{goal_number}** goal at **{goal_time}** in period {period}! 🚨"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {"body": comment}

    if DEBUG:
        print(f"Would have posted: {comment}")
        return

    response = requests.post(GITHUB_API_URL, json=payload, headers=headers)
    if response.status_code == 201:
        print("Comment posted successfully!")
    else:
        print(f"Failed to post comment: {response.text}")

def check_and_notify(goal_number, period, goal_time):
    """Check if the goal is new and notify."""
    last_goal = read_last_goal()
    if goal_number > last_goal:
        total = goal_number + GOALS_AT_START_OF_YEAR
        print(f"New goal detected: {goal_number}, {total} total")
        post_github_comment(total, period, goal_time)
        post_to_x(total, period, goal_time)
        write_last_goal(total)
        return True
    else:
        print(f"No new goals. Last known goal: {last_goal}")
        return False

def is_today(date): 
    return date.date() == datetime.now().date()

def is_date_past(date):
    return date.date() < datetime.now().date()

def convert_utc_to_pst(date):
    return date.astimezone(timezone('US/Pacific'))

def generate_cron_schedule_for_remaining_games():
    # 1/5 3-6 3 3 * 
    games = get_scheduled_games()
    for game in games:
        game_id = game["id"]
        # game_date = datetime.strptime(game["gameDate"], "%Y-%m-%d")
        game_date = datetime.strptime(game["startTimeUTC"], "%Y-%m-%dT%H:%M:%SZ")
        cron_date = f"1/5 {game_date.hour}-{game_date.hour+3} {game_date.day} {game_date.month} *"
        print(f"{cron_date}")

def get_scheduled_games():
    """reads the schedule from schedule.json or fetches it from the NHL API."""
    try:
        with open(SCHEDULE_FILE, "r") as f:
            return json.load(f).get("games", [])
    except:
        print("Fetching schedule from NHL API.")
        url = SCHEDULE_URL
        response = requests.get(url)
        return response.json().get("games", [])

def get_todays_game():
    """Fetches current games and checks if the Capitals are playing."""
    games = get_scheduled_games()
    for game in games:
        game_date = datetime.strptime(game["startTimeUTC"], "%Y-%m-%dT%H:%M:%SZ")
        if is_today(game_date):
            return game["id"]        
    return None

"""
 {
      "eventId": 1067,
      "periodDescriptor": {
        "number": 3,
        "periodType": "REG",
        "maxRegulationPeriods": 3
      },
      "timeInPeriod": "16:01",
      "timeRemaining": "03:59",
      "situationCode": "1551",
      "homeTeamDefendingSide": "right",
      "typeCode": 505,
      "typeDescKey": "goal",
      "sortOrder": 744,
      "details": {
        "xCoord": -64,
        "yCoord": 3,
        "zoneCode": "O",
        "shotType": "snap",
        "scoringPlayerId": 8471214,
        "scoringPlayerTotal": 31,
        "assist1PlayerId": 8478911,
        "assist1PlayerTotal": 18,
        "eventOwnerTeamId": 15,
        "goalieInNetId": 8476883,
        "awayScore": 2,
        "homeScore": 1,
        "highlightClipSharingUrl": "https://nhl.com/video/tbl-wsh-ovechkin-scores-goal-against-andrei-vasilevskiy-6369498269112",
        "highlightClipSharingUrlFr": "https://nhl.com/fr/video/tbl-wsh-ovechkin-marque-un-but-contre-andrei-vasilevskiy-6369498560112",
        "highlightClip": 6369498269112,
        "highlightClipFr": 6369498560112,
        "discreteClip": 6369497777112,
        "discreteClipFr": 6369497775112
      },
      "pptReplayUrl": "https://wsr.nhle.com/sprites/20242025/2024020950/ev1067.json"
    },
"""
def check_ovechkin_goals(game_id):
    """Fetches the game feed and checks if Ovechkin has scored."""
    url = PLAY_BY_PLAY_FORMAT.format(game_id=game_id)    
    response = requests.get(url)
    data = response.json()

    new_goal = False
    for play in data["plays"]:
        if play["typeDescKey"] == "goal":
            if play["details"]["scoringPlayerId"] == OVECHKIN_PLAYER_ID:
                goal_number = play["details"]["scoringPlayerTotal"]
                period = play["periodDescriptor"]["number"]
                goal_time = play["timeInPeriod"]
                new_goal = check_and_notify(goal_number, period, goal_time)
    return new_goal

if __name__ == "__main__":
    game_id = get_todays_game()
    if game_id:
        print("Capitals are playing today.")
        if check_ovechkin_goals(game_id):
            print("Goal detected!")        
    else:
        print("Capitals are not playing right now.")
    # generate_cron_schedule_for_remaining_games()
    # get_todays_game()
