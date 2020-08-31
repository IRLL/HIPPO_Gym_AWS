import json, boto3, os

S3 = boto3.resource('s3')

def lambda_handler(event, context):
    config, warnings = verify_config(event) 
    if config:
        try:
            update_project_master_list(config)
            return {
                'statusCode': 200,
                'body': warnings
            }
        except:
            return {
                'statusCode': 400,
                'body': 'Error with S3'
            }
    return {
        'statusCode': 400,
        'body': warnings
    }

def update_project_master_list(config):
    bucket = os.environ['BUCKET']
    filename = 'project_master_list.json'
    projectList = S3.Object(bucket, filename).get()['Body'].read().decode('utf-8')
    print(projectList)
    projectList = json.loads(projectList)
    for index, project in enumerate(projectList['projects']):
        if project['id'] == config['id']:
            projectList['projects'].pop(index)
    projectList['projects'].append(config)
    print(f'Updated Project List: {projectList}')
    response = S3.Object(bucket, filename).put(
        ACL = 'private',
        Body = json.dumps(projectList, indent=2).encode('utf-8'),
        ContentEncoding = 'utf-8',
        StorageClass = 'STANDARD'
    )
    print(f'S3 Response: {response}')

def verify_config(event):
    config = dict()
    warnings = ''
    keys = {
        'id': 'required',
        'name': 'required',
        'live': None,
        'researcher': None,
        'team_members': None,
        'ecsTask': 'required',
        'steps': 'required',
        'events': 'required',
        'maxRuntime': 'required',
        'bucket': None
    }
    for key in keys.keys():
        config[key] = event.get(key)
        if keys[key] == 'required':
            if not config.get(key):
                return False, f'Missing Config Value for {key}'
    events = config.get('events')
    for item in ('startServerStep','stopServerStep'):
        if not item in events.keys():
            return False, '"{item}" missing in "events" Config'
        if not events[item]:
            warnings += f'Warning: {item} is set to None\n'
    return config, warnings
    

