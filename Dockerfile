FROM python
RUN apt update
RUN pip install tornado sqlalchemy psycopg2
