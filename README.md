## 应用简介

本应用适用于解压 OSS 大文件。应用会创建 OSS 触发器监听 `SrcBucket` 指定 Bucket 下以 `OSSKeyPrefix` 指定前缀开始并且以 `OSSKeySuffix` 指定后缀结束的文件，当符合条件的文件上传到 OSS 后，会自动触发函数和解压流程。解压后的文件会存放到 `DestBucket` 指定 Bucket 下 `ProcessedDir` 指定目录下。

## 部署

1. 使用[Funcraft](https://help.aliyun.com/document_detail/64204.html)部署资源。

    ```
    fun package -b bucket-to-store-function-code
    fun deploy --use-ros --stack-name oss-unzip -p 'SrcBucket=hangzhouhangzhou' -p 'DestBucket=hangzhouhangzhou2' -p 'OSSKeyPrefix=zip' -p 'OSSKeySuffix=.zip'
    ```

2. 测试解压文件：使用[阿里云 CLI](https://help.aliyun.com/document_detail/122611.html) 执行流程。使用控制台请参见[文档](https://help.aliyun.com/document_detail/124156.html)。执行使用下面的输入格式。该输入将会把 `hangzhouhangzhou` bucket 下的 `tbc/Archive.zip` 解压到 `hangzhouhangzhou2` bucket。

    ```
    aliyun fnf StartExecution --FlowName unzip-single-file --Input '{"src_bucket": "hangzhouhangzhou", "dest_bucket": "hangzhouhangzhou2", "key": "tbc/Archive.zip"}' --ExecutionName run1
    ```

## 使用示例

1. 上传文件到源 Bucket，确保文件前缀和后缀符合应用参数设置。
2. 检查目的 Bucket 下 `ProcessedDir` 指定目录，确保文件解压正常。
3. 如果文件没有被解压，或者解压不完全，请前往[函数工作流控制台](https://fnf.console.aliyun.com/)找到解压流程，查看执行是否成功和错误原因。


## 工作原理

如果压缩文件包含数万个甚至更多个小文件，整个解压过程可能超过函数计算最长执行时间（10分钟），导致解压失败。本应用通过将解压过程分解成多个步骤，采用函数工作流通过多次解压确保超大文件也可以全部解压。

解压流程逻辑如下：

1. 解压文件，每流式解压完其中的一个子文件，检查是否超过设置的时间阈值，如果超过，则结束，并返回下一个要解压的子文件名称。
2. 流程检查是否文件已全部解压，如上一步骤返回子文件名称，则再次调用解压函数，并传入子文件名称。该函数从子文件名称起始处开始解压；否则流程结束。

其它相关解压方案：

1. 如果解压后的文件不会超过函数计算运行环境最大内存限制（3GB），可以直接将文件在内存解压并将结果保存到 OSS，请参见[方案](https://github.com/coco-super/simple-fc-uncompress-service-for-oss)
2. 如果解压后文件太大，超过最大内存限制，则可以使用流式将文件解压并将结果保存到 OSS，请参见[方案](https://github.com/coco-super/streaming-fc-uncompress-service-for-oss)

