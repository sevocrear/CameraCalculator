# Security policy

## Supported versions

Security fixes are applied to the latest code on the default branch. Older
releases and forks are not maintained unless stated in their release notes.

## Public deployment

The bundled Compose file is intended for local use. Internet-facing deployments
should terminate TLS at a reverse proxy and set request-body and rate limits.
`MODELS_DIR` is an operator-controlled filesystem path and must point only to
public model assets.

## Reporting a vulnerability

Please do not disclose a suspected vulnerability in a public issue, discussion,
or pull request.

Use GitHub's **Report a vulnerability** form on the repository's Security page
when private vulnerability reporting is enabled. Include:

- affected version or commit;
- reproducible steps or a minimal proof of concept;
- expected impact and affected data;
- any known workaround.

If private reporting is unavailable, contact the maintainer privately through
the contact method listed on their GitHub profile and ask for a secure reporting
channel. Do not send secrets or exploit details until that channel is agreed.

You should receive an acknowledgement within seven days. A fix timeline depends
on severity and reproducibility. Please allow a reasonable remediation period
before coordinated disclosure.
