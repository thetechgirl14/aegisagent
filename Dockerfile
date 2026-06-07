# AegisAgent — Docker image
#
# Builds the Streamlit operator console.
# For Azure Container Apps deployment:
#
#   az containerapp create \
#     --name aegisagent \
#     --resource-group <rg> \
#     --image <acr>.azurecr.io/aegisagent:latest \
#     --env-vars AZURE_OPENAI_ENDPOINT=... AZURE_OPENAI_API_KEY=... \
#     --ingress external --target-port 8501

FROM python:3.11-slim

# Keep image lean
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Streamlit listens on 8501 by default
EXPOSE 8501

# Disable Streamlit's browser auto-open and telemetry in container
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

CMD ["streamlit", "run", "dashboard.py"]
