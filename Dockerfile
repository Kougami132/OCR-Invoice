FROM python:3.11-slim
RUN apt-get update && apt-get install -y libgomp1 libgl1 libglib2.0-0
WORKDIR /usr/src/app
COPY . .
RUN python3 -m pip install --no-cache-dir --upgrade -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
CMD [ "python3", "run.py" ]