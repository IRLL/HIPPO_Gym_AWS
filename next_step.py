import json, boto3, os
from datetime import datetime, timezone

S3 = boto3.resource('s3')
S3CLIENT = boto3.client('s3')
SNS = boto3.client('sns')
ROUTE53 = boto3.client('route53')
HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "OPTIONS,GET"
}

def lambda_handler(event, context):
    print(event)
    qs = event.get('queryStringParameters', dict())
    UserId = None
    projectId = qs.get('projectId', None) 
    project = check_project(projectId)
    userId = qs.get('userId', None)
    if project and userId:
        step = get_user_step(userId, projectId, event, project)
        stepFile = get_step_file(project, step)
        topicArn = check_step_events(project, step)
        if topicArn:
            send_message(topicArn, projectId, userId)
        content = get_content(projectId, userId, stepFile, project)
        print('Content: ', content)
        return {
            'statusCode': 200,
            'headers': HEADERS,
            'body': json.dumps({'page': content, 'css': None})
        }
    return {
        'statusCode': 400,
        'headers': HEADERS,
        'body': json.dumps('Project ID Not Found')
    }

def send_message(topicArn, projectId, userId):
    response = SNS.publish(
        TopicArn=topicArn,
        Message=json.dumps({"projectId":projectId,"userId":userId})
    )
    print('Send Message: ', response)

def get_content(projectId, userId, stepFile, project):
    if stepFile == 'game': # Temp behavior to be replaced by actual template
        if check_dns(userId):
            return "show_game_page"
        decrement_user_step_count(userId, projectId, project)
        return "wait"
    bucket = project.get('bucket') or os.environ['BUCKET']
    filename = check_groups(bucket, projectId, userId, stepFile)
    print(filename)
    try:
        content = S3.Object(bucket, filename).get()['Body'].read().decode('utf-8')
        return content
    except: 
        return 'Content Not Found'

def check_groups(bucket, projectId, userId, stepfile):
    files = S3CLIENT.list_objects(Bucket=bucket, Prefix=projectId).get('Contents')
    steps = []
    for file in files:
        filename = file.get('Key')
        if 'html' in filename:
            steps.append(filename)
    stepfile = stepfile.replace('.html','')
    this_step = []
    for step in steps:
        if stepfile in step:
            this_step.append(step)
    if len(this_step) > 1:
        group = bucketer(userId, len(this_step))
        for step in this_step:
            if f'-{group}.html' in step:
                return step
    return f'{projectId}/{stepfile}.html'

def check_step_events(project, step):
    topicArn = None
    if str(project['events']['startServerStep']) == step:
        topicArn = os.environ['START_SERVER_TOPIC_ARN']
    elif str(project['events']['stopServerStep']) == step:
        topicArn = os.environ['STOP_SERVER_TOPIC_ARN']
    return topicArn

def get_step_file(project, step):
    steps = project.get('steps')
    stepFile = steps.get(step, steps.get('finalStep'))
    return stepFile

def get_user_step(userId, projectId, event, project):
    bucket = project.get('bucket') or os.environ['BUCKET']
    filename = f'{projectId}/Users/{userId}'
    try:
        userFile = S3.Object(bucket, filename).get()['Body'].read().decode('utf-8')
        userRecord = json.loads(userFile)
        print(userRecord)
    except:
        userRecord = {
            "created": str(datetime.now(timezone.utc)), 
            "nextStep": 1,
            "requests": []
        }
        print('New User Created')
    nextStep = userRecord['nextStep']
    userRecord['nextStep'] += 1
    userRecord['requests'].append(event)
    response = S3.Object(bucket, filename).put(
        ACL='private',
        Body=json.dumps(userRecord).encode('utf-8'),
        ContentEncoding='utf-8',
    )
    return str(nextStep)

def decrement_user_step_count(userId, projectId, project):
    bucket = project.get('bucket') or os.environ['BUCKET']
    filename = f'{projectId}/Users/{userId}'
    userFile = S3.Object(bucket, filename).get()['Body'].read().decode('utf-8')
    userRecord = json.loads(userFile)
    userRecord['nextStep'] -= 1
    response = S3.Object(bucket, filename).put(
        ACL='private',
        Body=json.dumps(userRecord).encode('utf-8'),
        ContentEncoding='utf-8',
    )
    
def check_project(projectId):
    print(projectId)
    bucket = os.environ['BUCKET']
    filename = 'project_master_list.json'
    projectList = S3.Object(bucket, filename).get()['Body'].read().decode('utf-8')
    print(projectList)
    projectList = json.loads(projectList)
    for project in projectList.get('projects', list()):
        if projectId == project.get('id'):
            if project.get('live'):
                return project
    return None

def check_dns(userId):
    dnsEntry = f"{userId}.{os.environ['ROOT_DOMAIN']}." # must include trailing '.'
    response = ROUTE53.list_resource_record_sets(
        HostedZoneId = os.environ['HOSTED_ZONE_ID'],
        StartRecordName = dnsEntry,
        StartRecordType = 'A',
        MaxItems = '1'
    )
    print("DNS Check: ", response)
    if response['ResourceRecordSets'][0]['Name'] != dnsEntry:
        return False
    return True

def bucketer(UUID, n):
  # Get the number of requisite hex characters for the UUID
  hex_chars = UUID[-num_chars(n):]

  # sum last largest_prime digits
  sum = 0
  for char in hex_chars:
    sum += int(char, 16)

  return sum % n

def num_chars(n):
  # Determine all prime factors
  i = 2
  factors = []
  while i * i <= n:
      if n % i:
          i += 1
      else:
          n //= i
          factors.append(i)
  if n > 1:
      factors.append(n)
  
  # Get unique factors
  factors = list(set(factors))

  # Remove 2
  factors.pop(0)

  product = 1

  for factor in factors:
    product *= factor

  return product
