import json
import requests
import time
import sys
import os

request_count = 0
milestones_cache = {}
target_org_users = []

def post_data(url,payload,headers):
    global request_count
    retry_cnt = 1
    while retry_cnt < 10:
        request_count = request_count + 1
        response = requests.post(url ,data=json.dumps(payload), headers=headers)
        if response.ok:
            return json.loads(response.text),response.headers
        time.sleep(5)
        retry_cnt = retry_cnt + 1    
    sys.exit('POST operation for '+url+' sending status '+str(response.status_code) + '\n for payload \n'+ json.dumps(payload) + '\nResponse is\n'+response.text)
        


def get_data(url,headers):  
    global request_count
    retry_cnt = 1
    while retry_cnt < 10:
        request_count = request_count + 1
        response = requests.get(url,headers=headers)
        if response.ok:
            return json.loads(response.text),response.headers
        time.sleep(5)
        retry_cnt = retry_cnt + 1     
    sys.exit('GET operation for '+url+' sending status '+str(response.status_code))

def get_paginated_data(url,headers):
    data,response_header = get_data(url,headers)
    if 'Link' in response_header:
        starting_page = 2
        while True:
            paginated_url = url+'?page='+str(starting_page)
            paginated_data,response_header = get_data(paginated_url,headers)
            for d in paginated_data:
                data.append(d)
            if 'rel="next"' not in response_header['Link']:
                break
            starting_page = starting_page + 1  
    return data


def populate_target_org_members(target_org_members_url,headers):
    members = get_paginated_data(target_org_members_url,headers)
    for member in members:
        target_org_users.append(member['login'])
      
def create_milestone(milestones_post_url,headers,milestone):
    global milestones_cache
    if not milestones_cache:
        existing_milestones = get_paginated_data(milestones_post_url,headers)
        if existing_milestones:
            for m in existing_milestones:
                milestones_cache[m['title']] = m['number']   
    milestone_title = milestone['title']
    if milestone_title in milestones_cache:
        return milestones_cache[milestone_title]
    else:
        new_milestone = {}
        new_milestone['title'] = milestone['title']
        new_milestone['state'] = milestone['state']
        new_milestone['description'] = milestone['description']
        new_milestone['due_on'] = milestone['due_on']
        new_milestone_data,_ = post_data(milestones_post_url,new_milestone,headers)
        milestones_cache[new_milestone_data['title']] = new_milestone_data['number']
        return new_milestone_data['number']

def construct_issue(issue_data,milestone_number):
    global target_org_users
    issue = {}
    comments = []
    if 'pull_request' in issue_data:
        issue['title'] = 'Place holder issue for Pull Request '+ str(issue_data['number']) 
        issue['body'] = 'This is a place holder issue for Pull request from ' + issue_data['html_url']
        issue['closed'] = True
    else:
        issue['title'] = issue_data['title']
        if issue_data['body'] != "":
            issue['body'] = issue_data['body']
        else:
            issue['body'] = 'No description provided.'
        issue['created_at'] = issue_data['created_at']
        issue['updated_at'] = issue_data['updated_at']
        labels = issue_data['labels']
        issue_labels = []
        for label in labels:
            issue_labels.append(label['name'])
        issue['labels'] = issue_labels 
        milestone = issue_data['milestone']
        if milestone is not None:
            issue['milestone'] = milestone_number
        initial_comment ={}
        assignee = 'Unassigned'
        if issue_data['assignee'] is not None:    
            assignee = '@'+issue_data['assignee']['login']
            if issue_data['assignee']['login'] in target_org_users:
                issue['assignee'] = issue_data['assignee']['login']
        initial_comment['body'] = '* **Issue Imported From:** ' + issue_data['html_url'] + '\n* **Original Issue Raised By:**@' + issue_data['user']['login'] + '\n* **Original Issue  Assigned To:** '+assignee
        if issue_data['state'] == 'closed':
            issue['closed'] = True
            issue['closed_at'] = issue_data['closed_at']
            initial_comment['body'] = initial_comment['body'] + '\n* **Original Issue  Closed By:**@'+ issue_data['closed_by']['login']
        comments.append(initial_comment)
        comments_url = issue_data['comments_url']
        all_comments,_ = get_data(comments_url,headers)
        for c in all_comments:
            comment = {}
            comment['created_at'] = c['created_at']
            comment['body'] = '@' + c['user']['login'] + ' Commented \n' + c['body']
            comments.append(comment)
    payload = {}
    payload['issue'] = issue
    payload['comments'] = comments  
    return payload 

