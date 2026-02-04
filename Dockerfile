# Use the official AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.10

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 
    PYTHONUNBUFFERED=1 
    PYTHONPATH="/var/task" 
    ENVIRONMENT="PROD"

# Install system dependencies (including those for LightGBM and FAISS if needed)
RUN yum install -y libgomp && yum clean all

# Copy only the serving-related files
COPY backend/main.py ${LAMBDA_TASK_ROOT}/
COPY backend/api/ ${LAMBDA_TASK_ROOT}/api/
COPY backend/common/ ${LAMBDA_TASK_ROOT}/common/
COPY backend/configs/ ${LAMBDA_TASK_ROOT}/configs/
COPY backend/features/ ${LAMBDA_TASK_ROOT}/features/
COPY backend/pipeline/ ${LAMBDA_TASK_ROOT}/pipeline/
COPY backend/ranking/ ${LAMBDA_TASK_ROOT}/ranking/
COPY backend/retrieval/ ${LAMBDA_TASK_ROOT}/retrieval/
COPY backend/data/loader.py ${LAMBDA_TASK_ROOT}/data/loader.py

# Note: We EXCLUDE backend/training, backend/scripts, and backend/data/* (except loader)
# We also EXCLUDE all native C++ source files.

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt mangum

# Final Cleanup: Remove training logic that might have been caught in subdirectories
RUN rm -rf ${LAMBDA_TASK_ROOT}/ranking/native 
    && rm -rf ${LAMBDA_TASK_ROOT}/retrieval/native 
    && rm -rf ${LAMBDA_TASK_ROOT}/features/native

# Set the handler to the Mangum wrapper in main.py
CMD ["main.handler"]
