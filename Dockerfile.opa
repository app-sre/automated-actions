FROM registry.access.redhat.com/ubi9-minimal@sha256:e12131db2e2b6572613589a94b7f615d4ac89d94f859dad05908aeb478fb090f AS base
COPY --from=openpolicyagent/opa:1.5.1-static@sha256:72c5186ef74bc7a88faf88204109476be41cdc392ff1de722f7d8ecb08f18c4d /opa /opa

ENV PATH=${PATH}:/
USER 1000:1000

COPY LICENSE /licenses/
COPY packages/opa/authz /authz

#
# Test image
#
FROM base AS test
COPY --from=ghcr.io/styrainc/regal:0.34.1@sha256:3d74487cfed3ab92d89ee60b622fe70ee50c2af82c28bbf04f3ac1c813b4965f /ko-app/regal /bin/regal
USER 0
RUN microdnf install -y make
USER 1000:1000

COPY packages/opa/Makefile /
COPY .regal.yaml /

# Image does not have make installed, so we run the tests directly
RUN make -C / test

#
# Prod image
#
FROM base AS prod

ENTRYPOINT ["/opa"]
CMD ["run"]
