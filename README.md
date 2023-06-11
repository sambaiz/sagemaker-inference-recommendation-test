## sagemaker-inference-recommendation-test

```sh
$ poetry install

$ poetry run python3 src/output_sample_payload.py
# upload sample_payload.tar.gz to your bucket
$ export S3_BUCKET=sagemaker-ap-northeast-1-524580158183 # set your bucket name

$ export SAGEMAKER_JOB_ROLE=arn:aws:iam::***
$ poetry run python3 src/deploy.py
...
Default job: COMPLETED (0:27:32.690195)
--- Default ----
ml.c6i.large: $8.415588581556221e-08/inference
ml.c5.large: $9.639134646022285e-08/inference
ml.c5.2xlarge: $2.580865441359492e-07/inference
ml.c6i.4xlarge: $5.111057816975517e-07/inference
ml.c6i.8xlarge: $9.818766102398513e-07/inference
-------
...
Advanced job: COMPLETED (0:27:43.094279)
--- Advanced ----
ml.c6i.large: $2.8510524430203077e-07/inference
ml.c5.large: $3.1202768013827153e-07/inference
ml.c5.2xlarge: $1.1260077599217766e-06/inference
ml.c6i.4xlarge: $2.1104535790072987e-06/inference
ml.c6i.8xlarge: $4.351804818725213e-06/inference
-------

$ aws sagemaker delete-endpoint --endpoint-name sagemaker-inference-test
```