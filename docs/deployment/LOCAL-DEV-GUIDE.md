# Axiom PWA — Local Development Guide
## Testing on Android & iPhone with a Local Backend

---

## The Setup

```
Your Phone (WiFi)
      │
      │  https://192.168.x.x:3000
      ▼
Your Computer
  ├── Next.js :3000  (HTTPS via mkcert)
  │       │ proxies /api/*
  │       ▼
  └── FastAPI :8000  (HTTP, localhost only)
```

Your phone talks to Next.js over HTTPS on your local network.  
Next.js proxies API calls to FastAPI — so FastAPI never needs to be exposed or have HTTPS.

---

## One-Time Setup

### 1. Install mkcert (generates trusted local SSL certs)

**Mac:**
```bash
brew install mkcert
mkcert -install
```

**Windows (run as Administrator):**
```powershell
choco install mkcert
# or: scoop install mkcert
mkcert -install
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install libnss3-tools
# Install mkcert binary from https://github.com/FiloSottile/mkcert/releases
mkcert -install
```

### 2. Generate SSL certificates for your local network

```bash
cd web
npm run dev:setup-https
```

This will:
- Detect your local IP address (e.g. `192.168.1.42`)
- Generate trusted SSL certs for `localhost` + your IP
- Save them to `web/.certs/`

Example output:
```
📱 Your local IP: 192.168.1.42
   Mobile devices will access: https://192.168.1.42:3000

Created a new certificate valid for the following names 📜
 - "localhost"
 - "127.0.0.1"  
 - "192.168.1.42"

✅ Certificates generated!
```

### 3. Install dependencies

```bash
cd web
npm install
```

---

## Daily Development Workflow

### Terminal 1 — FastAPI backend
```bash
# From project root
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> `--host 0.0.0.0` makes FastAPI accessible on your local network.  
> It's still only reachable from devices on the same WiFi.

### Terminal 2 — Next.js frontend (HTTPS)
```bash
cd web
npm run dev:https
```

Output:
```
🚀 Starting Axiom dev server with HTTPS...

   Local:   https://localhost:3000
   Mobile:  https://192.168.1.42:3000

   ⚠️  Make sure your phone is on the same WiFi network
   ⚠️  FastAPI backend must be running
```

### On your phone

1. Connect to the **same WiFi** as your computer
2. Open the URL shown (e.g. `https://192.168.1.42:3000`) in:
   - **iPhone**: Safari
   - **Android**: Chrome
3. You'll see a security warning the first time — tap "Advanced" → "Proceed"  
   *(This is expected with local certs — it's safe)*

---

## Install as App

### Android
1. Open `https://192.168.x.x:3000` in Chrome
2. Tap the menu (⋮) → **"Add to Home screen"**
   or wait for the automatic install banner at the bottom
3. The app opens full-screen like a native app

### iPhone
1. Open `https://192.168.x.x:3000` in **Safari**
2. Tap the **Share button** (↑) at the bottom of the screen
3. Scroll down → tap **"Add to Home Screen"**
4. Tap **"Add"** — app icon appears on home screen

---

## CORS Configuration

Since your phone accesses the app from a different IP, update your FastAPI CORS settings.

Open `app/main.py` and update the CORS middleware (see `app/main-cors-patch.py` for the full snippet):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # Allow all in dev
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> The Next.js proxy handles most requests so CORS rarely triggers —  
> but this ensures direct browser requests also work.

---

## Environment Variables

Copy the example env file:
```bash
cp web/.env.local.example web/.env.local
```

The default `.env.local` points to `http://localhost:8000` which works  
because Next.js proxies API calls server-side (not from the phone directly).

---

## Deploying the Backend (Optional)

When you're ready to make the app accessible without being on your home WiFi:

### Option A: Railway (easiest, free tier available)
```bash
# Install Railway CLI
npm install -g @railway/cli

# From project root
railway login
railway init
railway up
```

### Option B: Render
1. Push your repo to GitHub
2. Go to render.com → New → Web Service
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Option C: Docker + any VPS
```bash
# Your repo already has a Dockerfile
docker build -t axiom-api .
docker run -p 8000:8000 axiom-api
```

After deploying, update `web/.env.local`:
```
NEXT_PUBLIC_API_URL=https://your-api.railway.app
```

And for the frontend, deploy to Vercel:
```bash
cd web
npx vercel
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Phone can't reach the server | Check both devices are on the same WiFi |
| "NET::ERR_CERT_AUTHORITY_INVALID" | Tap "Advanced" → "Proceed" (expected with local certs) |
| Safari shows "This connection is not private" | Same — tap "Show Details" → "visit this website" |
| Service worker not registering | Requires HTTPS — use `npm run dev:https`, not `npm run dev` |
| Install banner not appearing | Try Chrome on Android; Safari on iPhone (Chrome iOS can't install PWAs) |
| API calls failing (401/CORS) | Check FastAPI is running with `--host 0.0.0.0` and CORS allows `*` |
| `.certs/` folder missing | Run `npm run dev:setup-https` again |
| mkcert not found | Install it first — see setup instructions above |
