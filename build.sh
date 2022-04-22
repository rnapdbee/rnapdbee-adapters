#! /bin/bash
docker build --target bpnet-adapter -t bpnet-adapter .
docker build --target fr3d-adapter -t fr3d-adapter .
docker build --target barnaba-adapter -t barnaba-adapter .
docker build --target maxit -t maxit .
docker build --target server -t rnapdbee-adapter-server .
