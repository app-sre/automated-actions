FROM registry.access.redhat.com/ubi9-minimal@sha256:92b1d5747a93608b6adb64dfd54515c3c5a360802db4706765ff3d8470df6290 AS base
COPY --from=openpolicyagent/opa:1.4.2-static@sha256:3c995dc8a59f6ddfd92eb7404d2f7ff9fe71cd025d9251199957a8a6afbfd76e /opa /opa

ENV PATH=${PATH}:/
USER 1000:1000

COPY LICENSE /licenses/
COPY packages/opa/authz /authz

#
# Test image
#
FROM base AS test

USER 0
RUN microdnf install -y make
USER 1000:1000

COPY packages/opa/Makefile /
COPY packages/opa/tests /tests

# Image does not have make installed, so we run the tests directly
RUN make -C / test

#
# Prod image
#
FROM base AS prod

ENTRYPOINT ["/opa"]
CMD ["run"]
