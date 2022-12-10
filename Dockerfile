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

COPY app/maxit app/maxit

RUN cd ${RCSBROOT} \
 && patch -p0 < /app/maxit/bison_patch \
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

COPY app/rnaview app/rnaview

RUN patch -p0 < app/rnaview/patch \
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
 && Rscript -e 'BiocManager::install("R4RNA", lib="/usr/local/lib/R/site-library")'

COPY app/rchie/rchie.R ${rchie_dir}/rchie.R

################################################################################

FROM ubuntu:22.04 AS pseudoviewer-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -y \
 && apt-get install -y \
        curl \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir pseudoviewer \
 && curl -L https://github.com/IronLanguages/ironpython3/releases/download/v3.4.0-beta1/ironpython_3.4.0-beta1.deb > pseudoviewer/ipython.deb \
 && curl -L http://pseudoviewer.inha.ac.kr/download.asp?file=PseudoViewer3.exe > pseudoviewer/PseudoViewer3.exe

COPY app/pseudoviewer/ pseudoviewer/

################################################################################

FROM quay.io/biocontainers/viennarna:2.5.1--py310pl5321hc8f18ef_0 AS rnapuzzler-builder

ENV DEBIAN_FRONTEND=noninteractive

COPY app/rnapuzzler RNAplot/
RUN mv /usr/local/bin/RNAplot RNAplot/

################################################################################

FROM ubuntu:22.04 AS server

ARG maxit_version
ARG rchie_dir
ENV DEBIAN_FRONTEND=noninteractive \
    NUCLEIC_ACID_DIR=/bpnet-master/sysfiles \
    PATH=${PATH}:/bpnet-master/bin:/maxit/bin:/mc-annotate:/rnaview/bin:/venv/bin:${rchie_dir}:/pseudoviewer:/RNAplot \
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
       gnupg \
       ca-certificates \
       inkscape \
 && apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 3FA7E0328081BFF6A14DA29AA6A19B38D3D831EF \
 && echo "deb https://download.mono-project.com/repo/ubuntu stable-focal main" | tee /etc/apt/sources.list.d/mono-official-stable.list \
 && apt-get update && apt-get install -y mono-devel \
 && rm -rf /var/lib/apt/lists/*

COPY --from=bpnet-builder /bpnet-master /bpnet-master

COPY --from=maxit-builder /maxit-v${maxit_version}-prod-src /maxit

COPY --from=mc-annotate-builder /mc-annotate /mc-annotate/

COPY --from=rnaview-builder /RNAVIEW /rnaview

COPY --from=r-builder /usr/local/lib/R/site-library /usr/local/lib/R/site-library

COPY --from=pseudoviewer-builder /pseudoviewer /pseudoviewer
RUN dpkg -i pseudoviewer/ipython.deb && rm pseudoviewer/ipython.deb

COPY --from=rnapuzzler-builder /RNAplot /RNAplot

COPY --from=python-builder /venv /venv

EXPOSE 80
CMD [  "gunicorn", \
       "--worker-tmp-dir", "/dev/shm", \
       "--workers", "2", \
       "--threads", "2", \
       "--worker-clas", "gthread", \
       "--bind", "0.0.0.0:80", \
       "adapters.server:app" \
]

COPY src/adapters /rnapdbee-adapters/src/adapters
