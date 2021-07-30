FROM amazon/aws-lambda-python:3.8

COPY get-report-via-api.py ${LAMBDA_TASK_ROOT}/app.py
COPY onetrust ${LAMBDA_TASK_ROOT}/onetrust
COPY onetrust.cfg ${LAMBDA_TASK_ROOT}

COPY requirements.txt /tmp/
COPY install-driver.sh /tmp/

RUN yum install unzip xz atk cups-libs gtk3 libXcomposite alsa-lib tar \
    libXcursor libXdamage libXext libXi libXrandr libXScrnSaver \
    libXtst pango at-spi2-atk libXt xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel -y -q

RUN /usr/bin/bash /tmp/install-driver.sh

RUN pip install --upgrade pip -q
RUN pip install -r /tmp/requirements.txt -q

RUN yum remove unzip -y

CMD [ "app.main" ]