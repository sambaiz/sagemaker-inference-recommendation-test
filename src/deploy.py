from sagemaker.pytorch import PyTorch
import os
import boto3
from botocore.exceptions import ClientError
import time
from datetime import datetime, timezone

def create_model():
  estimator = PyTorch(
    source_dir='src',
    entry_point='train.py',
    output_path=f's3://{os.getenv("S3_BUCKET")}/artifacts',
    role=os.getenv("SAGEMAKER_JOB_ROLE"),
    framework_version='1.13',
    py_version='py39',
    instance_count=2,
    instance_type='ml.g4dn.xlarge',
    hyperparameters={
      'epochs': 10,
      'backend': 'gloo',
      'dropout': 0.2,
    },
  )
  estimator.fit()

  model = estimator.create_model()
  model.create(
    instance_type='ml.m5.xlarge',
  )
  return model


def start_default_inference_recommendations_job(sagemaker_client, model_name: str):
  job_name = f"{model_name}-default"
  sagemaker_client.create_inference_recommendations_job(
    JobName=job_name,
    JobType='Default',
    RoleArn=os.getenv("SAGEMAKER_JOB_ROLE"),
    InputConfig={
      'ModelName': model_name,
      'ContainerConfig': {
        'Domain': 'COMPUTER_VISION',
        'Framework': 'PYTORCH',
        'FrameworkVersion': '1.13',
        'PayloadConfig': {
          # TODO upload & change this if you need
          'SamplePayloadUrl': f's3://{os.getenv("S3_BUCKET")}/sample_payload.tar.gz',
          'SupportedContentTypes': ['application/x-npy'],
        },
        'Task': 'IMAGE_CLASSIFICATION',
      },
    }
  )

  while True:
    response = sagemaker_client.describe_inference_recommendations_job(JobName=job_name)
    execution_time = datetime.now(timezone.utc) - response['CreationTime']
    print(f"\033[34mDefault job: {response['Status']} ({execution_time})\033[0m")

    if response['Status'] == 'COMPLETED':
      recommendations = [
        {
          'InstanceType': r['EndpointConfiguration']['InstanceType'],
          'InitialInstanceCount': r['EndpointConfiguration']['InitialInstanceCount'],
          'CostPerInference': r['Metrics']['CostPerInference'],
          'ModelLatency': r['Metrics']['ModelLatency'],
          'CpuUtilization': r['Metrics']['CpuUtilization'],
          'MemoryUtilization': r['Metrics']['MemoryUtilization'],
          'MaxInvocationsPerMinute': r['Metrics']['MaxInvocations'],
        } for r in response['InferenceRecommendations']
      ]
      return sorted(recommendations, key=lambda v: v['CostPerInference'])

    elif response['Status'] == 'FAILED':
      raise response

    time.sleep(15)


def start_advanced_inference_recommendations_job(
        sagemaker_client,
        model_name: str,
        instance_type_options: list[str]):
  job_name = f"{model_name}-advanced"
  sagemaker_client.create_inference_recommendations_job(
    JobName=job_name,
    JobType='Advanced',
    RoleArn=os.getenv("SAGEMAKER_JOB_ROLE"),
    InputConfig={
      'ModelName': model_name,
      'JobDurationInSeconds': 6000,
      'ContainerConfig': {
        'Domain': 'COMPUTER_VISION',
        'Framework': 'PYTORCH',
        'FrameworkVersion': '1.13',
        'PayloadConfig': {
          # TODO upload & change this
          'SamplePayloadUrl': f's3://{os.getenv("S3_BUCKET")}/sample_payload.tar.gz',
          'SupportedContentTypes': ['application/x-npy'],
        },
        'Task': 'IMAGE_CLASSIFICATION',
      },
      'TrafficPattern': {
        'TrafficType': 'PHASES',
        'Phases': [
          {
            'InitialNumberOfUsers': 1,
            'SpawnRate': 1,
            'DurationInSeconds': 120
          },
          {
            'InitialNumberOfUsers': 1,
            'SpawnRate': 1,
            'DurationInSeconds': 120
          }
        ]
      },
      'ResourceLimit': {
        'MaxNumberOfTests': 10,
        'MaxParallelOfTests': 3
      },
      "EndpointConfigurations": [{'InstanceType': instance_type} for instance_type in instance_type_options]
    },
    StoppingConditions={
      "MaxInvocations": 1000,
      "ModelLatencyThresholds": [{"Percentile": "P95", "ValueInMilliseconds": 500}],
    },
  )

  while True:
    response = sagemaker_client.describe_inference_recommendations_job(JobName=job_name)
    elapsed_time = datetime.now(timezone.utc) - response['CreationTime']
    print(f"\033[32mAdvanced job: {response['Status']} ({elapsed_time})\033[0m")

    if response['Status'] == 'COMPLETED':
      recommendations = [
        {
          'InstanceType': r['EndpointConfiguration']['InstanceType'],
          'InitialInstanceCount': r['EndpointConfiguration']['InitialInstanceCount'],
          'CostPerInference': r['Metrics']['CostPerInference'],
          'ModelLatency': r['Metrics']['ModelLatency'],
          'CpuUtilization': r['Metrics']['CpuUtilization'],
          'MemoryUtilization': r['Metrics']['MemoryUtilization'],
          'MaxInvocationsPerMinute': r['Metrics']['MaxInvocations'],
        } for r in response['InferenceRecommendations']
      ]
      return sorted(recommendations, key=lambda v: v['CostPerInference'])

    elif response['Status'] == 'FAILED':
      raise response

    time.sleep(15)


