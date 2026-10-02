import os
from datetime import date, timedelta

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError


REGION = os.environ.get("AWS_REGION", "us-east-1")
ECS_CLUSTER = os.environ.get("ECS_CLUSTER", "")
ECS_SERVICE = os.environ.get("ECS_SERVICE", "")
ECR_REPOSITORY = os.environ.get("ECR_REPOSITORY", "aws-cicd-webapp")


def _error(message):
    return {"configured": False, "message": message}


def ecs_status():
    if not ECS_CLUSTER or not ECS_SERVICE:
        return _error("Set ECS_CLUSTER and ECS_SERVICE to connect to ECS.")
    try:
        service = boto3.client("ecs", region_name=REGION).describe_services(
            cluster=ECS_CLUSTER, services=[ECS_SERVICE]
        )["services"][0]
        return {
            "configured": True,
            "service": service["serviceName"],
            "status": service["status"],
            "running": service["runningCount"],
            "desired": service["desiredCount"],
            "pending": service["pendingCount"],
        }
    except (BotoCoreError, ClientError, NoCredentialsError) as error:
        return _error(f"ECS unavailable: {error.__class__.__name__}")


def ecr_images():
    try:
        images = boto3.client("ecr", region_name=REGION).describe_images(
            repositoryName=ECR_REPOSITORY,
            filter={"tagStatus": "TAGGED"},
        ).get("imageDetails", [])
        images.sort(key=lambda image: image.get("imagePushedAt", date.min), reverse=True)
        return {
            "configured": True,
            "repository": ECR_REPOSITORY,
            "images": [
                {
                    "tags": image.get("imageTags", []),
                    "pushed_at": image.get("imagePushedAt").isoformat() if image.get("imagePushedAt") else None,
                    "size_mb": round(image.get("imageSizeInBytes", 0) / 1024 / 1024, 1),
                }
                for image in images[:10]
            ],
        }
    except (BotoCoreError, ClientError, NoCredentialsError) as error:
        return _error(f"ECR unavailable: {error.__class__.__name__}")


def costs():
    end = date.today()
    start = end.replace(day=1)
    try:
        result = boto3.client("ce", region_name="us-east-1").get_cost_and_usage(
            TimePeriod={"Start": start.isoformat(), "End": (end + timedelta(days=1)).isoformat()},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        amount = float(result["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"])
        return {"configured": True, "currency": result["ResultsByTime"][0]["Total"]["UnblendedCost"]["Unit"], "current_month": round(amount, 2)}
    except (BotoCoreError, ClientError, NoCredentialsError) as error:
        return _error(f"Cost Explorer unavailable: {error.__class__.__name__}")
