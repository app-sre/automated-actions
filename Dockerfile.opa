FROM registry.access.redhat.com/ubi10/ubi-minimal@sha256:ceaad73890ea88685eeb1b40a502b7983f2cfac6f1aa10915d1176d51eb90124 AS base
COPY --from=openpolicyagent/opa:1.18.2-static@sha256:57f7d06808fff6de3ea1d698e6430990973ca1370be0e54975f0083d615521da /opa /opa

ENV PATH=${PATH}:/ \
    IS_TESTED_FLAG="/tmp/is_tested"

USER 1000:1000

COPY LICENSE /licenses/
COPY packages/opa/authz /authz

#
# Test image
#
FROM base AS test
COPY --from=ghcr.io/open-policy-agent/regal:0.42.0@sha256:07984036043f772a1f921bd0ad9045b8bd9dc58460a1d76f476c458dc8a98b16 /ko-app/regal /bin/regal

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
