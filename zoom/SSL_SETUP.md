# SSL Certificate Setup for Zoom Development

## Overview

Zoom Apps SDK requires HTTPS for security reasons. This guide provides multiple solutions to resolve SSL certificate issues during development.

## Problem: ERR_SSL_VERSION_OR_CIPHER_MISMATCH

This error occurs because browsers don't trust self-signed certificates by default. Here are several solutions:

## Solution 1: Accept Self-Signed Certificate (Quickest)

### Chrome/Edge:
1. Navigate to `https://localhost:3001`
2. Click "Advanced" 
3. Click "Proceed to localhost (unsafe)"
4. The site should load

### Firefox:
1. Navigate to `https://localhost:3001`
2. Click "Advanced"
3. Click "Accept the Risk and Continue"

### Safari:
1. Navigate to `https://localhost:3001`
2. Click "Show Details"
3. Click "visit this website"
4. Click "Visit Website" again

## Solution 2: Use mkcert (Recommended for Development)

### Install mkcert:

**macOS:**
```bash
brew install mkcert
brew install nss # for Firefox support
```

**Windows:**
```bash
# Using Chocolatey
choco install mkcert

# Using Scoop
scoop bucket add extras
scoop install mkcert
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install libnss3-tools
wget -O mkcert https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64
chmod +x mkcert
sudo mv mkcert /usr/local/bin/
```

### Setup Local CA:
```bash
# Create local CA
mkcert -install

# Generate certificates for localhost
cd zoom/
mkcert localhost 127.0.0.1 ::1

# This creates:
# localhost+2.pem (certificate)
# localhost+2-key.pem (private key)
```

### Update Vite Config:
```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import { resolve } from 'path'
import fs from 'fs'

export default defineConfig({
  // ... other config
  server: {
    port: 3001,
    host: true,
    https: {
      key: fs.readFileSync('./localhost+2-key.pem'),
      cert: fs.readFileSync('./localhost+2.pem'),
    },
    cors: true,
  },
})
```

## Solution 3: Use HTTP for Development (Not Recommended)

**Note**: This won't work with actual Zoom SDK, but useful for initial development.

### Update Vite Config:
```typescript
// vite.config.ts - Development only
export default defineConfig({
  server: {
    port: 3001,
    host: true,
    https: false, // Disable HTTPS
  },
})
```

### Access via:
```
http://localhost:3001
```

## Solution 4: Use Ngrok for Public HTTPS

### Install Ngrok:
```bash
# macOS
brew install ngrok

# Windows
choco install ngrok

# Or download from https://ngrok.com/download
```

### Setup:
```bash
# Start your dev server
npm run dev

# In another terminal, expose with HTTPS
ngrok http 3001

# Use the HTTPS URL provided by ngrok
# Example: https://abc123.ngrok.io
```

## Solution 5: Chrome Flags (Development Only)

### Disable SSL Checks in Chrome:
```bash
# macOS/Linux
google-chrome --ignore-certificate-errors --ignore-ssl-errors --allow-running-insecure-content --disable-web-security --user-data-dir=/tmp/chrome_dev

# Windows
chrome.exe --ignore-certificate-errors --ignore-ssl-errors --allow-running-insecure-content --disable-web-security --user-data-dir=c:\temp\chrome_dev
```

**Warning**: Only use this for development. Never browse other sites with these flags.

## Recommended Development Workflow

### For Quick Testing:
1. Use Solution 1 (Accept self-signed certificate)
2. Bookmark the page after accepting

### For Ongoing Development:
1. Use Solution 2 (mkcert) for trusted local certificates
2. Commit the certificate files to your repo (they're safe for localhost)

### For Team Development:
1. Use Solution 4 (ngrok) to share development instances
2. Each developer can use their own ngrok tunnel

### For Production Testing:
1. Deploy to a staging environment with proper SSL
2. Use real domain certificates

## Troubleshooting

### Certificate Still Not Trusted:
```bash
# Clear browser cache and certificates
# Chrome: Settings > Privacy > Clear browsing data > Cached images and files

# Regenerate mkcert certificates
mkcert -uninstall
mkcert -install
mkcert localhost 127.0.0.1 ::1
```

### Port Already in Use:
```bash
# Find process using port 3001
lsof -ti:3001

# Kill the process
kill -9 $(lsof -ti:3001)

# Or use a different port in vite.config.ts
```

### Vite Not Starting with HTTPS:
```bash
# Check if certificates exist
ls -la localhost+2*

# Verify certificate content
openssl x509 -in localhost+2.pem -text -noout
```

## Environment Variables

Create `.env.local` with proper URLs:

```bash
# For mkcert setup
VITE_APP_URL=https://localhost:3001

# For ngrok setup  
VITE_APP_URL=https://your-ngrok-url.ngrok.io

# Zoom configuration
REACT_APP_ZOOM_WEB_ENDPOINT=https://localhost:3001
```

## Security Notes

1. **Never commit real SSL certificates** to version control
2. **mkcert certificates are safe** for localhost development
3. **Self-signed certificates** should only be accepted for development
4. **Production apps** must use proper SSL certificates from a trusted CA

## Next Steps

After resolving SSL issues:

1. Verify the development server starts: `npm run dev`
2. Access `https://localhost:3001` without SSL errors
3. Proceed with Zoom SDK integration
4. Test with actual Zoom meeting integration

Choose the solution that best fits your development environment and security requirements.
