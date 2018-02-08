FROM python:3
WORKDIR /usr/src/app
RUN pip install --no-cache-dir requests
COPY github-issues-mover.py github-issues-mover.py
CMD [ "python", "./github-issues-mover.py" ]