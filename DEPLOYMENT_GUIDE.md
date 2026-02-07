# 🚢 Deployment Guide - Railway

## Prerequisites

1. **GitHub Account** - Code must be in a GitHub repository
2. **Railway Account** - Sign up at [railway.app](https://railway.app)

## Step-by-Step Deployment

### 1. Push Code to GitHub

```bash
cd /Users/xinwan/Github/pvp_amm_challenge

# Initialize git if not already
git init

# Add all files
git add .

# Commit
git commit -m "Initial PVP AMM Challenge"

# Add remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/pvp_amm_challenge.git

# Push to GitHub
git push -u origin main
```

### 2. Deploy to Railway

#### Option A: Using Railway CLI (Recommended)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Link to new project
railway init

# Deploy
railway up

# Get URL
railway domain
```

#### Option B: Using Railway Web UI

1. **Go to Railway**
   - Visit [railway.app](https://railway.app)
   - Click "Start a New Project"

2. **Connect GitHub**
   - Select "Deploy from GitHub repo"
   - Authorize Railway to access your GitHub
   - Select `pvp_amm_challenge` repository

3. **Configure Project**
   - Railway auto-detects `Dockerfile`
   - Railway auto-detects `railway.toml`
   - No additional config needed!

4. **Deploy**
   - Click "Deploy"
   - Wait for build (15-20 minutes first time due to Rust compilation)
   - Railway provides public URL when done

### 3. Add Persistent Storage (Optional but Recommended)

By default, Railway containers are ephemeral - database resets on each deploy.

#### Add a Volume:

1. **In Railway Dashboard**
   - Go to your project
   - Click "New" → "Volume"
   - Name: `pvp-data`
   - Mount path: `/app/data`
   - Size: 1GB (free tier)

2. **Redeploy**
   - Railway will restart with persistent storage
   - Database will persist across deployments

### 4. Configure Environment Variables (Optional)

Railway auto-sets `PORT`, but you can add custom variables:

```bash
# Via CLI
railway variables set DATABASE_PATH=/app/data/strategies.db

# Via Web UI
Settings → Variables → Add Variable
```

Useful variables:
- `DATABASE_PATH` - Custom database location
- `LOG_LEVEL` - `debug` or `info`
- `MAX_SIMULATIONS` - Limit simulations per match

### 5. Setup Custom Domain (Optional)

1. **Generate Railway Domain**
   - Settings → Domains → Generate Domain
   - Get URL like: `pvp-amm-challenge.railway.app`

2. **Add Custom Domain** (requires paid plan)
   - Settings → Domains → Custom Domain
   - Add your domain: `ammchallenge.yourdomain.com`
   - Update DNS:
     ```
     CNAME ammchallenge yourdomain.railway.app
     ```

### 6. Monitor Deployment

```bash
# View logs
railway logs

# Check status
railway status

# View metrics
# Go to Railway dashboard → Metrics
```

## Post-Deployment Setup

### 1. Seed Database with Sample Strategies

Option A: Run seed script via Railway shell
```bash
railway shell
python pvp_app/seed_data.py
exit
```

Option B: Deploy pre-seeded database
```bash
# Locally
python pvp_app/seed_data.py

# Upload to Railway volume
railway volume mount pvp-data
# Copy data/strategies.db to mounted directory
```

### 2. Test the Deployment

1. Visit your Railway URL
2. Sign in (temporary username for now)
3. Submit a test strategy
4. Create a match
5. View results

### 3. Share the URL

Your app is now live! Share:
- `https://your-project.railway.app`

## Troubleshooting

### Build Fails - Rust Compilation Error

**Symptom**: Build fails with "cargo not found" or Rust errors

**Solution**:
```dockerfile
# Already handled in Dockerfile
# Verify Rust installation step is present:
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
```

### App Crashes - Out of Memory

**Symptom**: App crashes with OOM error

**Solution**:
- Upgrade Railway plan (free tier: 512MB RAM)
- Or reduce `MAX_SIMULATIONS` in match config

### Database Resets on Deploy

**Symptom**: Strategies disappear after redeployment

**Solution**:
- Add Railway Volume (see Step 3 above)
- Mount at `/app/data`

### Port Binding Error

**Symptom**: App fails to start, "port already in use"

**Solution**:
```bash
# Railway auto-sets PORT variable
# Verify start command uses $PORT:
streamlit run pvp_app/app.py --server.port=$PORT
```

Already configured in `railway.toml` ✓

### Slow First Load

**Symptom**: App takes 30+ seconds to load first time

**Solution**:
- Normal! Streamlit initializes on first request
- Railway auto-sleeps after 30min inactivity (free tier)
- Upgrade to Pro for always-on

## Cost Estimate

### Railway Pricing

**Free Tier:**
- $5 free credits/month
- 512MB RAM
- Shared CPU
- Sleeps after 30min inactivity
- Good for: Testing, demos

**Hobby Plan ($5/month):**
- $5 + $0.000231/GB-hour RAM
- $0.000463/vCPU-hour
- No sleep
- Good for: Personal projects

**Estimated costs for PVP AMM:**
- RAM (1GB): ~$17/month
- CPU (0.5 vCPU): ~$17/month
- Network: ~$1/month
- **Total: ~$35-40/month**

### Cost Optimization

1. **Use free tier** for MVP testing
2. **Optimize match execution**:
   - Limit concurrent matches
   - Cache compiled bytecode
3. **Scale on demand**:
   - Scale down during low traffic
   - Railway auto-scales

## Advanced Configuration

### Enable Twitter OAuth (Future)

1. **Create Twitter App**
   - [developer.twitter.com](https://developer.twitter.com)
   - Get API keys and callback URL

2. **Add to Railway**
   ```bash
   railway variables set TWITTER_CLIENT_ID=your_id
   railway variables set TWITTER_CLIENT_SECRET=your_secret
   railway variables set TWITTER_CALLBACK_URL=https://your-app.railway.app/callback
   ```

3. **Update app.py**
   - Implement OAuth flow
   - Replace temporary username auth

### Add Redis Cache (Optional)

1. **Add Redis to Railway**
   - New → Database → Redis

2. **Update app**
   ```python
   import redis
   cache = redis.from_url(os.environ['REDIS_URL'])
   ```

### Setup CI/CD

Railway auto-deploys on push to main. To customize:

```bash
# .github/workflows/railway.yml
name: Deploy to Railway
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm i -g @railway/cli
      - run: railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## Monitoring & Maintenance

### Check Health

```bash
# Health endpoint
curl https://your-app.railway.app/_stcore/health
```

### View Logs

```bash
railway logs --follow
```

### Database Backups

```bash
# Download database
railway volume download pvp-data data/backup.db

# Upload database
railway volume upload pvp-data data/strategies.db
```

### Update Deployment

```bash
# Make changes
git add .
git commit -m "Update feature"
git push origin main

# Railway auto-deploys!
```

## Security Checklist

- [ ] Enable HTTPS (Railway provides SSL by default)
- [ ] Add rate limiting (for future)
- [ ] Sanitize strategy code input
- [ ] Validate all user inputs
- [ ] Setup database backups
- [ ] Monitor logs for errors
- [ ] Add Twitter OAuth (replace temp auth)

## Support

- Railway Docs: [docs.railway.app](https://docs.railway.app)
- Railway Discord: [Community](https://discord.gg/railway)
- Railway Status: [status.railway.app](https://status.railway.app)

---

🎉 Your PVP AMM Challenge is now live!
