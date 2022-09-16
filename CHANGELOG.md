# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [0.0.15] - 2022-09-15
* fixing building wheel for x86_64
* fixing behaviors over Meta class in Models with missing attributes

## [0.0.7] - 2022-09-14
* Added "from_dict" and "from_json" methods to create datamodels from json strings and dictionaries
* added a new json encoder, based on orjson
* "model()" method export a json version of Model (serialization).

## [0.0.1] - 2022-09-12
* First version
