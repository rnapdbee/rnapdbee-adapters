FROM ubuntu:20.04 AS bpnet-adapter

RUN apt-get update -y \
 && apt-get install -y \
        curl \
        python3 \
        python3-pip \
 && rm -rf /var/lib/apt/lists/*

RUN pip3 install orjson

RUN curl -L https://github.com/computational-biology/bpnet/archive/refs/heads/master.tar.gz | tar xz

COPY src/adapters/__init__.py /rnapdbee-adapters/src/adapters/__init__.py
COPY src/adapters/model.py /rnapdbee-adapters/src/adapters/model.py
COPY src/adapters/bpnet.py /rnapdbee-adapters/src/adapters/bpnet.py
COPY src/adapters/utils.py /rnapdbee-adapters/src/adapters/utils.py

ENV NUCLEIC_ACID_DIR=/bpnet-master/sysfiles \
    PATH=${PATH}:/bpnet-master/bin \
    PYTHONPATH=${PYTHONPATH}:/rnapdbee-adapters/src

CMD ["python3", "/rnapdbee-adapters/src/adapters/bpnet.py"]

################################################################################

FROM bpnet-adapter AS fr3d-adapter

RUN apt-get update -y \
 && apt-get install -y \
        git \
 && rm -rf /var/lib/apt/lists/*

RUN pip3 install git+https://github.com/tzok/fr3d-python

COPY src/adapters/fr3d_.py /rnapdbee-adapters/src/adapters/fr3d_.py

CMD ["python3", "/rnapdbee-adapters/src/adapters/fr3d_.py"]

################################################################################

FROM fr3d-adapter AS barnaba-adapter

RUN apt-get update -y \
 && apt-get install -y \
        git \
 && rm -rf /var/lib/apt/lists/*

RUN pip3 install barnaba

COPY src/adapters/barnaba_.py /rnapdbee-adapters/src/adapters/barnaba_.py

CMD ["python3", "/rnapdbee-adapters/src/adapters/barnaba_.py"]

################################################################################

FROM barnaba-adapter AS maxit

RUN apt-get update -y \
 && apt-get install -y \
        bison \
        build-essential \
        ca-certificates \
        flex \
        tcsh \
 && rm -rf /var/lib/apt/lists/*

ARG maxit_version=11.100

RUN curl -L https://sw-tools.rcsb.org/apps/MAXIT/maxit-v${maxit_version}-prod-src.tar.gz | tar xz

ENV RCSBROOT=/maxit-v${maxit_version}-prod-src \
    PATH=${PATH}:/maxit-v${maxit_version}-prod-src/bin

RUN cd ${RCSBROOT} \
 && make \
 && make binary

COPY src/adapters/maxit.py /rnapdbee-adapters/src/adapters/maxit.py

CMD ["python3", "/rnapdbee-adapters/src/adapters/maxit.py"]

################################################################################

FROM maxit AS server

RUN apt-get update -y \
 && apt-get install -y \
        gunicorn \
 && rm -rf /var/lib/apt/lists/*

RUN pip3 install flask

COPY src/adapters/server.py /rnapdbee-adapters/src/adapters/server.py

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "adapters.server:app"]
