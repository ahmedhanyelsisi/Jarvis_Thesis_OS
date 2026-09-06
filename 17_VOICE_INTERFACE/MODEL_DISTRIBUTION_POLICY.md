# Stone 26.5 model distribution policy

The voice runtime stays local and offline after setup. Source control contains
model metadata, pinned revisions, checksums, and license notices; it does not
contain model binaries or wheelhouse assets.

| Asset | Current recorded terms | Stone 26.5 delivery decision |
|---|---|---|
| faster-whisper base | MIT | Verified first-run download or user-supplied asset. |
| Piper engine | GPL-3.0 | Do not bundle in a desktop release without a release-specific license review. |
| Piper `en_GB-alan-medium` voice | See bundled model card | Do not bundle until the selected voice terms are recorded and approved. |
| openWakeWord code | Apache-2.0 | Code terms are tracked separately from models. |
| supplied openWakeWord pretrained models | CC BY-NC-SA 4.0 | Never bundle in a distributable product under this policy. |

`provision_models.py --download` remains an explicit setup/repair action.
Runtime providers never download models. A future distribution must present
applicable notices before downloading and accept only manifest allowlisted
model/license combinations. This policy does not change the user’s local
personal installation.
