import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
// import { genSLUserDataBucket } from './storage/resource';
import { GenASLBackendStack } from './custom/functions/resource';
import {Stack} from "aws-cdk-lib";
import { PolicyStatement, Effect } from 'aws-cdk-lib/aws-iam';
import * as fs from 'fs';
import * as ini from 'ini';


const backend = defineBackend({
  auth,
  // genSLUserDataBucket,
});





// Read the INI file
const fileContent = fs.readFileSync("config.ini", 'utf-8');

// Parse the INI content
const config = ini.parse(fileContent);

const genASLConfig = {
  lambdaSettings: {
    runtime: 'nodejs18.x',
    memorySize: 1024,
    timeout: 900,
  },
  pose_bucket: config.DEFAULT.pose_bucket,
  key_prefix: config.DEFAULT.s3_prefix,
  table_name: config.DEFAULT.table_name,
  region: config.DEFAULT.region,
  eng_to_asl_model:config.DEFAULT.eng_to_asl_model,
  asl_to_eng_model:config.DEFAULT.asl_to_eng_model
  };



// Add the Audio2Sign custom Lambda stack to the backend
const genASLBackendStack =  new GenASLBackendStack(
  backend.createStack('GenASLBackendStack'),
  'GenASLBackendStackResource',
  genASLConfig
);

const authRole = backend.auth.resources.authenticatedUserIamRole;
authRole.addToPrincipalPolicy(
    new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        'kinesisvideo:*',
      ],
      resources: [
        '*',
      ],
    })
  );
authRole.addToPrincipalPolicy(
    new PolicyStatement({
      effect: Effect.ALLOW,
      actions: [
        's3:*',
      ],
      resources: [
         genASLBackendStack.dataBucket.bucketArn + '/*'
      ],
    })
  );

backend.addOutput({
  storage: {
    aws_region: Stack.of(genASLBackendStack.api).region,
    bucket_name: genASLBackendStack.dataBucket.bucketName
  },
  custom: {
    ENV:{
      amplify_env: process.env.AMPLIFY_ENV,
      region: Stack.of(genASLBackendStack).region,
    },
    API: {
      [genASLBackendStack.api.restApiName]: {
        endpoint: genASLBackendStack.api.url,
        region: Stack.of(genASLBackendStack.api).region,
        apiName: genASLBackendStack.api.restApiName,
      },
    },
    WSS: {
      [genASLBackendStack.webSocketApi.webSocketApiName!]: {
        endpoint: genASLBackendStack.webSocketStage.url,
        region: Stack.of(genASLBackendStack.webSocketApi).region,
        apiName: genASLBackendStack.webSocketApi.webSocketApiName,
      },
    },
  },}
  );