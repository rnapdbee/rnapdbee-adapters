# syntax=docker/dockerfile:1
FROM ubuntu:20.04 AS bpnet-builder

RUN apt-get update -y \
 && apt-get install -y \
        curl \
 && rm -rf /var/lib/apt/lists/*

RUN curl -L https://github.com/computational-biology/bpnet/archive/refs/heads/master.tar.gz | tar xz

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
        sed \
 && rm -rf /var/lib/apt/lists/*

ARG maxit_version=11.100

RUN curl -L https://sw-tools.rcsb.org/apps/MAXIT/maxit-v${maxit_version}-prod-src.tar.gz | tar xz

ENV RCSBROOT=/maxit-v${maxit_version}-prod-src

RUN cd ${RCSBROOT} \
 && sed -i '18i %define api.header.include {"CifParser.h"}' cifparse-obj-v7.0/src/CifParser.y \
 && sed -i '17i %define api.header.include {"DICParser.h"}' cifparse-obj-v7.0/src/DICParser.y \
 && make \
 && make binary

################################################################################

FROM ubuntu:20.04 AS mc-annotate-builder

RUN apt-get update -y \
 && apt-get install -y \
        curl \
        unzip \
 && rm -rf /var/lib/apt/lists/*

 RUN curl -L https://major.iric.ca/MajorLabEn/MC-Tools_files/MC-Annotate.zip -o mc-annotate.zip \
  && unzip mc-annotate.zip \
  && mv MC-Annotate mc-annotate

################################################################################

FROM ubuntu:20.04 AS rnaview-builder

RUN apt-get update -y \
 && apt-get install -y \
        build-essential \
        curl \
 && rm -rf /var/lib/apt/lists/*

RUN curl -L http://ndbserver.rutgers.edu/ndbmodule/services/download/RNAVIEW.tar.gz | tar xz

RUN cd RNAVIEW \
 && make

################################################################################

RUN apt-get update -y \
 && apt-get install -y \
        gunicorn \
        python3 \
        python3-pip \
        git \
 && rm -rf /var/lib/apt/lists/*

COPY --from=bpnet-builder /bpnet-master /bpnet-master

ARG maxit_version=11.100
COPY --from=maxit-builder /maxit-v${maxit_version}-prod-src /maxit

COPY --from=mc-annotate-builder /mc-annotate /mc-annotate/

COPY --from=rnaview-builder /RNAVIEW /rnaview


ENV NUCLEIC_ACID_DIR=/bpnet-master/sysfiles \
    PATH=${PATH}:/bpnet-master/bin:/maxit/bin:/mc-annotate:/rnaview/bin:/venv/bin \
    PYTHONPATH=${PYTHONPATH}:/rnapdbee-adapters/src \
    RCSBROOT=/maxit \
    RNAVIEW=/rnaview

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "adapters.server:app"]

COPY src/adapters /rnapdbee-adapters/src/adapters
