FROM python:3.10-slim

# Install system dependencies
RUN apt-get update &amp;&amp; apt-get install -y \
    gcc \
    &amp;&amp; rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    &amp;&amp; pip cache purge

# Copy application code
COPY . .

# Expose port if needed (adjust based on app)
EXPOSE 8080

# Run the application
CMD ["python", "agent_loop.py"]