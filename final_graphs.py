import matplotlib
matplotlib.use('Agg')

import csv
import matplotlib.pyplot as plt
import numpy as np

scenarios = []
sent = []
received = []
pdr = []
loss = []
throughput = []

with open("final_results.csv", "r") as file:
    reader = csv.DictReader(file)

    for row in reader:
        scenarios.append(row["Scenario"])
        sent.append(int(row["Packets Sent"]))
        received.append(int(row["Packets Received"]))
        pdr.append(float(row["PDR (%)"]))
        loss.append(int(row["Packet Loss"]))
        throughput.append(float(row["Throughput(Bytes/sec)"]))

# ---------------- PDR ----------------
plt.figure(figsize=(8,5))
plt.bar(scenarios, pdr)
plt.xlabel("Scenario")
plt.ylabel("PDR (%)")
plt.title("Packet Delivery Ratio Comparison")
plt.tight_layout()
plt.savefig("PDR_comparison.png")
plt.close()

# ---------------- Packet Loss ----------------
plt.figure(figsize=(8,5))
plt.bar(scenarios, loss)
plt.xlabel("Scenario")
plt.ylabel("Packet Loss")
plt.title("Packet Loss Comparison")
plt.tight_layout()
plt.savefig("Packet_Loss_comparison.png")
plt.close()

# ---------------- Throughput ----------------
plt.figure(figsize=(8,5))
plt.bar(scenarios, throughput)
plt.xlabel("Scenario")
plt.ylabel("Throughput (Bytes/sec)")
plt.title("Throughput Comparison")
plt.tight_layout()
plt.savefig("Throughput_comparison.png")
plt.close()

# ---------------- Packets Sent vs Received ----------------
x = np.arange(len(scenarios))
width = 0.35

plt.figure(figsize=(8,5))
plt.bar(x - width/2, sent, width, label="Sent")
plt.bar(x + width/2, received, width, label="Received")

plt.xticks(x, scenarios)
plt.xlabel("Scenario")
plt.ylabel("Packets")
plt.title("Packets Sent vs Received")
plt.legend()
plt.tight_layout()
plt.savefig("Packets_Comparison.png")
plt.close()

print("All graphs generated successfully!")
