FROM python:3.7-slim

# RUN apt-get update && \
#   apt-get install build-deps gcc python-dev musl-dev && \
#   apk add postgresql-dev

# because of https://github.com/debuerreotype/docker-debian-artifacts/issues/24
RUN mkdir -p /usr/share/man/man1

RUN apt update && apt install -y \
      pdftk \
      ghostscript \
      python3-reportlab \
      python3-pillow \
      libjpeg-dev \
      zlib1g-dev \
      libfreetype6-dev \
      liblcms2-dev \
      #libopenjpeg-dev \
      libtiff-dev \
      tk-dev \
      tcl-dev \
      build-essential
RUN apt update && apt install -y \
      libxml2-dev \
      libxslt-dev \
      libffi-dev \
      musl-dev \
      libgcc-7-dev \
      libssl-dev \
      curl

COPY republica.py /data/republica.py
COPY requirements.txt /data/requirements.txt

COPY assets /data/assets

RUN pip install -r /data/requirements.txt
RUN mkdir /paperw

ENTRYPOINT [ "python", "/data/republica.py"]

