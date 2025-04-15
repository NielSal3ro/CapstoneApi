FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl gnupg unixodbc-dev gcc g++ && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 10000
CMD ["python", "app.py"]