def create_endpoint_config(
        sagemaker_client,
        model_name: str,
        variant_name: str,
        instance_type: str):
  sagemaker_client.create_endpoint_config(
    EndpointConfigName=model_name,
    ProductionVariants=[
      {
        "VariantName": variant_name,
        "ModelName": model_name,
        "InstanceType": instance_type,
        "InitialInstanceCount": 1,
        "InitialVariantWeight": 1,
      }
    ],
  )
  return model_name


def create_or_update_endpoint(
        sagemaker_client,
        endpoint_name: str,
        config_name: str):
  try:
    sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
    sagemaker_client.update_endpoint(
      EndpointName=endpoint_name,
      EndpointConfigName=config_name,
    )

  except ClientError as e:
    if "Cannot update in-progress endpoint" in str(e):
      raise e
    sagemaker_client.create_endpoint(
      EndpointName=endpoint_name,
      EndpointConfigName=config_name,
    )


def register_auto_scale_settings(
        sagemaker_client,
        autoscaling_client,
        endpoint_name: str,
        variant_name: str,
        min_capacity: int,
        max_capacity: int,
        invocation_per_instance_minute: int):
  while True:
    endpoint = sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
    elapsed_time = datetime.now(timezone.utc) - endpoint['LastModifiedTime']
    print(f"\033[33mEndpoint status: {endpoint['EndpointStatus']} ({elapsed_time})\033[0m")

    if endpoint['EndpointStatus'] == 'InService':
      break
    elif endpoint['EndpointStatus'] == 'Failed':
      raise endpoint

    time.sleep(15)

  resource_id = f"endpoint/{endpoint_name}/variant/{variant_name}"
  autoscaling_client.register_scalable_target(
    ServiceNamespace="sagemaker",
    ResourceId=resource_id,
    ScalableDimension="sagemaker:variant:DesiredInstanceCount",
    MinCapacity=min_capacity,
    MaxCapacity=max_capacity,
  )

  autoscaling_client.put_scaling_policy(
    PolicyName="Invocations-ScalingPolicy",
    ServiceNamespace="sagemaker",
    ResourceId=resource_id,
    ScalableDimension="sagemaker:variant:DesiredInstanceCount",
    PolicyType="TargetTrackingScaling",
    TargetTrackingScalingPolicyConfiguration={
      "TargetValue": invocation_per_instance_minute,
      "PredefinedMetricSpecification": {
        "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
      }
    },
  )


def main():
  sess = boto3.Session()
  sagemaker_client = sess.client("sagemaker")
  autoscaling_client = sess.client("application-autoscaling")

  # train and create a model
  model = create_model()

  # start default & advanced inference recommendations jobs
  recommendations = start_default_inference_recommendations_job(sagemaker_client, model.name)
  print("--- Default ----")
  for r in recommendations:
    print(f"{r['InstanceType']} x {r['InitialInstanceCount']}: ${r['CostPerInference']}/inference")
  print("-------")

  recommendations = start_advanced_inference_recommendations_job(
    sagemaker_client,
    model.name,
    map(lambda r: r['InstanceType'], recommendations)
  )
  print("--- Advanced ----")
  for r in recommendations:
    print(f"{r['InstanceType']} x {r['InitialInstanceCount']}: ${r['CostPerInference']}/inference")
  print("-------")

  # create an endpoint config with recommended instance type
  variant_name = 'main-model'
  config_name = create_endpoint_config(
    sagemaker_client,
    model.name,
    variant_name,
    recommendations[0]['InstanceType'],
  )

  # create or update an endpoint with the config
  endpoint_name = 'sagemaker-inference-test'
  create_or_update_endpoint(sagemaker_client, endpoint_name, config_name)

  invocation_per_instance_minute = recommendations[0]['MaxInvocationsPerMinute'] / recommendations[0]['InitialInstanceCount']

  # set up auto scaling to the variant
  register_auto_scale_settings(
    sagemaker_client,
    autoscaling_client,
    endpoint_name,
    variant_name,
    min_capacity=recommendations[0]['InitialInstanceCount'],
    max_capacity=recommendations[0]['InitialInstanceCount']+10,
    invocation_per_instance_minute=int(invocation_per_instance_minute * 0.8),
  )

  print(f"Endpoint name: {endpoint_name}")


if __name__ == '__main__':
  main()
