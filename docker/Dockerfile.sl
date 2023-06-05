FROM python:3.10-slim

WORKDIR /mutiny

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY util/ util/
COPY backend/ backend/
COPY mutiny.py .
COPY mutiny_classes/ mutiny_classes/
COPY tcp.pcap .

RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    git \
    wget \
    curl

COPY radamsa-v0.6.tar.gz radamsa-v0.6.tar.gz

RUN tar -xzf radamsa-v0.6.tar.gz &&\
    cd radamsa-0.6 && \
    make

CMD ["/bin/bash"]