# bagi

[![Actions Status][actions-badge]][actions-link]
[![PyPI version][pypi-version]][pypi-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

Indexed bagit exposed with fsspec.

## Installation

From source:
```bash
git clone https://github.com/datadavev/bagi
cd bagi
python -m pip install .
```

## Usage

Given a BagIt source zip:
```
vieglais bagi [main] $ ls -al ${HOME}/Downloads/tmp
total 9639584
drwxr-xr-x   3 vieglais  staff          96 2026-09-30 17:01:42 .
drwx------@ 47 vieglais  staff        1504 2026-09-30 17:01:29 ..
-rw-r--r--@  1 vieglais  staff  4931051308 2026-09-30 17:01:42 resource_map_doi_10_18739_A2M61BS14.zip
```

Create an index of the imges contained in the zip file, and write the index back to the zip as `/index.parquet`
```
vieglais bagi [main] $ bagi index ${HOME}/Downloads/tmp/resource_map_doi_10_18739_A2M61BS14.zip
INFO:bagi:Index created with 704 rows.
```

Mount the bagit file (use `-f`, there's a bug being worked on):
```
mkdir mnt
bagi mount -f ${HOME}/Downloads/tmp/resource_map_doi_10_18739_A2M61BS14.zip mnt
```

```
ls -la mnt
total 352
drwxrwxrwx@  0 1000      1000       0 2026-09-30 17:09:28 .
drwxr-xr-x@ 22 vieglais  staff    704 2026-09-30 16:06:40 ..
-rwxrwxrwx   1 1000      1000      71 2026-09-30 17:09:28 bag-info.txt
-rwxrwxrwx   1 1000      1000      54 2026-09-30 17:09:28 bagit.txt
drwxrwxrwx   0 1000      1000       0 2026-09-30 17:09:28 data
-rwxrwxrwx   1 1000      1000   14971 2026-09-30 17:09:28 index.parquet
-rwxrwxrwx   1 1000      1000   47940 2026-09-30 17:09:28 manifest-md5.txt
drwxrwxrwx   0 1000      1000       0 2026-09-30 17:09:28 metadata
-rwxrwxrwx   1 1000      1000   76579 2026-09-30 17:09:28 tagmanifest-md5.txt

tree mnt | more
mnt
├── bag-info.txt
├── bagit.txt
├── data
│   ├── Orthomap2024
│   │   └── Orthomap2024.tif
│   └── raw_drone_images
│       ├── DJI_0134.JPG
│       ├── DJI_0135.JPG
│       ├── DJI_0136.JPG
│       ├── DJI_0137.JPG
│       ├── DJI_0138.JPG
│       ├── DJI_0139.JPG
│       ├── DJI_0140.JPG
│       ├── DJI_0141.JPG
│       ├── DJI_0142.JPG
│       ├── DJI_0143.JPG
│       ├── DJI_0144.JPG
│       ├── DJI_0145.JPG
│       ├── DJI_0146.JPG
│       ├── DJI_0147.JPG
...
│       ├── sysmeta-urn_uuid_fc23d959-f348-4066-8a3d-f363d79fc686.xml
│       ├── sysmeta-urn_uuid_fc6876ac-163b-483e-91c8-d3b52ebe93b7.xml
│       ├── sysmeta-urn_uuid_fc8f0736-d6b4-43c5-9774-a0b070e162f0.xml
│       ├── sysmeta-urn_uuid_fcb42a3a-d0e8-4da0-b873-d98fee19eefa.xml
│       ├── sysmeta-urn_uuid_fda9d656-b5e3-4934-b54f-379a28de3434.xml
│       ├── sysmeta-urn_uuid_fe03ee27-9b80-4a31-a830-1552ba2bd575.xml
│       ├── sysmeta-urn_uuid_fe2ab22a-b803-439a-b419-6fa0b527d634.xml
│       └── sysmeta-urn_uuid_ff047d6b-b255-45a4-addb-7f6cc0dcd6a9.xml
└── tagmanifest-md5.txt

cat mnt/metadata/sysmeta/sysmeta-urn_uuid_ff047d6b-b255-45a4-addb-7f6cc0dcd6a9.xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns3:systemMetadata xmlns:ns2="http://ns.dataone.org/service/types/v1" xmlns:ns3="http://ns.dataone.org/service/types/v2.0">
    <serialVersion>0</serialVersion>
    <identifier>urn:uuid:ff047d6b-b255-45a4-addb-7f6cc0dcd6a9</identifier>
    <formatId>image/jpeg</formatId>
    <size>6245261</size>
    <checksum algorithm="MD5">9a5085a2be59dac23c85784853e105b2</checksum>
    <submitter>http://orcid.org/0009-0004-7648-0108</submitter>
    <rightsHolder>http://orcid.org/0009-0004-7648-0108</rightsHolder>
    <accessPolicy>
        <allow>
            <subject>CN=arctic-data-admins,DC=dataone,DC=org</subject>
            <permission>read</permission>
            <permission>write</permission>
            <permission>changePermission</permission>
        </allow>
        <allow>
            <subject>public</subject>
            <permission>read</permission>
        </allow>
    </accessPolicy>
    <replicationPolicy replicationAllowed="false" numberReplicas="0"/>
    <archived>false</archived>
    <dateUploaded>2026-03-11T05:45:25.353+00:00</dateUploaded>
    <dateSysMetadataModified>2026-09-15T03:05:05.096+00:00</dateSysMetadataModified>
    <originMemberNode>urn:node:ARCTIC</originMemberNode>
    <authoritativeMemberNode>urn:node:ARCTIC</authoritativeMemberNode>
    <fileName>DJI_0313.JPG</fileName>
</ns3:systemMetadata>
```

Peek at the generated `index.parquet`:

```
duckdb -c "select * from read_parquet('mnt/index.parquet') limit 10;"
┌────────────────────────────────┬─────────────────────┬────────────────────────────────┐
│              path              │    date_created     │            geometry            │
│            varchar             │      timestamp      │ geometry('{"$schema":"https:// │
│                                │                     │ proj.org/schemas/v0.5/projjson │
│                                │                     │ .schema.json","type":"geograph │
│                                │                     │ iccrs","name":"wgs 84","datum… │
├────────────────────────────────┼─────────────────────┼────────────────────────────────┤
│ data/raw_drone_images/DJI_0801 │ 2024-06-15 14:55:21 │ POINT (-49.99856936111111 67.1 │
│ .JPG                           │                     │ 5879063888889)                 │
├────────────────────────────────┼─────────────────────┼────────────────────────────────┤
│ data/raw_drone_images/DJI_0615 │ 2024-06-15 14:37:38 │ POINT (-49.99667075 67.1577545 │
│ .JPG                           │                     │ 0000001)                       │
├────────────────────────────────┼─────────────────────┼────────────────────────────────┤
│ data/raw_drone_images/DJI_0429 │ 2024-06-15 14:25:25 │ POINT (-49.997585111111114 67. │
│ .JPG                           │                     │ 15828177777779)                │
├────────────────────────────────┼─────────────────────┼────────────────────────────────┤
│ data/raw_drone_images/DJI_0712 │ 2024-06-15 14:52:11 │ POINT (-49.997079416666665 67. │
│ .JPG                           │                     │ 15858383333334)                │
├────────────────────────────────┼─────────────────────┼────────────────────────────────┤
│ data/raw_drone_images/DJI_0607 │ 2024-06-15 14:37:22 │ POINT (-49.99662547222222 67.1 │
│ .JPG                           │                     │ 581051388889)                  │
├────────────────────────────────┼─────────────────────┼────────────────────────────────┤
│ data/raw_drone_images/DJI_0526 │ 2024-06-15 14:34:24 │ POINT (-49.99593105555556 67.1 │
│ .JPG                           │                     │ 580563888889)                  │
├────────────────────────────────┼─────────────────────┼────────────────────────────────┤
│ data/raw_drone_images/DJI_0348 │ 2024-06-15 14:22:30 │ POINT (-49.998564055555555 67. │
│ .JPG                           │                     │ 15804252777778)                │
├────────────────────────────────┼─────────────────────┼────────────────────────────────┤
│ data/raw_drone_images/DJI_0720 │ 2024-06-15 14:52:27 │ POINT (-49.99779930555555 67.1 │
│ .JPG                           │                     │ 5858830555555)                 │
├────────────────────────────────┼─────────────────────┼────────────────────────────────┤
│ data/raw_drone_images/DJI_0534 │ 2024-06-15 14:34:40 │ POINT (-49.99597855555556 67.1 │
│ .JPG                           │                     │ 5770516666667)                 │
├────────────────────────────────┼─────────────────────┼────────────────────────────────┤
│ data/raw_drone_images/DJI_0437 │ 2024-06-15 14:25:45 │ POINT (-49.99689638888889 67.1 │
│ .JPG                           │                     │ 5832986111111)                 │
└────────────────────────────────┴─────────────────────┴────────────────────────────────┘
  10 rows                                                                     3 columns
```

Unmount:

```
$ umount mnt
```

Serve via http:

```
bagi serve ${HOME}/Downloads/tmp/resource_map_doi_10_18739_A2M61BS14.zip
INFO:     Started server process [39189]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8888 (Press CTRL+C to quit)
```

Open browser at "http://localhost:8888/base/id"

`base` is an arbitrary base of the url, `id` is any string that can be used to distinguish
between multiple zips should more than one be served (not currently implemented).

[![Screen capture](https://img.youtube.com/vi/pGpJTZ54r_c/0.jpg)](https://www.youtube.com/watch?v=pGpJTZ54r_c)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for instructions on how to contribute.

## License

Distributed under the terms of the [Apache license](LICENSE).


<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/datadavev/bagi/workflows/CI/badge.svg
[actions-link]:             https://github.com/datadavev/bagi/actions
[pypi-link]:                https://pypi.org/project/bagi/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/bagi
[pypi-version]:             https://img.shields.io/pypi/v/bagi
<!-- prettier-ignore-end -->
