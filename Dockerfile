FROM python:3.11-slim

# Install system dependencies including Microsoft ODBC Driver 18
RUN apt-get update && apt-get install -y \
    curl gnupg unixodbc-dev gcc g++ && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18

# Set the working directory
WORKDIR /app

# Copy all files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the app's port
EXPOSE 10000

# Run the Flask app
CMD ["python", "app.py"]
