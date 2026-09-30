> Research note produced 2026-09-30 by Claude Code (session `bbd1b029-3204-552c-b443-51a876efe97f`, see `llm-logs/`) from public sources reachable at the time. The egress proxy blocked `signpath.org`, `platon.sikt.no` and `learn.microsoft.com`, so the rows marked *(snippet)* rest on search-engine summaries, not on the primary page. Check those before acting on them.

# Cheap code signing for the standalone executables

Question: the standalone executables (REQ025, release `cwelleegread-standalone-v0.3.0`)
are unsigned, so Windows SmartScreen warns and macOS Gatekeeper blocks them
until the user removes the quarantine flag. What is the cheapest way to sign
them, and what does signing actually buy?

## What signing buys (and does not)

- **Windows.** Since 2024, Microsoft treats every code-signing certificate the
  same for SmartScreen: EV no longer grants instant reputation, and neither does
  Azure Artifact Signing. A signed file still warns until the publisher has built
  reputation through downloads over time. Signing with the *same identity* on
  every release is what lets that reputation accumulate. *(snippet: Microsoft
  "Code signing options" and "SmartScreen reputation" pages; confirmed by ToDesktop
  and electron-builder write-ups.)*
- **macOS.** Only a Developer ID signature plus Apple notarization removes the
  Gatekeeper block. There is no free route to it. PyInstaller's ad-hoc signature
  (arm64) only makes the binary runnable once the quarantine flag is removed.
- **Linux.** No OS-level signing. Provenance (below) is the useful measure.

## Options

| Option | Platform | Cost | Eligibility / catch | Source |
|---|---|---|---|---|
| SignPath Foundation | Windows (Authenticode, OV) | free | OSI licence (the Unlicense is OSI-approved), no proprietary components, actively maintained, already released, functionality described on the download page. Every team member needs MFA. A code-signing policy page must be published. Builds must come from a trusted build system (GitHub Actions connector; signs only workflow artifacts). The **publisher shown is "SignPath Foundation"**, not the project. Whether the Foundation also signs or notarizes for macOS is unclear: SignPath's commercial product notarizes, but notarization needs the publisher's own Apple Developer ID. | *(snippet)* signpath.org/terms.html; docs.signpath.io |
| GÉANT TCS via Sikt (HARICA) | Windows | free or discounted for member institutions | Sikt is Norway's NREN in TCS (HARICA since January 2025; the current TCS contract runs to December 2026). TCS includes code-signing certificates in the institution's name. Since June 2023 HARICA issues code-signing keys only on hardware tokens (FIPS 140-2 L3 / CC EAL4+), which makes signing in CI awkward. Needs the institution's certificate administrator. | GÉANT TCS pages; HARICA; *(snippet)* Sikt |
| Certum Open Source Code Signing (SimplySign cloud) | Windows | from about €49 per certificate | For individual open-source developers; the key is in Certum's cloud HSM. Certificates are valid for at most 459 days from 2026-02-27. Automating the cloud login in CI is possible but fiddly. | shop.certum.eu |
| Azure Artifact Signing (formerly Trusted Signing) | Windows | $9.99/month (5 000 signatures) | GA 2026 for businesses in the US, Canada, EU and UK, including self-employed individuals, without the former three-year history requirement. Private individuals outside the US and Canada are still excluded. Best GitHub Actions integration of the paid options. | *(snippet)* azure.microsoft.com; Microsoft tech community |
| Apple Developer Program + notarization | macOS | $99/year | The only way to remove the Gatekeeper block. Fee waivers are for nonprofits, accredited educational institutions and government bodies in a fixed country list; Norway was not in the lists found (2018, 2020). | developer.apple.com |
| GitHub artifact attestations (Sigstore) | all | free for public repositories | Not code signing: OS warnings stay. Proves a file was built by this repository's workflow from a given commit (`gh attestation verify FILE --repo janbrogger/CwellEEGRead`). | docs.github.com; actions/attest-build-provenance |

## Decision and next steps

1. **Done:** the release workflow attests every asset
   (`actions/attest-build-provenance@v4` in `.github/workflows/release-standalone.yml`,
   DES023); the standalone README tells users how to verify.
2. **Windows:** apply to SignPath Foundation (the maintainer must apply; it needs
   a code-signing policy page and a workflow step that submits the executable as
   a GitHub artifact). Alternative if the publisher should be the institution:
   ask the institution's IT for a TCS/HARICA code-signing certificate.
3. **macOS:** only with an Apple Developer account ($99/year). Until then keep the
   documented `xattr -d com.apple.quarantine` step and point Mac users to the
   `.pyz`, which Gatekeeper does not block.
4. **Linux:** attestations only.

## Sources

- SignPath Foundation: https://signpath.org/, https://signpath.org/terms.html,
  https://docs.signpath.io/trusted-build-systems/github,
  https://signpath.io/solutions/open-source-community
- Azure Artifact Signing: https://azure.microsoft.com/en-us/products/artifact-signing,
  https://techcommunity.microsoft.com/blog/microsoft-security-blog/trusted-signing-is-now-open-for-individual-developers-to-sign-up-in-public-previ/4273554
- SmartScreen: https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options,
  https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation,
  https://www.todesktop.com/blog/posts/windows-apps-psa-ev-certs-do-not-grant-immediate-reputation-anymore,
  https://github.com/electron-userland/electron-builder/pull/10190
- Certum: https://shop.certum.eu/open-source-code-signing-on-simplysign.html
- GÉANT TCS / HARICA: https://security.geant.org/trusted-certificate-services/,
  https://wiki.geant.org/spaces/TCSNT/pages/929693819/TCS+Participants+HARICA,
  https://www.harica.gr/en/Products/Code-Signing, https://platon.sikt.no/tjenester/certificates
- Apple fee waivers: https://developer.apple.com/help/account/membership/fee-waivers/,
  https://developer.apple.com/news/?id=02032020a
- GitHub attestations: https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds,
  https://github.com/actions/attest-build-provenance
