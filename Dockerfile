FROM python

COPY . /fr3d-python-adapter
RUN pip install /fr3d-python-adapter

CMD ["fr3d-python-adapter"]