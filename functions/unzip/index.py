# -*- coding: utf-8 -*-
'''
声明：
这个函数针对文件和文件夹命名编码是如下格式：
1. mac/linux 系统， 默认是utf-8
2. windows 系统， 默认是gb2312， 也可以是utf-8

对于其他编码，我们这里尝试使用chardet这个库进行编码判断， 但是这个并不能保证100% 正确，
建议用户先调试函数，如果有必要改写这个函数，并保证调试通过

函数最新进展可以关注该blog: https://yq.aliyun.com/articles/680958

Statement:
This function names and encodes files and folders as follows:
1. MAC/Linux system, default is utf-8
2. For Windows, the default is gb2312 or utf-8

For other encodings, we try to use the chardet library for coding judgment here, 
but this is not guaranteed to be 100% correct. 
If necessary to rewrite this function, and ensure that the debugging pass
'''

import helper
import oss2, json
import os
import logging
import chardet
import time

"""
When a source/ prefix object is placed in an OSS, it is hoped that the object will be decompressed and then stored in the OSS as processed/ prefixed.
For example, source/a.zip will be processed as processed/a/... 
"Source /", "processed/" can be changed according to the user's requirements.

detail: https://yq.aliyun.com/articles/680958
"""
# Close the info log printed by the oss SDK
logging.getLogger("oss2.api").setLevel(logging.ERROR)
logging.getLogger("oss2.auth").setLevel(logging.ERROR)

def handler(event, context):
  """
  The object from OSS will be decompressed automatically .
  param: event:   The OSS event json string. Including oss object uri and other information.
  
  param: context: The function context, including credential and runtime info.

      For detail info, please refer to https://help.aliyun.com/document_detail/56316.html#using-context
  """
  start_time = time.time()
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)
  evt = json.loads(event)
  logger.info("Handling event: %s", evt)
  src_client = get_oss_client(context, os.environ['OSS_ENDPOINT'], evt["src_bucket"])
  dest_client = get_oss_client(context, os.environ['OSS_ENDPOINT'], evt["dest_bucket"])
  key = evt["key"]
  ext = os.path.splitext(key)[1]

  if ext != ".zip":
    raise RuntimeError('{} filetype is not zip'.format(key))

  logger.info("start to decompress zip file = {}".format(key))

  processed_dir = os.environ.get("PROCESSED_DIR", "")
  if processed_dir and processed_dir[-1] != "/":
    processed_dir += "/"
  # Keep the old key structure
  new_path = processed_dir + key
  new_path = new_path.rstrip(".zip")

  zip_fp = helper.OssStreamFileLikeObject(src_client, key)
  
  # Run up to threshold seconds
  threshold = evt.get("time_threshold", int(os.environ["TIME_THRESHOLD"]))
  marker = evt.get("marker", "")
  gate_closed = True if marker else False

  with helper.zipfile_support_oss.ZipFile(zip_fp) as zf:
    for name in zf.namelist():
      logger.debug("Processing %s", name)
      elapsed_time = time.time() - start_time
      # If elapsed_time exceeds the threshold, return the name as marker
      if threshold and elapsed_time >= threshold:
        return {
          "marker": name
        }
      # If marker is specified, skip names before the marker 
      if gate_closed:
        if marker != name:
          logger.debug("Skipping key %s", name)
          continue
        else:
          gate_closed = False
      if name.endswith("/"):
        logger.debug("Skipping dir %s", name)
        continue
      logger.debug("Unzipping %s", name)
      with zf.open(name) as file_obj:
        try:
          name = name.encode(encoding='cp437')
        except:
          name = name.encode(encoding='utf-8')
        
        # the string to be detect is long enough, the detection result accuracy is higher 
        detect = chardet.detect( (name*100)[0:100] )
        confidence = detect["confidence"]
        if confidence > 0.8:
          try:
            name = name.decode(encoding=detect["encoding"])
          except:
            name = name.decode(encoding='gb2312')
        else:
          name = name.decode(encoding="gb2312")
          
        dest_client.put_object(new_path + "/" + name, file_obj)

  # Reaches the end of file
  return {"marker": ""}

def get_oss_client(context, endpoint, bucket):
  creds = context.credentials
  if creds.security_token != None:
    auth = oss2.StsAuth(creds.access_key_id, creds.access_key_secret, creds.security_token)
  else:
    # for local testing, use the public endpoint
    endpoint = str.replace(endpoint, "-internal", "")
    auth = oss2.Auth(creds.access_key_id, creds.access_key_secret)
  return oss2.Bucket(auth, endpoint, bucket)