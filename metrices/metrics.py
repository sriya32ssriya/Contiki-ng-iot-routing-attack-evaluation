import re
import sys
import csv

if len(sys.argv) not in (2, 3):
    print("Usage: python3 metrics.py <logfile> [simulation_time_seconds]")
    exit()

logfile = sys.argv[1]
# Optional second arg: actual simulated duration in seconds, for throughput.
# Defaults to 100.0 to reproduce this script's original behavior/results
# unchanged for any existing invocation that only passes a logfile.
cli_simulation_time = float(sys.argv[2]) if len(sys.argv) == 3 else None

sent = 0
received = 0
total_bytes = 0

# Change this if you run the simulation longer, or pass it as argv[2].
simulation_time = cli_simulation_time if cli_simulation_time is not None else 100.0   # seconds

with open(logfile, "r") as f:
    for line in f:

        if "PACKET SENT" in line:
            sent += 1

        if "CLIENT NODE" in line and "RECEIVED RESPONSE" in line:
            received += 1

        m = re.search(r'Packet Size\s*:\s*(\d+)', line)
        if m:
            total_bytes += int(m.group(1))

packet_loss = sent - received

if sent > 0:
    pdr = (received / sent) * 100
else:
    pdr = 0

throughput = total_bytes / simulation_time

print("\n========== METRICS ==========")
print(f"Packets Sent      : {sent}")
print(f"Packets Received  : {received}")
print(f"Packet Loss       : {packet_loss}")
print(f"PDR               : {pdr:.2f}%")
print(f"Total Bytes Sent  : {total_bytes}")
print(f"Throughput        : {throughput:.2f} Bytes/sec")
print("=============================\n")

with open("results.csv", "w", newline="") as csvfile:
    writer = csv.writer(csvfile)

    writer.writerow([
        "Packets Sent",
        "Packets Received",
        "Packet Loss",
        "PDR (%)",
        "Total Bytes",
        "Throughput(Bytes/sec)"
    ])

    writer.writerow([
        sent,
        received,
        packet_loss,
        round(pdr,2),
        total_bytes,
        round(throughput,2)
    ])

print("Results saved to results.csv")
