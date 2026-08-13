FROM public.ecr.aws/lambda/python:3.10

WORKDIR /var/task

COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/

COPY pyproject.toml uv.lock /var/task/
RUN uv sync --frozen --no-dev --no-install-project
RUN mkdir -p /opt/lib && \
    cp $(ls /var/task/.venv/lib/python3.10/site-packages/scikit_learn.libs/libgomp*.so* 2>/dev/null | head -n 1) /opt/lib/libgomp.so.1 || \
    cp $(ls /var/task/.venv/lib/python3.10/site-packages/scipy.libs/libgomp*.so* 2>/dev/null | head -n 1) /opt/lib/libgomp.so.1

COPY backend/ /var/task/

ENV PYTHONPATH=/var/task
ENV PATH="/var/task/.venv/bin:${PATH}"

ENTRYPOINT ["bash", "scripts/start_backend.sh"]
