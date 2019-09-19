# -*- coding: utf-8 -*-
import oss2
from oss2 import utils, models
import ossZipfile as zipfile

zipfile_support_oss = zipfile

# support upload to oss as a file-like object
def make_crc_adapter(data, init_crc=0):
  data = utils.to_bytes(data)
  # file-like object
  if hasattr(data,'read'): 
    return utils._FileLikeAdapter(data, crc_callback=utils.Crc64(init_crc))

utils.make_crc_adapter = make_crc_adapter

class OssStreamFileLikeObject(object):
  def __init__(self, bucket, key):
    super(OssStreamFileLikeObject, self).__init__()
    self._bucket = bucket
    self._key = key
    self._meta_data = self._bucket.get_object_meta(self._key)

  @property
  def bucket(self):
    return self._bucket

  @property
  def key(self):
    return self._key

  @property
  def filesize(self):
    return self._meta_data.content_length

  def get_reader(self, begin, end):
    begin = begin if begin >= 0 else 0
    end = end if end > 0 else self.filesize - 1
    end = end if end < self.filesize else self.filesize - 1 
    begin = begin if begin < end else end
    return self._bucket.get_object(self._key, byte_range=(begin, end))

  def get_content_bytes(self, begin, end):
    reader = self.get_reader(begin, end)
    return reader.read()

  def get_last_content_bytes(self, offset):
    return self.get_content_bytes(self.filesize-offset, self.filesize-1)