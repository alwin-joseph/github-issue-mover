# Tools Details 
We have written a tool to migrate issues from GitHub javaee repositories to eclipse-ee4j repository. We can't use GitHub public API(https://developer.github.com/v3/)) for this migration work. If we use it,  after importing 10-15 issues(with enough delay in between post operation) we would hit GitHub Abuse limit(https://developer.github.com/v3/#abuse-rate-limits). This is because GitHub doesn't allow users to post bulk content creation request using public API. As a work around GitHub offers an experimental issue importer API that is suitable for issue import(https://gist.github.com/jonmagic/5282384165e0f86ef105). So we developed the tool using it(that's the GitHub recommended way). 
## Prerequisite:
In order to move the issues from GitHub source repository to target repository using GitHub issue importer API, we need to use an user that is the admin of the target repository. So before we can start moving issues from javaee to eclipse-ee4j, Eclipse needs to provide admin access for eclipse-ee4j to one of our account(our bot glassfishrobot). If that is a problem for them, they can share the user id and API bearer token of one of the eclipse-ee4j admin account. Otherwise we can share the tool with Eclipse and they need to run it by themselves.
## Tool Features:
* All the issue IDs are preserved if target repository is empty. The tool can also accept start issue and ending issue id to migrate (if the starting and ending issue is not provided by default the tool would migrate all the issues from the source to target repository). For e.g If the target repository is not empty and there are 3 issues in the target repository, the tool can start migrating issue from 4 to last from the source repository to the destination repository. Once the migration is done, tool can migrate issue 1 to 3 at last. So in that case issue id 1 to 3 in the source repository would not have proper issue mapping in target repository. 
* The tool would create a "blank" issue for any PR, provide a link back to JavaEE GitHub repo and would close the dummy issue for the PR.
* The tool would migrate original issue's title, body, creation date, updated at date, closed at date(if the issue is closed), issue state(open/close),  all the labels associated with the original issue, milestone and all the comments with actual comment date.
* All the issues would be raised by the user id that we are using to migrate the issue. Actual issue raiser would no longer be the issue raiser in the target repository. As a work around, the tool would add the actual issue raiser information in a comment.
* All the closed issues in the source repository would be closed by the user id that we are using to migrate the issue in the target repository. The user who closed the actual issue would no longer be the one who closes the issue in the target repository. As a work around, the tool would add the closed by user information in a comment.
* All the issue comments would be raised by the user id that we are using to migrate the issue. As a work around the tool would add the commenter name before the comment body(i.e @<commentor> Commented <comment body>)
* If the assignee of the issue in javaee org is also member of eclipse-ee4j org, the member would be automatically assigned to the new issue.If not, the issue would be unassigned and the assignee information would be preserved in the issue comment.
* The tool would preserve the milestones for the issues. The milestones associated with old issues would be created and would be associated with issues in eclipse-ee4j organisation with their respective 'title', 'state','description' and 'due_on' filed. The milestones with no issues associated would not be moved to the new organisation.
* In order to minimise the data loss described above and in order to link the source issue to the target issue, the tool would add a comment at the end of the issue like following
Issue Imported From:<original issue link>
Original Issue Raised By:<user>/Unassigned
Original Issue Assigned To:<user>
Original Issue Closed By:<user>
Closed by information will only be available for the closed issues.
* The tool would close the original issue in javaee GitHub repo. It would add a comment on the closed issue as "Closing this as this issue is migrated to <new issue link>"

# How to run the tool

**Prerequisite** Docker should be installed on the system

```docker run -it -e source_repo=<source_repo> -e target_repo=<target_repo> -e bearer_token=<bearer_token> -e user=<user> -e http_proxy=<http_proxy> -e https_proxy=<https_proxy> arindamb/gh-issue-mover```
  
Here is brief explanation of all the mandatory and optional environment variable.
* source_repo - Name of the source repository. It should be org_name/repo_name format. e.g - javaee/grizzly. It's **mandatory** 
* target_repo - Name of the target repository. It should be org_name/repo_name format. e.g - eclipse-ee4j/grizzly. It's **mandatory**
* bearer_token - GitHub Bearer token for eclipse-ee4j org admin. It's **mandatory**
  
* user - GitHub user id for eclipse-ee4j org admin. It's **mandatory**
* start_issue - First issue number from the source repository for the migration. By default it's 1. It's **optional**
* end_issue - last issue in the source repository to be migrated. By default it's the last issue of the source repository. It's **optional**
