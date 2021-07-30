FROM amazon/aws-lambda-python:3.8

COPY get-report-via-api.py ${LAMBDA_TASK_ROOT}/app.py
COPY onetrust ${LAMBDA_TASK_ROOT}/onetrust
COPY onetrust.cfg ${LAMBDA_TASK_ROOT}

COPY requirements.txt /tmp/
COPY install-driver.sh /tmp/

COPY google-chrome.repo /etc/yum.repos.d/

RUN yum install unzip libglib2 libnss3 libgconf libfontconfig1 libxcb -y -q
RUN yum install google-chrome-stable -y -q

RUN /usr/bin/bash /tmp/install-driver.sh

RUN pip install --upgrade pip -q
RUN pip install -r /tmp/requirements.txt -q

RUN yum remove unzip -y

ENV PATH="/opt/chromedriver:${PATH}"

CMD [ "app.main" ]