FROM public.ecr.aws/lambda/python:3.10

WORKDIR /var/task

RUN python -m pip install --no-cache-dir --upgrade pip

COPY backend/requirements.txt /var/task/requirements.txt
RUN pip install --no-cache-dir --only-binary=:all: -r /var/task/requirements.txt
RUN mkdir -p /opt/lib && \
    cp $(ls /var/lang/lib/python3.10/site-packages/scikit_learn.libs/libgomp*.so* 2>/dev/null | head -n 1) /opt/lib/libgomp.so.1 || \
    cp $(ls /var/lang/lib/python3.10/site-packages/scipy.libs/libgomp*.so* 2>/dev/null | head -n 1) /opt/lib/libgomp.so.1

COPY backend/ /var/task/

ENV PYTHONPATH=/var/task

ENTRYPOINT ["bash", "scripts/start_backend.sh"]
