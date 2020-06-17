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
from concurrent.futures import ThreadPoolExecutor

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

    endpoint = 'https://oss-%s-internal.aliyuncs.com' % context.region
    src_client = get_oss_client(context, endpoint, evt["src_bucket"])
    dest_client = get_oss_client(context, endpoint, evt["dest_bucket"])
    key = evt["key"]
    group = evt["group"]
    start_index = group[0]
    end_index = group[1]
    max_workers_per_task = evt.get('max_workers_per_task', 10)

    if "ObjectCreated:PutSymlink" == evt.get('event_name'):
        key = src_client.get_symlink(key).target_key
        logger.info("Resolved target key %s from %s", key, evt["key"])
        if key == "":
            raise RuntimeError('{} is invalid symlink file'.format(key))

    ext = os.path.splitext(key)[1]

    if ext != ".zip":
        raise RuntimeError('{} filetype is not zip'.format(key))

    logger.info("Start to decompress zip file %s in group: %s", key, str(group))
    processed_dir = os.environ.get("PROCESSED_DIR", "")
    if processed_dir and processed_dir[-1] != "/":
        processed_dir += "/"
    # Keep the old key structure
    new_path = processed_dir + key
    new_path = new_path.rstrip(".zip")

    zip_fp = helper.OssStreamFileLikeObject(src_client, key)

    # Run up to threshold seconds
    threshold = evt.get("time_threshold", int(os.environ["TIME_THRESHOLD"]))

    executor = ThreadPoolExecutor(max_workers=max_workers_per_task)
    with helper.zipfile_support_oss.ZipFile(zip_fp) as zf:
        # unzip single file
        def unzip(name):
            logger = logging.getLogger()
            logger.debug("Processing %s", name)

            if name.endswith("/"):
                logger.debug("Skipping dir %s", name)
                return

            logger.debug("Unzipping %s", name)
            with zf.open(name) as file_obj:
                try:
                    name = name.encode(encoding='cp437')
                except:
                    name = name.encode(encoding='utf-8')

                # the string to be detect is long enough, the detection result accuracy is higher
                detect = chardet.detect((name * 100)[0:100])
                confidence = detect["confidence"]
                if confidence > 0.8:
                    try:
                        name = name.decode(encoding=detect["encoding"])
                    except:
                        name = name.decode(encoding='gb2312')
                else:
                    name = name.decode(encoding="gb2312")

                dest_client.put_object(new_path + "/" + name, file_obj)
                return

        namelist = zf.namelist()
        while start_index <= end_index:
            cur_count = min(end_index - start_index + 1, max_workers_per_task)
            res = []
            for ind in range(start_index, start_index + cur_count):
                res.append(executor.submit(unzip, namelist[ind]))

            # Wait for all unzip finished
            for f in res:
                f.result()

            start_index += cur_count

            # Check time over
            if threshold and time.time() - start_time >= threshold:
                break

    executor.shutdown()

    return {
        "group": [start_index, end_index],
        "status": "running" if start_index <= end_index else "success",
    }


def get_oss_client(context, endpoint, bucket):
    creds = context.credentials
    if creds.security_token is not None:
        auth = oss2.StsAuth(creds.access_key_id, creds.access_key_secret, creds.security_token)
    else:
        # for local testing, use the public endpoint
        endpoint = str.replace(endpoint, "-internal", "")
        auth = oss2.Auth(creds.access_key_id, creds.access_key_secret)
    return oss2.Bucket(auth, endpoint, bucket)
