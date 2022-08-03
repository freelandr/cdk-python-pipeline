#!/usr/bin/env python3

import aws_cdk as cdk

from cdk_workshop_pipeline.cdk_workshop_pipeline_stack import CdkWorkshopPipelineStack


app = cdk.App()
CdkWorkshopPipelineStack(app, "cdk-workshop-pipeline")

app.synth()
