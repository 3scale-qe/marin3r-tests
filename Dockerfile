FROM quay.io/centos/centos:stream9
LABEL description="Run Marin3r integration tests \
Default ENTRYPOINT: 'make' and CMD: 'test' \
Bind dynaconf settings to /opt/secrets.yaml \
Bind kubeconfig to /opt/kubeconfig \
Bind a dir to /test-run-results to get reports "

RUN useradd --no-log-init -u 1001 -g root -m testsuite
RUN dnf install -y python3.11 python3.11-pip make git && dnf clean all

RUN curl https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable/openshift-client-linux.tar.gz >/tmp/oc.tgz && \
	tar xzf /tmp/oc.tgz -C /usr/local/bin && \
	rm /tmp/oc.tgz

RUN curl -L https://github.com/cloudflare/cfssl/releases/download/v1.6.3/cfssl_1.6.3_linux_amd64 >/usr/bin/cfssl && \
    chmod +x /usr/bin/cfssl

RUN python3.11 -m pip --no-cache-dir install poetry

WORKDIR /opt/workdir/marin3r-testsuite

COPY . .

RUN mkdir -m 0700 /test-run-results && chown testsuite /test-run-results && \
    chown testsuite -R /opt/workdir/*

USER testsuite


ENV KUBECONFIG=/run/kubeconfig \
    SECRETS_FOR_DYNACONF=/run/secrets.yaml \
    WORKON_HOME=/opt/workdir/virtualenvs \
    junit=yes \
    resultsdir=/test-run-results

RUN poetry env use python3.11 && poetry install

ENTRYPOINT [ "make" ]
CMD [ "test" ]
