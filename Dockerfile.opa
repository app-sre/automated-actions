FROM registry.access.redhat.com/ubi9-minimal@sha256:6d5a6576c83816edcc0da7ed62ba69df8f6ad3cbe659adde2891bfbec4dbf187 AS base
COPY --from=openpolicyagent/opa:1.6.0-static@sha256:3e5a77e73b42c4911ff2a9286f9ba280b273afc17784f7e5d8ba69db22a1e1c0 /opa /opa

ENV PATH=${PATH}:/
USER 1000:1000

COPY LICENSE /licenses/
COPY packages/opa/authz /authz

#
# Test image
#
FROM base AS test
COPY --from=ghcr.io/styrainc/regal:0.35.1@sha256:7caf9953f1c49054c94030ec7be087b46ae501fc347cdaace9557a57abd3f4ff /ko-app/regal /bin/regal
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
