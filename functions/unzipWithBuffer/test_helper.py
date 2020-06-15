# -*- coding: utf-8 -*-

import json
import logging
import os
import string
import unittest
from unittest import TestCase, mock, main

from helper import OssStreamFileLikeObject, META_FILE, DATA_FILE


class TestHelper(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestHelper, self).__init__(*args, **kwargs)

    def test_get_reader_out_of_range(self):
        CHUNK_SIZE = 9
        key = "/a"
        meta = {'key': '/a', 'begin': 2, 'end': 10}
        with open(META_FILE, "w") as f:
            json.dump(meta, f)
        # ab
        # cdefghijk
        with open(DATA_FILE, "w") as f:
            for i in range(ord('c'), ord('k')+1):
                f.write(chr(i))
        gomr = mock.Mock()
        gomr.content_length = 14
        def create_file(key, filename, byte_range=None, headers=None, progress_callback=None, process=None):
            # abcdefghi [0,8]
            with open(DATA_FILE, "w") as f:
                for i in range(ord('a'), ord('i')+1):
                    f.write(chr(i))
        mock_bucket = mock.Mock()
        mock_bucket.get_object_meta.return_value = gomr
        mock_bucket.get_object_to_file.side_effect = create_file
        o = OssStreamFileLikeObject(mock_bucket, key)
        rst = o.get_reader(0, 4)
        self.assertEqual(rst.read(), b'abcde')

    def test_get_reader_in_range_part(self):
        CHUNK_SIZE = 9
        key = "/a"
        meta = {'key': '/a', 'begin': 2, 'end': 10}
        with open(META_FILE, "w") as f:
            json.dump(meta, f)
        # ab [0,1]
        # cdefghijk [2,10]
        # lmn [11,13]
        with open(DATA_FILE, "w") as f:
            for i in range(ord('c'), ord('k')+1):
                f.write(chr(i))
        gomr = mock.Mock()
        gomr.content_length = 14
        def create_file(key, filename, byte_range=None, headers=None, progress_callback=None, process=None):
            # lmn [11,13]
            with open(DATA_FILE, "w") as f:
                for i in range(ord('l'), ord('n')+1):
                    f.write(chr(i))
        mock_bucket = mock.Mock()
        mock_bucket.get_object_meta.return_value = gomr
        mock_bucket.get_object_to_file.side_effect = create_file
        o = OssStreamFileLikeObject(mock_bucket, key)
        rst = o.get_reader(2, 10)
        self.assertEqual(rst.read(), b'cdefghijk')
        rst = o.get_reader(4, 8)
        self.assertEqual(rst.read(), b'efghi')
        rst = o.get_reader(4, 10)
        self.assertEqual(rst.read(), b'efghijk')
        rst = o.get_reader(4, 12)
        self.assertEqual(rst.read(), b'efghijklm')
        rst = o.get_reader(11, 13)
        self.assertEqual(rst.read(), b'lmn')

if __name__ == '__main__':
    unittest.main()