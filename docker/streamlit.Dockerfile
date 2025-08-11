# docker/streamlit.Dockerfile
FROM python:3.11-slim
WORKDIR /client
COPY ./client ./client
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "client/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
