FROM public.ecr.aws/lambda/python:3.10

# Install system dependencies for FAISS and LightGBM
RUN yum install -y 
    libgomp 
    mesa-libGL 
    && yum clean all

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
# We copy from the backend root to the Lambda task root
COPY . ${LAMBDA_TASK_ROOT}

# Set the CMD to your mangum handler
CMD [ "main.handler" ]
