## 简介

本示例演示了如何使用函数工作流和函数计算解压 OSS 文件。

## 解决方案比较

1. 如果解压后的文件不会超过函数计算运行环境最大内存限制（3GB），可以直接将文件在内存解压并将结果保存到 OSS，请参见[方案](https://github.com/coco-super/simple-fc-uncompress-service-for-oss)
2. 如果解压后文件太大，超过最大内存限制，则可以使用流式将文件解压并将结果保存到 OSS，请参见[方案](https://github.com/coco-super/streaming-fc-uncompress-service-for-oss)


但是如果解压文件过多，可能超过函数计算最长计算时间（10分钟），导致部分解压。这时就需要将解压分成多个步骤。在上述流式解压的基础上，我们采用函数工作流通过多次解压确保超大问题文件也可以全部解压，流程逻辑如下：
1. 解压文件，每流式解压完其中的一个子文件，检查是否超过设置的时间阈值，如果超过，则结束，并返回下一个要解压的子文件名称。
2. 流程检查是否文件已全部解压，如上一步骤返回子文件名称，则再次调用解压函数，并传入子文件名称。该函数从子文件名称起始处开始解压；否则流程结束。

**使用步骤**

1. 使用[Funcraft](https://help.aliyun.com/document_detail/64204.html)部署函数。注意：默认配置是自动解压 Bucket 下 `zip` 目录下的文件。

    ```
    fun deploy -t template.yml
    ```

2. 测试解压文件：使用[阿里云 CLI](https://help.aliyun.com/document_detail/122611.html) 执行流程。使用控制台请参见[文档](https://help.aliyun.com/document_detail/124156.html)。执行使用下面的输入格式。该输入将会把 `hangzhouhangzhou` bucket 下的 `tbc/Archive.zip` 解压到 `hangzhouhangzhou2` bucket。

    ```
    aliyun fnf StartExecution --FlowName unzip-single-file --Input '{"src_bucket": "hangzhouhangzhou", "dest_bucket": "hangzhouhangzhou2", "key": "tbc/Archive.zip"}' --ExecutionName run1
    ```