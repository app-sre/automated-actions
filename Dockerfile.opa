# ubi-minimal (not ubi-micro) is required here: OPA runs as a sidecar bound to
# 127.0.0.1 only (see openshift/template.yaml), so kubelet's httpGet/tcpSocket
# probes can't reach it from outside the pod netns. Liveness/readiness/startup
# probes instead exec `curl` inside this container against 127.0.0.1:8181 —
# provided by ubi-minimal's curl-minimal package. Do not slim this image down
# without replacing that probe mechanism.
FROM registry.access.redhat.com/ubi10/ubi-minimal@sha256:204e1531cee54562b107fb31e0b327062fc3d5d67af7cc0d2e66b2c572b9044f AS base
COPY --from=openpolicyagent/opa:1.21.1-static@sha256:4675ab04ad1627f74741d2d9c5142698c79e18b7b09f192587d31d6dba20838e /opa /opa

ENV PATH=${PATH}:/ \
    IS_TESTED_FLAG="/tmp/is_tested"

USER 1000:1000

COPY LICENSE /licenses/
COPY packages/opa/authz /authz

#
# Test image
#
FROM base AS test
COPY --from=ghcr.io/open-policy-agent/regal:0.43.0@sha256:29460f0ec1340d37f6c0c74bcbd88dd232fd8382c7a2337f0684415bd4c46da1 /ko-app/regal /bin/regal

USER 0
RUN microdnf install -y make
USER 1000:1000

COPY packages/opa/Makefile /
COPY .regal.yaml /

RUN make -C / test
RUN touch ${IS_TESTED_FLAG}

#
# Prod image
#
FROM base AS prod
COPY --from=test ${IS_TESTED_FLAG} ${IS_TESTED_FLAG}

ENTRYPOINT ["/opa"]
CMD ["run"]
