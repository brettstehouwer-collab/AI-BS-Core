#!/bin/sh
set -eu

host_gateway="$(ip -4 route show default | awk 'NR == 1 {print $3}')"
if [ -z "$host_gateway" ]; then
    echo "Could not determine the Windows host gateway" >&2
    exit 1
fi

service_ports="8055,8085,8089,1935"
iptables -C INPUT -i eth0 -s "$host_gateway" -p tcp -m multiport --dports "$service_ports" -j ACCEPT 2>/dev/null \
    || iptables -I INPUT 1 -i eth0 -s "$host_gateway" -p tcp -m multiport --dports "$service_ports" -j ACCEPT
iptables -C INPUT -i eth0 -p tcp -m multiport --dports "$service_ports" -j DROP 2>/dev/null \
    || iptables -I INPUT 2 -i eth0 -p tcp -m multiport --dports "$service_ports" -j DROP
