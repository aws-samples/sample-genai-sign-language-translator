import * as cdk from 'aws-cdk-lib';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import { WebSocketApi, WebSocketStage } from 'aws-cdk-lib/aws-apigatewayv2';
import { WebSocketLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';
import {Stack, StackProps, Duration, RemovalPolicy} from 'aws-cdk-lib';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs'
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';

import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as ddb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import {S3} from "aws-cdk-lib/aws-ses-actions";
import {Bucket} from "aws-cdk-lib/aws-s3";

interface GenASLConfig {
    lambdaSettings: {
      runtime: string;
      memorySize: number;
      timeout: number;
    };
    // bucketName: string;
    pose_bucket: string,
    key_prefix: string,
    table_name: string,
    region: string
    eng_to_asl_model:string,
    asl_to_eng_model:string,
    amplifyEnv?: string
    }


export class GenASLBackendStack extends Stack {
    public readonly api: apigateway.RestApi;
    public readonly webSocketApi: WebSocketApi;
    public readonly webSocketStage: WebSocketStage;
    public readonly dataBucket:Bucket;

    constructor(scope: Construct, id: string, config: GenASLConfig, props?: StackProps) {
      super(scope, id, props);

      //GenASLDataBucket
      this.dataBucket = new s3.Bucket(this, 'user_data_bucket', {

              versioned: true,
              encryption: s3.BucketEncryption.S3_MANAGED,
              blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
              removalPolicy: RemovalPolicy.DESTROY,
              autoDeleteObjects: true,

              // Add CORS rules if needed
              cors: [
                {
                  allowedMethods: [
                      s3.HttpMethods.GET,
                      s3.HttpMethods.PUT,
                      s3.HttpMethods.POST,
                      s3.HttpMethods.DELETE,
                      s3.HttpMethods.HEAD,

                  ],
                  allowedOrigins: ['*'],
                  allowedHeaders: ['*'],
                    exposedHeaders:[
                        "x-amz-server-side-encryption",
                        "x-amz-request-id",
                        "x-amz-id-2",
                        "ETag",
                        "x-amz-meta-foo"
                    ],
                    maxAge:3000
                },
              ],
        });

       // Define the FFmpeg Layer — binary is downloaded at build time via build-layer.sh
        const ffmpegLayer = new lambda.LayerVersion(this, 'FFmpegLayer', {
          code: lambda.Code.fromAsset('./amplify/custom/functions/layers/ffmpeg', {
            bundling: {
              image: cdk.DockerImage.fromRegistry('public.ecr.aws/sam/build-python3.11:latest'),
              command: [
                'bash', '-c',
                'bash /asset-input/build-layer.sh && cp -r /asset-input/bin /asset-output/bin',
              ],
            },
          }),
          compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
          description: 'FFmpeg layer for video processing',
        });



        const blendedPoseFunction = new lambda.Function(this, 'BlendedPoseFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'blendedpose_handler.lambda_handler',
            code: lambda.Code.fromAsset('./amplify/custom/functions/blendedpose'),
            functionName: 'BlendedPoseFunction-' + (config.amplifyEnv || 'dev'),
            description: 'This function creates a blended pose',
            timeout: Duration.seconds(config.lambdaSettings.timeout),
            memorySize: 2048, // Increased memory for video processing
            tracing: lambda.Tracing.ACTIVE, // Enable X-Ray tracing
            environment: {
            POSE_BUCKET: config.pose_bucket,
            ASL_DATA_BUCKET: this.dataBucket.bucketName,
            KEY_PREFIX: config.key_prefix,
            TABLE_NAME: config.table_name,
            },
        });

        blendedPoseFunction.addToRolePolicy(new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ['dynamodb:GetItem', 'dynamodb:Scan', 'dynamodb:Query'],
          resources: [this.formatArn({
            service: 'dynamodb',
            resource: 'table',
            resourceName: config.table_name,
          })],
        }));



        const gloss2PoseFunction = new lambda.Function(this, 'Gloss2PoseFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'gloss2pose_handler.lambda_handler',
            code: lambda.Code.fromAsset('./amplify/custom/functions/gloss2pose'),
            functionName: 'Gloss2PoseFunction-' + (config.amplifyEnv || 'dev'),
            description: 'This function converts gloss to pose',
            timeout: Duration.seconds(config.lambdaSettings.timeout),
            memorySize: 2048, // Increased memory for video processing
            layers: [ffmpegLayer],
            tracing: lambda.Tracing.ACTIVE, // Enable X-Ray tracing
            environment: {
            POSE_BUCKET: config.pose_bucket,
            ASL_DATA_BUCKET: this.dataBucket.bucketName,
            KEY_PREFIX: config.key_prefix,
            TABLE_NAME: config.table_name,
            },
        });

        gloss2PoseFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['dynamodb:GetItem', 'dynamodb:Scan', 'dynamodb:Query'],
      resources: [this.formatArn({
        service: 'dynamodb',
        resource: 'table',
        resourceName: 'Pose_Data*',
      })],
    }));

        // Add S3 read permissions for genasl-avatar bucket
    const avatarBucket = s3.Bucket.fromBucketName(this, 'AvatarBucket', config.pose_bucket);
    avatarBucket.grantRead(gloss2PoseFunction);
    avatarBucket.grantRead(blendedPoseFunction);

    // Add S3 full access permissions for genasl-data bucket
    this.dataBucket.grantReadWrite(gloss2PoseFunction);
    this.dataBucket.grantReadWrite(blendedPoseFunction);


        const text2GlossFunction = new lambda.Function(this, 'Text2GlossFunction', {
            runtime: lambda.Runtime.PYTHON_3_11, // Specify the runtime
            handler: 'text2gloss_handler.lambda_handler',           // Specify the handler function
            code: lambda.Code.fromAsset('./amplify/custom/functions/text2gloss'),
            functionName: 'Text2GlossFunction-' + (config.amplifyEnv || 'dev'),
            description: 'This function converts text to gloss',
            timeout: Duration.seconds(300), // Reduced timeout for text processing
            memorySize: 512, // Reduced memory for text processing
            tracing: lambda.Tracing.ACTIVE, // Enable X-Ray tracing
            environment: {
                ENG_TO_ASL_MODEL: config.eng_to_asl_model,
            },

        });
        text2GlossFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['bedrock:*'],
      resources: ['*'],
    }));
        // Define new Lambda functions for the updated Step Functions
        const processTranscriptionFunction = new lambda.Function(this, 'ProcessTranscriptionFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'process_transcription_handler.lambda_handler',
            code: lambda.Code.fromAsset('./amplify/custom/functions/process_transcription'),
            functionName: 'ProcessTranscriptionFunction-' + (config.amplifyEnv || 'dev'),
            description: 'This function processes the transcription job result',
            timeout: Duration.seconds(120), // Reduced timeout for transcription processing
            memorySize: 512, // Reduced memory for transcription processing
        });

    processTranscriptionFunction.addToRolePolicy(new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: [
            'transcribe:GetTranscriptionJob',
            's3:GetObject'
          ],
          resources: ['*'],
        }));

        const stateMachineRole = new iam.Role(this, 'StateMachineRole', {
            assumedBy: new iam.ServicePrincipal('states.amazonaws.com'),
          });
          
        this.dataBucket.grantRead(stateMachineRole);

        stateMachineRole.addToPolicy(new iam.PolicyStatement({
            actions: ['transcribe:StartTranscriptionJob', 'transcribe:GetTranscriptionJob'],
            resources: ['*'],
          }));
          
        // Grant Transcribe permissions
        stateMachineRole.addToPolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
            'transcribe:StartTranscriptionJob',
            'transcribe:GetTranscriptionJob',
            's3:GetObject',
            's3:ListBucket'
            ],
            resources: ['*'],
        }));
        // Step Functions definition
        const startTranscriptionJob = new tasks.CallAwsService(this, 'StartTranscriptionJob', {
            service: 'transcribe',
            action: 'startTranscriptionJob',
            parameters: {
                Media: {
                    'MediaFileUri.$': "States.Format('s3://{}/{}', $.BucketName, $.KeyName)"
                },
                'TranscriptionJobName.$': 'States.UUID()',
                IdentifyLanguage: true
            },
            iamResources: ['*'],
        });



                
        const wait = new sfn.Wait(this, 'Wait', {
            time: sfn.WaitTime.duration(cdk.Duration.seconds(2))
        });

        const getTranscriptionJob = new tasks.CallAwsService(this, 'GetTranscriptionJob', {
            service: 'transcribe',
            action: 'getTranscriptionJob',
            iamResources: ['*'],
            parameters: {
                'TranscriptionJobName.$': '$.TranscriptionJob.TranscriptionJobName'
            },
            });
        
            // Now, we can create the ProcessTranscription task
        const processTranscription = new tasks.LambdaInvoke(this, 'ProcessTranscription', {
            lambdaFunction: processTranscriptionFunction,
            payload: sfn.TaskInput.fromObject({
            'TranscriptionJobName.$': '$.TranscriptionJob.TranscriptionJobName'
            }),
            retryOnServiceExceptions: true,
            outputPath: '$.Payload',
            });
        
        // Add retry configuration
        processTranscription.addRetry({
            errors: ['States.TaskFailed'],
            interval: cdk.Duration.seconds(2),
            maxAttempts: 3,
            backoffRate: 1,
            });

        const text2Gloss = new tasks.LambdaInvoke(this, 'Text2Gloss', {
            lambdaFunction: text2GlossFunction,
            payload: sfn.TaskInput.fromObject({
                'Text.$': '$.Text'
            }),
            outputPath: '$.Payload',
            retryOnServiceExceptions: true,
        }).addRetry({
            errors: ['States.TaskFailed'],
            interval: cdk.Duration.seconds(15),
            maxAttempts: 5,
            backoffRate: 1.5,
          });

        const gloss2Pose = new tasks.LambdaInvoke(this, 'Gloss2Pose', {
            lambdaFunction: gloss2PoseFunction,
            retryOnServiceExceptions: true,
        }).addRetry({
            errors: ['States.TaskFailed'],
            interval: cdk.Duration.seconds(15),
            maxAttempts: 5,
            backoffRate: 1.5,
          });

        const inputCheck = new sfn.Choice(this, 'InputCheck')
            .when(sfn.Condition.isPresent('$.Text'), text2Gloss)
            .otherwise(startTranscriptionJob);

        
        // Failed state
        const failedState = new sfn.Fail(this, 'Failed', {
            cause: 'transcription job failed',
            error: 'FAILED',
        });

        // TranscriptionJobStatus Choice state
        const transcriptionJobStatus = new sfn.Choice(this, 'TranscriptionJobStatus')
        .when(sfn.Condition.stringEquals('$.TranscriptionJob.TranscriptionJobStatus', 'COMPLETED'), processTranscription)
        .when(sfn.Condition.stringEquals('$.TranscriptionJob.TranscriptionJobStatus', 'FAILED'), failedState)
        .otherwise(wait);

            // Chain the states
        startTranscriptionJob.next(wait);
        wait.next(getTranscriptionJob);
        getTranscriptionJob.next(transcriptionJobStatus);
        processTranscription.next(text2Gloss);
        text2Gloss.next(gloss2Pose);
        
        // const logGroup = new logs.LogGroup(this, 'GenASLStateMachineLogGroup'+(config.amplifyEnv || 'dev'));

        // Create the state machine
        const stateMachine = new sfn.StateMachine(this, 'GenASLStateMachine'+(config.amplifyEnv || 'dev'), {
            definition: inputCheck,
            comment: 'A state machine that converts english text to ASL sign',
            role: stateMachineRole,
            // logs: {
            //     destination: logGroup,
            //     level: sfn.LogLevel.ALL }
        });

        const blendedPoseTask = new tasks.LambdaInvoke(this, 'BlendedPose', {
          lambdaFunction: blendedPoseFunction,
          outputPath: '$.Payload',
          retryOnServiceExceptions: true,
        });

        const blendedPoseStateMachine = new sfn.StateMachine(this, 'BlendedPoseStateMachine'+(config.amplifyEnv || 'dev'), {
          definition: blendedPoseTask,
          comment: 'Invoke BlendedPose Lambda in async',
        });

        const audio2SignFunction = new lambda.Function(this, 'Audio2SignFunction', {
          runtime: lambda.Runtime.PYTHON_3_11, // Specify the runtime
          handler: 'audio2sign_handler.lambda_handler',           // Specify the handler function
          code: lambda.Code.fromAsset('./amplify/custom/functions/audio2sign'),
          functionName: 'Audio2SignFunction-' + (config.amplifyEnv || 'dev'),
          description: 'This function converts audio to sign',
          timeout: Duration.seconds(config.lambdaSettings.timeout),
          memorySize: config.lambdaSettings.memorySize,
          environment: {
              STATE_MACHINE_ARN: stateMachine.stateMachineArn,
              STATE_MACHINE_ARN_BLENDED_POSE: blendedPoseStateMachine.stateMachineArn,
              AGENTCORE_AGENT_ID: 'slagent-4BncgN2p1h',
              AGENTCORE_AGENT_ARN: 'arn:aws:bedrock-agentcore:us-west-2:853513360253:runtime/slagent-4BncgN2p1h',
              AGENTCORE_REGION: 'us-west-2'
          },
      });

      audio2SignFunction.addToRolePolicy(new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: [
            'states:StartExecution',
            'states:DescribeExecution',
            'states:StopExecution'
          ],
          resources: ["*"],
        }));

        // Grant audio2SignFunction permission to invoke the AgentCore agent
        audio2SignFunction.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
                'bedrock-agentcore:InvokeAgentRuntime',
                'bedrock-agentcore:GetSession',
                'bedrock-agentcore:CreateSession'
            ],
            resources: ['*'],
        }));

        // Create the Conversational ASL Agent Lambda function (enhanced SignLanguageAgent)
        const signLanguageAgentFunction = new lambda.Function(this, 'SignLanguageAgentFunction', {
            runtime: lambda.Runtime.PYTHON_3_11,
            handler: 'conversational_asl_agent_main.invoke',
            code: lambda.Code.fromAsset('./amplify/custom/functions/conversational_asl_agent'),
            functionName: 'SignLanguageAgentFunction-' + (config.amplifyEnv || 'dev'),
            description: 'Conversational bidirectional ASL agent with enhanced natural language capabilities',
            timeout: Duration.seconds(900), // 15 minutes for complex workflows
            memorySize: 1536, // Increased memory for conversational processing and context management
            layers: [ffmpegLayer],
            tracing: lambda.Tracing.ACTIVE, // Enable X-Ray tracing
            environment: {
                POSE_BUCKET: config.pose_bucket,
                ASL_DATA_BUCKET: this.dataBucket.bucketName,
                KEY_PREFIX: config.key_prefix,
                TABLE_NAME: config.table_name,
                ENG_TO_ASL_MODEL: config.eng_to_asl_model,
                ASL_TO_ENG_MODEL: config.asl_to_eng_model,
                REGION: config.region,
                // AgentCore specific environment variables
                BEDROCK_AGENT_RUNTIME_REGION: config.region,
                LOG_LEVEL: 'INFO',
                // Conversational agent specific environment variables
                CONVERSATION_MEMORY_TTL: '3600', // 1 hour session timeout
                CONVERSATION_HISTORY_LIMIT: '50', // Maximum conversation history items
                CONVERSATION_CONTEXT_CLEANUP_INTERVAL: '300', // 5 minutes cleanup interval
                CONVERSATION_ENABLE_PROACTIVE_TIPS: 'true',
                CONVERSATION_ENABLE_CONTEXT_ANALYSIS: 'true',
                CONVERSATION_RESPONSE_ENHANCEMENT: 'true',
                // Memory optimization settings
                AGENTCORE_MEMORY_OPTIMIZATION: 'true',
                AGENTCORE_MEMORY_COMPRESSION: 'true',
                AGENTCORE_MEMORY_BATCH_SIZE: '10'
            },
        });

        // Grant comprehensive IAM permissions for the agent
        signLanguageAgentFunction.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
                'bedrock:*',
                'bedrock-agent:*',
                'bedrock-runtime:*'
            ],
            resources: ['*'],
        }));

        signLanguageAgentFunction.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
                'transcribe:StartTranscriptionJob',
                'transcribe:GetTranscriptionJob',
                'transcribe:ListTranscriptionJobs'
            ],
            resources: ['*'],
        }));

        signLanguageAgentFunction.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
                'dynamodb:GetItem',
                'dynamodb:Scan',
                'dynamodb:Query',
                'dynamodb:PutItem',
                'dynamodb:UpdateItem'
            ],
            resources: [
                this.formatArn({
                    service: 'dynamodb',
                    resource: 'table',
                    resourceName: config.table_name,
                }),
                this.formatArn({
                    service: 'dynamodb',
                    resource: 'table',
                    resourceName: 'Pose_Data*',
                })
            ],
        }));

        signLanguageAgentFunction.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
                'kinesisvideo:*'
            ],
            resources: ['*'],
        }));

        signLanguageAgentFunction.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents'
            ],
            resources: ['*'],
        }));

        // Grant S3 permissions
        const avatarBucketForAgent = s3.Bucket.fromBucketName(this, 'AvatarBucketForAgent', config.pose_bucket);
        avatarBucketForAgent.grantRead(signLanguageAgentFunction);
        this.dataBucket.grantReadWrite(signLanguageAgentFunction);

        // Configure monitoring and logging
        
        // Create CloudWatch Log Groups for better log organization
        const agentLogGroup = new logs.LogGroup(this, 'SignLanguageAgentLogGroup', {
            logGroupName: `/aws/lambda/${signLanguageAgentFunction.functionName}`,
            retention: logs.RetentionDays.ONE_MONTH,
            removalPolicy: RemovalPolicy.DESTROY,
        });

        const text2GlossLogGroup = new logs.LogGroup(this, 'Text2GlossLogGroup', {
            logGroupName: `/aws/lambda/${text2GlossFunction.functionName}`,
            retention: logs.RetentionDays.ONE_MONTH,
            removalPolicy: RemovalPolicy.DESTROY,
        });

        const gloss2PoseLogGroup = new logs.LogGroup(this, 'Gloss2PoseLogGroup', {
            logGroupName: `/aws/lambda/${gloss2PoseFunction.functionName}`,
            retention: logs.RetentionDays.ONE_MONTH,
            removalPolicy: RemovalPolicy.DESTROY,
        });

        // X-Ray tracing is enabled via the tracing property on each function

        // Grant X-Ray permissions
        const xrayPolicy = new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: [
                'xray:PutTraceSegments',
                'xray:PutTelemetryRecords'
            ],
            resources: ['*'],
        });

        signLanguageAgentFunction.addToRolePolicy(xrayPolicy);
        text2GlossFunction.addToRolePolicy(xrayPolicy);
        gloss2PoseFunction.addToRolePolicy(xrayPolicy);
        blendedPoseFunction.addToRolePolicy(xrayPolicy);

        // Create custom CloudWatch metrics for translation pipeline monitoring
        const translationMetricsNamespace = 'GenASL/Translation';
        const conversationMetricsNamespace = 'GenASL/Conversation';

        // Create CloudWatch Dashboard for monitoring
        const dashboard = new cloudwatch.Dashboard(this, 'GenASLDashboard', {
            dashboardName: `GenASL-Dashboard-${config.amplifyEnv || 'dev'}`,
        });

        // Add Lambda function metrics to dashboard
        dashboard.addWidgets(
            new cloudwatch.GraphWidget({
                title: 'Conversational Agent Function Metrics',
                left: [signLanguageAgentFunction.metricInvocations()],
                right: [signLanguageAgentFunction.metricErrors()],
            }),
            new cloudwatch.GraphWidget({
                title: 'Conversational Agent Duration & Memory',
                left: [signLanguageAgentFunction.metricDuration()],
                right: [
                    new cloudwatch.Metric({
                        namespace: 'AWS/Lambda',
                        metricName: 'MemoryUtilization',
                        dimensionsMap: {
                            FunctionName: signLanguageAgentFunction.functionName,
                        },
                    }),
                ],
            }),
            new cloudwatch.GraphWidget({
                title: 'Conversation Success Rates',
                left: [
                    new cloudwatch.Metric({
                        namespace: conversationMetricsNamespace,
                        metricName: 'ConversationSuccess',
                        statistic: 'Sum',
                    }),
                    new cloudwatch.Metric({
                        namespace: conversationMetricsNamespace,
                        metricName: 'ConversationFailure',
                        statistic: 'Sum',
                    }),
                ],
                right: [
                    new cloudwatch.Metric({
                        namespace: conversationMetricsNamespace,
                        metricName: 'IntentClassificationAccuracy',
                        statistic: 'Average',
                    }),
                ],
            }),
            new cloudwatch.GraphWidget({
                title: 'Session Lifecycle Metrics',
                left: [
                    new cloudwatch.Metric({
                        namespace: conversationMetricsNamespace,
                        metricName: 'SessionsCreated',
                        statistic: 'Sum',
                    }),
                    new cloudwatch.Metric({
                        namespace: conversationMetricsNamespace,
                        metricName: 'SessionsActive',
                        statistic: 'Average',
                    }),
                ],
                right: [
                    new cloudwatch.Metric({
                        namespace: conversationMetricsNamespace,
                        metricName: 'SessionDuration',
                        statistic: 'Average',
                    }),
                    new cloudwatch.Metric({
                        namespace: conversationMetricsNamespace,
                        metricName: 'MemoryUsage',
                        statistic: 'Average',
                    }),
                ],
            }),
            new cloudwatch.GraphWidget({
                title: 'Translation Pipeline Functions',
                left: [
                    text2GlossFunction.metricInvocations(),
                    gloss2PoseFunction.metricInvocations(),
                    blendedPoseFunction.metricInvocations()
                ],
                right: [
                    text2GlossFunction.metricErrors(),
                    gloss2PoseFunction.metricErrors(),
                    blendedPoseFunction.metricErrors()
                ],
            })
        );

        // Create CloudWatch Alarms for critical errors
        const conversationalAgentErrorAlarm = new cloudwatch.Alarm(this, 'ConversationalAgentErrorAlarm', {
            metric: signLanguageAgentFunction.metricErrors(),
            threshold: 5,
            evaluationPeriods: 2,
            alarmDescription: 'Conversational ASL Agent function errors',
        });

        const conversationalAgentDurationAlarm = new cloudwatch.Alarm(this, 'ConversationalAgentDurationAlarm', {
            metric: signLanguageAgentFunction.metricDuration(),
            threshold: 30000, // 30 seconds
            evaluationPeriods: 3,
            alarmDescription: 'Conversational ASL Agent function duration too high',
        });

        const conversationSuccessRateAlarm = new cloudwatch.Alarm(this, 'ConversationSuccessRateAlarm', {
            metric: new cloudwatch.MathExpression({
                expression: '(conversation_success / (conversation_success + conversation_failure)) * 100',
                usingMetrics: {
                    conversation_success: new cloudwatch.Metric({
                        namespace: conversationMetricsNamespace,
                        metricName: 'ConversationSuccess',
                        statistic: 'Sum',
                    }),
                    conversation_failure: new cloudwatch.Metric({
                        namespace: conversationMetricsNamespace,
                        metricName: 'ConversationFailure',
                        statistic: 'Sum',
                    }),
                },
            }),
            threshold: 85, // Alert if success rate drops below 85%
            evaluationPeriods: 3,
            comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            alarmDescription: 'Conversation success rate too low',
        });

        const memoryUsageAlarm = new cloudwatch.Alarm(this, 'ConversationMemoryUsageAlarm', {
            metric: new cloudwatch.Metric({
                namespace: conversationMetricsNamespace,
                metricName: 'MemoryUsage',
                statistic: 'Average',
            }),
            threshold: 1000, // Alert if average memory usage exceeds 1000 MB
            evaluationPeriods: 2,
            alarmDescription: 'Conversation memory usage too high',
        });

        const intentClassificationAccuracyAlarm = new cloudwatch.Alarm(this, 'IntentClassificationAccuracyAlarm', {
            metric: new cloudwatch.Metric({
                namespace: conversationMetricsNamespace,
                metricName: 'IntentClassificationAccuracy',
                statistic: 'Average',
            }),
            threshold: 80, // Alert if accuracy drops below 80%
            evaluationPeriods: 3,
            comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            alarmDescription: 'Intent classification accuracy too low',
        });

        const translationPipelineErrorAlarm = new cloudwatch.Alarm(this, 'TranslationPipelineErrorAlarm', {
            metric: new cloudwatch.MathExpression({
                expression: 'text2gloss_errors + gloss2pose_errors + blended_errors',
                usingMetrics: {
                    text2gloss_errors: text2GlossFunction.metricErrors(),
                    gloss2pose_errors: gloss2PoseFunction.metricErrors(),
                    blended_errors: blendedPoseFunction.metricErrors(),
                },
            }),
            threshold: 10,
            evaluationPeriods: 2,
            alarmDescription: 'Translation pipeline function errors',
        });


         // Create the Lambda function
    const textToSpeechFunction = new lambda.Function(this, 'TextToSpeechFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'text2audio_handler.lambda_handler',
      code: lambda.Code.fromAsset('./amplify/custom/functions/text2audio'),
        functionName: 'Text2GAudioFunction-' + (config.amplifyEnv || 'dev'),
        description: 'This function converts text to audio',
        timeout: Duration.seconds(config.lambdaSettings.timeout),
        environment: {
            ASL_DATA_BUCKET: this.dataBucket.bucketName,
        },

    });

    // Grant the Lambda function permissions to use Polly and access the S3 bucket
    textToSpeechFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['polly:SynthesizeSpeech'],
      resources: ['*'],
    }));
    this.dataBucket.grantReadWrite(textToSpeechFunction);

    // Create an API Gateway
    this.api = new apigateway.RestApi(this, 'GenASLAPI' + (config.amplifyEnv || 'dev'), {
      restApiName: 'GenASLAPI' + (config.amplifyEnv || 'dev'),
      description: 'APIs for supporting bidirectional English to ASL ',
        defaultMethodOptions: {
        authorizationType: apigateway.AuthorizationType.NONE
      },
        defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization'],
        allowCredentials: false,
      },
    });

    // Create an API Gateway resource and method
    const textToSpeechResource = this.api.root.addResource('text-to-speech');
    textToSpeechResource.addMethod('POST', new apigateway.LambdaIntegration(textToSpeechFunction,
        {
      proxy: true,
      integrationResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': "'*'",
        },
      }],
    }), {
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      }],
    });

    const audioToSignResource = this.api.root.addResource('audio-to-sign');
    audioToSignResource.addMethod('POST', new apigateway.LambdaIntegration(audio2SignFunction, {
      proxy: true,
      integrationResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': "'*'",
        },
      }],
    }), {
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      }],
    });

    // Add Strands Agent API endpoint
    const agentResource = this.api.root.addResource('agent');
    agentResource.addMethod('POST', new apigateway.LambdaIntegration(signLanguageAgentFunction, {
      proxy: true,
      integrationResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': "'*'",
        },
      }],
    }), {
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
        },
      }],
    });

    /**Websocket Stack */
    const websocketTable = new ddb.Table(this, 'ConnectionsTable-'+ (config.amplifyEnv || 'dev'), {
        partitionKey: { name: 'pk', type: ddb.AttributeType.STRING },
        sortKey: { name: 'epoch', type: ddb.AttributeType.NUMBER },
        removalPolicy: cdk.RemovalPolicy.DESTROY,
        billingMode: ddb.BillingMode.PAY_PER_REQUEST,
    });
    
    const onConnectFunction = new lambda.Function(this, 'OnConnectFunction-'+ (config.amplifyEnv || 'dev'), {
        runtime: lambda.Runtime.PYTHON_3_11, // Specify the runtime
        handler: 'handler.connect',           // Specify the handler function
        code: lambda.Code.fromAsset('./amplify/custom/functions/websocket'),
        functionName: 'OnConnectFunction-'+ (config.amplifyEnv || 'dev'),
        description: 'This function is called when a user connects to the websocket',
        timeout: Duration.seconds(30), // Reduced timeout for connection handling
        layers: [ffmpegLayer],
        memorySize: 512, // Reduced memory for simple connection handling
        environment: {
            DYNAMO_TABLE_NAME: websocketTable.tableName,
            INPUT_BUCKET: this.dataBucket.bucketName,
            ASL_TO_ENG_MODEL: config.asl_to_eng_model,

        },
    });

    const OnDisConnectFunction = new lambda.Function(this, 'OnDisConnectFunction-'+ (config.amplifyEnv || 'dev'), {
        runtime: lambda.Runtime.PYTHON_3_11, // Specify the runtime
        handler: 'handler.disconnect',           // Specify the handler function
        code: lambda.Code.fromAsset('./amplify/custom/functions/websocket'),
        functionName: 'OnDisConnectFunction-'+ (config.amplifyEnv || 'dev'),
        description: 'This function is called when a user disconnects to the websocket',
        timeout: Duration.seconds(30), // Reduced timeout for disconnection handling
        layers: [ffmpegLayer],
        memorySize: 512, // Reduced memory for simple disconnection handling
        environment: {
            DYNAMO_TABLE_NAME: websocketTable.tableName,
            INPUT_BUCKET: this.dataBucket.bucketName,
            ASL_TO_ENG_MODEL: config.asl_to_eng_model,

        },
    });

    const OnDefaultFunction = new lambda.Function(this, 'OnDefaultFunction-'+ (config.amplifyEnv || 'dev'), {
        runtime: lambda.Runtime.PYTHON_3_11, // Specify the runtime
        handler: 'handler.default',           // Specify the handler function
        code: lambda.Code.fromAsset('./amplify/custom/functions/websocket'),
        functionName: 'OnDefaultFunction-'+ (config.amplifyEnv || 'dev'),
        timeout: Duration.seconds(300), // Increased timeout for agent communication
        memorySize: 1024, // Adequate memory for agent communication and processing
        layers: [ffmpegLayer],
        tracing: lambda.Tracing.ACTIVE, // Enable X-Ray tracing
        environment: {
            DYNAMO_TABLE_NAME: websocketTable.tableName,
            INPUT_BUCKET: this.dataBucket.bucketName,
            ASL_TO_ENG_MODEL: config.asl_to_eng_model,
            AGENTCORE_AGENT_ID: 'slagent-4BncgN2p1h',
            AGENTCORE_AGENT_ARN: 'arn:aws:bedrock-agentcore:us-west-2:853513360253:runtime/slagent-4BncgN2p1h',
            AGENTCORE_REGION: 'us-west-2'
        },
    });
    websocketTable.grantReadWriteData(onConnectFunction);
    websocketTable.grantReadWriteData(OnDisConnectFunction);
    websocketTable.grantReadWriteData(OnDefaultFunction);
    this.dataBucket.grantReadWrite(onConnectFunction);
    this.dataBucket.grantReadWrite(OnDefaultFunction);

    // TODO - Need to provide granular level permission
    const bedrockPolicy = new iam.PolicyStatement({
        actions: ['bedrock:*'],
        resources: ['*'],
    });

    const kvsPolicy = new iam.PolicyStatement({
      actions: ['kinesisvideo:*'],
      resources: ['*'],
    });

    OnDefaultFunction.addToRolePolicy(bedrockPolicy)
    OnDefaultFunction.addToRolePolicy(kvsPolicy)
    OnDefaultFunction.addToRolePolicy(xrayPolicy)
    
    // Grant WebSocket function permission to invoke the agentcore agent
    OnDefaultFunction.addToRolePolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
            'bedrock-agentcore:InvokeAgent',
            'bedrock-agentcore:InvokeAgentStreaming'
        ],
        resources: ['arn:aws:bedrock-agentcore:us-west-2:853513360253:runtime/slagent-4BncgN2p1h'],
    }));
    
    // Add S3 full access permissions for genasl-data bucket
    this.dataBucket.grantReadWrite(onConnectFunction);
    this.dataBucket.grantReadWrite(OnDefaultFunction);

    this.webSocketApi = new WebSocketApi(this, 'ServerlessChatWebsocketApi', {
        apiName: 'GenASLWSS'+ (config.amplifyEnv || 'dev'),
        connectRouteOptions: { integration: new WebSocketLambdaIntegration("ConnectIntegration", onConnectFunction)},
        disconnectRouteOptions: { integration: new WebSocketLambdaIntegration("DisconnectIntegration", OnDisConnectFunction) },
        defaultRouteOptions: { integration: new WebSocketLambdaIntegration("DefaultIntegration", OnDefaultFunction) },
    });

     this.webSocketStage = new WebSocketStage(this, 'Prod', {
        webSocketApi: this.webSocketApi,
        stageName: 'prod',
        autoDeploy: true,
    });
    this.webSocketApi.grantManageConnections(onConnectFunction);
    this.webSocketApi.grantManageConnections(OnDefaultFunction);

    }
}

