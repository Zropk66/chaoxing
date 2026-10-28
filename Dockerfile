FROM python:3.13-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

RUN mkdir -p /config /app/accounts && \
    cp config_template.ini /config/config.ini

EXPOSE 5000

VOLUME ["/config", "/app/accounts"]

ENTRYPOINT ["python3", "main.py"]
CMD ["-c", "/config/config.ini"]
