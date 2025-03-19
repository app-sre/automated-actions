FROM registry.access.redhat.com/ubi9-minimal@sha256:bafd57451de2daa71ed301b277d49bd120b474ed438367f087eac0b885a668dc AS base
COPY --from=openpolicyagent/opa:1.2.0-static@sha256:2636af0937bf7c5ab7f79271399c53c45d4b4d2af8a2b9cc43f65c6598b49064 /opa /opa

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
