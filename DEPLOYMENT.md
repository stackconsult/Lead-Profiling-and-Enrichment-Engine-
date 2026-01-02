# Streamlit Deployment Guide

This guide will help you deploy the Lead Profiling and Enrichment Engine to Streamlit Cloud.

## Prerequisites

1. A GitHub account
2. Your code pushed to this GitHub repository
3. A Streamlit Cloud account (free tier available)

## Step-by-Step Deployment

### 1. Prepare Your Code

Ensure all your enyir project code is added to the repository:

```bash
# Add your code files
cp -r /path/to/your/enyir/code/* enyir/src/
cp -r /path/to/your/enyir/utils/* enyir/utils/
cp -r /path/to/your/enyir/data/* enyir/data/

# Update requirements if needed
echo "your-package>=1.0.0" >> requirements.txt

# Test locally first
pip install -r requirements.txt
streamlit run app.py
```

### 2. Push to GitHub

```bash
git add .
git commit -m "Add enyir project code"
git push origin main
```

### 3. Deploy to Streamlit Cloud

1. **Go to Streamlit Cloud**
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

2. **Create New App**
   - Click "New app" button
   - Select your GitHub repository: `stackconsult/Lead-Profiling-and-Enrichment-Engine-`
   - Branch: `main` (or your deployment branch)
   - Main file path: `app.py`

3. **Configure Advanced Settings** (if needed)
   - Python version: 3.11 (recommended)
   - Click "Advanced settings"
   - Add any secrets or environment variables

4. **Deploy**
   - Click "Deploy"
   - Wait for deployment to complete (usually 2-5 minutes)
   - Your app will be live at: `https://your-app-name.streamlit.app`

### 4. Configure Secrets (if needed)

If your app uses API keys or sensitive data:

1. In Streamlit Cloud dashboard, select your app
2. Click on "Settings" (⚙️)
3. Go to "Secrets" section
4. Add your secrets in TOML format:

```toml
# Example secrets
api_key = "your-secret-api-key"
database_url = "your-database-connection-string"

[database]
host = "localhost"
port = 5432
```

Access secrets in your code:

```python
import streamlit as st

api_key = st.secrets["api_key"]
db_host = st.secrets["database"]["host"]
```

## File Structure for Deployment

Required files:
- ✅ `app.py` - Main Streamlit application
- ✅ `requirements.txt` - Python dependencies
- ⚠️ `packages.txt` - System dependencies (if needed)
- ⚠️ `.streamlit/config.toml` - App configuration (optional)

## Troubleshooting

### App won't start

1. Check the logs in Streamlit Cloud dashboard
2. Verify all dependencies are in `requirements.txt`
3. Test locally: `streamlit run app.py`

### Import errors

```python
# Make sure your imports are correct
from enyir.src import your_module  # ✅ Correct
from enyir import your_module      # ❌ Wrong if module is in src/
```

### Missing system packages

Add required system packages to `packages.txt`:

```
libgl1-mesa-glx
libglib2.0-0
```

### Environment variables not working

Use Streamlit secrets instead:
1. Add to Streamlit Cloud > Settings > Secrets
2. Access via `st.secrets["key_name"]`

## Updating Your Deployment

To update your deployed app:

```bash
# Make changes to your code
git add .
git commit -m "Update feature X"
git push origin main
```

Streamlit Cloud will automatically redeploy your app when you push to GitHub!

## Custom Domain (Optional)

To use a custom domain:
1. Upgrade to Streamlit Cloud paid plan
2. Follow [Streamlit's custom domain guide](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app/custom-domains)

## Monitoring

- View app usage in Streamlit Cloud dashboard
- Check logs for errors
- Monitor resource usage

## Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit Forum](https://discuss.streamlit.io/)

## Need Help?

- Check the [Streamlit Forum](https://discuss.streamlit.io/)
- Open an issue in this repository
- Consult the [Streamlit Documentation](https://docs.streamlit.io/)
