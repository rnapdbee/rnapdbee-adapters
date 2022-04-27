FROM ubuntu:20.04 AS bpnet-builder

RUN apt-get update -y \
 && apt-get install -y \
        curl \
 && rm -rf /var/lib/apt/lists/*

RUN curl -L https://github.com/computational-biology/bpnet/archive/refs/heads/master.tar.gz | tar xz

################################################################################

FROM ubuntu:20.04 AS fr3d-builder

RUN apt-get update -y \
 && apt-get install -y \
        git \
 && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/tzok/fr3d-python

################################################################################

FROM ubuntu:20.04 AS maxit-builder

RUN apt-get update -y \
 && apt-get install -y \
        bison \
        build-essential \
        ca-certificates \
        curl \
        flex \
        tcsh \
 && rm -rf /var/lib/apt/lists/*

ARG maxit_version=11.100

RUN curl -L https://sw-tools.rcsb.org/apps/MAXIT/maxit-v${maxit_version}-prod-src.tar.gz | tar xz

ENV RCSBROOT=/maxit-v${maxit_version}-prod-src

RUN cd ${RCSBROOT} \
 && make \
 && make binary

################################################################################

FROM ubuntu:20.04 AS barnaba-builder

RUN apt-get update -y \
 && apt-get install -y \
        git \
 && rm -rf /var/lib/apt/lists/*

################################################################################

FROM ubuntu:20.04 AS server

RUN apt-get update -y \
 && apt-get install -y \
        gunicorn \
        python3 \
        python3-pip \
 && rm -rf /var/lib/apt/lists/*

RUN pip3 install flask mmcif orjson

COPY --from=fr3d-builder /fr3d-python /fr3d-python

RUN pip install /fr3d-python

COPY --from=bpnet-builder /bpnet-master /bpnet-master

RUN pip3 install barnaba

ARG maxit_version=11.100
COPY --from=maxit-builder /maxit-v${maxit_version}-prod-src /maxit

ENV NUCLEIC_ACID_DIR=/bpnet-master/sysfiles \
    PATH=${PATH}:/bpnet-master/bin:/maxit/bin \
    PYTHONPATH=${PYTHONPATH}:/rnapdbee-adapters/src

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "adapters.server:app"]

COPY src/adapters /rnapdbee-adapters/src/adapters
