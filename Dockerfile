FROM python:3.11-slim
WORKDIR /usr/src/app
COPY . .
RUN pip install --no-cache-dir --upgrade -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
CMD [ "python3", "run.py" ]