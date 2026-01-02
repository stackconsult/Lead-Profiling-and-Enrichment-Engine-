# Lead Profiling and Enrichment Engine

Add leads, let the backend automation engine research, profile and grade them so you understand them better than they understand themselves. Then start connecting and making sales.

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. Clone this repository:
```bash
git clone https://github.com/stackconsult/Lead-Profiling-and-Enrichment-Engine-.git
cd Lead-Profiling-and-Enrichment-Engine-
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Running Locally

Run the Streamlit application:
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 📁 Project Structure

```
Lead-Profiling-and-Enrichment-Engine-/
├── app.py                  # Main Streamlit application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore            # Git ignore rules
├── .streamlit/           # Streamlit configuration
│   ├── config.toml       # App theme and settings
│   └── secrets.toml.example  # Secrets template
└── enyir/                # Enyir project package
    ├── __init__.py       # Package initialization
    ├── src/              # Source code
    ├── utils/            # Utility functions
    └── data/             # Data files
```

## 🔧 Adding Your Enyir Project Code

1. Add your Python modules to the `enyir/src/` directory
2. Add utility functions to the `enyir/utils/` directory
3. Place data files in the `enyir/data/` directory
4. Update `requirements.txt` with any additional dependencies
5. Import and use your code in `app.py`

Example:
```python
# In app.py
from enyir.src import your_module
from enyir.utils import your_utilities

# Use your code in the Streamlit app
result = your_module.process_lead(lead_data)
```

## 🌐 Deploying to Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click "New app"
5. Select this repository
6. Set the main file path to: `app.py`
7. Click "Deploy"

### Environment Variables & Secrets

For Streamlit Cloud deployment:
1. In the Streamlit Cloud dashboard, go to your app settings
2. Click "Secrets" in the left sidebar
3. Add your secrets in TOML format (see `.streamlit/secrets.toml.example`)

## 📦 Dependencies

The project uses:
- **Streamlit**: Web application framework
- **Pandas**: Data manipulation
- **NumPy**: Numerical computing
- **Requests**: HTTP library
- **python-dotenv**: Environment variable management

Add additional dependencies to `requirements.txt` as needed.

## 🛠️ Development

### Running in Development Mode
```bash
streamlit run app.py --server.runOnSave true
```

### Updating Dependencies
```bash
pip install -r requirements.txt --upgrade
```

## 📝 License

See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📞 Support

For questions or issues, please open an issue in the GitHub repository.
