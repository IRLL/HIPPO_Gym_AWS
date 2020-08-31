import json, boto3, time, os

ECS = boto3.client('ecs')
ROUTE53 = boto3.client('route53')
EVENT_BRIDGE = boto3.client('events')

def lambda_handler(event, context):
    print(event)
    message = json.loads(event['Records'][0]['Sns']['Message'])
    userId = message.get('userId', None)
    if userId:
        stop_server(userId)

        return {
            'statusCode': 200,
        }
    return {
        'statusCode': 400,
    }

def stop_server(userId):
    try:
        taskId = get_task(userId)
        stop_task(userId, taskId)
    except Exception as error: 
        print(f'Stop Task Failed for {userId}')
        print(error)
    try:
        stop_cluster(userId)
    except Exception as error:
        print(f'Stop Cluster Failed for {userId}')
        print(error)
    try:
        dnsEntry = f'{userId}.irll.net'
        ip, ttl = get_ip_and_ttl(dnsEntry)
        remove_dns(dnsEntry, ip, ttl)
    except Exception as error:
        print(f'Delete DNS Failed for {dnsEntry}')
        print(error)
    try:
        delete_cron(userId)
    except:
        print(f'Delete Cron Failed for {userId}')

def delete_cron(userId):
    response = EVENT_BRIDGE.remove_targets(
        Rule=userId,
        Ids=[userId]
    )
    print("Remove Targets: ", response)
    response = EVENT_BRIDGE.delete_rule(
        Name=userId,
    )
    print("Event Bridge: ", response)

def get_task(userId):
    response = ECS.list_tasks(
        cluster=userId
    )
    print('Get Task: ', response)
    taskId = response['taskArns'][0]
    print(taskId)
    return taskId

def stop_task(userId, taskId):
    response = ECS.stop_task(
        cluster = userId,
        task = taskId,
        reason = 'Done'
    )
    print('Task: ', response)

def stop_cluster(userId):
    for _ in range(3):
        try:
            response = ECS.delete_cluster(
                cluster = userId
            )
            print('Cluster: ', response)
            return
        except ClusterContainsTasksException:
            time.sleep(20)
        except:
            raise

def get_ip_and_ttl(dnsEntry):
    response = ROUTE53.list_resource_record_sets(
        HostedZoneId = os.environ['HOSTED_ZONE_ID'],
        StartRecordName = dnsEntry,
        StartRecordType = 'A',
        MaxItems = '1'
    )
    print('Route53 lookup: ', response)
    ip = response['ResourceRecordSets'][0]['ResourceRecords'][0]['Value']
    ttl = response['ResourceRecordSets'][0]['TTL']
    print('Ip: ', ip)
    print('TTL: ', ttl)
    return ip, ttl

def remove_dns(dnsEntry, ip, ttl):
    response = ROUTE53.change_resource_record_sets(
        HostedZoneId = os.environ['HOSTED_ZONE_ID'],
        ChangeBatch = {
            'Changes': [
                {
                    'Action': 'DELETE',
                    'ResourceRecordSet': {
                        'Name': dnsEntry,
                        'Type': 'A',
                        'TTL': ttl,
                        'ResourceRecords': [
                            {
                                'Value': ip
                            }
                        ]
                    }
                }
            ]
        }
    )
    print('Route53 delete: ', response)
