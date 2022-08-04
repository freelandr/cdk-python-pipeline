from aws_cdk import Stack
from aws_cdk import SecretValue
from constructs import Construct
from aws_cdk.aws_s3 import Bucket
from aws_cdk.aws_codebuild import (
    BuildSpec,
     PipelineProject,
     BuildEnvironment,
     LinuxBuildImage,
     ComputeType,
     BuildEnvironmentVariableType
)
from aws_cdk.aws_codepipeline import Pipeline, Artifact
from aws_cdk.aws_codepipeline_actions import GitHubSourceAction, CodeBuildAction
from aws_cdk.aws_iam import PolicyStatement, Effect

class CdkWorkshopPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.environment_type = self.node.try_get_context("environmentType")
        self.context = self.node.try_get_context(self.environment_type)

        # Artifacts bucket
        bucket = Bucket(
            self,
            "S3Bucket",
            bucket_name=self.context["pipeline"]["bucketName"],
            public_read_access=False
        )
        
        # CodePipeline pipeline definition
        pipeline = Pipeline(
            self,
            "Pipeline",
            artifact_bucket=bucket,
            pipeline_name="cdk-workshop-pipeline"
        )
        source_output = Artifact()
        self.source_stage = pipeline.add_stage(stage_name="Source")
        self.code_validation_stage = pipeline.add_stage(stage_name="CodeQuality")
        self.build_stage = pipeline.add_stage(stage_name="Deploy")

        # Source Stage
        self.source_stage.add_action(
            GitHubSourceAction(
                action_name = "GitHub_source",
                output = source_output,
                owner = self.context["github"]["owner"],
                repo = self.context["github"]["repositoryName"],
                oauth_token = SecretValue.secrets_manager(self.context["github"]["oauthSecretName"]),
                branch = "main"
            )
        )

        environment = BuildEnvironment(
            build_image=LinuxBuildImage.STANDARD_4_0,
            compute_type=ComputeType.SMALL,
            privileged=True
        )
        # Code Validation stage
        self.add_code_validation_stage(environment,source_output)
        # Deploy stage
        build_spec_file = BuildSpec.from_source_filename(self.context["pipeline"]["buildSpecLocation"])
        project = PipelineProject(
            self,
            "PipelineProject",
            project_name="cdk-workshop-deploy",
            build_spec=build_spec_file,
            environment=environment
        )
        self.build_stage.add_action(
            CodeBuildAction(
                input=source_output,
                project=project,
                outputs=[Artifact()],
                action_name="CodeBuild"
            )
        )
        self.add_deploy_permissions(project)
        
    def add_deploy_permissions(self,project):
        project.add_to_role_policy(
            PolicyStatement(
                sid = "CloudFormationPermissions",
                actions = [
                    "cloudformation:DescribeStacks",
                    "cloudformation:GetTemplate",
                    "cloudformation:DeleteChangeSet",
                    "cloudformation:CreateChangeSet",
                    "cloudformation:DescribeChangeSet",
                    "cloudformation:ExecuteChangeSet",
                    "cloudformation:DescribeStackEvents",
                    "cloudformation:DeleteStack"
                ],
                effect = Effect.ALLOW,
                resources= [
                    f'arn:aws:cloudformation:{self.region}:{self.account}:stack/{self.stack_name}*',
                    f'arn:aws:cloudformation:{self.region}:{self.account}:stack/{self.stack_name}/*',
                    f'arn:aws:cloudformation:{self.region}:{self.account}:stack/cdk-workshop-stack*',
                    f'arn:aws:cloudformation:{self.region}:{self.account}:stack/cdk-workshop-stack*/*',
                    f'arn:aws:cloudformation:{self.region}:{self.account}:stack/CDKToolkit/*'
                ]
            )
        )

        project.add_to_role_policy(
            PolicyStatement(
                sid = "S3Permissions",
                actions = [
                   "s3:*"
                ],
                effect = Effect.ALLOW,
                resources= [
                    "arn:aws:s3:::cdk*",
                    f'arn:aws:s3:::{self.context["pipeline"]["bucketName"]}'
                ]
            )
        )

        project.add_to_role_policy(
            PolicyStatement(
                sid = "S3Permissions2",
                actions = [
                   "s3:GetBucketLocation",
                   "s3:ListAllMyBuckets",
                   "s3:ListBucket"
                ],
                effect = Effect.ALLOW,
                resources= [
                    "*"
                ]
            )
        )

        project.add_to_role_policy(
            PolicyStatement(
                sid = "IAMPermissions",
                actions = [
                    "iam:*"
                ],
                effect = Effect.ALLOW,
                resources= [
                    f'arn:aws:iam::{self.account}:role/{self.context["pipeline"]["targetStack"]}*',
                    f'arn:aws:iam::{self.account}:role/cdk-*'
                ]
            ) 
        )

        project.add_to_role_policy(
            PolicyStatement(
                sid = "APIGatewayPermissions",
                actions = [
                    "apigateway:POST",
                    "apigateway:PUT",
                    "apigateway:DELETE",
                    "apigateway:GET",
                    "apigateway:GetResources",
                    "apigateway:PATCH"
                ],
                effect = Effect.ALLOW,
                resources= [
                    f'arn:aws:apigateway:{self.region}::/restapis*',
                    f'arn:aws:apigateway:{self.region}::/account'
                ]
            ) 
        )

        project.add_to_role_policy(
            PolicyStatement(
                sid = "CodeDeployPermissions",
                actions = [
                    "codedeploy:CreateApplication",
                    "codedeploy:DeleteApplication",
                    "codedeploy:UpdateApplication",
                    "codedeploy:CreateDeployment",
                    "codedeploy:CreateDeploymentGroup",
                    "codedeploy:DeleteDeploymentGroup",
                    "codedeploy:UpdateDeploymentGroup",
                    "codedeploy:GetDeploymentConfig",
                    "codedeploy:GetDeployment",
                    "codedeploy:RegisterApplicationRevision"
                ],
                effect = Effect.ALLOW,
                resources= [
                    f'arn:aws:codedeploy:{self.region}:{self.account}:application:{self.context["pipeline"]["targetStack"]}*',
                    f'arn:aws:codedeploy:{self.region}:{self.account}:deploymentgroup:{self.context["pipeline"]["targetStack"]}*',
                    f'arn:aws:codedeploy:{self.region}:{self.account}:deploymentconfig:CodeDeployDefault.LambdaCanary10Percent5Minutes'
                ]
            ) 
        )

        project.add_to_role_policy(
            PolicyStatement(
                sid = "LambdaPermissions",
                actions = [
                    "lambda:GetFunction",
                    "lambda:DeleteFunction",
                    "lambda:CreateFunction",
                    "lambda:UpdateFunction",
                    "lambda:ListVersionsByFunction",
                    "lambda:PublishVersion",
                    "lambda:UpdateAlias",
                    "lambda:DeleteAlias",
                    "lambda:GetAlias",
                    "lambda:CreateAlias",
                    "lambda:AddPermission",
                    "lambda:UpdateFunctionCode",
                    "lambda:RemovePermission"
                ],
                effect = Effect.ALLOW,
                resources= [
                    f'arn:aws:lambda:{self.region}:{self.account}:function:cdk-workshop-function*'
                ]
            ) 
        )

        project.add_to_role_policy(
            PolicyStatement(
                sid = "AlarmPermissions",
                actions = [
                    "cloudwatch:DescribeAlarms",
                    "cloudwatch:DeleteAlarms",
                    "cloudwatch:PutMetricAlarm"
                ],
                effect = Effect.ALLOW,
                resources= [
                    f'arn:aws:cloudwatch:{self.region}:{self.account}:alarm:{self.context["pipeline"]["targetStack"]}*'
                ]
            ) 
        )

        project.add_to_role_policy(
            PolicyStatement(
                sid = "SSMPermissions",
                actions = [
                    "ssm:GetParameter"
                ],
                effect = Effect.ALLOW,
                resources= [
                    f'arn:aws:ssm:{self.region}:{self.account}:parameter/cdk-bootstrap/*' 
                ]
            ) 
        )

    def add_code_validation_stage(self,environment,source_output):
        runtime_versions = {
            "python": 3.8,
            "nodejs": 12
        }
        cdk_install_commands = [
            "npm install -g aws-cdk",
            "cdk --version",
            "python3 -m venv .env",
            "chmod +x .env/bin/activate",
            ". .env/bin/activate",
            "pip3 install -r requirements.txt"
        ]
        # PyLint Stage
        project = PipelineProject(
            self,
            "LinterStage",
            project_name="cdk-workshop-linter",
            build_spec= BuildSpec.from_object_to_yaml({
              "version": 0.2,
              "phases": {
                "install": {
                  "runtime-versions": runtime_versions,
                  "commands": cdk_install_commands
                },
                "build": {
                  "commands": [
                    "python3 -m pylint cdk_workshop",
                    "python3 -m pylint tests",
                    "python3 -m pylint app.py"
                  ]
                }
              }
            }),
            environment=environment
        )
        self.code_validation_stage.add_action(
            CodeBuildAction(
                input=source_output,
                project=project,
                outputs=[Artifact()],
                action_name="Linter")
        )
        #Unit testing Stage
        project = PipelineProject(
            self,
            "UnitTestingStage",
            project_name="cdk-workshop-unit-tests",
            build_spec= BuildSpec.from_object_to_yaml({
              "version": 0.2,
              "phases": {
                "install": {
                  "runtime-versions": runtime_versions,
                  "commands": cdk_install_commands
                },
                "build": {
                  "commands": [
                    "coverage run -m pytest",
                    "coverage report"
                  ]
                }
              }
            }),
            environment=environment
        )
        self.code_validation_stage.add_action(
            CodeBuildAction(
                input=source_output,
                project=project,
                outputs=[Artifact()],
                action_name="UnitTesting"
            )
        )
        # CFN Nag stage
        project = PipelineProject(
            self,
            "CfnNagStage",
            project_name="cdk-workshop-cfn-nag",
            environment=environment,
            environment_variables= {
                "ENV": { "value": self.environment_type, "type": BuildEnvironmentVariableType.PLAINTEXT },
                "STACK_NAME": { "value": self.context["pipeline"]["targetStack"], "type": BuildEnvironmentVariableType.PLAINTEXT },
            },
            build_spec= BuildSpec.from_object_to_yaml({
              "version": 0.2,
              "phases": {
                "install": {
                    "runtime-versions": {
                        "python": 3.8,
                        "nodejs": 12,
                        "ruby": 2.7
                    },
                    "commands": [
                        "npm install -g aws-cdk",
                        "cdk --version",
                        "python3 -m venv .env",
                        "chmod +x .env/bin/activate",
                        ". .env/bin/activate",
                        "pip3 install -r requirements.txt",
                        "gem install cfn-nag"
                    ]
                },
                "pre_build": {
                    "commands": [
                        "ACCOUNT=$(aws sts get-caller-identity | jq -r '.Account')",
                        "cdk synth $STACK_NAME -c account=$ACCOUNT -c environmentType=$ENV >> template.yaml"
                    ]
                },
                "build": {
                    "commands": [
                        "cfn_nag_scan --input-path template.yaml"
                    ]
                }
              }
            })
        )
        self.code_validation_stage.add_action(
            CodeBuildAction(
                input=source_output,
                project=project,
                outputs=[Artifact()],
                action_name="CfnNag")
        )
        # Safety stage
        project = PipelineProject(
            self,
            "PipAudit",
            project_name="cdk-workshop-dependency-audit",
            build_spec= BuildSpec.from_object_to_yaml({
              "version": 0.2,
              "phases": {
                "install": {
                    "runtime-versions": {
                        "python": 3.8
                    },
                    "commands": [
                        "python3 -m venv .env",
                        "chmod +x .env/bin/activate",
                        ". .env/bin/activate",
                        "pip3 install -r requirements.txt"
                    ]
                },
                "build": {
                    "commands": [
                        "safety check"
                    ]
                }
              }
            }),
            environment=environment
        )
        self.code_validation_stage.add_action(
            CodeBuildAction(
                input=source_output,
                project=project,
                outputs=[Artifact()],
                action_name="DependenciesAudit")
        )
        #Git-secrets Stage
        project = PipelineProject(
            self,
            "GitSecretsStage",
            project_name="cdk-workshop-git-secrets",
            build_spec= BuildSpec.from_object_to_yaml({
              "version": 0.2,
              "phases": {
                "install": {
                    "commands": [
                        "SECRETS_FOLDER=git-secrets",
                        "mkdir $SECRETS_FOLDER",
                        "git clone --quiet https://github.com/awslabs/git-secrets.git $SECRETS_FOLDER",
                        "cd $SECRETS_FOLDER",
                        "make install",
                        "cd .. && rm -rf $SECRETS_FOLDER"
                    ]
                },
                "build": {
                    "commands": [
                        "git secrets --scan"
                    ]
                }
              }
            }),
            environment=environment
        )
        self.code_validation_stage.add_action(
            CodeBuildAction(
                input=source_output,
                project=project,
                outputs=[Artifact()],
                action_name="GitSecrets")
        )
