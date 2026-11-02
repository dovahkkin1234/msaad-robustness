"""Robustness-evaluation toolkit for our own reimplementation of MSAAD.

Everything here runs offline on public benchmark CSVs (IoTID20, CICIoT2023): it perturbs
feature vectors to measure how the published defence holds up, as the base paper's own
Scenario 2 does. It does not generate, send or touch any network traffic.
"""
