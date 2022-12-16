# AWS Setup instructions for HIPPO Gym

## Infrastructure Checklist:
- [ ] Lambda Functions
  - [ ] next_step.py
  - [ ] start_server.py
  - [ ] stop_server.py
- [ ] API Gateway
  - [ ] /next - endpoint: Lambda Function next_step.py
- [ ] ECR (Elastic Container Registry)
  - [ ] project repository
- [ ] ECS (Elastic Container Service)
  - [ ] project task definition
- [ ] S3 (Simple Storage Service)
  - [ ] projects bucket (for all organization projects) **private** contains:
    - [ ] project folders (for individual projects) **private** each contains:
      - [ ] all content files for project steps (generally .html files) **private**
    - [ ] project_master_list.json file **private**
  - [ ] webpage bucket (for hosting front end) **public** contains:
    - [ ] all files and folders required for front-end website **public**
- [ ] Cloud Front
  - [ ] Distribution for front-end hosted in S3
- [ ] Route53
  - [ ] Hosted Zone for Root Domain
    - [ ] A record for api.ROOT_DOMAIN points to API Gateway
    - [ ] AAAA record for api.ROOT_DOMAIN points to API Gateway
    - [ ] A record for either root or subdomain points to Cloud Front
    - [ ] AAAA record for either root or subdomain points to Cloud Front
- [ ] Certificate Manager contains:
  - [ ] Region: us-east-1 for ROOT_DOMAIN and *.ROOT_DOMAIN (for use in Cloud Front)
  - [ ] Region: same as API Gateway for ROOT_DOMAIN and *.ROOT_DOMAIN (for use in API Gateway)
- [ ] SNS (Simple Notification Service) contains Topics:
  - [ ] start_server subscribed by Lambda Function start_server.py
  - [ ] stop_server subscribed by Lambda Function stop_server.py
- [ ] IAM (Identity and Access Management)

## Setup Instructions:

Note on regions: Choose a region that's most appropriate for your use case and setup all region specific services in that region. Write it down, there are lots of regions and it is annoying when you can't find your infrastructure.

For the purposes if these instructions, PROJECT_REGION represents the specific region that has been chosen for the project. If a more specific region is listed then it must be used.

### 1. Route53
**region:** Global

This project requires the use of a Route53 hosted zone. If you do not currently own a domain name, one can be purchase through the Route53 page. If you already own a domain name you can change the root domain nameservers to point to Route53, this is faster than transferring a domain which can take up to 14 days. 

  - create hosted zone for your domain name
  - if needed go to your domain registrar and change the Nameservers to the 4 given in the newly created hosted zone.
  - copy the hosted zone ID and paste it into .env under HOSTED_ZONE_ID
  - enter your root domain into .env under ROOT_DOMAIN
  - move on to step 2

### 2. Certificate Manager
**region:** us-east-1
  - Request a Certificate
    - select request a public certificate
    - put in ROOT_DOMAIN
    - add another name and put in the wildcard: *.ROOT_DOMAIN
    - choose DNS validation
    - click the "Create record in Route 53" button
    - click continue

**region:** PROJECT_REGION
  - change to your project region and repeat the exact same steps above.
  - move on to step 3

### 3. S3 (Simple Storage Service)
**region:** Global
  - create bucket (for projects folders)
    - For the region select your PROJECT_REGION
    - You may choose to select Versioning, Logging, or Encryption but none are required.
    - Ensure that 'Block all public access' is selected
    - click on bucket
    - click on "Upload"
    - upload your project_master_list.json file
    - click on "Create folder"
    - name the folder the same as the projectID listed in the project_master_list.json file
    - click on the project folder and upload all of the step files
  - add bucket name to .env file as BUCKET 
  - go back to main S3 screen
  - create a second bucket for the front-end hosting
    - For the region select your PROJECT_REGION
    - You may choose to select Versioning, Logging, or Encryption but none are required.
    - Uncheck 'Block all public access' making the bucket public
  - Click on the second bucket (front-end host)
  - Select Properties > Static website hosting 
  - Select "Use this bucket to host a website"
  - enter 'index.html' for both index document and error document
  - copy the full Endpoint url at the top to your clipboard for the next step
  - click save
  - click "Upload" and upload all files and folders from the front-end 'build' directory. When uploading make sure to click through 'Next' and select "Grand public read access to this object(s)" from the dropdown before uploading.
  - move to step 4

