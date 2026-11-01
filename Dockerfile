ARG IMAGE=intersystemsdc/iris-community:latest
FROM ${IMAGE}

WORKDIR /home/irisowner/dev

ARG NAMESPACE="USER"

ENV IRISUSERNAME="_SYSTEM"
ENV IRISPASSWORD="SYS"
ENV IRISNAMESPACE=$NAMESPACE
ENV PATH="/usr/irissys/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/irisowner/bin"
ENV PYTHONPATH="/home/irisowner/dev:/home/irisowner/dev/python"

COPY requirements.txt .
RUN pip3 --timeout 120 --retries 5 install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

RUN iris start IRIS && \
    iris session IRIS < iris.script > /tmp/hfloader-build.log 2>&1 && \
    cat /tmp/hfloader-build.log && \
    grep -Eq '^HFLOADER_BUILD_OK=1[[:space:]]*$' /tmp/hfloader-build.log && \
    ! grep -Eq 'ERROR #|[<][A-Z][A-Z ]+[>]' /tmp/hfloader-build.log && \
    iris stop IRIS quietly
