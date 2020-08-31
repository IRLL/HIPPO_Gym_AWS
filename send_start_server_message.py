import json, boto3, os

SNS = boto3.client('sns')
HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "OPTIONS,GET"
}

def lambda_handler(event, context):
    print(event)
    qs = event.get('queryStringParameters', dict())
    projectId = qs.get('projectId', None)
    userId = qs.get('userId', None)
    if projectId and userId:
        send_message(projectId, userId)
        return {
            'statusCode': 200,
            'headers': HEADERS
        }
    return {
        'statusCode': 400,
        'headers': HEADERS
    }

def send_message(projectId, userId):
    response = SNS.publish(
        TopicArn= os.environ['START_SERVER_TOPIC_ARN'],
        Message = json.dumps({
            "projectId": projectId,
            "userId": userId
        }),
    )
