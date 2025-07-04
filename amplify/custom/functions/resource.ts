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
import * as python from '@aws-cdk/aws-lambda-python-alpha';
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
    asl_to_eng_model:string
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
              bucketName: 'genasl-data-'+ process.env.AMPLIFY_ENV,
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

       // Define the FFmpeg Layer
        const ffmpegLayer = new lambda.LayerVersion(this, 'FFmpegLayer', {
          code: lambda.Code.fromAsset('./amplify/custom/functions/layers/ffmpeg'),
          compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
          description: 'FFmpeg layer for video processing',
          layerVersionName: 'ffmpeg-layer' + process.env.AMPLIFY_ENV,
        });



        const blendedPoseFunction = new lambda.Function(this, 'BlendedPoseFunction', {
          code: lambda.Code.fromAssetImage('./amplify/custom/functions/blendedpose', {
          }),
            handler: lambda.Handler.FROM_IMAGE,
            runtime: lambda.Runtime.FROM_IMAGE,
            architecture: lambda.Architecture.ARM_64,
            functionName: 'BlendedPoseFunction-' + process.env.AMPLIFY_ENV,
            description: 'This function creates a blended pose',
            timeout: Duration.seconds(config.lambdaSettings.timeout),
            memorySize: config.lambdaSettings.memorySize,
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



        const gloss2PoseFunction = new python.PythonFunction(this, 'Gloss2PoseFunction', {
            runtime: lambda.Runtime.PYTHON_3_11, // Specify the runtime
            // handler: 'gloss2pose_handler.lambda_handler',           // Specify the handler function
            entry: './amplify/custom/functions/gloss2pose',
            index: 'gloss2pose_handler.py',
            handler: 'lambda_handler',
            // code: lambda.Code.fromAsset('./amplify/custom/functions/gloss2pose',),
            functionName: 'Gloss2PoseFunction-' + process.env.AMPLIFY_ENV,
            description: 'This function converts gloss to pose',
            timeout: Duration.seconds(config.lambdaSettings.timeout),
            memorySize: config.lambdaSettings.memorySize,
            layers: [ffmpegLayer],
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
            functionName: 'Text2GlossFunction-' + process.env.AMPLIFY_ENV,
            description: 'This function converts text to gloss',
            timeout: Duration.seconds(config.lambdaSettings.timeout),
            memorySize: config.lambdaSettings.memorySize,
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
            functionName: 'ProcessTranscriptionFunction-' + process.env.AMPLIFY_ENV,
            description: 'This function processes the transcription job result',
            timeout: Duration.seconds(config.lambdaSettings.timeout),
            memorySize: config.lambdaSettings.memorySize,
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
        
        // const logGroup = new logs.LogGroup(this, 'GenASLStateMachineLogGroup'+process.env.AMPLIFY_ENV);

        // Create the state machine
        const stateMachine = new sfn.StateMachine(this, 'GenASLStateMachine'+process.env.AMPLIFY_ENV, {
            definition: inputCheck,
            comment: 'A state machine that converts english text to ASL sign',
            role: stateMachineRole,
            // logs: {
            //     destination: logGroup,
            //     level: sfn.LogLevel.ALL }
        });

         // Create the Lambda task
        const blendedPoseTask = new tasks.LambdaInvoke(this, 'BlendedPose', {
          lambdaFunction: blendedPoseFunction,
          outputPath: '$.Payload',
          retryOnServiceExceptions: true,
        });

    // Create the state machine
        const blendedPoseStateMachine = new sfn.StateMachine(this, 'BlendedPoseStateMachine'+process.env.AMPLIFY_ENV, {
          definition: blendedPoseTask,
          comment: 'Invoke BlendedPose Lambda in async',
        });

        const audio2SignFunction = new lambda.Function(this, 'Audio2SignFunction', {
          runtime: lambda.Runtime.PYTHON_3_11, // Specify the runtime
          handler: 'audio2sign_handler.lambda_handler',           // Specify the handler function
          code: lambda.Code.fromAsset('./amplify/custom/functions/audio2sign'),
          functionName: 'Audio2SignFunction-' + process.env.AMPLIFY_ENV,
          description: 'This function converts audio to sign',
          timeout: Duration.seconds(config.lambdaSettings.timeout),
          memorySize: config.lambdaSettings.memorySize,
          environment: {
              STATE_MACHINE_ARN: stateMachine.stateMachineArn,
              STATE_MACHINE_ARN_BLENDED_POSE: blendedPoseStateMachine.stateMachineArn
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


         // Create the Lambda function
    const textToSpeechFunction = new lambda.Function(this, 'TextToSpeechFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'text2audio_handler.lambda_handler',
      code: lambda.Code.fromAsset('./amplify/custom/functions/text2audio'),
        functionName: 'Text2GAudioFunction-' + process.env.AMPLIFY_ENV,
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
    this.api = new apigateway.RestApi(this, 'GenASLAPI' + process.env.AMPLIFY_ENV, {
      restApiName: 'GenASLAPI' + process.env.AMPLIFY_ENV,
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

    /**Websocket Stack */
    const websocketTable = new ddb.Table(this, 'ConnectionsTable-'+ process.env.AMPLIFY_ENV, {
        partitionKey: { name: 'pk', type: ddb.AttributeType.STRING },
        sortKey: { name: 'epoch', type: ddb.AttributeType.NUMBER },
        removalPolicy: cdk.RemovalPolicy.DESTROY,
        billingMode: ddb.BillingMode.PAY_PER_REQUEST,
    });
    
    const onConnectFunction = new lambda.Function(this, 'OnConnectFunction-'+ process.env.AMPLIFY_ENV, {
        runtime: lambda.Runtime.PYTHON_3_11, // Specify the runtime
        handler: 'handler.connect',           // Specify the handler function
        code: lambda.Code.fromAsset('./amplify/custom/functions/websocket'),
        functionName: 'OnConnectFunction-'+ process.env.AMPLIFY_ENV,
        description: 'This function is called when a user connects to the websocket',
        timeout: Duration.seconds(config.lambdaSettings.timeout),
        layers: [ffmpegLayer],
        memorySize: config.lambdaSettings.memorySize,
        environment: {
            DYNAMO_TABLE_NAME: websocketTable.tableName,
            INPUT_BUCKET: this.dataBucket.bucketName,
            ASL_TO_ENG_MODEL: config.asl_to_eng_model,

        },
    });

    const OnDisConnectFunction = new lambda.Function(this, 'OnDisConnectFunction-'+ process.env.AMPLIFY_ENV, {
        runtime: lambda.Runtime.PYTHON_3_11, // Specify the runtime
        handler: 'handler.disconnect',           // Specify the handler function
        code: lambda.Code.fromAsset('./amplify/custom/functions/websocket'),
        functionName: 'OnDisConnectFunction-'+ process.env.AMPLIFY_ENV,
        description: 'This function is called when a user disconnects to the websocket',
        timeout: Duration.seconds(config.lambdaSettings.timeout),
        layers: [ffmpegLayer],
        memorySize: config.lambdaSettings.memorySize,
        environment: {
            DYNAMO_TABLE_NAME: websocketTable.tableName,
            INPUT_BUCKET: this.dataBucket.bucketName,
            ASL_TO_ENG_MODEL: config.asl_to_eng_model,

        },
    });

    const OnDefaultFunction = new lambda.Function(this, 'OnDefaultFunction-'+ process.env.AMPLIFY_ENV, {
        runtime: lambda.Runtime.PYTHON_3_11, // Specify the runtime
        handler: 'handler.default',           // Specify the handler function
        code: lambda.Code.fromAsset('./amplify/custom/functions/websocket'),
        functionName: 'OnDefaultFunction-'+ process.env.AMPLIFY_ENV,
        timeout: Duration.seconds(config.lambdaSettings.timeout),
        memorySize: config.lambdaSettings.memorySize,
        layers: [ffmpegLayer],
        environment: {
            DYNAMO_TABLE_NAME: websocketTable.tableName,
            INPUT_BUCKET: this.dataBucket.bucketName,
            ASL_TO_ENG_MODEL: config.asl_to_eng_model
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
    // Add S3 full access permissions for genasl-data bucket
    this.dataBucket.grantReadWrite(onConnectFunction);
    this.dataBucket.grantReadWrite(OnDefaultFunction);

    this.webSocketApi = new WebSocketApi(this, 'ServerlessChatWebsocketApi', {
        apiName: 'GenASLWSS'+ process.env.AMPLIFY_ENV,
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

