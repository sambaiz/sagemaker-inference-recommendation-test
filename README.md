## sagemaker-inference-recommendation-test

```sh
$ poetry install

$ poetry run python3 src/output_sample_payload.py
# upload sample_payload.tar.gz to your bucket
$ export S3_BUCKET=sagemaker-ap-northeast-1-524580158183 # set your bucket name

$ export SAGEMAKER_JOB_ROLE=arn:aws:iam::***
$ poetry run python3 src/deploy.py
...
Default job: COMPLETED (0:27:45.502514)
--- Default ----
ml.c6i.large x 1: $8.428847309005505e-08/inference
ml.c6i.xlarge x 1: $1.2575290497807146e-07/inference
ml.c5.2xlarge x 1: $2.536017404963786e-07/inference
ml.c6i.4xlarge x 1: $4.970098075318674e-07/inference
ml.c6i.8xlarge x 1: $9.742772135723499e-07/inference
-------
...
Advanced job: COMPLETED (0:29:44.586078)
--- Advanced ----
ml.c6i.large x 1: $2.8025144160892523e-07/inference
ml.c6i.xlarge x 1: $5.61164256396296e-07/inference
ml.c5.2xlarge x 1: $1.0954817071251455e-06/inference
ml.c6i.4xlarge x 1: $2.252038939332124e-06/inference
ml.c6i.8xlarge x 1: $4.375719072413631e-06/inference
-------

$ aws sagemaker delete-endpoint --endpoint-name sagemaker-inference-test
```

### Article

- ja: [SageMaker Inference Recommender でコスト最適なインスタンスタイプの推論エンドポイントを立てる - sambaiz-net](https://www.sambaiz.net/article/447/)
- en: [Create a cost-optimized real-time inference endpoint with SageMaker Inference Recommender - sambaiz-net](https://www.sambaiz.net/en/article/447/)