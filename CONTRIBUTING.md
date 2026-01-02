# Contributing to Lead Profiling and Enrichment Engine

Thank you for your interest in contributing!

## How to Add Your Enyir Project Code

### Step 1: Add Your Python Files

Place your existing enyir project files in the appropriate directories:

```bash
# Add main application modules
cp -r /path/to/your/enyir/modules/* enyir/src/

# Add utility functions
cp -r /path/to/your/enyir/utils/* enyir/utils/

# Add data files
cp -r /path/to/your/enyir/data/* enyir/data/
```

### Step 2: Update Dependencies

If your enyir project has additional dependencies, add them to `requirements.txt`:

```bash
echo "your-package>=1.0.0" >> requirements.txt
```

### Step 3: Integrate with Streamlit

Edit `app.py` to import and use your enyir code:

```python
# Import your modules
from enyir.src.your_module import YourClass
from enyir.utils.helpers import helper_function

# Use in your Streamlit app
def main():
    st.title("Lead Profiling Engine")
    
    # Your enyir code integration here
    result = YourClass().process()
    st.write(result)
```

### Step 4: Test Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### Step 5: Commit and Push

```bash
git add .
git commit -m "Add enyir project integration"
git push origin main
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and small

## Questions?

Open an issue if you need help!
