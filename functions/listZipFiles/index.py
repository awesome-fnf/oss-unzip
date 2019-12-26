# -*- coding: utf-8 -*-
import oss2
import json
import os
import logging

def handler(event, context):
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)
  evt = json.loads(event)
  logger.info("Handling event: %s", evt)
  endpoint = 'https://oss-%s-internal.aliyuncs.com' % context.region
  src_client = get_oss_client(context, endpoint, evt["bucket"])

  marker = evt["marker"]
  keys = []
  keys_threshold = evt.get("keys_threshold", 50)
  has_more = False

  while True:
    result = src_client.list_objects(prefix = evt["prefix"], marker = marker, delimiter = evt["delimiter"], max_keys = 50)
    marker = result.next_marker
    has_more = result.is_truncated
    for obj in result.object_list:
      logger.debug("Checking %s", obj.key)
      ext = os.path.splitext(obj.key)[1]
      # Only include files ending with zip
      if ext == ".zip":
        keys.append(obj.key)
    if not result.is_truncated or len(keys) >= keys_threshold:
      break

  logger.info("Found %d objects", len(keys))
  return {
    "keys": keys,
    "has_more": has_more,
    "marker": marker
  }

def get_oss_client(context, endpoint, bucket):
  creds = context.credentials
  if creds.security_token != None:
    auth = oss2.StsAuth(creds.access_key_id, creds.access_key_secret, creds.security_token)
  else:
    # for local testing, use the public endpoint
    endpoint = str.replace(endpoint, "-internal", "")
    auth = oss2.Auth(creds.access_key_id, creds.access_key_secret)
  return oss2.Bucket(auth, endpoint, bucket)