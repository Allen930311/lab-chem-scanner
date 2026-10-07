# AGENT_CONTEXT — lab-chem-scanner

> Fresh-agent entrypoint. Classification: **UTILITY**.

## Purpose

A webcam/OCR chemical-inventory helper that detects validated CAS numbers and
reconciles them against an inventory CSV.

## Operating boundary

`README.md` owns usage and known limitations.
`cas_scanner.py` / `run_mobile.py` own implementation.

There is no standing feature roadmap. Maintain or extend this utility only for
a concrete requested lab workflow; do not turn it into a broader inventory
system by default.

## Data / safety boundary

Real lab inventory may contain sensitive operational information. The public
repo uses sample data only. Never commit the owner's real inventory merely to
test the scanner.

CAS-number recognition is an inventory aid, not chemical identity/safety
authority. Do not infer handling instructions or compatibility from OCR output.

## Remote vs local truth

Remote `main` is shared source truth. Camera devices, Tesseract installation,
DroidCam state and actual inventory files are local runtime facts.
