# Drive-backed resource library

Google Drive stores cold generated resource archives. `resource_catalog.json` records their stable file IDs, SHA-256 digests, lengths and verified cache paths. The first archive was retrieved through the authenticated connector and its entire SHA compared before removing its redundant C: ZIP. Its complete editable masters and active source remain local.

For retrieval, fetch the catalog's Drive URL with download_raw_file=true and include_base64=false. Pass the fresh connector download URL, expected bytes and SHA as JSON on stdin to `python -B engine/tools/resource_cache.py`. The helper streams to D:, checks length/SHA, and publishes a content-addressed cached ZIP. Expiring URLs are never cataloged. Existing damaged cache entries reject rather than being overwritten. Archive extraction is a separate explicit operation; no downloaded code is automatically executed.

Active engine/Blender files, retained releases/SDKs, active scene assets and original family references remain local. This is a resource library, not a live game filesystem or a Google Drive mount. Before further offload, classify the resource, upload to its existing organized folder, download and hash-check the complete bytes, record restoration details, then remove only the positively identified generated duplicate. Do not delete unclassified directories or originals. Cache eviction may target only cataloged verified generated ZIPs outside active use.

Current Google Drive connector exposes file sizes but not remaining account quota. Track actual uploaded bytes and C:/D:/E: free space separately.
