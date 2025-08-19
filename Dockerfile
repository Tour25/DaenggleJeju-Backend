FROM python:3.9

WORKDIR /Backend

COPY . /Backend/

RUN pip install --upgrade pip
COPY requirements.txt /Backend/
RUN pip install -r requirements.txt

EXPOSE 8000
