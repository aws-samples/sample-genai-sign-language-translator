import { defineStorage } from '@aws-amplify/backend';


export const genSLUserDataBucket = defineStorage({
  name: 'genasl-data-' + process.env.AMPLIFY_ENV,
  isDefault: true, // identify your default storage bucket (required)
    access: (allow) => ({
    "public/*": [
      allow.guest.to(['read','write']),
      allow.authenticated.to(['read', 'write', 'delete'])
    ]
  }),
});
