# post_to_linkedin.py

import os
import json
from linkedin_api import Linkedin
from github import Github
from datetime import datetime

def get_commit_info():
    """Get the latest commit information"""
    event_path = os.getenv('GITHUB_EVENT_PATH')
    if event_path and os.path.exists(event_path):
        with open(event_path) as f:
            event = json.load(f)
            if 'release' in event:
                return format_release_message(event['release'])
            elif 'commits' in event:
                return format_commit_message(event['commits'][0])
    return None

def format_release_message(release):
    """Format message for a new release"""
    return f"""🎉 New Release: {release['name']}

{release['body'][:200]}... 

Check out the full release notes:
{release['html_url']}

#github #development #coding #newrelease"""

def format_commit_message(commit):
    """Format message for a significant commit"""
    return f"""📝 New Update: {commit['message'].split('\n')[0]}

Repository: {os.getenv('GITHUB_REPOSITORY')}
🔗 {commit['url']}

#github #development #coding"""

def post_to_linkedin(message):
    """Post the message to LinkedIn"""
    api = Linkedin(os.getenv('LINKEDIN_ACCESS_TOKEN'))
    
    # Create the post using LinkedIn API v2
    api.post(message)

def main():
    try:
        message = get_commit_info()
        if message:
            post_to_linkedin(message)
            print("Successfully posted to LinkedIn")
        else:
            print("No relevant content to post")
    except Exception as e:
        print(f"Error posting to LinkedIn: {str(e)}")
        raise e

if __name__ == "__main__":
    main()