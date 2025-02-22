FROM public.ecr.aws/lambda/python:3.13

COPY pyproject.toml ${LAMBDA_TASK_ROOT}

RUN pip install -e .

COPY main.py ${LAMBDA_TASK_ROOT}

CMD ["main.handler"]
