#!/usr/bin/env python3
from aws_cdk import App, Environment
from cdk_workshop_pipeline.cdk_workshop_pipeline_stack import CdkWorkshopPipelineStack

app = App()
environment_type = app.node.try_get_context("environmentType")
region = app.node.try_get_context(environment_type)["region"]
account = app.node.try_get_context("account")

CdkWorkshopPipelineStack(
    app, 
    "cdk-workshop-pipeline",
    env=Environment(account=account, region=region)
)

app.synth()
