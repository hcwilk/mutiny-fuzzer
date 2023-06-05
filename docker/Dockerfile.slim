FROM python:3.10-slim as slimbase

WORKDIR /mutiny

ADD radamsa-v0.6.tar.gz .
RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    git \
    wget \
    curl
RUN (cd radamsa-0.6 && make)

FROM python:3.10-slim

WORKDIR /mutiny

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY util/ util/
COPY backend/ backend/
COPY mutiny.py .
COPY mutiny_classes/ mutiny_classes/

COPY --from=slimbase /mutiny/radamsa-0.6 ./radamsa-0.6/


CMD ["/bin/bash"]
