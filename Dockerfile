FROM container-registry.oracle.com/os/oraclelinux:7.9 as builder

RUN yum clean all \
    && yum -y update \
    && yum install -y python3 \
    && yum clean all \
    && ln -nfs /usr/bin/python3 /usr/bin/python \
    && ln -nfs /usr/bin/pip3 /usr/bin/pip

COPY ./requirements/requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
RUN pip list

COPY ./main.py /main.py
COPY ./contents/index.html /index.html
COPY ./config/config.ini /config.ini
COPY ./config/jsonConfig.json /jsonConfig.json
RUN chmod 755 /main.py

EXPOSE 25
CMD ["python","main.py","logs","sample.log", "config.ini"]
