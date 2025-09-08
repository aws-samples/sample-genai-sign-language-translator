# GenASL - Generative AI powered American Sign Language Avatars

In today's world, effective communication is essential for fostering inclusivity and breaking down barriers. However, for individuals who rely on visual communication methods like American Sign Language (ASL), traditional communication tools often fall short. That's where GenASL comes in – a Generative AI-powered solution that translates speech or text into expressive ASL avatar animations, bridging the gap between spoken/written language and sign language. 

The rise of the foundational models, and the fascinating world of Generative AI that we live in, is incredibly exciting and it opens up doors to imagine and build what was not previously possible. In this blog-post, we'll dive into the architecture and implementation details of GenASL, leveraging AWS Generative AI capabilities to create human-like ASL avatar videos.



## Deploying to AWS

### 1. Batch Process


### 2. Set up the Amplify App

#### 2.1 Setup Amplify Gen2 GenASL SL Translator in your AWS account

##### 2.1.1 Create the repository
Use the following starter template to create a repository in your GitHub account. This template scaffolds genai-sl-translator with Amplify backend capabilities.
Click [genal-sl-translator](https://github.com/new?template_name=amplify-vite-react-template&template_owner=aws-samples&name=genai-sl-translator&description=GenASL%20%2D%20GenAI%20Sign%20Language%20Translator) link
and use the form in GitHub to finalize your repo's creation.

##### 2.1.2 Deploy the initial version of GenASL app

Now that the repository has been created, deploy it with Amplify.  Select GitHub. After you give Amplify access to your GitHub account via the popup window, pick the repository and main branch to deploy. Make no other changes and click through the flow to Save and deploy.
Follow the instructions in the video 
![](https://docs.amplify.aws/images/gen2/getting-started/react/deploy.mp4gggggg)

<video width="100%" controls  muted loop autoPlay>
    <source src="https://docs.amplify.aws/images/gen2/getting-started/react/deploy.mp4" type="video/mp4">
</video>

#### 2.2 Setup your local environment 


##### 2.2.2. Clone the GenASL translator source code to your local development environment
Now clone the GenASL translator repo and install the required dependencies 

```
git clone https://github.com/<github-user>/sample-genai-sign-language-translator.git
cd sample-genai-sign-language-translator && npm install --legacy-peer-deps
```

##### 2.2.1. Download amplify_outputs.json 
Now let's set up our local development environment to add features to the frontend. Click on your deployed branch and you will land on the Deployments page which shows you your build history and a list of deployed backend resources.
![](https://docs.amplify.aws/images/gen2/getting-started/react/branch-details.mp4)

<video width="100%" controls  muted loop autoPlay>
    <source src="https://docs.amplify.aws/images/gen2/getting-started/react/branch-details.mp4" type="video/mp4">
</video>

At the bottom of the page you will see a tab for Deployed backend resources. Click on the tab and then click the Download amplify_outputs.json file button.
![](https://docs.amplify.aws/images/gen2/getting-started/react/nextImageExportOptimizer/amplify-outputs-download-opt-1920.WEBP)


##### 2.2.3 Override amplify_outputs.json 
Now move the amplify_outputs.json file you downloaded above to the root of your project.

```
├── amplify
├── src
├── amplify_outputs.json <== backend outputs file
├── package.json
└── tsconfig.json
```

##### 2.2.4 Set up local AWS credentials
To make backend updates, we are going to require AWS credentials to deploy backend updates from our local machine.

Skip ahead to next step, if you already have an AWS profile with credentials on your local machine, and your AWS profile has the AmplifyBackendDeployFullAccess permission policy.

Otherwise, set up local AWS credentials that grant Amplify permissions to deploy backend updates from your local machine.

##### 2.2.5  Batch process

##### 2.2.5  Push the changes with latest config files 
To get these changes to the cloud, commit them to git and push the changes upstream.
```commandline
git commit -am "With updated configuration"
git push
```


##### 2.2.5  Deploy cloud sandbox
To update your backend without affecting the production branch, use Amplify's cloud sandbox. This feature provides a separate backend environment for each developer on a team, ideal for local development and testing.

To start your cloud sandbox, run the following command in a new Terminal window:

```commandline
export AMPLIFY_ENV=<youralias>
export AMPLIFY_REGION=us-west-2
npx ampx sandbox
```
Once the cloud sandbox has been fully deployed (~5 min), you'll see the amplify_outputs.json file updated with connection information to a new isolated authentication and data backend.

##### 2.2.6  Local Testing

Try out the GenASl SL translator functionality now by starting the local dev server:

```commandline
npm run dev
```
This should start a local dev server at http://localhost:5173.













## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.