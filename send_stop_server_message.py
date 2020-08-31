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
    userId = qs.get('userId', None)
    if userId:
        send_message(userId)
        return {
            'statusCode': 200,
            'headers': HEADERS
        }
    return {
        'statusCode': 400,
        'headers': HEADERS
    }

def send_message(userId):
    response = SNS.publish(
        TopicArn= os.environ['STOP_SERVER_TOPIC_ARN'],
        Message = json.dumps({"userId":userId})
    )
