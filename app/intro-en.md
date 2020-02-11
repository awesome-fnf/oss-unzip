## Introduction

This application is used to decompress big OSS files. It creates an OSS trigger which monitors new files uploaded to bucket (`SrcBucket`) and whose key begins with the prefix (`OSSKeyPrefix`) and ends with the suffix (`OSSKeySuffix`). The uncompressed files are saved to a directory (`ProcessedDir`) under the bucket (`DestBucket`).

## Usage

1. Upload a file to the source bucket.
2. Go to the destination bucket and directory, check if the uncompressed files exist.
3. If the files do not exist, go to the [Function Flow console](https://fnf.console.aliyun.com/), check the flow executions and see if there are any errors.

## Architecture & Design

If a compressed file contains many small files, decompressing the file could take more than the maximum allowed function timeout (10 minutes). The solution is to decompose the process into multiple steps by leveraging the Function Flow service.

The decompression process is as follows:

![oss unzip flow](https://img.alicdn.com/tfs/TB1Wx6uvEY1gK0jSZFCXXcwqXXa-831-991.png)

1. Decompress one of the files (from a single zip file) and save it to the destination bucket. Check if there is any time left to decompress more files, if so, decompress the next file. Otherwise leave the function and return the next file name.
2. The flow (defined in Function Flow) determines to exit the execution or run the unzip step again based on whether there is more files to be decompressed.


Project Source: [https://github.com/awesome-fnf/oss-unzip](https://github.com/awesome-fnf/oss-unzip)