def close_original_issue(url_source_repo,headers,issue_data,new_issue_api_url):
    comment = {}
    comment_url = issue_data['comments_url']
    new_issue_api_url_split = new_issue_api_url.split('/')
    html_url = 'https://github.com/'+new_issue_api_url_split[4] + '/'+ new_issue_api_url_split[5] + '/issues/' + new_issue_api_url_split[7]
    comment['body'] = '**Closing this as this issue is migrated to** ' + html_url
    post_data(comment_url,comment,headers)
    issue = {}
    issue['state'] = 'closed'
    url = url_source_repo + '/issues/' + str(issue_data['number'])
    post_data(url,issue,headers)

def import_issues(url_source_repo, url_target_repo, headers, start_issue, end_issue,user,close_issue):
    if end_issue is None:
        url = url_source_repo + '/issues?state=all'
        all_issues,_ = get_data(url,headers)
        end_issue = all_issues[0]['number']
    issue = start_issue
    issue_post_url = url_target_repo + '/import/issues'
    milestones_post_url = url_target_repo + '/milestones'
    while issue <= end_issue:
        rate_limit_url = 'https://api.github.com/users/' + user
        _,req_headers = get_data(rate_limit_url,headers)
        global request_count
        if request_count > 4900:
            remaning_rate_limit = int(req_headers['X-RateLimit-Remaining'])
            if remaning_rate_limit < 20:
                reset_time = int(req_headers['X-RateLimit-Reset'])
                current_time = int(time.time())
                time_to_sleep = reset_time - current_time
                time.sleep(time_to_sleep)
                request_count = 1
        url = url_source_repo + '/issues/'+ str(issue)    
        issue_data,_ = get_data(url,headers)
        milestone_number = None
        milestone = issue_data['milestone']
        if milestone is not None:
            milestone_number = create_milestone(milestones_post_url,headers,milestone)
        issue_payload = construct_issue(issue_data,milestone_number)
        print('Migrating Issue Number ' + str(issue))
        new_issue,_ = post_data(issue_post_url,issue_payload,headers)
        issue_creation_status = {}
        cnt = 0
        while cnt < 20:
            callback_url = new_issue['url'] 
            issue_creation_status,_ = get_data(callback_url,headers)
            if issue_creation_status['status'] == 'imported':
                break
            else:
                time.sleep(5)
                cnt = cnt + 1
        if issue_data['state'] == 'open' and 'pull_request' not in issue_data and close_issue != 'n':
            close_original_issue(url_source_repo,headers,issue_data,issue_creation_status['issue_url'])
        print('Completed Migration of Issue Number ' + str(issue))          
        issue = issue + 1
    
if __name__ == "__main__":
    source_repo = os.environ.get('source_repo')
    target_repo = os.environ.get('target_repo')
    bearer_token = os.environ.get('bearer_token')
    close_issue =  os.environ.get('close_issue')
    start_issue = int(os.environ.get('start_issue','1'))
    end_issue = os.environ.get('end_issue')
    user = os.environ.get('user')
    if source_repo is None:
        sys.exit('Please enter source repo as an environment variable')
    if target_repo is None:
        sys.exit('Please enter target repo as an environment variable')
    if bearer_token is None:
        sys.exit('Please enter bearer_token repo as an environment variable')
    if user is None:
        sys.exit('Please enter github user name for the bearer_token as an environment variable')    
    if end_issue is not None:
        end_issue = int(end_issue)
    url_template = 'https://api.github.com/repos/{repo}'
    headers = {'user-agent': 'gf-issue-mover' , 'Accept':'application/vnd.github.golden-comet-preview+json'}
    headers['Authorization'] = 'token ' + bearer_token
    url_source_repo = url_template.format(repo=source_repo)
    url_target_repo = url_template.format(repo=target_repo)
    target_org_name = target_repo.split('/')[0]
    print("Getting list of collaborators from "+ target_org_name)
    target_org_members_url = 'https://api.github.com/orgs/'+ target_org_name +'/members'
    populate_target_org_members(target_org_members_url,headers)
    print('Total number of collaborators in  '+ target_org_name+' is '+str(len(target_org_users)))
    print("Starting Migration of issues from repository "+source_repo+" to "+target_repo+" repository at "+time.strftime("%H:%M:%S"))
    import_issues(url_source_repo, url_target_repo, headers, start_issue, end_issue,user, close_issue)
    print("Completed Migration of issues from repository "+source_repo+" to "+target_repo+" repository at "+time.strftime("%H:%M:%S"))

