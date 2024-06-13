FROM public.ecr.aws/lambda/python:3.12

COPY pyproject.toml ${LAMBDA_TASK_ROOT}

RUN pip install -e .

COPY . ${LAMBDA_TASK_ROOT}

CMD ["main.handler"]
