import base64

json_key = """
{
  "type": "service_account",
  "project_id": "ya-eda-484711",
  "private_key_id": "8657bb99d587b4dc6446854f14e6c04220cadbd1",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDL0vrUZffjHCQ9\nV5UIwBJJoZ8ML9s47mEE7TxqPX/WXBk7VF5BRRP4djAhcb/tWYi+ZT2BWmtv0WtT\nxiGO1zEoz5cR1MRgTsrJRpDenemieeRYPJDMsqr6BLwQpJJVkDA+MkCOOHfwoGHs\nYeoqYKOhkIAXGHxLaVde6OHGdWH6V4ByVZ26ZmX37qVL0LLFQZ7JY2f0NJJSrc9V\nzqmmXTlijE/IoNfPIigdcskHSxgPVoKMkban9nV9qO4YJpQy1Oz5ssVRKiUd7zbz\n5UnFftETOtUq1bRQc5rpmPnp1Oepf9quEaz6f7Y0DF00hOMDa2inkk+ljVo6GYh/\nXg5flQGzAgMBAAECggEABGyPajXOZB0TwksY3ohAvV1nNN4DDaDK9U7q7UlpcW8t\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "ya-edas@ya-eda-484711.iam.gserviceaccount.com",
  "client_id": "112551368835900280616",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/ya-edas%40ya-eda-484711.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
"""

encoded = base64.b64encode(json_key.encode("utf-8")).decode("ascii")
print(encoded)
