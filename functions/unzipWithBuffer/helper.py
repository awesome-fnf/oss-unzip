# -*- coding: utf-8 -*-
from io import BytesIO
import json
import logging
import oss2
from oss2 import utils
import ossZipfile as zipfile

zipfile_support_oss = zipfile
logger = logging.getLogger()

# support upload to oss as a file-like object
def make_crc_adapter(data, init_crc=0):
  data = utils.to_bytes(data)
  # file-like object
  if hasattr(data,'read'): 
    return utils._FileLikeAdapter(data, crc_callback=utils.Crc64(init_crc))

utils.make_crc_adapter = make_crc_adapter


CHUNK_SIZE = 256*1014*1024
META_FILE = '/tmp/meta.json'
# data file stores the file range between [begin, end]
DATA_FILE = '/tmp/data'

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

  # Data betweeen [begin, end]
  def get_reader(self, begin, end):
    begin = begin if begin >= 0 else 0
    # end cannot exceed file size
    end = end if end > 0 else self.filesize - 1
    end = end if end < self.filesize else self.filesize - 1 
    begin = begin if begin < end else end

    logger.info("Start to get file %s [%d, %d]", self._key, begin, end)
    
    # meta has key, begin, and end fields.
    meta = {'key': '', 'begin': -1, 'end': -1}
    try:
        with open(META_FILE, "r") as f:
            meta = json.load(f)
    except Exception as e:
        pass
    # Check if the part of the file exists
    if meta.get('key', None) != self._key or begin > meta['end'] or end < meta['begin'] or begin < meta['begin']:
      # Download new file range to local file
      # [begin, min(file_size, begin+CHUNK_SIZE)]
      r_begin = begin
      r_end = min(self.filesize, begin + CHUNK_SIZE) - 1
      self._bucket.get_object_to_file(self._key, DATA_FILE, byte_range=(r_begin, r_end))
      # Update meta file
      meta = {'key': self._key, 'begin': r_begin, 'end': r_end}
      with open(META_FILE, "w") as f:
        json.dump(meta, f)
      with open(DATA_FILE, "rb") as f:
        return BytesIO(f.read(end-begin+1))
    else:
      if begin >= meta['begin'] and end <= meta['end']:
        # If the requested file range is within the file range
        with open(DATA_FILE, "rb") as f:
            # e.g. meta = {'begin': 10, 'end': 100}, begin = 20, end = 80
            # Jump to the offset (20-10), and read (80-20) bytes
            f.seek(begin - meta['begin'])
            return BytesIO(f.read(end-begin+1))
      elif begin <= meta['end'] and end >= meta['end']:
        # If end exceeds the meta['end'], e.g. begin = 20, end = 120,
        # Read [20, 100] -> 81
        remaining = end - meta['end'] # 20
        # Read [begin, end] from local file
        with open(DATA_FILE, "rb") as f:
          f.seek(begin - meta['begin']) # 20 - 10 = 10
          p1 = f.read(meta['end'] - begin + 1) # 100 - 20 + 1 = 81
        # Download new file to local file
        r_begin = meta['end'] + 1
        r_end = min(self.filesize, end + CHUNK_SIZE) - 1
        self._bucket.get_object_to_file(self._key, DATA_FILE, byte_range=(r_begin, r_end))
        # Update meta file
        meta = {'key': self._key, 'begin': r_begin, 'end': r_end}
        with open(META_FILE, "w") as f:
          json.dump(meta, f)
        # Read [0, end-begin] from local file
        with open(DATA_FILE, "rb") as f:
          p2 = f.read(remaining)
        return BytesIO(p1 + p2)

  def get_content_bytes(self, begin, end):
    reader = self.get_reader(begin, end)
    return reader.read()

  def get_last_content_bytes(self, offset):
    return self.get_content_bytes(self.filesize-offset, self.filesize-1)