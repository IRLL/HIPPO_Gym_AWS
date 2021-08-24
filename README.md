# HIPPO Gym 
##### Human Input Parsing Platform for Openai Gym
[hippogym.irll.net](https://irll.net)

Written by [Nick Nissen](https://nicknissen.com), Payas Singh, Nadeen Mohammed, and Yuan Wang
Supervised by [Matt Taylor](https://drmatttaylor.net) and Neda Navi
For the Intelligent Robot Learning Laboratory [(IRLL)](https://irll.ca) at the University of Alberta [(UofA)](https://ualberta.ca)
Supported by the Alberta Machine Intelligence Institure [(AMII)](https://amii.ca)

For questions or support contact us at [hippogym.irll@gmail.com](mailto:hippogym.irll@gmail.com)

The HIPPO Gym Project contains 4 repositories:

1. The main framework: [HIPPO_Gym](https://github.com/IRLL/HIPPO_Gym)

2. The AWS code and instructions: [HIPPO_Gym_AWS](https://github.com/IRLL/HIPPO_Gym_AWS)

3. The React Front End: [HIPPO_Gym_React_FrontEnd](https://github.com/IRLL/HIPPO_Gym_FrontEnd_React)

4. The SSL Certificate Getter: [HIPPO_Gym_SSL](https://github.com/IRLL/HIPPO Gym_SSL)

For members of the IRLL or anyone whose organization has already setup the AWS infrastructure, the only repo required is #1.

Anyone is welcome to use the front-end deployed to [irll.net](https://irll.net)

## AWS Lambda Functions

Python3.8 recommended

## Required Permissions:
AWS security needs are different for every organization/project. It's best to follow a strategy of least privelege and only allow the minimum required access. The authors recommend having separate roles for each Lambda Function.

Note that below permissions list only the services required. Individual admins can choose how restrictive to make each policy based on their organizational needs.

### start_server.py
- [ ] S3
- [ ] ECS
- [ ] Route53

### send_start_server_message.py
- [ ] SNS

### stop_server.py
- [ ] ECS
- [ ] Route53

### send_stop_server_message.py
- [ ] SNS

### next_step.py
- [ ] S3
- [ ] SNS
- [ ] Route53

### update_project_master_list.py
- [ ] S3

### stop_server SNS Access Policy
Add the following to the default policy:
```json
    {
      "Sid": "TrustCWEToPublishEventsToMyTopic",
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": "sns:Publish",
      "Resource": "THE_STOP_SERVER_LAMBDA_ARN"
    }
```

## Required Environment Variables:

### start_server.py

BUCKET
HOSTED_ZONE_ID
ROOT_DOMAIN
SECURITY_GROUP
STOP_SERVER_TOPIC_ARN
SUBNET
MAX_RUNTIME

### send_start_server_message.py
START_SERVER_TOPIC_ARN

### stop_server.py
HOSTED_ZONE_ID

### send_stop_server_message.py
STOP_SERVER_TOPIC_ARN

### next_step.py
BUCKET
START_SERVER_TOPIC_ARN
STOP_SERVER_TOPIC_ARN
HOSTED_ZONE_ID
ROOT_DOMAIN

### update_project_master_list.py
BUCKET

## Required Minimum Timeouts:

### start_server.py
5 minutes

### send_start_server_message.py
3 seconds

### stop_server.py
3 seconds

### send_stop_server_message.py
3 seconds

### next_step.py
3 seconds minimum
10 seconds recommended (if S3 lookup files start getting large there could be network delay, 10 seconds will prevent any future issues)

### update_project_master_list.py
3 seconds

## Overview of AWS structure:

## next_step.py

This function is the primary controller for a project. 
  - Accepts: GET, POST
  - Returns: HTML or equivalent for page display at each step.
  - Logs: Post Data, all request headers
  - Triggers: send_start_server_message.py and send_stop_server_message.py based on config file

## start_server.py

Coordinates the standup of services for the participant session:
  1. Sets cron job via Event Bridge for shutdown of services at maxRuntime
  2. Creates ECS cluster using Fargate or Fargate_Spot
  3. Starts Task on new cluster. Cluster must be pre-set, id is retrieved from config
  4. Creates DNS entry via Route53 at unique subdomain pointing to Task on Cluster

Requires longer timeout due to service start times. Must be triggered via SNS or similar service. If an HTTP trigger via API gateway is desired, then a function must be called to send the start server message via SNS as the maximum API gateway timeout is insufficient to start all the required services. See send_start_server_message.py if this functionality is desired.

## stop_server.py

Coordinates the stopping and removing of services after completion of participant session:
  1. Stops the Task on ECS Cluster
  2. Stops and Deletes the Cluster on ECS
  3. Deletes the DNS subdomain entry on Route53
  4. Deletes the cron job on Event Bridge that either called the stop_server function, or was scheduled to call the function for the given userId.

It may be desireable to delay the shutting down of services at the end of a user session. This delay cannot be achieved with the next_step function due to the maximum API Gateway timeout, and a delay cannot be directly incorporated into SNS. Should a delay under 15 minutes be desired, a middle function can be used that will sleep for the desired delay on initial call, which will then send the stop server message to SNS. See send_stop_server_message.py

## update_project_master_list.py

Allows researchers to add or update their project information to the project_master_list.json file in a safe way via the deployment script updateProject.py contained in the root dir of HIPPO Gym.
