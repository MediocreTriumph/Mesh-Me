import os
import json
import requests
from github import Github

def get_commit_info():
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
    return f"""🎉 New Release: {release['name']}

{release['body'][:200]}... 

Check out the full release notes:
{release['html_url']}

#github #development #coding #newrelease"""

def format_commit_message(commit):
    return f"""📝 New Update: {commit['message'].split('\n')[0]}

Repository: {os.getenv('GITHUB_REPOSITORY')}
🔗 {commit['url']}

#github #development #coding"""

def post_to_linkedin(message):
    access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
    author_id = os.getenv('LINKEDIN_USER_ID')
    api_url = f'https://api.linkedin.com/rest/posts'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'LinkedIn-Version': '202308',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    post_data = {
        "author": f"urn:li:person:{author_id}",
        "commentary": message,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": []
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False
    }
    
    print(f"Sending request to LinkedIn API: {json.dumps(post_data, indent=2)}")
    response = requests.post(api_url, headers=headers, json=post_data)
    print(f"Response: {response.text}")
    response.raise_for_status()

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