### 4. Cloud Front
**region:** Global
  - create distribution > web
  - paste url from previous step in "Origin Domain Name"
    - Note: the input field will drop down and offer your S3 buckets. You must paste the full url with http:// rather than select the bucket from the dropdown in order to get correct routing behavior.
  - Select "Redirect HTTP to HTTPS"
  - In "Alternate Domain Names" enter the domain name where you want to host the front-end site.
  - Select "Custom SSL Certificate" and in the input box select the certificate created in step 2 from the dropdown. If you have not created a certificate, you can click the button to Request a Certificate, but you will need to restart the CloudFront step.
  - You can leave all other settings as default.
  - Click "Create Distribution" button
  - Navigate back to Route53
    - click the project hosted zone
    - create record > simple routing > define simple record
    - enter a subdomain, or leave blank for root domain ( note this must match the "Alternate Domain Name" that you entered in Cloudfront
    - Click "choose endpoint" and select "Alias to CloudFront distribution"
    - click "choose distribution" and select from dropdown. If nothing is found check that the domain name matches. Sometimes it takes a little longer for CloudFront to initialize, if you started the Route53 process before CloudFront initialized, you may need to reload the page in order to see the distribution.
    - Select 'A' for record type
    - click "Define simple record" button
    - Repeat the process making a "AAAA" record (optional but recommended as a good habit)
  - move on to step 5 

### 5. ECR (Elastic Container Registry)
**region:** PROJECT_REGION
  - create repository
  - click on the repository name
    - click on "View push commands" to see instructions to push docker container to repo
    - push container to repo
  - go back to Repositories view and copy the URI to the clipboard for use in next step
  - move on to step 6

### 6. ECS (Elastic Container Service)
**region:** PROJECT_REGION
  - Create new Task Definition
    - Select Fargate
    - Give task definition a name, then copy and paste the name to the project_def config file under ecs_task:
    - for Task execution role, select ecsTaskExecutionRole if available or let the system automatically generate a role.
    - select Memory and CPU sizes. Correct sizes are dependent on the agent implimentation 10GB and 2vCPU is a good starting point.
    - click "Add container"
    - enter a container name
    - paste the image address copied in step 5
    - add Port mapping of 5000 to tcp
    - click "create"
  - move on to step 7

### 7. Lambda
**region:** PROJECT_REGION

For each of: start_server.py stop_server.py and next_step.py
  - create function > Author from scratch
    - give function appropiate name 
    - select python3.8 as runtime
    - click "Create function" button
  - copy code from file and paste into editor, hit save button. (This is often faster than trying to upload via zip file)
  - scroll down to "Basic Settings" and edit Timeout if required for function.
  - go to top of page and click "Permissions"
  - click on role name (opens IAM in new tab)
    - Attach policies as listed in the Lambda Functions README.md for the function
  - close IAM tab
  - Note at this time not all of the Environment Variables are available for entry, therefore move on to step 8, we will return to complete the Lambda setup at the end.

### 8. SNS (Simple Notification Service)
**region:** PROJECT_REGION

2 topics are required, 1 for start_server and 1 for stop_server. Details can be found in Lambda Functions README.md repeat the following steps for each.
  - Topics > Create topic
  - Give topic appropriate name
  - for stop_server topic only edit the Access policy according to instructions in the Lambda Functions README.md
  - click "Create topic"
  - click on topic
  - click "Create subscription"
    - "Protocol" select AWS Lambda from dropdown
    - select the appropriate function as the Endpoint
    - click "Create subscription"
  - copy the topic ARN and add to appropriate value in .env (either START_SERVER_TOPIC_ARN or STOP_SERVER_TOPIC_ARN)

### 9. API Gateway
**region:** PROJECT_REGION
  - create API > REST API
  - selct "REST" and "New API"
  - give appropriate name
  - click "Create API"
  - In the API click on "Actions" dropdown and select "create Method"
    - choose "GET" first, then repeat the steps for "POST" as well
    - select "Lambda Function"
    - check "Use Lambda Proxy integration"
    - Select next_step Lambda Function created in step 7
    - click "Save"
    - reminder do this for both GET and POST
  - click "Actions" dropdown
  - select "Enable CORS"
    - check DEFAULT 4XX and DEFAULT 5XX boxes and leave all other setting as default
    - click "Enable CORS and replace existing CORS headers" button
    - click "Yes..." to confirm
  - select "Actions" dropdown
  - choose "Deploy API"
  - select a stage, or [new stage] if not already created. suggested name 'live'
  - click "Deploy"
  - click "Custom domain names"
    - create
    - enter a subdomain such as api.ROOT_DOMAIN
    - Regional is sufficient
    - Choose your certificate from step 2. If you don't see it in the dropdown, check the region.
  - click on the domain name
  - scroll down and click on "Configure API mappings"
  - "Add new mapping"
    - select your next_step API
    - select the stage you deployed it to
    - put 'next' in path
    - click save

### 10. Finish Lambda Setup
**region** PROJECT_REGION

  - go to Services > VPC
  - click on "Subnets"
  - copy a 'Subnet ID' with status available and save in .env under SUBNET (note that some subnets aren't compatible with ECS so if you get an error due to the subnet choice, simply select one of the others in your account.)
  - go to Services > EC2
  - click on "Security Groups"
  - create security group
  - add Inbound rule for TCP Port 5000 source any
  - click "Create security group"
  - copy security group Id and paste into .env under SECURITY_GROUP
  - For each of the Lambda Functions go to the editor and find the "Environment Variables" section. Add all of the Environment Variables listed for the function in the README.md with the values that you've been saving in your .env file.

