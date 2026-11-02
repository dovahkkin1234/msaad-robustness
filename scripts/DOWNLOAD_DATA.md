# Getting the datasets (public benchmarks)

Full step-by-step instructions with commands are in **SETUP.md (Steps 4–6)**. Summary:

## IoTID20 — you need the CSV, not the PCAPs
- Use the CSV of flow features (625,783 rows, 86 columns; labels in `Label`, `Cat`, `Sub_Cat`).
- Source: the Kaggle mirror used by published IoTID20 work (free login),
  https://www.kaggle.com/datasets/rohulaminlabid/iotid20-dataset
- **Avoid** the "IoT-DI20" Google Drive folder on the Ontario Tech datasets page: it holds
  `IoT-23[Profile].csv`, a different dataset.
- **Avoid** the IEEE DataPort "IoT Network Intrusion Dataset" (823 MB zip): it is the raw
  PCAP capture, not the feature CSV.
- Place it at: `data/iotid20/IoT_Network_Intrusion_Dataset.csv`

## CICIoT2023 — one CSV part is enough for Week 1
- Official: https://www.unb.ca/cic/datasets/iotdataset-2023.html → "Download the dataset"
  → `CICIoT2023/CSV/` (plain HTTP server).
- Kaggle mirror (HTTPS): https://www.kaggle.com/datasets/madhavmalhotra/unb-cic-iot-dataset
- Label column: `label` (benign rows are `BenignTraffic`; DDoS rows start with `DDoS-`).
- Place one file at: `data/ciciot2023/part-00000.csv`

## Then
Run `scripts/inspect_dataset.py` on both files and send the reports (SETUP.md Step 6).
The `data/` folder is git-ignored: never commit the datasets.
