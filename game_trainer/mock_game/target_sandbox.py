"""
AI-BS Game Trainer Suite: Mock Game Sandbox Target
Simulates a real single-player game executable with dynamic heap structures,
multi-level pointer chains, and live entity state for testing game trainers.
"""

import ctypes
import os
import sys
import time

class PlayerData(ctypes.Structure):
    _fields_ = [
        ("health", ctypes.c_int32),
        ("shield", ctypes.c_int32),
        ("ammo", ctypes.c_int32),
        ("score", ctypes.c_int32),
        ("speed", ctypes.c_float),
        ("is_invulnerable", ctypes.c_bool),
        ("player_name", ctypes.c_char * 32),
    ]

class EntityNode(ctypes.Structure):
    pass

EntityNode._fields_ = [
    ("entity_id", ctypes.c_int32),
    ("padding", ctypes.c_int32),
    ("player_ptr", ctypes.POINTER(PlayerData)),
]

class WorldContext(ctypes.Structure):
    _fields_ = [
        ("world_id", ctypes.c_int32),
        ("padding", ctypes.c_int32),
        ("active_entity_ptr", ctypes.POINTER(EntityNode)),
    ]

class GameEngineRoot(ctypes.Structure):
    _fields_ = [
        ("magic_marker", ctypes.c_uint32), # 0xDEADBEEF for signature scan
        ("padding", ctypes.c_uint32),
        ("world_ptr", ctypes.POINTER(WorldContext)),
    ]


GLOBAL_PLAYER = None
GLOBAL_ENTITY = None
GLOBAL_WORLD = None
GLOBAL_ROOT = None

def run_sandbox():
    global GLOBAL_PLAYER, GLOBAL_ENTITY, GLOBAL_WORLD, GLOBAL_ROOT
    pid = os.getpid()
    print("=" * 65)
    print("         AI-BS MOCK GAME SANDBOX: TITAN ARENA (SIMULATOR)")
    print("=" * 65)
    print(f" Process ID (PID)  : {pid}")
    print(f" Executable Target : python.exe (PID {pid})")

    # Allocate mock player struct
    GLOBAL_PLAYER = PlayerData(
        health=100,
        shield=50,
        ammo=30,
        score=0,
        speed=1.0,
        is_invulnerable=False,
        player_name=b"Agent_Titan"
    )
    player = GLOBAL_PLAYER

    # Allocate multi-level pointer chain: Root -> World -> Entity -> Player
    GLOBAL_ENTITY = EntityNode(
        entity_id=1001,
        padding=0,
        player_ptr=ctypes.pointer(GLOBAL_PLAYER)
    )
    entity = GLOBAL_ENTITY

    GLOBAL_WORLD = WorldContext(
        world_id=42,
        padding=0,
        active_entity_ptr=ctypes.pointer(GLOBAL_ENTITY)
    )
    world = GLOBAL_WORLD

    GLOBAL_ROOT = GameEngineRoot(
        magic_marker=0xDEADBEEF,
        padding=0,
        world_ptr=ctypes.pointer(GLOBAL_WORLD)
    )
    root = GLOBAL_ROOT

    player_addr = ctypes.addressof(player)
    entity_addr = ctypes.addressof(entity)
    world_addr = ctypes.addressof(world)
    root_addr = ctypes.addressof(root)

    print(f"\n [ALLOCATED MEMORY HIERARCHY]")
    print(f"  Root Engine Base      : {hex(root_addr)} (Marker: 0xDEADBEEF)")
    print(f"  World Context Addr    : {hex(world_addr)}")
    print(f"  Active Entity Addr    : {hex(entity_addr)}")
    print(f"  Player Direct Addr    : {hex(player_addr)}")
    print(f"\n [POINTER CHAIN TO PLAYER]")
    print(f"  Base Address : {hex(root_addr)}")
    print(f"  Offsets      : [0x8 (world_ptr), 0x8 (active_entity_ptr), 0x8 (player_ptr), 0x0 (health)]")
    print(f"  Offset Vector: [0x8, 0x8, 0x8, 0x0]")
    print("=" * 65)
    print(" Starting Game Simulation Loop (Take damage, fire ammo, gain score)...")
    print(" Press Ctrl+C in this terminal to exit game simulation.\n")

    tick = 0
    try:
        while True:
            time.sleep(1.0)
            tick += 1

            # Simulate gameplay dynamics unless invulnerable
            if not player.is_invulnerable:
                # Simulate taking environmental damage every tick
                player.health = max(0, player.health - 5)
            
            # Simulate weapon firing every 2 ticks
            if tick % 2 == 0 and player.ammo > 0:
                player.ammo -= 1

            # Simulate score increment
            player.score += 25

            # If player died, respawn
            if player.health == 0:
                print("  [!] Player Health reached 0! Respawning with 100 HP...")
                player.health = 100
                player.ammo = 30

            status_color = "GREEN" if player.health > 50 else ("YELLOW" if player.health > 20 else "RED")
            print(f" [Tick {tick:03d}] HP: {player.health:<4} | Shield: {player.shield:<3} | Ammo: {player.ammo:<3} | Score: {player.score:<6} | Name: {player.player_name.decode('utf-8', errors='ignore')}")

    except KeyboardInterrupt:
        print("\n [Simulation Terminated by User]")


if __name__ == "__main__":
    run_sandbox()
