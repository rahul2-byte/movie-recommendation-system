FROM public.ecr.aws/lambda/python:3.10

WORKDIR /var/task

RUN python -m pip install --no-cache-dir --upgrade pip

COPY backend/requirements.txt /var/task/requirements.txt
RUN pip install --no-cache-dir -r /var/task/requirements.txt

COPY backend/ /var/task/

ENV PYTHONPATH=/var/task

ENTRYPOINT ["bash", "scripts/start_backend.sh"]
