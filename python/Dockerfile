From python:3.8
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ecs_anywhere_ip_port.py .
COPY bigip-ecs-ctlr.py .
COPY template.json .
CMD [ "python", "./bigip-ecs-ctlr.py" ]
