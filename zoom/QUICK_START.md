# GenASL Zoom Integration - Quick Start Guide

## Overview

This guide will help you quickly set up and start developing the GenASL Zoom integration. Follow these steps to get your development environment ready and begin building the sign language translation features for Zoom meetings.

## Prerequisites

Before you begin, ensure you have the following:

- **Node.js** (v18 or higher)
- **npm** (v8 or higher)
- **Git** for version control
- **Zoom Developer Account** (free at [marketplace.zoom.us](https://marketplace.zoom.us))
- **AWS Account** (for GenASL backend services)
- **Code Editor** (VS Code recommended)

## Step 1: Environment Setup

### 1.1 Clone and Navigate to Project
```bash
cd zoom/
```

### 1.2 Install Dependencies
```bash
npm install
```

**Note**: If you encounter any package installation errors, try:
```bash
npm install --legacy-peer-deps
```

### 1.3 Create Environment Configuration
Create a `.env.local` file in the zoom directory:

```bash
# Zoom Configuration
REACT_APP_ZOOM_API_KEY=stygQZB9RY6NhaKoziB77w
REACT_APP_ZOOM_API_SECRET=HIRxcxQtIeWjTYUEN2DXmpKpzuqne88N
REACT_APP_ZOOM_WEB_ENDPOINT=https://localhost:3001

# GenASL API Configuration
REACT_APP_GENASL_API_URL=https://your-genasl-api-endpoint.com
REACT_APP_GENASL_API_KEY=your_genasl_api_key_here
REACT_APP_GENASL_WSS_URL=wss://your-websocket-endpoint.com

# Development Configuration
REACT_APP_ENV=development
REACT_APP_DEBUG=true
```

## Step 2: Zoom Developer Account Setup

### 2.1 Create Zoom App - In progress
1. Go to [Zoom App Marketplace](https://marketplace.zoom.us/)
2. Sign in or create a developer account
3. Click **Develop** → **Build App**
4. Select **General App** and click **Create**

### 2.2 Configure OAuth App
1. **App Name**: GenASL - Sign Language Translator
2. **App Type**: User-managed
3. **OAuth Redirect URL**: `https://localhost:3001/auth/callback`
4. **OAuth Allow Lists**: `https://localhost:3001`

### 2.3 Required Scopes
Add the following scopes to your app:
- `meeting:read` - Access meeting information
- `meeting:write` - Control meeting features
- `user:read` - Access user profile information
- `recording:read` - Access meeting recordings (optional)

### 2.4 Get Credentials
1. Copy your **API Key** and **API Secret**
2. Update your `.env.local` file with these credentials

## Step 3: Development Server

### 3.1 Start Development Server
```bash
npm run dev
```

The app will be available at `http://localhost:3001`

### 3.2 Development Setup
**Current Configuration:**
- Using HTTP for initial development and testing
- No SSL certificate issues to worry about
- Ready for immediate development

**For Production Zoom SDK Integration:**
When you're ready to integrate with the actual Zoom SDK (which requires HTTPS), see `SSL_SETUP.md` for:
- Setting up trusted local certificates with mkcert
- Using ngrok for public HTTPS tunnels
- Configuring proper SSL for Zoom Apps SDK

**Access Your App:**
Simply navigate to `http://localhost:3001` in your browser - no certificate warnings!

## Step 4: Project Structure Overview

```
zoom/
├── src/
│   ├── components/          # React components
│   │   ├── ZoomApp.tsx     # Main application component
│   │   ├── MeetingControls/ # Meeting control UI (to be implemented)
│   │   ├── ASLTranslator/   # Translation logic (to be implemented)
│   │   ├── AvatarDisplay/   # Avatar rendering (to be implemented)
│   │   └── SettingsPanel/   # Settings UI (to be implemented)
│   ├── hooks/              # Custom React hooks (to be implemented)
│   ├── services/           # API and SDK services
│   │   ├── zoomSDK.ts     # Zoom SDK wrapper
│   │   └── genASLAPI.ts   # GenASL API client
│   ├── types/             # TypeScript definitions
│   │   └── zoom.ts        # Type definitions
│   └── utils/             # Utility functions (to be implemented)
├── public/                # Static assets
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
├── vite.config.ts        # Vite build configuration
└── README.md             # Project documentation
```

## Step 5: Next Development Steps

### 5.1 Immediate Tasks (This Week)
1. **Implement Missing Components**
   ```bash
   # Create component directories
   mkdir -p src/components/{MeetingControls,ASLTranslator,AvatarDisplay,SettingsPanel}
   mkdir -p src/hooks
   mkdir -p src/utils
   ```

2. **Create Custom Hooks**
   - `useZoomMeeting.ts` - Zoom SDK integration
   - `useASLTranslation.ts` - GenASL API integration
   - `useWebSocket.ts` - Real-time communication

3. **Implement Core Components**
   - MeetingControls - UI for controlling ASL features
   - ASLTranslator - Core translation logic
   - AvatarDisplay - ASL avatar rendering
   - SettingsPanel - User preferences

### 5.2 Testing Your Setup
1. **Check TypeScript Compilation**
   ```bash
   npm run type-check
   ```

2. **Run Linting**
   ```bash
   npm run lint
   ```

3. **Build for Production**
   ```bash
   npm run build
   ```

## Step 6: Integration with Existing GenASL Backend

### 6.1 Connect to AWS Services
The GenASL backend is already deployed using AWS Amplify. To integrate:

1. **Copy Configuration**
   ```bash
   # Copy amplify_outputs.json from main project
   cp ../amplify_outputs.json ./src/config/
   ```

2. **Update API Endpoints**
   Update your `.env.local` with the correct API endpoints from the main GenASL project.

### 6.2 Test Backend Connection
Create a simple test to verify backend connectivity:

```typescript
// src/utils/testConnection.ts
import { getGenASLAPI } from '@/services/genASLAPI';

export const testBackendConnection = async () => {
  try {
    const api = getGenASLAPI();
    const isHealthy = await api.healthCheck();
    console.log('Backend connection:', isHealthy ? 'Success' : 'Failed');
    return isHealthy;
  } catch (error) {
    console.error('Backend connection failed:', error);
    return false;
  }
};
```

## Step 7: Development Workflow

### 7.1 Daily Development
1. **Start Development Server**
   ```bash
   npm run dev
   ```

2. **Run Tests in Watch Mode**
   ```bash
   npm run test:watch
   ```

3. **Check Code Quality**
   ```bash
   npm run lint
   npm run type-check
   ```

### 7.2 Git Workflow
```bash
# Create feature branch
git checkout -b feature/meeting-controls

# Make changes and commit
git add .
git commit -m "feat: implement meeting controls component"

# Push and create PR
git push origin feature/meeting-controls
```

## Step 8: Testing with Zoom

### 8.1 Create Test Meeting
1. Schedule a Zoom meeting
2. Get meeting number and password
3. Generate JWT signature (server-side recommended)

### 8.2 Test Integration
```typescript
// Example test meeting join
const testMeetingConfig = {
  apiKey: process.env.REACT_APP_ZOOM_API_KEY!,
  meetingNumber: '123456789',
  passWord: 'test123',
  userName: 'Test User',
  signature: 'generated_jwt_signature',
  role: 0 // 0 for attendee, 1 for host
};
```

## Troubleshooting

### Common Issues

1. **HTTPS Certificate Errors**
   - Solution: Accept the self-signed certificate in your browser
   - Alternative: Use mkcert for trusted local certificates

2. **Zoom SDK Loading Issues**
   - Check that you're using HTTPS
   - Verify API key and signature are correct
   - Ensure meeting number and password are valid

3. **TypeScript Errors**
   - Run `npm run type-check` to see all errors
   - Check that all imports have correct paths
   - Verify that all required dependencies are installed

4. **Build Errors**
   - Clear node_modules and reinstall: `rm -rf node_modules && npm install`
   - Check for conflicting dependencies
   - Verify all environment variables are set

### Getting Help

1. **Documentation**
   - [Zoom Web SDK Documentation](https://developers.zoom.us/docs/meeting-sdk/web/)
   - [React TypeScript Documentation](https://react-typescript-cheatsheet.netlify.app/)

2. **Support Channels**
   - Zoom Developer Forum
   - GitHub Issues (for this project)
   - Team Slack/Discord channels

## Next Steps

After completing this quick start:

1. **Review the Implementation Plan** (`IMPLEMENTATION_PLAN.md`)
2. **Study the existing GenASL components** in the main project
3. **Implement the missing React hooks** (Week 1 priority)
4. **Create the core UI components** (Week 2 priority)
5. **Test basic Zoom SDK integration** (Week 3 priority)

## Resources

- [Zoom Developer Documentation](https://developers.zoom.us/docs/)
- [GenASL Main Project](../README.md)
- [React Hooks Documentation](https://reactjs.org/docs/hooks-intro.html)
- [Material-UI Documentation](https://mui.com/getting-started/installation/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

**Happy Coding!** 🚀

If you encounter any issues or have questions, please refer to the implementation plan or reach out to the development team.
