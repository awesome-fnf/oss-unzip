# -*- coding: utf-8 -*-
import json
import os
import logging
import re

from aliyunsdkcore import client
from aliyunsdkcore.auth.credentials import StsTokenCredential
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkfnf.request.v20190315 import StartExecutionRequest

"""
  param: event:   The OSS event json string. Including oss object uri and other information.
      For detail info, please refer https://help.aliyun.com/document_detail/70140.html

  param: context: The function context, including credential and runtime info.
      For detail info, please refer to https://help.aliyun.com/document_detail/56316.html#using-context
"""


def handler(event, context):
    logger = logging.getLogger()
    # event format: https://help.aliyun.com/document_detail/62922.html
    evt_lst = json.loads(event)
    logger.info("Handling event: %s", evt_lst)

    creds = context.credentials
    sts_token_credential = StsTokenCredential(creds.access_key_id, creds.access_key_secret, creds.security_token)
    fnf_client = client.AcsClient(region_id=context.region, credential=sts_token_credential)

    request = StartExecutionRequest.StartExecutionRequest()
    request.set_FlowName(os.environ["FLOW_NAME"])

    evt = evt_lst["events"][0]
    key = evt["oss"]["object"]["key"]

    max_concurrent = int(os.environ.get('MAX_CONCURRENT', 100))
    max_workers_per_task = int(os.environ.get('MAX_WORKERS_PER_TASK', 100))
    min_count_per_task = int(os.environ.get('MIN_COUNT_PER_TASK', 1000))

    input = {
        "src_bucket": evt["oss"]["bucket"]["name"],
        "dest_bucket": os.environ['DEST_BUCKET'],
        "key": key,
        "event_name": evt["eventName"],
        'max_concurrent': max_concurrent,
        'max_workers_per_task': max_workers_per_task,
        'min_count_per_task': min_count_per_task,
    }
    request.set_Input(json.dumps(input))
    execution_name = re.sub(r"[^a-zA-Z0-9-_]", "_", key) + "-" + evt["responseElements"]["requestId"]
    request.set_ExecutionName(execution_name)

    logger.info("Starting flow execution: %s", execution_name)
    # TODO: swallow ExecutionAlreadyExists error
    return fnf_client.do_action_with_exception(request)
