import json, boto3, time, uuid, os, datetime

S3 = boto3.resource('s3')
ECS = boto3.client('ecs')
EC2 = boto3.client('ec2')
ROUTE53 = boto3.client('route53')
EVENT_BRIDGE = boto3.client('events')

def lambda_handler(event, context):
    print('Event: ',event)
    message = json.loads(event['Records'][0]['Sns']['Message'])
    projectId = message.get('projectId', None)
    if projectId:
        ecsTask, maxRuntime = check_project(projectId)
    else:
        ecsTask = None
    userId = message.get('userId', None)
    if ecsTask:
        address = start_server(ecsTask, projectId, userId, maxRuntime)
        if address:
            return {
                'statusCode': 200,
            }
    return {
        'statusCode': 400,
    }

def start_server(ecsTask, projectId, userId, maxRuntime):
    set_shutdown_event(userId, maxRuntime)
    create_cluster(projectId, userId)
    taskId = run_task(ecsTask, userId)
    if taskId:
        ip = get_ip(taskId,userId)
        if ip:
            dnsEntry = create_dns_entry(ip, userId)
            return dnsEntry
    return None

def set_shutdown_event(userId, maxRuntime):
    now = datetime.datetime.now()
    change = datetime.timedelta(minutes=int(maxRuntime))
    t = now + change
    shutdownTime = f'cron({t.minute} {t.hour} {t.day} {t.month} ? {t.year})'
    response = EVENT_BRIDGE.put_rule(
        Name=userId,
        ScheduleExpression=shutdownTime,
        State='ENABLED',
        Description='Shutdown Sever',
    )
    ruleArn = response['RuleArn']
    print('Shutdown Rule: ',ruleArn)
    response = EVENT_BRIDGE.put_targets(
        Rule=userId,
        Targets=[
            {
                'Id':userId,
                'Arn':os.environ['STOP_SERVER_TOPIC_ARN'],
                'Input': json.dumps({"userId":userId})
            }
        ]
    )
    print('Shutdown Targets Response: ',response)

def create_cluster(projectId, userId):
    response = ECS.create_cluster(
        clusterName = userId,
        tags=[
            {
                'key':'projectId',
                'value':projectId
            },
            {
                'key':'userId',
                'value':userId
            }
        ],
        capacityProviders=[
            'FARGATE_SPOT',
            'FARGATE'
        ],
        defaultCapacityProviderStrategy=[
            {
                'capacityProvider': 'FARGATE_SPOT',
                'base': 1
            }
        ]
    )
    print('Cluster Response: ',response)
    return

def run_task(ecsTask, userId):
    for _ in range(3):
        try:
            response = ECS.run_task(
                cluster=userId,
                capacityProviderStrategy=[
                    {
                        'capacityProvider': 'FARGATE_SPOT',
                    }
                ],
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets':[
                            os.environ['SUBNET']
                        ],
                        'securityGroups': [
                            os.environ['SECURITY_GROUP']
                        ],
                        'assignPublicIp':'ENABLED'
                    }
                },
                taskDefinition=ecsTask
                )
            print('Run Task Response: ',response)
            taskId = response['tasks'][0]['containers'][0]['taskArn']
            return taskId
        except:
            time.sleep(20)
    return None

def get_ip(taskId, userId):
    ip = None
    for i in range(3):
        if not ip:
            time.sleep(20)
            response = ECS.describe_tasks(
                cluster = userId,
                tasks = [taskId]
            )
            print('Get IP Response: ',response)
            try:
                eni = response['tasks'][0]['attachments'][0]['details'][1]['value']
                print('ENI :',eni)
                result = EC2.describe_network_interfaces(
                    NetworkInterfaceIds = [eni]
                )
                print('Describe ENI: ',result)
                ip = result['NetworkInterfaces'][0]['Association']['PublicIp']
                print('IP: ',ip)
                print(i)
            except:
                ip = None
    return ip

def create_dns_entry(ip,userId):
    dnsEntry = f"{userId}.{os.environ['ROOT_DOMAIN']}"
    print('DNS Entry:',dnsEntry)
    try:
        response = ROUTE53.change_resource_record_sets(
            HostedZoneId= os.environ['HOSTED_ZONE_ID'],
            ChangeBatch={
                'Changes': [
                    {
                        'Action': 'CREATE',
                        'ResourceRecordSet': {
                            'Name': dnsEntry,
                            'Type': 'A',
                            'TTL': 60,
                            'ResourceRecords': [
                                {
                                    'Value': ip
                                },
                            ]
                        }
                    }    
                ]
            }
        )
        print('DNS Entry Response: ',response)
        return dnsEntry
    except: 
        return None
    
def check_project(projectId):
    bucket = os.environ['BUCKET']
    filename = 'project_master_list.json'
    projectList = S3.Object(bucket, filename).get()['Body'].read().decode('utf-8')
    projectList = json.loads(projectList)
    for project in projectList['projects']:
        if projectId == project['id']:
            maxRuntime = project.get('maxRuntime') or 60
            if int(maxRuntime) > int(os.environ['MAX_RUNTIME']):
                maxRuntime = int(os.environ['MAX_RUNTIME'])
            return project.get('ecsTask'), maxRuntime
    return None, None

