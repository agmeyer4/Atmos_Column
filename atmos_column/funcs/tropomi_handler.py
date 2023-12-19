'''First attempts at automating retrieval of TROPOMI data from earthdata.nasa.gov.
Based on https://archive.podaac.earthdata.nasa.gov/s3credentialsREADME

Found out that it needs to be run on an AWS EC2 instance in the us-west-2 region per
https://forum.earthdata.nasa.gov/viewtopic.php?t=3995 and stopped trying '''



import argparse
import base64
import boto3
import json
import requests

def retrieve_credentials(event):
    """Makes the Oauth calls to authenticate with EDS and return a set of s3
    same-region, read-only credntials.
    """
    login_resp = requests.get(
        event['s3_endpoint'], allow_redirects=False
    )
    login_resp.raise_for_status()

    auth = f"{event['edl_username']}:{event['edl_password']}"
    encoded_auth  = base64.b64encode(auth.encode('ascii'))

    auth_redirect = requests.post(
        login_resp.headers['location'],
        data = {"credentials": encoded_auth},
        headers= { "Origin": event['s3_endpoint'] },
        allow_redirects=False
    )
    auth_redirect.raise_for_status()

    final = requests.get(auth_redirect.headers['location'], allow_redirects=False)

    results = requests.get(event['s3_endpoint'], cookies={'accessToken': final.cookies['accessToken']})
    results.raise_for_status()

    return json.loads(results.content)



def lambda_handler(event):

    creds = retrieve_credentials(event)
    bucket = event['bucket_name']

    # create client with temporary credentials
    client = boto3.client(
        's3',
        aws_access_key_id=creds["accessKeyId"],
        aws_secret_access_key=creds["secretAccessKey"],
        aws_session_token=creds["sessionToken"]
    )
    # use the client for readonly access.
    response = client.list_objects_v2(Bucket=bucket, Prefix=event['prefix'])

    return {
        'statusCode': 200,
        'body': json.dumps([r["Key"] for r in response['Contents']])
    }

event = {'s3_endpoint':'https://data.gesdisc.earthdata.nasa.gov/s3credentials',
         'edl_username':'agmeyer4',
         'edl_password':'Mister_zit0',
         'bucket_name':'gesdisc-cumulus-prod-protected',
         'prefix':"S5P_TROPOMI_Level2/S5P_L2__CH4____HiR.2/"}

resp = lambda_handler(event)
print(resp)

