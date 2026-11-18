FROM apache/airflow:2.10.5-python3.12

COPY requirements.txt /tmp/requirements-ml.txt
RUN pip install --no-cache-dir -r /tmp/requirements-ml.txt \
    && pip install --no-cache-dir "numpy==1.26.4" "scipy==1.13.1" "joblib==1.4.2" "scikit-learn==1.6.1"
