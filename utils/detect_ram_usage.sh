#!/bin/bash

# A robust script to calculate the total Resident Set Size (RSS) RAM usage
# for a docker-compose workload. It automatically detects cgroup v1 or v2.

echo "Calculating actual RAM usage (RSS) for each container..."
echo "--------------------------------------------------------"

# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
  echo "This script must be run as root (or with sudo) to access cgroup stats." >&2
  exit 1
fi

total_rss_mb=0
cgroup_v2=false

# Detect cgroup version by checking for a known v2 file
if [ -f /sys/fs/cgroup/cgroup.controllers ]; then
    echo "System is using cgroup v2."
    cgroup_v2=true
else
    echo "System is using cgroup v1."
fi
echo "--------------------------------------------------------"


for id in $(docker compose ps -q); do
  name=$(docker inspect --format '{{.Name}}' "$id" | sed 's,^/,,')
  pid=$(docker inspect -f '{{.State.Pid}}' "$id")
  rss_mb=0

  if [[ "$pid" == "0" ]]; then
    printf "Container: %-40s | Status: Not running\n" "$name"
    continue
  fi

  if $cgroup_v2; then
    # --- Cgroup v2 Logic ---
    # In v2, the "anon" stat represents non-cache memory (RSS).
    stat_file="/sys/fs/cgroup/$(grep -oP '(?<=:memory:)/.*' /proc/$pid/cgroup)/memory.stat"
    if [ -f "$stat_file" ]; then
      rss_bytes=$(grep "^anon " "$stat_file" | awk '{print $2}')
    fi
  else
    # --- Cgroup v1 Logic ---
    # In v1, "total_rss" is the value we need.
    stat_file="/sys/fs/cgroup/memory/docker/$id/memory.stat"
    if [ -f "$stat_file" ]; then
        rss_bytes=$(grep "total_rss" "$stat_file" | awk '{print $2}')
    fi
  fi

  if [[ -n "$rss_bytes" ]]; then
    rss_mb=$(echo "scale=2; $rss_bytes / 1024 / 1024" | bc)
    total_rss_mb=$(echo "$total_rss_mb + $rss_mb" | bc)
    printf "Container: %-40s | Actual RAM (RSS): %8.2f MB\n" "$name" "$rss_mb"
  else
    printf "Container: %-40s | Warning: Could not read stats.\n" "$name"
  fi
done

echo "--------------------------------------------------------"
echo "Total Actual RAM Usage (RSS) for all containers: ${total_rss_mb} MB"