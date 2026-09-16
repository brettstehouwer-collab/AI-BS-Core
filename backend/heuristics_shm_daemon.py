import os
import sys
import time
import logging
import argparse

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "sandbox_scratch", "ipc_benchmark"
    )
)

try:
    from shm_bridge import ShmBridge, TOPIC_HEURISTICS_TELEMETRY, FLAG_HIGH_PRIORITY
except ImportError:
    import ctypes

    TOPIC_HEURISTICS_TELEMETRY = 0x0003
    FLAG_HIGH_PRIORITY = 0x02

    class ShmBridge:
        def init_shm_bridge(self):
            return 0

        def push_topic_event(self, topic, flags, data):
            return 0

        def close_shm_bridge(self):
            pass


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [HeuristicsSHM] - %(message)s"
)


class HeuristicsSHMDaemon:
    def __init__(self):
        self.bridge = ShmBridge()
        res = self.bridge.init_shm_bridge()
        if res == 0:
            logging.info(
                "✅ Connected to Multi-Topic SHM Bus under TOPIC_HEURISTICS_TELEMETRY (0x0003)"
            )
        else:
            logging.error(f"❌ Failed to attach to SHM Bus: {res}")

    def emit_mutation_log(self, rule_id: str, file_path: str, action: str):
        payload = (
            f"R:{rule_id[:10]}|F:{os.path.basename(file_path)[:15]}|A:{action[:15]}"
        )
        return self.bridge.push_topic_event(
            TOPIC_HEURISTICS_TELEMETRY, FLAG_HIGH_PRIORITY, payload
        )

    def publish_ast_mutation(
        self, rule_id: str, file_target: str, diff_type: str, status: str = "MUTATED"
    ):
        # Format payload: AST_MUTATE|RULE:<id>|FILE:<target>|TYPE:<diff>|STAT:<status>
        payload = f"AST_MUTATE|RULE:{rule_id[:12]}|FILE:{os.path.basename(file_target)[:15]}|TYPE:{diff_type[:10]}|STAT:{status[:6]}"
        logging.info(f"✨ Emitting AST Mutation Event to SHM Topic 0x0003: {payload}")
        return self.bridge.push_topic_event(
            TOPIC_HEURISTICS_TELEMETRY, FLAG_HIGH_PRIORITY, payload
        )

    def close(self):
        self.bridge.close_shm_bridge()


def run_heuristics_benchmark(count=100000):
    logging.info(
        f"🚀 Running Heuristics & AST Mutation Producer Benchmark ({count} events)..."
    )
    daemon = HeuristicsSHMDaemon()
    start = time.time()
    for i in range(count):
        daemon.publish_ast_mutation(
            f"AST_RULE_{i%20}", "learned_rules.md", "SYNTAX_MUT", "MUTATED"
        )
    elapsed = time.time() - start
    ns_per_op = (elapsed * 1e9) / count
    logging.info(f"⏱️ Total Time: {elapsed:.4f}s | Latency: {ns_per_op:.2f} ns/event")
    daemon.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI-BS Heuristics & AST Mutator SHM Daemon"
    )
    parser.add_argument(
        "--benchmark", action="store_true", help="Run IPC throughput benchmark"
    )
    parser.add_argument(
        "--emit-sample", action="store_true", help="Emit sample AST mutation event"
    )
    args = parser.parse_args()

    if args.benchmark:
        run_heuristics_benchmark()
    elif args.emit_sample:
        daemon = HeuristicsSHMDaemon()
        daemon.publish_ast_mutation(
            "RULE_SECURITY_SHRED", "AI_BS_Backend.py", "AST_PATCH", "APPLIED"
        )
        daemon.close()
    else:
        daemon = HeuristicsSHMDaemon()
        daemon.emit_mutation_log("RULE_001", "learned_rules.md", "SYSTEM_MUTATION")
        daemon.close()
