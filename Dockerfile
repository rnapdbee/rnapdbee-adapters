# syntax=docker/dockerfile:1

ARG maxit_version=11.100
ARG rchie_dir=/usr/local/lib/R/site-library/rchie

################################################################################

FROM ubuntu:22.04 AS bpnet-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y \
 && apt-get install -y \
        curl \
 && rm -rf /var/lib/apt/lists/*

RUN curl -L https://github.com/computational-biology/bpnet/archive/refs/heads/master.tar.gz | tar xz

################################################################################

FROM ubuntu:22.04 AS maxit-builder

ARG maxit_version
ENV DEBIAN_FRONTEND=noninteractive \
    RCSBROOT=/maxit-v${maxit_version}-prod-src

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

RUN curl -L https://sw-tools.rcsb.org/apps/MAXIT/maxit-v${maxit_version}-prod-src.tar.gz | tar xz

RUN cd ${RCSBROOT} \
 && sed -i '18i %define api.header.include {"CifParser.h"}' cifparse-obj-v7.0/src/CifParser.y \
 && sed -i '17i %define api.header.include {"DICParser.h"}' cifparse-obj-v7.0/src/DICParser.y \
 && make \
 && make binary

################################################################################

FROM ubuntu:22.04 AS mc-annotate-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y \
 && apt-get install -y \
        curl \
        unzip \
 && rm -rf /var/lib/apt/lists/*

RUN curl -L https://major.iric.ca/MajorLabEn/MC-Tools_files/MC-Annotate.zip -o mc-annotate.zip \
 && unzip mc-annotate.zip \
 && mv MC-Annotate mc-annotate

################################################################################

FROM ubuntu:22.04 AS rnaview-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y \
 && apt-get install -y \
        build-essential \
        curl \
 && rm -rf /var/lib/apt/lists/*

RUN curl -L http://ndbserver.rutgers.edu/ndbmodule/services/download/RNAVIEW.tar.gz | tar xz

COPY rnaview.patch rnaview.patch

RUN patch -p0 < rnaview.patch \
 && cd RNAVIEW \
 && make

################################################################################

FROM ubuntu:22.04 AS python-builder

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/venv/bin:$PATH

RUN apt-get update -y \
 && apt-get install -y \
        build-essential \
        python3 \
        python3-pip \
        python3-venv \
        git \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /venv

COPY requirements.txt .
RUN pip3 install --upgrade --no-cache-dir wheel setuptools \
 && pip3 install --no-cache-dir -r requirements.txt

################################################################################

FROM ubuntu:22.04 AS r-builder

ARG rchie_dir
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y \
 && apt-get install -y \
        curl \
        r-base \
        libcurl4-openssl-dev \
 && rm -rf /var/lib/apt/lists/*

RUN echo 'options(BioC_mirror = "https://packagemanager.rstudio.com/bioconductor", repos = c(REPO_NAME = "https://packagemanager.rstudio.com/all/__linux__/jammy/2022-11-09+MToxNDMzODE3MywyOjQ1MjYyMTU7RDFFQTQ0MUE"))' > ~/.Rprofile \
 && Rscript -e 'install.packages(c("BiocManager", "optparse", "RColorBrewer"), lib="/usr/local/lib/R/site-library")' \
 && Rscript -e 'BiocManager::install("R4RNA", lib="/usr/local/lib/R/site-library")' \
 && curl -L https://raw.githubusercontent.com/jujubix/r-chie/master/rchie.R -o rchie.R \
 && mkdir ${rchie_dir} \
 && mv rchie.R ${rchie_dir}/rchie.R \
 && chmod 755 ${rchie_dir}/rchie.R

################################################################################

FROM ubuntu:22.04 AS server

ARG maxit_version
ARG rchie_dir
ENV DEBIAN_FRONTEND=noninteractive \
    NUCLEIC_ACID_DIR=/bpnet-master/sysfiles \
    PATH=${PATH}:/bpnet-master/bin:/maxit/bin:/mc-annotate:/rnaview/bin:/venv/bin:${rchie_dir} \
    PYTHONPATH=${PYTHONPATH}:/rnapdbee-adapters/src \
    RCSBROOT=/maxit \
    RNAVIEW=/rnaview

RUN apt-get update -y \
 && apt-get install -y \
       python3 \
       python3-venv \
       build-essential \
       pdf2svg \
       ghostscript \
       librsvg2-bin \
       r-base \
 && rm -rf /var/lib/apt/lists/*

COPY --from=bpnet-builder /bpnet-master /bpnet-master

COPY --from=maxit-builder /maxit-v${maxit_version}-prod-src /maxit

COPY --from=mc-annotate-builder /mc-annotate /mc-annotate/

COPY --from=rnaview-builder /RNAVIEW /rnaview

COPY --from=python-builder /venv /venv

COPY --from=r-builder /usr/local/lib/R/site-library /usr/local/lib/R/site-library

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "adapters.server:app"]

COPY src/adapters /rnapdbee-adapters/src/adapters
