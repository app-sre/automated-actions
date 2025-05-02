FROM registry.access.redhat.com/ubi9-minimal@sha256:e1c4703364c5cb58f5462575dc90345bcd934ddc45e6c32f9c162f2b5617681c AS base
COPY --from=openpolicyagent/opa:1.4.0-static@sha256:8eb5ef478f757fabba76dfdafb58ab85667c151415b4f3689d9f05acc635d8ea /opa /opa

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
