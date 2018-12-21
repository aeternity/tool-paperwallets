FROM python:3-alpine

# RUN apt-get update && \
#   apt-get install build-deps gcc python-dev musl-dev && \
#   apk add postgresql-dev

RUN apk --no-cache add pdftk ghostscript py3-reportlab py3-pillow jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev build-base
RUN apk --update add libxml2-dev libxslt-dev libffi-dev musl-dev libgcc openssl-dev curl

COPY republica.py /data/republica.py
COPY requirements.txt /data/requirements.txt

COPY assets /data/assets

RUN pip install -r /data/requirements.txt
RUN mkdir /paperw

ENTRYPOINT [ "python", "/data/republica.py"]

